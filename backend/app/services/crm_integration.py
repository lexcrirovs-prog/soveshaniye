"""CRM integration: auto-write analysis notes to Bitrix24 deals and activities.

After a call is analyzed, this service can:
1. Add a comment to the linked deal with the analysis summary
2. Create a CRM activity with the CRM note suggestion
"""
import logging
from typing import Optional

from app.config import settings
from app.services.bitrix import BitrixClient

logger = logging.getLogger(__name__)


def add_deal_comment(
    deal_id: int,
    employee_name: str,
    direction: str,
    overall_score: int,
    summary: str,
    crm_note: str,
    strengths: list[str],
    weaknesses: list[str],
) -> bool:
    """Add a comment to a Bitrix24 deal with call analysis."""
    if not settings.bitrix_webhook_url:
        return False

    direction_ru = "Входящий" if direction == "incoming" else "Исходящий"

    # Score indicator
    if overall_score >= 7:
        indicator = "🟢"
    elif overall_score >= 4:
        indicator = "🟡"
    else:
        indicator = "🔴"

    comment_parts = [
        f"📞 Анализ звонка",
        f"",
        f"Менеджер: {employee_name}",
        f"Направление: {direction_ru}",
        f"{indicator} Оценка: {overall_score}/10",
        f"",
        f"Резюме: {summary}",
    ]

    if crm_note:
        comment_parts.extend(["", "📝 Заметка:", crm_note])

    if strengths:
        comment_parts.extend(["", "✅ Сильные стороны:"])
        for s in strengths[:3]:
            comment_parts.append(f"  • {s}")

    if weaknesses:
        comment_parts.extend(["", "⚠️ Зоны роста:"])
        for w in weaknesses[:3]:
            comment_parts.append(f"  • {w}")

    comment_text = "\n".join(comment_parts)

    bitrix = BitrixClient()
    try:
        result = bitrix._call("crm.timeline.comment.add", {
            "fields": {
                "ENTITY_ID": deal_id,
                "ENTITY_TYPE": "deal",
                "COMMENT": comment_text,
            },
        })
        logger.info("Added comment to deal %d: %s", deal_id, result)
        return True
    except Exception as e:
        logger.error("Failed to add deal comment: %s", e)
        return False
    finally:
        bitrix.close()


def create_crm_activity(
    deal_id: int,
    employee_bitrix_id: int,
    subject: str,
    description: str,
    deadline_days: int = 3,
) -> bool:
    """Create a CRM activity (task) for follow-up."""
    if not settings.bitrix_webhook_url:
        return False

    from datetime import datetime, timedelta
    deadline = (datetime.now() + timedelta(days=deadline_days)).strftime("%Y-%m-%dT%H:%M:%S")

    bitrix = BitrixClient()
    try:
        result = bitrix._call("crm.activity.add", {
            "fields": {
                "OWNER_TYPE_ID": 2,  # Deal
                "OWNER_ID": deal_id,
                "TYPE_ID": 6,  # Task
                "SUBJECT": subject,
                "DESCRIPTION": description,
                "RESPONSIBLE_ID": employee_bitrix_id,
                "DEADLINE": deadline,
                "PRIORITY": 2,  # Normal
            },
        })
        logger.info("Created activity for deal %d: %s", deal_id, result)
        return True
    except Exception as e:
        logger.error("Failed to create CRM activity: %s", e)
        return False
    finally:
        bitrix.close()


def post_analysis_to_crm(
    deal_id: Optional[int],
    employee_bitrix_id: Optional[int],
    employee_name: str,
    direction: str,
    overall_score: int,
    summary: str,
    crm_note: str,
    strengths: list[str],
    weaknesses: list[str],
    next_step_agreed: bool,
    recommendations: list[str],
):
    """Post full analysis results to CRM (deal comment + follow-up activity)."""
    if not deal_id:
        return

    # Add analysis comment to deal timeline
    add_deal_comment(
        deal_id=deal_id,
        employee_name=employee_name,
        direction=direction,
        overall_score=overall_score,
        summary=summary,
        crm_note=crm_note,
        strengths=strengths,
        weaknesses=weaknesses,
    )

    # If no next step was agreed, create a follow-up task
    if not next_step_agreed and employee_bitrix_id:
        top_rec = recommendations[0] if recommendations else "Связаться с клиентом и договориться о следующем шаге"
        create_crm_activity(
            deal_id=deal_id,
            employee_bitrix_id=employee_bitrix_id,
            subject=f"Требуется follow-up (оценка {overall_score}/10)",
            description=(
                f"По результатам анализа звонка следующий шаг не был зафиксирован.\n\n"
                f"Рекомендация: {top_rec}\n\n"
                f"Заметка для CRM: {crm_note}"
            ),
        )
