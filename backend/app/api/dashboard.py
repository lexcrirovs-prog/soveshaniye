from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Analysis, Call, Employee
from app.schemas import DashboardSummary, EmployeeRanking, TrendPoint
from app.services.bitrix import get_period_dates

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


def _parse_period(period: Optional[str], date_from: Optional[str], date_to: Optional[str]):
    """Parse period filter into datetime range."""
    if date_from and date_to:
        return datetime.fromisoformat(date_from), datetime.fromisoformat(date_to)
    if period:
        return get_period_dates(period)
    return get_period_dates("30d")


@router.get("/summary", response_model=DashboardSummary)
def get_summary(
    period: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    employee_id: Optional[int] = None,
    db: Session = Depends(get_db),
):
    """Get dashboard summary stats."""
    d_from, d_to = _parse_period(period, date_from, date_to)

    calls_q = db.query(Call).filter(Call.call_date >= d_from, Call.call_date <= d_to)
    if employee_id:
        calls_q = calls_q.filter(Call.employee_id == employee_id)

    total_calls = calls_q.count()

    total_employees = (
        db.query(func.count(func.distinct(Call.employee_id)))
        .filter(Call.call_date >= d_from, Call.call_date <= d_to)
        .scalar()
    ) or 0

    total_deals = (
        db.query(func.count(func.distinct(Call.deal_id)))
        .filter(Call.call_date >= d_from, Call.call_date <= d_to, Call.deal_id.isnot(None))
        .scalar()
    ) or 0

    # Average score
    score_q = (
        db.query(func.avg(Analysis.overall_score))
        .join(Call, Analysis.call_id == Call.id)
        .filter(Call.call_date >= d_from, Call.call_date <= d_to)
    )
    if employee_id:
        score_q = score_q.filter(Call.employee_id == employee_id)
    avg_score = score_q.scalar()

    # Average duration
    dur_q = db.query(func.avg(Call.duration_sec)).filter(
        Call.call_date >= d_from, Call.call_date <= d_to
    )
    if employee_id:
        dur_q = dur_q.filter(Call.employee_id == employee_id)
    avg_duration = dur_q.scalar()

    # Next step stats
    next_step_q = (
        db.query(Analysis.next_step_agreed, func.count())
        .join(Call, Analysis.call_id == Call.id)
        .filter(Call.call_date >= d_from, Call.call_date <= d_to)
    )
    if employee_id:
        next_step_q = next_step_q.filter(Call.employee_id == employee_id)
    next_step_stats = dict(next_step_q.group_by(Analysis.next_step_agreed).all())

    return DashboardSummary(
        total_calls=total_calls,
        total_employees=total_employees,
        total_deals=total_deals,
        avg_score=round(avg_score, 1) if avg_score else None,
        avg_duration=round(avg_duration, 0) if avg_duration else None,
        calls_with_next_step=next_step_stats.get(True, 0),
        calls_without_next_step=next_step_stats.get(False, 0),
    )


@router.get("/scores", response_model=list[EmployeeRanking])
def get_scores(
    period: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """Get employee rankings by scores."""
    d_from, d_to = _parse_period(period, date_from, date_to)

    results = (
        db.query(
            Employee.id,
            Employee.name,
            func.count(Call.id).label("total_calls"),
            func.avg(Analysis.greeting_score).label("avg_greeting"),
            func.avg(Analysis.needs_discovery).label("avg_needs_discovery"),
            func.avg(Analysis.presentation_score).label("avg_presentation"),
            func.avg(Analysis.objection_handling).label("avg_objection_handling"),
            func.avg(Analysis.closing_score).label("avg_closing"),
            func.avg(Analysis.initiative_score).label("avg_initiative"),
            func.avg(Analysis.overall_score).label("avg_overall"),
        )
        .join(Call, Call.employee_id == Employee.id)
        .join(Analysis, Analysis.call_id == Call.id)
        .filter(Call.call_date >= d_from, Call.call_date <= d_to)
        .group_by(Employee.id, Employee.name)
        .order_by(func.avg(Analysis.overall_score).desc())
        .all()
    )

    return [
        EmployeeRanking(
            employee_id=r.id,
            name=r.name,
            total_calls=r.total_calls,
            avg_greeting=round(r.avg_greeting, 1) if r.avg_greeting else None,
            avg_needs_discovery=round(r.avg_needs_discovery, 1) if r.avg_needs_discovery else None,
            avg_presentation=round(r.avg_presentation, 1) if r.avg_presentation else None,
            avg_objection_handling=round(r.avg_objection_handling, 1) if r.avg_objection_handling else None,
            avg_closing=round(r.avg_closing, 1) if r.avg_closing else None,
            avg_initiative=round(r.avg_initiative, 1) if r.avg_initiative else None,
            avg_overall=round(r.avg_overall, 1) if r.avg_overall else None,
        )
        for r in results
    ]


@router.get("/trends", response_model=list[TrendPoint])
def get_trends(
    period: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    employee_id: Optional[int] = None,
    db: Session = Depends(get_db),
):
    """Get weekly score trends."""
    d_from, d_to = _parse_period(period, date_from, date_to)

    query = (
        db.query(
            func.date_trunc("week", Call.call_date).label("week"),
            func.avg(Analysis.overall_score).label("avg_score"),
            func.count(Call.id).label("total_calls"),
        )
        .join(Analysis, Analysis.call_id == Call.id)
        .filter(Call.call_date >= d_from, Call.call_date <= d_to)
    )

    if employee_id:
        query = query.filter(Call.employee_id == employee_id)

    results = query.group_by("week").order_by("week").all()

    return [
        TrendPoint(
            week=str(r.week.date()) if r.week else "",
            avg_score=round(r.avg_score, 1) if r.avg_score else None,
            total_calls=r.total_calls,
        )
        for r in results
    ]
