import logging
from datetime import datetime

from app.database import SessionLocal
from app.models import Call, Employee, ExportJob
from app.services.bitrix import BitrixClient, get_period_dates
from app.services.storage import storage_service
from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="app.tasks.export_task.export_calls", bind=True)
def export_calls(self, period: str, department_id: int | None = None, job_id: int | None = None):
    """
    Main export pipeline:
    1. Get employees from Bitrix24
    2. Get calls for period
    3. Link calls to deals
    4. Download audio to MinIO
    """
    db = SessionLocal()
    bitrix = BitrixClient()

    try:
        # Get or create export job
        if job_id:
            job = db.query(ExportJob).get(job_id)
        else:
            date_from, date_to = get_period_dates(period)
            job = ExportJob(
                period=period,
                date_from=date_from,
                date_to=date_to,
                department_id=department_id,
                status="running",
                started_at=datetime.now(),
            )
            db.add(job)
            db.commit()
            db.refresh(job)

        job.status = "running"
        job.started_at = datetime.now()
        db.commit()

        date_from, date_to = job.date_from, job.date_to

        # Step 1: Sync employees
        logger.info("Fetching employees from Bitrix24...")
        bx_employees = bitrix.get_employees(department_id)
        employee_map = {}  # bitrix_id -> db employee

        for emp_data in bx_employees:
            existing = db.query(Employee).filter_by(bitrix_id=emp_data["bitrix_id"]).first()
            if existing:
                existing.name = emp_data["name"]
                existing.position = emp_data["position"]
                existing.department = emp_data["department"]
                employee_map[emp_data["bitrix_id"]] = existing
            else:
                emp = Employee(**emp_data)
                db.add(emp)
                db.flush()
                employee_map[emp_data["bitrix_id"]] = emp

        db.commit()
        logger.info("Synced %d employees", len(employee_map))

        # Step 2: Fetch calls
        logger.info("Fetching calls from Bitrix24 for %s to %s...", date_from, date_to)
        bx_calls = bitrix.get_calls(date_from, date_to)
        job.total_calls = len(bx_calls)
        db.commit()
        logger.info("Found %d calls", len(bx_calls))

        # Step 3: Process each call
        processed = 0
        phone_deal_cache: dict[str, dict | None] = {}

        for bx_call in bx_calls:
            # Skip if already exists
            existing = db.query(Call).filter_by(bitrix_call_id=bx_call["bitrix_call_id"]).first()
            if existing:
                processed += 1
                continue

            # Find employee
            employee = employee_map.get(bx_call["portal_user_id"])
            if not employee:
                # Try to find in DB
                employee = db.query(Employee).filter_by(bitrix_id=bx_call["portal_user_id"]).first()

            # Link to deal via phone
            phone = bx_call.get("phone_number", "")
            deal_info = None
            if phone:
                if phone not in phone_deal_cache:
                    try:
                        deals = bitrix.find_deals_by_phone(phone)
                        phone_deal_cache[phone] = deals[0] if deals else None
                    except Exception:
                        phone_deal_cache[phone] = None
                deal_info = phone_deal_cache.get(phone)

            # Create call record
            call = Call(
                bitrix_call_id=bx_call["bitrix_call_id"],
                employee_id=employee.id if employee else None,
                direction=bx_call["direction"],
                phone_number=phone,
                duration_sec=bx_call["duration_sec"],
                call_date=bx_call["call_date"],
                deal_id=deal_info["id"] if deal_info else None,
                deal_name=deal_info["title"] if deal_info else None,
                deal_stage=deal_info["stage_id"] if deal_info else None,
                deal_amount=deal_info["opportunity"] if deal_info else None,
                status="new",
                export_job_id=job.id,
            )
            db.add(call)
            db.flush()

            # Download and upload audio
            record_url = bx_call.get("record_url", "")
            if record_url:
                try:
                    audio_data = bitrix.download_audio(record_url)
                    if audio_data:
                        audio_path = storage_service.upload_audio(str(call.id), audio_data)
                        call.audio_path = audio_path
                        call.status = "audio_downloaded"
                except Exception as e:
                    logger.error("Failed to download audio for call %s: %s", call.bitrix_call_id, e)

            processed += 1
            job.processed = processed
            if processed % 10 == 0:
                db.commit()
                logger.info("Processed %d/%d calls", processed, job.total_calls)

        db.commit()

        # Step 4: Launch transcription + analysis tasks for new calls
        from app.tasks.transcribe_task import transcribe_call

        new_calls = (
            db.query(Call)
            .filter(Call.export_job_id == job.id, Call.audio_path.isnot(None))
            .all()
        )
        for call in new_calls:
            transcribe_call.delay(call.id)

        job.status = "transcribing"
        db.commit()
        logger.info("Export complete. %d calls sent for transcription.", len(new_calls))

    except Exception as e:
        logger.exception("Export failed: %s", e)
        if job:
            job.status = "failed"
            job.error_msg = str(e)
            db.commit()
        raise
    finally:
        bitrix.close()
        db.close()

    return {"job_id": job.id, "total_calls": job.total_calls, "processed": processed}
