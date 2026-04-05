from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import desc
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models import Analysis, Call, Employee, Transcript
from app.schemas import CallDetail, CallListResponse, CallOut, ReanalyzeRequest
from app.services.storage import storage_service

router = APIRouter(prefix="/api/calls", tags=["calls"])


@router.get("", response_model=CallListResponse)
def list_calls(
    employee_id: Optional[int] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    direction: Optional[str] = None,
    status: Optional[str] = None,
    min_score: Optional[int] = None,
    max_score: Optional[int] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    """List calls with filters."""
    query = db.query(Call).options(
        joinedload(Call.employee),
        joinedload(Call.analysis),
    )

    if employee_id:
        query = query.filter(Call.employee_id == employee_id)
    if date_from:
        query = query.filter(Call.call_date >= datetime.fromisoformat(date_from))
    if date_to:
        query = query.filter(Call.call_date <= datetime.fromisoformat(date_to))
    if direction:
        query = query.filter(Call.direction == direction)
    if status:
        query = query.filter(Call.status == status)
    if min_score is not None or max_score is not None:
        query = query.join(Analysis, Analysis.call_id == Call.id)
        if min_score is not None:
            query = query.filter(Analysis.overall_score >= min_score)
        if max_score is not None:
            query = query.filter(Analysis.overall_score <= max_score)

    total = query.count()
    calls = query.order_by(desc(Call.call_date)).offset((page - 1) * page_size).limit(page_size).all()

    items = []
    for call in calls:
        item = CallOut(
            id=call.id,
            bitrix_call_id=call.bitrix_call_id,
            employee_id=call.employee_id,
            employee_name=call.employee.name if call.employee else None,
            direction=call.direction,
            phone_number=call.phone_number,
            duration_sec=call.duration_sec,
            call_date=call.call_date,
            deal_id=call.deal_id,
            deal_name=call.deal_name,
            deal_stage=call.deal_stage,
            deal_amount=call.deal_amount,
            status=call.status,
            overall_score=call.analysis.overall_score if call.analysis else None,
            who_leads=call.analysis.who_leads if call.analysis else None,
            next_step_agreed=call.analysis.next_step_agreed if call.analysis else None,
        )
        items.append(item)

    return CallListResponse(items=items, total=total, page=page, page_size=page_size)


@router.get("/{call_id}", response_model=CallDetail)
def get_call(call_id: int, db: Session = Depends(get_db)):
    """Get call details with transcript and analysis."""
    call = (
        db.query(Call)
        .options(
            joinedload(Call.employee),
            joinedload(Call.transcript),
            joinedload(Call.analysis),
        )
        .get(call_id)
    )
    if not call:
        raise HTTPException(status_code=404, detail="Call not found")

    audio_url = None
    if call.audio_path:
        audio_url = storage_service.get_audio_url(call.audio_path)

    return CallDetail(
        id=call.id,
        bitrix_call_id=call.bitrix_call_id,
        employee_id=call.employee_id,
        employee_name=call.employee.name if call.employee else None,
        direction=call.direction,
        phone_number=call.phone_number,
        duration_sec=call.duration_sec,
        call_date=call.call_date,
        deal_id=call.deal_id,
        deal_name=call.deal_name,
        deal_stage=call.deal_stage,
        deal_amount=call.deal_amount,
        status=call.status,
        overall_score=call.analysis.overall_score if call.analysis else None,
        who_leads=call.analysis.who_leads if call.analysis else None,
        next_step_agreed=call.analysis.next_step_agreed if call.analysis else None,
        transcript=call.transcript,
        analysis=call.analysis,
        audio_url=audio_url,
    )


@router.post("/{call_id}/reanalyze")
def reanalyze_call(call_id: int, data: ReanalyzeRequest, db: Session = Depends(get_db)):
    """Reanalyze a call with a different sales script."""
    call = db.query(Call).get(call_id)
    if not call:
        raise HTTPException(status_code=404, detail="Call not found")

    transcript = db.query(Transcript).filter_by(call_id=call_id).first()
    if not transcript:
        raise HTTPException(status_code=400, detail="Call has no transcript")

    from app.tasks.analyze_task import analyze_call_task
    analyze_call_task.delay(call_id, data.script_id)

    return {"status": "reanalysis_started", "call_id": call_id}


@router.get("/{call_id}/audio")
def get_audio_url(call_id: int, db: Session = Depends(get_db)):
    """Get presigned URL for call audio."""
    call = db.query(Call).get(call_id)
    if not call:
        raise HTTPException(status_code=404, detail="Call not found")
    if not call.audio_path:
        raise HTTPException(status_code=404, detail="No audio available")

    url = storage_service.get_audio_url(call.audio_path)
    if not url:
        raise HTTPException(status_code=500, detail="Failed to generate audio URL")

    return {"url": url}
