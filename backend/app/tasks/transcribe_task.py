import logging

from sqlalchemy import update

from app.database import SessionLocal
from app.models import Call, ExportJob, Transcript
from app.services.storage import storage_service
from app.services.transcriber import transcribe
from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


def _increment_transcribed(db, call: Call):
    """Atomically increment transcribed counter on the export job."""
    if not call.export_job_id:
        return
    db.execute(
        update(ExportJob)
        .where(ExportJob.id == call.export_job_id)
        .values(transcribed=ExportJob.transcribed + 1)
    )
    job = db.query(ExportJob).get(call.export_job_id)
    if job and job.status in ("running", "transcribing"):
        job.status = "transcribing"
    db.commit()


def _get_whisper_provider(db, call: Call) -> str:
    """Get whisper provider from the export job."""
    if call.export_job_id:
        job = db.query(ExportJob).get(call.export_job_id)
        if job and job.whisper_provider:
            return job.whisper_provider
    return "openai"


@celery_app.task(name="app.tasks.transcribe_task.transcribe_call", bind=True, max_retries=2)
def transcribe_call(self, call_id: int):
    """Transcribe a single call audio file."""
    db = SessionLocal()

    try:
        call = db.query(Call).get(call_id)
        if not call:
            logger.error("Call %d not found", call_id)
            return

        # Check if job was cancelled
        if call.export_job_id:
            job = db.query(ExportJob).get(call.export_job_id)
            if job and job.status == "cancelled":
                logger.info("Skipping call %d — job %d cancelled", call_id, job.id)
                return

        if not call.audio_path:
            logger.error("Call %d has no audio", call_id)
            _increment_transcribed(db, call)
            return

        # Skip if already transcribed
        existing = db.query(Transcript).filter_by(call_id=call_id).first()
        if existing:
            logger.info("Call %d already transcribed, triggering analysis", call_id)
            _increment_transcribed(db, call)
            from app.tasks.analyze_task import analyze_call_task
            analyze_call_task.delay(call_id)
            return

        # Download audio from MinIO
        logger.info("Downloading audio for call %d from MinIO...", call_id)
        audio_data = storage_service.download_audio(call.audio_path)
        if not audio_data:
            logger.error("Failed to download audio for call %d (path: %s)", call_id, call.audio_path)
            call.status = "transcription_failed"
            _increment_transcribed(db, call)
            return

        logger.info("Audio downloaded for call %d: %d bytes", call_id, len(audio_data))

        # Get whisper provider from job
        provider = _get_whisper_provider(db, call)

        # Transcribe
        call.status = "transcribing"
        db.commit()

        logger.info("Starting transcription for call %d via %s...", call_id, provider)
        result = transcribe(audio_data, provider=provider)

        if not result:
            logger.error("Transcription returned None for call %d via %s", call_id, provider)
            call.status = "transcription_failed"
            _increment_transcribed(db, call)
            return

        if not result.get("text"):
            logger.warning("Transcription returned empty text for call %d", call_id)

        # Save transcript
        transcript = Transcript(
            call_id=call_id,
            text=result["text"],
            language=result["language"],
            model_used=f"whisper-1-{provider}" if provider == "openai" else "faster-whisper",
            confidence=result["confidence"],
            segments=result["segments"],
        )
        db.add(transcript)
        call.status = "transcribed"
        _increment_transcribed(db, call)

        logger.info("Transcribed call %d via %s: %d chars", call_id, provider, len(result["text"]))

        # Trigger analysis
        from app.tasks.analyze_task import analyze_call_task
        analyze_call_task.delay(call_id)

    except Exception as e:
        logger.exception("Transcription failed for call %d: %s", call_id, e)
        try:
            call = db.query(Call).get(call_id)
            if call:
                call.status = "transcription_failed"
                _increment_transcribed(db, call)
        except Exception:
            pass
        raise self.retry(exc=e, countdown=60)
    finally:
        db.close()
