from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Call, ExportJob
from app.schemas import ExportJobCreate, ExportJobOut
from app.services.bitrix import get_period_dates
from app.services.storage import storage_service

router = APIRouter(prefix="/api/exports", tags=["exports"])


@router.post("", response_model=ExportJobOut)
def create_export(data: ExportJobCreate, db: Session = Depends(get_db)):
    """Start a new export job."""
    date_from, date_to = get_period_dates(data.period)

    job = ExportJob(
        period=data.period,
        date_from=date_from,
        date_to=date_to,
        department_id=data.department_id,
        status="pending",
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    from app.tasks.export_task import export_calls
    export_calls.delay(data.period, data.department_id, job.id)

    return job


@router.get("", response_model=list[ExportJobOut])
def list_exports(db: Session = Depends(get_db)):
    """List all export jobs."""
    return db.query(ExportJob).order_by(ExportJob.created_at.desc()).all()


@router.get("/{job_id}", response_model=ExportJobOut)
def get_export(job_id: int, db: Session = Depends(get_db)):
    """Get export job status."""
    job = db.query(ExportJob).get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Export job not found")
    return job


@router.post("/{job_id}/cancel")
def cancel_export(job_id: int, db: Session = Depends(get_db)):
    """Cancel a running export job."""
    job = db.query(ExportJob).get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Export job not found")
    if job.status in ("completed", "failed", "cancelled"):
        raise HTTPException(status_code=400, detail=f"Job already {job.status}")

    job.status = "cancelled"
    job.finished_at = datetime.now()
    db.commit()

    # Purge pending Celery tasks for this job's calls
    from app.tasks.celery_app import celery_app
    celery_app.control.purge()

    return {"status": "cancelled", "job_id": job.id}


@router.get("/{job_id}/report")
def download_report(job_id: int, db: Session = Depends(get_db)):
    """Get download URL for export report."""
    job = db.query(ExportJob).get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Export job not found")
    if not job.report_path:
        raise HTTPException(status_code=404, detail="Report not yet generated")

    url = storage_service.get_report_url(job.report_path)
    if not url:
        raise HTTPException(status_code=500, detail="Failed to generate download URL")

    return {"url": url}
