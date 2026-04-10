"""Email notification service for sending reports to managers.

Setup:
1. Set SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD in .env
2. Set NOTIFY_EMAIL_TO for the recipient(s)
"""
import logging
import smtplib
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

from app.config import settings

logger = logging.getLogger(__name__)


def _get_smtp_config() -> Optional[dict]:
    host = getattr(settings, "smtp_host", "") or ""
    if not host:
        return None
    return {
        "host": host,
        "port": int(getattr(settings, "smtp_port", 587) or 587),
        "user": getattr(settings, "smtp_user", "") or "",
        "password": getattr(settings, "smtp_password", "") or "",
        "from_email": getattr(settings, "smtp_from_email", "") or getattr(settings, "smtp_user", ""),
    }


def send_report_email(
    to_emails: list[str],
    subject: str,
    body_html: str,
    attachment_bytes: Optional[bytes] = None,
    attachment_name: str = "report.xlsx",
) -> bool:
    """Send an email with optional Excel attachment."""
    config = _get_smtp_config()
    if not config:
        logger.debug("SMTP not configured, skipping email")
        return False

    if not to_emails:
        logger.debug("No recipients, skipping email")
        return False

    msg = MIMEMultipart()
    msg["From"] = config["from_email"]
    msg["To"] = ", ".join(to_emails)
    msg["Subject"] = subject

    msg.attach(MIMEText(body_html, "html", "utf-8"))

    if attachment_bytes:
        part = MIMEBase("application", "octet-stream")
        part.set_payload(attachment_bytes)
        encoders.encode_base64(part)
        part.add_header("Content-Disposition", f"attachment; filename={attachment_name}")
        msg.attach(part)

    try:
        with smtplib.SMTP(config["host"], config["port"]) as server:
            server.ehlo()
            if config["port"] != 25:
                server.starttls()
            if config["user"] and config["password"]:
                server.login(config["user"], config["password"])
            server.sendmail(config["from_email"], to_emails, msg.as_string())
        logger.info("Email sent to %s", to_emails)
        return True
    except Exception as e:
        logger.error("Failed to send email: %s", e)
        return False


def send_weekly_report(
    to_emails: list[str],
    period: str,
    total_calls: int,
    avg_score: Optional[float],
    top_problems: list[str],
    report_bytes: Optional[bytes] = None,
):
    """Send weekly report summary email."""
    score_color = "#22c55e" if (avg_score or 0) > 6 else "#eab308" if (avg_score or 0) > 3 else "#ef4444"

    problems_html = ""
    for i, p in enumerate(top_problems[:5], 1):
        problems_html += f"<li>{p}</li>"

    body = f"""
    <html>
    <body style="font-family: Arial, sans-serif; color: #333;">
        <h2>📊 Еженедельный отчёт по звонкам</h2>
        <p>Период: <strong>{period}</strong></p>

        <table style="border-collapse: collapse; margin: 20px 0;">
            <tr>
                <td style="padding: 10px 20px; background: #f3f4f6; border-radius: 8px;">
                    <div style="font-size: 12px; color: #6b7280;">Звонков</div>
                    <div style="font-size: 24px; font-weight: bold;">{total_calls}</div>
                </td>
                <td style="padding: 10px 20px; background: #f3f4f6; border-radius: 8px; margin-left: 10px;">
                    <div style="font-size: 12px; color: #6b7280;">Средняя оценка</div>
                    <div style="font-size: 24px; font-weight: bold; color: {score_color};">
                        {f'{avg_score:.1f}' if avg_score else '-'}/10
                    </div>
                </td>
            </tr>
        </table>

        {"<h3>Основные проблемы:</h3><ol>" + problems_html + "</ol>" if problems_html else ""}

        <p style="color: #6b7280; font-size: 12px; margin-top: 30px;">
            Полный отчёт в приложении (Excel).
            <br>Система анализа звонков — Call Analytics
        </p>
    </body>
    </html>
    """

    send_report_email(
        to_emails=to_emails,
        subject=f"Отчёт по звонкам за {period} — {total_calls} звонков, оценка {f'{avg_score:.1f}' if avg_score else '-'}",
        body_html=body,
        attachment_bytes=report_bytes,
        attachment_name=f"report_{period}.xlsx",
    )
