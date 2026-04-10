import logging
from collections import defaultdict
from datetime import datetime

from sqlalchemy import func

from app.database import SessionLocal
from app.models import Analysis, Call, Employee, ExportJob, Transcript
from app.services.analyzer import aggregate_department, aggregate_employee
from app.services.report import generate_report
from app.services.storage import storage_service
from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="app.tasks.report_task.generate_report_task", bind=True)
def generate_report_task(self, job_id: int):
    """Generate Excel report for a completed export job."""
    db = SessionLocal()

    try:
        job = db.query(ExportJob).get(job_id)
        if not job:
            logger.error("Job %d not found", job_id)
            return

        # Get all analyzed calls for this job
        calls_query = (
            db.query(Call, Employee, Analysis, Transcript)
            .outerjoin(Employee, Call.employee_id == Employee.id)
            .outerjoin(Analysis, Analysis.call_id == Call.id)
            .outerjoin(Transcript, Transcript.call_id == Call.id)
            .filter(Call.export_job_id == job_id)
            .all()
        )

        if not calls_query:
            job.status = "completed"
            job.finished_at = datetime.now()
            db.commit()
            return

        # Prepare data structures
        calls_data = []
        transcripts_data = []
        detailed_analyses = []
        employee_analyses = defaultdict(list)
        deal_calls = defaultdict(list)

        for call, employee, analysis, transcript in calls_query:
            emp_name = employee.name if employee else "Неизвестный"

            call_info = {
                "call_id": call.id,
                "call_date": str(call.call_date),
                "employee_name": emp_name,
                "direction": "входящий" if call.direction == "incoming" else "исходящий",
                "phone_number": call.phone_number or "",
                "duration_sec": call.duration_sec,
                "deal_name": call.deal_name or "",
                "overall_score": analysis.overall_score if analysis else "",
                "who_leads": analysis.who_leads if analysis else "",
                "next_step_agreed": analysis.next_step_agreed if analysis else False,
            }
            calls_data.append(call_info)

            if transcript:
                transcripts_data.append({
                    "call_id": call.id,
                    "employee_name": emp_name,
                    "deal_name": call.deal_name or "",
                    "text": transcript.text,
                })

            if analysis:
                analysis_info = {
                    "call_id": call.id,
                    "employee_name": emp_name,
                    "greeting_score": analysis.greeting_score,
                    "needs_discovery": analysis.needs_discovery,
                    "presentation_score": analysis.presentation_score,
                    "objection_handling": analysis.objection_handling,
                    "closing_score": analysis.closing_score,
                    "initiative_score": analysis.initiative_score,
                    "overall_score": analysis.overall_score,
                    "strengths": analysis.strengths or [],
                    "weaknesses": analysis.weaknesses or [],
                    "recommendations": analysis.recommendations or [],
                    "missed_script_steps": analysis.missed_script_steps or [],
                    "crm_note_suggestion": analysis.crm_note_suggestion or "",
                    "summary": analysis.summary or "",
                    "who_leads": analysis.who_leads or "",
                    "next_step_agreed": analysis.next_step_agreed,
                }
                detailed_analyses.append(analysis_info)

                if employee:
                    employee_analyses[employee.id].append(analysis_info)

                if call.deal_name:
                    deal_calls[call.deal_name].append((call, analysis))

        # Aggregate employee profiles
        employee_rankings = []
        employee_profiles = []
        for emp_id, analyses_list in employee_analyses.items():
            emp = db.query(Employee).get(emp_id)
            if not emp:
                continue

            # Calculate averages
            score_fields = [
                "greeting_score", "needs_discovery", "presentation_score",
                "objection_handling", "closing_score", "initiative_score", "overall_score",
            ]
            avgs = {}
            for field in score_fields:
                values = [a[field] for a in analyses_list if a[field] is not None]
                avgs[field] = round(sum(values) / len(values), 1) if values else None

            ranking_entry = {
                "employee_id": emp.id,
                "name": emp.name,
                "total_calls": len(analyses_list),
                "avg_greeting": avgs.get("greeting_score"),
                "avg_needs_discovery": avgs.get("needs_discovery"),
                "avg_presentation": avgs.get("presentation_score"),
                "avg_objection_handling": avgs.get("objection_handling"),
                "avg_closing": avgs.get("closing_score"),
                "avg_initiative": avgs.get("initiative_score"),
                "avg_overall": avgs.get("overall_score"),
                "priority_training": "",
            }

            # LLM aggregation for employee profile
            profile = aggregate_employee(
                analyses_list,
                emp.name,
                str(job.date_from),
                str(job.date_to),
            )
            if profile:
                ranking_entry["priority_training"] = profile.get("priority_training", "")
                employee_profiles.append({
                    "name": emp.name,
                    "total_calls": len(analyses_list),
                    **profile,
                })

            employee_rankings.append(ranking_entry)

        # Sort by overall score desc
        employee_rankings.sort(key=lambda x: x.get("avg_overall") or 0, reverse=True)

        # Deal analyses
        deal_analyses_data = []
        for deal_name, deal_data in deal_calls.items():
            calls_in_deal, analyses_in_deal = zip(*deal_data)
            total_dur = sum(c.duration_sec for c in calls_in_deal)
            scores = [a.overall_score for a in analyses_in_deal if a.overall_score]
            problems = set()
            for a in analyses_in_deal:
                if a.weaknesses:
                    for w in a.weaknesses[:2]:
                        problems.add(w)

            deal_analyses_data.append({
                "deal_name": deal_name,
                "employee_name": calls_in_deal[0].employee.name if calls_in_deal[0].employee else "",
                "call_count": len(calls_in_deal),
                "total_duration": total_dur,
                "stage": calls_in_deal[0].deal_stage or "",
                "avg_score": round(sum(scores) / len(scores), 1) if scores else "",
                "problems": list(problems)[:3],
            })

        # Department aggregate
        dept_analysis = aggregate_department(employee_profiles) if employee_profiles else {}

        # Build recommendations
        recommendations_data = []
        if dept_analysis:
            for i, problem in enumerate(dept_analysis.get("systemic_problems", []), 1):
                recommendations_data.append({
                    "priority": i,
                    "category": "Системная проблема",
                    "problem": problem,
                    "affected_employees": "Весь отдел",
                    "recommendation": dept_analysis.get("priority_actions", [""])[i - 1]
                    if i <= len(dept_analysis.get("priority_actions", []))
                    else "",
                    "expected_effect": "Повышение конверсии",
                })

        # Summary
        all_scores = [a["overall_score"] for a in detailed_analyses if a["overall_score"]]
        summary = {
            "period": f"{job.date_from} — {job.date_to}",
            "total_calls": len(calls_data),
            "total_employees": len(employee_rankings),
            "total_deals": len(deal_calls),
            "avg_score": round(sum(all_scores) / len(all_scores), 1) if all_scores else None,
            "avg_duration": round(
                sum(c["duration_sec"] for c in calls_data) / len(calls_data), 0
            )
            if calls_data
            else None,
            "calls_with_next_step": sum(1 for c in calls_data if c["next_step_agreed"]),
            "calls_without_next_step": sum(1 for c in calls_data if not c["next_step_agreed"]),
            "top_problems": dept_analysis.get("systemic_problems", [])[:3] if dept_analysis else [],
            "top_recommendations": dept_analysis.get("priority_actions", [])[:3] if dept_analysis else [],
        }

        # Generate Excel
        report_bytes = generate_report(
            summary=summary,
            employee_rankings=employee_rankings,
            calls=calls_data,
            transcripts=transcripts_data,
            deal_analyses=deal_analyses_data,
            detailed_analyses=detailed_analyses,
            recommendations=recommendations_data,
        )

        # Upload report to MinIO
        report_path = storage_service.upload_report(job_id, report_bytes)

        job.status = "completed"
        job.finished_at = datetime.now()
        job.report_path = report_path
        db.commit()

        logger.info("Report generated for job %d: %s", job_id, report_path)

        # Send notifications
        _send_report_notifications(job, summary, report_bytes)

    except Exception as e:
        logger.exception("Report generation failed for job %d: %s", job_id, e)
        try:
            job = db.query(ExportJob).get(job_id)
            if job:
                job.status = "report_failed"
                job.error_msg = str(e)
                db.commit()
        except Exception:
            pass
        raise
    finally:
        db.close()


def _send_report_notifications(job, summary: dict, report_bytes: bytes):
    """Send Telegram and email notifications about completed report."""
    from app.config import settings

    # Telegram
    if settings.telegram_notifications:
        try:
            from app.services.telegram import notify_export_completed

            notify_export_completed(
                job_id=job.id,
                period=summary.get("period", job.period),
                total_calls=summary.get("total_calls", 0),
                avg_score=summary.get("avg_score"),
            )
        except Exception as e:
            logger.error("Telegram notification failed: %s", e)

    # Email
    if settings.email_notifications and settings.notify_email_to:
        try:
            from app.services.email_notify import send_weekly_report

            recipients = [e.strip() for e in settings.notify_email_to.split(",") if e.strip()]
            send_weekly_report(
                to_emails=recipients,
                period=summary.get("period", job.period),
                total_calls=summary.get("total_calls", 0),
                avg_score=summary.get("avg_score"),
                top_problems=summary.get("top_problems", []),
                report_bytes=report_bytes,
            )
        except Exception as e:
            logger.error("Email notification failed: %s", e)
