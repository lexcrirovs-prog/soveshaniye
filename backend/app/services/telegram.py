"""Telegram bot for notifications about analyzed calls.

Setup:
1. Create a bot via @BotFather in Telegram
2. Set TELEGRAM_BOT_TOKEN in .env
3. Set TELEGRAM_CHAT_ID (get it from @userinfobot)
"""
import logging
from typing import Optional

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

TELEGRAM_API = "https://api.telegram.org/bot{token}"


def _get_token() -> Optional[str]:
    token = getattr(settings, "telegram_bot_token", "") or ""
    return token if token else None


def _get_chat_id() -> Optional[str]:
    chat_id = getattr(settings, "telegram_chat_id", "") or ""
    return chat_id if chat_id else None


def send_message(text: str, chat_id: Optional[str] = None, parse_mode: str = "HTML") -> bool:
    """Send a message via Telegram bot."""
    token = _get_token()
    if not token:
        logger.debug("Telegram bot token not configured, skipping notification")
        return False

    target_chat = chat_id or _get_chat_id()
    if not target_chat:
        logger.debug("Telegram chat_id not configured, skipping notification")
        return False

    url = f"{TELEGRAM_API.format(token=token)}/sendMessage"
    payload = {
        "chat_id": target_chat,
        "text": text,
        "parse_mode": parse_mode,
    }

    try:
        response = httpx.post(url, json=payload, timeout=10)
        response.raise_for_status()
        return True
    except Exception as e:
        logger.error("Failed to send Telegram message: %s", e)
        return False


def notify_call_analyzed(
    employee_name: str,
    direction: str,
    duration_sec: int,
    overall_score: int,
    deal_name: str = "",
    summary: str = "",
    call_id: int = 0,
):
    """Send notification about an analyzed call."""
    direction_ru = "Входящий" if direction == "incoming" else "Исходящий"
    minutes = duration_sec // 60
    seconds = duration_sec % 60

    # Score emoji
    if overall_score >= 7:
        score_emoji = "🟢"
    elif overall_score >= 4:
        score_emoji = "🟡"
    else:
        score_emoji = "🔴"

    text = (
        f"📞 <b>Звонок проанализирован</b>\n\n"
        f"👤 Менеджер: {employee_name}\n"
        f"📱 {direction_ru}, {minutes}:{seconds:02d}\n"
    )
    if deal_name:
        text += f"💼 Сделка: {deal_name}\n"
    text += f"\n{score_emoji} <b>Оценка: {overall_score}/10</b>\n"
    if summary:
        text += f"\n📝 {summary}\n"

    send_message(text)


def notify_export_completed(
    job_id: int,
    period: str,
    total_calls: int,
    avg_score: Optional[float] = None,
):
    """Send notification about a completed export."""
    text = (
        f"📊 <b>Выгрузка завершена</b>\n\n"
        f"📋 Выгрузка #{job_id}\n"
        f"📅 Период: {period}\n"
        f"📞 Звонков: {total_calls}\n"
    )
    if avg_score is not None:
        text += f"⭐ Средняя оценка: {avg_score:.1f}/10\n"
    text += "\n✅ Отчёт готов к скачиванию"

    send_message(text)


def notify_low_score(
    employee_name: str,
    call_id: int,
    overall_score: int,
    weaknesses: list[str],
):
    """Send alert when a call scores below threshold."""
    text = (
        f"⚠️ <b>Низкая оценка звонка</b>\n\n"
        f"👤 Менеджер: {employee_name}\n"
        f"🔴 Оценка: {overall_score}/10\n\n"
        f"<b>Проблемы:</b>\n"
    )
    for w in weaknesses[:3]:
        text += f"• {w}\n"

    send_message(text)
