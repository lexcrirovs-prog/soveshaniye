from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Analysis, Call, Employee
from app.schemas import CallOut, EmployeeOut, EmployeeProfile, EmployeeScores

router = APIRouter(prefix="/api/employees", tags=["employees"])


@router.get("", response_model=list[EmployeeOut])
def list_employees(db: Session = Depends(get_db)):
    """List all employees with aggregated stats."""
    employees = db.query(Employee).filter(Employee.is_active == True).all()
    result = []

    for emp in employees:
        total_calls = db.query(Call).filter(Call.employee_id == emp.id).count()
        avg_score = (
            db.query(func.avg(Analysis.overall_score))
            .join(Call, Analysis.call_id == Call.id)
            .filter(Call.employee_id == emp.id)
            .scalar()
        )

        result.append(
            EmployeeOut(
                id=emp.id,
                bitrix_id=emp.bitrix_id,
                name=emp.name,
                department=emp.department,
                position=emp.position,
                is_active=emp.is_active,
                total_calls=total_calls,
                avg_score=round(avg_score, 1) if avg_score else None,
            )
        )

    result.sort(key=lambda x: x.avg_score or 0, reverse=True)
    return result


@router.get("/{employee_id}", response_model=EmployeeProfile)
def get_employee(employee_id: int, db: Session = Depends(get_db)):
    """Get employee profile with aggregated analysis."""
    emp = db.query(Employee).get(employee_id)
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")

    total_calls = db.query(Call).filter(Call.employee_id == emp.id).count()
    avg_score = (
        db.query(func.avg(Analysis.overall_score))
        .join(Call, Analysis.call_id == Call.id)
        .filter(Call.employee_id == emp.id)
        .scalar()
    )

    # Aggregate strengths/weaknesses
    analyses = (
        db.query(Analysis)
        .join(Call, Analysis.call_id == Call.id)
        .filter(Call.employee_id == emp.id)
        .all()
    )

    all_strengths = []
    all_weaknesses = []
    all_recommendations = []
    for a in analyses:
        if a.strengths:
            all_strengths.extend(a.strengths)
        if a.weaknesses:
            all_weaknesses.extend(a.weaknesses)
        if a.recommendations:
            all_recommendations.extend(a.recommendations)

    # Count frequency
    def top_items(items, n=3):
        from collections import Counter
        return [item for item, _ in Counter(items).most_common(n)]

    return EmployeeProfile(
        id=emp.id,
        bitrix_id=emp.bitrix_id,
        name=emp.name,
        department=emp.department,
        position=emp.position,
        is_active=emp.is_active,
        total_calls=total_calls,
        avg_score=round(avg_score, 1) if avg_score else None,
        top_strengths=top_items(all_strengths),
        top_weaknesses=top_items(all_weaknesses),
        development_plan=top_items(all_recommendations),
    )


@router.get("/{employee_id}/calls", response_model=list[CallOut])
def get_employee_calls(
    employee_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    """Get calls for a specific employee."""
    emp = db.query(Employee).get(employee_id)
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")

    calls = (
        db.query(Call)
        .filter(Call.employee_id == employee_id)
        .order_by(Call.call_date.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    result = []
    for call in calls:
        analysis = call.analysis
        result.append(
            CallOut(
                id=call.id,
                bitrix_call_id=call.bitrix_call_id,
                employee_id=call.employee_id,
                employee_name=emp.name,
                direction=call.direction,
                phone_number=call.phone_number,
                duration_sec=call.duration_sec,
                call_date=call.call_date,
                deal_id=call.deal_id,
                deal_name=call.deal_name,
                deal_stage=call.deal_stage,
                deal_amount=call.deal_amount,
                status=call.status,
                overall_score=analysis.overall_score if analysis else None,
                who_leads=analysis.who_leads if analysis else None,
                next_step_agreed=analysis.next_step_agreed if analysis else None,
            )
        )
    return result


@router.get("/{employee_id}/scores", response_model=list[EmployeeScores])
def get_employee_scores(employee_id: int, db: Session = Depends(get_db)):
    """Get weekly score trends for an employee."""
    emp = db.query(Employee).get(employee_id)
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")

    # Get weekly aggregated scores
    results = (
        db.query(
            func.date_trunc("week", Call.call_date).label("week"),
            func.avg(Analysis.greeting_score).label("avg_greeting"),
            func.avg(Analysis.needs_discovery).label("avg_needs_discovery"),
            func.avg(Analysis.presentation_score).label("avg_presentation"),
            func.avg(Analysis.objection_handling).label("avg_objection_handling"),
            func.avg(Analysis.closing_score).label("avg_closing"),
            func.avg(Analysis.initiative_score).label("avg_initiative"),
            func.avg(Analysis.overall_score).label("avg_overall"),
        )
        .join(Call, Analysis.call_id == Call.id)
        .filter(Call.employee_id == employee_id)
        .group_by("week")
        .order_by("week")
        .all()
    )

    return [
        EmployeeScores(
            week=str(r.week.date()) if r.week else "",
            greeting=round(r.avg_greeting, 1) if r.avg_greeting else None,
            needs_discovery=round(r.avg_needs_discovery, 1) if r.avg_needs_discovery else None,
            presentation=round(r.avg_presentation, 1) if r.avg_presentation else None,
            objection_handling=round(r.avg_objection_handling, 1) if r.avg_objection_handling else None,
            closing=round(r.avg_closing, 1) if r.avg_closing else None,
            initiative=round(r.avg_initiative, 1) if r.avg_initiative else None,
            overall=round(r.avg_overall, 1) if r.avg_overall else None,
        )
        for r in results
    ]
