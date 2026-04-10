"""Bitrix24 webhook endpoint for real-time call processing.

Bitrix24 can send webhook notifications when a call ends.
Configure in Bitrix24: Settings -> Webhooks -> Add outbound webhook
Event: ONVOXIMPLANTCALLEND
URL: https://your-server/api/webhooks/bitrix24/call-end
"""
import logging

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Call, Employee
from app.services.bitrix import BitrixClient, _parse_datetime
from app.services.storage import storage_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/webhooks", tags=["webhooks"])


@router.post("/bitrix24/call-end")
async def bitrix24_call_end(request: Request, db: Session = Depends(get_db)):
    """
    Handle Bitrix24 ONVOXIMPLANTCALLEND webhook.

    When a call ends in Bitrix24, this endpoint receives the event,
    fetches call details, downloads audio, and launches the processing pipeline.
    """
    try:
        body = await request.json()
    except Exception:
        body = dict(await request.form())

    logger.info("Bitrix24 webhook received: %s", body)

    # Extract data from webhook payload
    data = body.get("data", body)
    call_id = data.get("CALL_ID") or data.get("call_id")

    if not call_id:
        return {"status": "ignored", "reason": "no call_id"}

    # Check if already processed
    existing = db.query(Call).filter_by(bitrix_call_id=str(call_id)).first()
    if existing:
        return {"status": "already_processed", "call_id": existing.id}

    # Fetch full call details from Bitrix24
    bitrix = BitrixClient()
    try:
        params = {"FILTER": {"ID": call_id}}
        result = bitrix._call("voximplant.statistic.get", params)
        items = result.get("result", [])
        if not items:
            return {"status": "call_not_found"}

        call_data = items[0]
        call_type = int(call_data.get("CALL_TYPE", 0))
        direction = "incoming" if call_type == 2 else "outgoing"
        portal_user_id = int(call_data.get("PORTAL_USER_ID", 0))
        phone = call_data.get("PHONE_NUMBER", "")
        duration = int(call_data.get("CALL_DURATION", 0))
        record_url = call_data.get("RECORD_URL", "")

        # Skip very short calls (< 30 sec)
        if duration < 30:
            return {"status": "ignored", "reason": "too_short", "duration": duration}

        # Find employee
        employee = db.query(Employee).filter_by(bitrix_id=portal_user_id).first()

        # Find linked deal
        deal_info = None
        if phone:
            deals = bitrix.find_deals_by_phone(phone)
            if deals:
                deal_info = deals[0]

        # Create call record
        call = Call(
            bitrix_call_id=str(call_id),
            employee_id=employee.id if employee else None,
            direction=direction,
            phone_number=phone,
            duration_sec=duration,
            call_date=_parse_datetime(call_data.get("CALL_START_DATE", "")),
            deal_id=deal_info["id"] if deal_info else None,
            deal_name=deal_info["title"] if deal_info else None,
            deal_stage=deal_info["stage_id"] if deal_info else None,
            deal_amount=deal_info["opportunity"] if deal_info else None,
            status="new",
        )
        db.add(call)
        db.flush()

        # Download and upload audio
        if record_url:
            audio_data = bitrix.download_audio(record_url)
            if audio_data:
                audio_path = storage_service.upload_audio(str(call.id), audio_data)
                call.audio_path = audio_path
                call.status = "audio_downloaded"

        db.commit()

        # Launch transcription pipeline
        if call.audio_path:
            from app.tasks.transcribe_task import transcribe_call
            transcribe_call.delay(call.id)

        logger.info(
            "Webhook processed: call_id=%s, db_id=%d, employee=%s",
            call_id, call.id, employee.name if employee else "unknown",
        )

        return {"status": "processing", "call_id": call.id}

    except Exception as e:
        logger.exception("Webhook processing failed: %s", e)
        return {"status": "error", "message": str(e)}
    finally:
        bitrix.close()
