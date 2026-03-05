"""
Планировщик автоматической отправки отчётов по расписанию пользователей.
Запускается ежедневно в 10:00, проверяет report_schedule и отправляет PDF.
"""
import json
import logging
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from core.database import SessionLocal
from core import models
from backend_api.reports.pdf_service import generate_report_pdf

logger = logging.getLogger(__name__)

# Формат: day_hour -> (day_of_week или None для daily, hour)
# day_of_week: 0=Mon, 1=Tue, ..., 6=Sun (Python weekday)
SCHEDULE_MAP = {
    "mon_10": (0, 10),
    "tue_10": (1, 10),
    "wed_10": (2, 10),
    "thu_10": (3, 10),
    "fri_10": (4, 10),
    "daily_10": (None, 10),  # None = любой день
}


def _get_today_matching_schedules() -> set:
    """Возвращает множество расписаний, которые должны сработать сегодня в текущий час."""
    now = datetime.now()
    result = set()
    for schedule, (day_filter, hour) in SCHEDULE_MAP.items():
        if now.hour != hour:
            continue
        if day_filter is None:  # daily
            result.add(schedule)
        elif now.weekday() == day_filter:
            result.add(schedule)
    return result


def _parse_email_recipients(val) -> list:
    """Парсит report_email_recipients из БД (JSON строка или список)."""
    if not val:
        return []
    if isinstance(val, list):
        return val
    try:
        return json.loads(val) if val else []
    except Exception:
        return []


async def run_scheduled_reports():
    """
    Запускается по крону в 10:00. Отправляет отчёты пользователям,
    у которых report_schedule совпадает с текущим днём.
    """
    db: Session = SessionLocal()
    try:
        users = db.query(models.User).filter(
            models.User.report_schedule.isnot(None),
            models.User.report_schedule != "",
            models.User.is_active == True,
        ).all()

        if not users:
            return

        today_schedules = _get_today_matching_schedules()
        if not today_schedules:
            return

        # Период: последние 14 дней
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=14)
        start_str = start_date.strftime("%Y-%m-%d")
        end_str = end_date.strftime("%Y-%m-%d")

        for user in users:
            if user.report_schedule not in today_schedules:
                continue

            channels = []
            telegram_chat_id = (user.report_telegram_chat_id or "").strip()
            email_recipients = _parse_email_recipients(user.report_email_recipients)

            if telegram_chat_id:
                channels.append("telegram")
            if email_recipients:
                channels.append("email")

            if not channels:
                logger.debug(f"User {user.email}: schedule {user.report_schedule} but no telegram/email configured, skip")
                continue

            try:
                pdf_bytes = generate_report_pdf(
                    db=db,
                    user_id=user.id,
                    client_id=None,
                    start_date=start_str,
                    end_date=end_str,
                    comment=None,
                )
            except Exception as e:
                logger.exception(f"Scheduled report PDF failed for user {user.email}: {e}")
                continue

            # Telegram
            if "telegram" in channels and telegram_chat_id:
                try:
                    from lead_validator.services.telegram import telegram_notifier
                    caption = f"Отчёт за период {start_str} — {end_str}"
                    ok = await telegram_notifier.send_document(
                        chat_id=telegram_chat_id,
                        document=pdf_bytes,
                        filename=f"report_{start_str}_{end_str}.pdf",
                        caption=caption,
                    )
                    if ok:
                        logger.info(f"Scheduled report sent to Telegram for user {user.email}")
                    else:
                        logger.warning(f"Scheduled report Telegram send failed for user {user.email}")
                except Exception as e:
                    logger.exception(f"Scheduled report Telegram error for user {user.email}: {e}")

            # Email
            if "email" in channels and email_recipients:
                try:
                    from lead_validator.services.email_sender import email_sender
                    subject = f"Отчёт за период {start_str} — {end_str}"
                    body_text = f"Отчёт по рекламным кампаниям за период {start_str} — {end_str}."
                    ok, err = await email_sender.send_report_email(
                        recipients=email_recipients,
                        subject=subject,
                        body=body_text,
                        pdf_bytes=pdf_bytes,
                        filename=f"report_{start_str}_{end_str}.pdf",
                    )
                    if ok:
                        logger.info(f"Scheduled report sent to Email for user {user.email}")
                    else:
                        logger.warning(f"Scheduled report Email failed for user {user.email}: {err}")
                except Exception as e:
                    logger.exception(f"Scheduled report Email error for user {user.email}: {e}")

    finally:
        db.close()
