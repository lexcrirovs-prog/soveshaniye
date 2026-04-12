import logging

from sqlalchemy import update

from app.database import SessionLocal
from app.models import Analysis, Call, ExportJob, SalesScript, Transcript
from app.services.analyzer import analyze_call
from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="app.tasks.analyze_task.analyze_call_task", bind=True, max_retries=2)
def analyze_call_task(self, call_id: int, script_id: int | None = None):
    """Analyze a single call transcript using Claude API."""
    db = SessionLocal()

    try:
        call = db.query(Call).get(call_id)
        if not call:
            logger.error("Call %d not found", call_id)
            return

        transcript = db.query(Transcript).filter_by(call_id=call_id).first()
        if not transcript:
            logger.error("No transcript for call %d", call_id)
            return

        # Get sales script if specified or use active one
        sales_script_content = None
        actual_script_id = script_id
        if not script_id:
            active_script = db.query(SalesScript).filter_by(is_active=True).first()
            if active_script:
                sales_script_content = active_script.content
                actual_script_id = active_script.id
        else:
            script = db.query(SalesScript).get(script_id)
            if script:
                sales_script_content = script.content

        # Get employee name
        employee_name = "Неизвестный"
        if call.employee:
            employee_name = call.employee.name

        call.status = "analyzing"
        db.commit()

        # Run analysis
        result = analyze_call(
            transcript=transcript.text,
            employee_name=employee_name,
            direction=call.direction,
            duration=call.duration_sec,
            deal_name=call.deal_name or "Не указана",
            stage=call.deal_stage or "Не указана",
            sales_script=sales_script_content,
        )

        if not result:
            call.status = "analysis_failed"
            db.commit()
            return

        # Delete existing analysis if reanalyzing
        existing = db.query(Analysis).filter_by(call_id=call_id).first()
        if existing:
            db.delete(existing)
            db.flush()

        scores = result.get("scores", {})
        analysis = Analysis(
            call_id=call_id,
            script_id=actual_script_id,
            greeting_score=scores.get("greeting"),
            needs_discovery=scores.get("needs_discovery"),
            presentation_score=scores.get("presentation"),
            objection_handling=scores.get("objection_handling"),
            closing_score=scores.get("closing"),
            initiative_score=scores.get("initiative"),
            overall_score=scores.get("overall"),
            summary=result.get("summary"),
            strengths=result.get("strengths"),
            weaknesses=result.get("weaknesses"),
            recommendations=result.get("recommendations"),
            missed_script_steps=result.get("missed_script_steps"),
            who_leads=result.get("who_leads"),
            next_step_agreed=result.get("next_step_agreed"),
            crm_note_suggestion=result.get("crm_note_suggestion"),
            raw_response=result.get("_raw_response"),
            model_used=result.get("_model_used"),
        )
        db.add(analysis)
        call.status = "analyzed"
        db.commit()

        logger.info("Analyzed call %d: overall_score=%s", call_id, scores.get("overall"))

        # Post-analysis integrations
        _post_analysis_integrations(call, analysis, employee_name)

        # Check if all calls in export job are analyzed
        _check_job_completion(db, call)

    except Exception as e:
        logger.exception("Analysis failed for call %d: %s", call_id, e)
        try:
            call = db.query(Call).get(call_id)
            if call:
                call.status = "analysis_failed"
                db.commit()
        except Exception:
            pass
        raise self.retry(exc=e, countdown=120)
    finally:
        db.close()


def _post_analysis_integrations(call: Call, analysis: Analysis, employee_name: str):
    """Run post-analysis integrations: Telegram, CRM."""
    from app.config import settings

    overall = analysis.overall_score or 0

    # Telegram notification
    if settings.telegram_notifications:
        try:
            from app.services.telegram import notify_call_analyzed, notify_low_score

            notify_call_analyzed(
                employee_name=employee_name,
                direction=call.direction,
                duration_sec=call.duration_sec,
                overall_score=overall,
                deal_name=call.deal_name or "",
                summary=analysis.summary or "",
                call_id=call.id,
            )

            if overall < settings.low_score_alert_threshold:
                notify_low_score(
                    employee_name=employee_name,
                    call_id=call.id,
                    overall_score=overall,
                    weaknesses=analysis.weaknesses or [],
                )
        except Exception as e:
            logger.error("Telegram notification failed: %s", e)

    # CRM auto-comment
    if settings.crm_auto_comment and call.deal_id:
        try:
            from app.services.crm_integration import post_analysis_to_crm

            employee_bitrix_id = call.employee.bitrix_id if call.employee else None
            post_analysis_to_crm(
                deal_id=call.deal_id,
                employee_bitrix_id=employee_bitrix_id,
                employee_name=employee_name,
                direction=call.direction,
                overall_score=overall,
                summary=analysis.summary or "",
                crm_note=analysis.crm_note_suggestion or "",
                strengths=analysis.strengths or [],
                weaknesses=analysis.weaknesses or [],
                next_step_agreed=analysis.next_step_agreed or False,
                recommendations=analysis.recommendations or [],
            )
        except Exception as e:
            logger.error("CRM integration failed: %s", e)


def _check_job_completion(db, call: Call):
    """Increment analyzed counter, check if all done, trigger report."""
    if not call.export_job_id:
        return

    # Atomically increment analyzed counter
    db.execute(
        update(ExportJob)
        .where(ExportJob.id == call.export_job_id)
        .values(analyzed=ExportJob.analyzed + 1)
    )
    db.commit()

    # Refresh to get current values
    job = db.query(ExportJob).get(call.export_job_id)
    if not job:
        return

    # Update status to analyzing if not already
    if job.status in ("transcribing", "analyzing"):
        job.status = "analyzing"
        db.commit()

    total = db.query(Call).filter(Call.export_job_id == job.id).count()
    if job.analyzed >= total:
        job.status = "generating_report"
        db.commit()

        from app.tasks.report_task import generate_report_task
        generate_report_task.delay(job.id)
