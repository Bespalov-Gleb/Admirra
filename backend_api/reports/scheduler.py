"""
Планировщик автоматической отправки отчётов по расписанию пользователей.
Запускается каждую минуту, проверяет report_schedule и отправляет отчёты.
"""
import json
import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from core.database import SessionLocal
from core import models
from backend_api.reports.pdf_service import generate_report_pdf
from backend_api.reports.export_service import _get_report_data

logger = logging.getLogger(__name__)
VAT_RATE = 1.22

MSK = ZoneInfo("Europe/Moscow")
DAY_TO_WEEKDAY = {
    "monday": 0,
    "tuesday": 1,
    "wednesday": 2,
    "thursday": 3,
    "friday": 4,
    "saturday": 5,
    "sunday": 6,
    "mon": 0,
    "tue": 1,
    "wed": 2,
    "thu": 3,
    "fri": 4,
    "sat": 5,
    "sun": 6,
}


def _parse_schedule(value) -> dict | None:
    if not value:
        return None
    if isinstance(value, dict):
        raw = value
    else:
        text = str(value).strip()
        if not text:
            return None
        if "_" in text and not text.startswith("{"):
            # Legacy: mon_10, daily_10
            day, _, hour = text.partition("_")
            return {"day": "daily" if day == "daily" else day, "time": f"{int(hour):02d}:00"}
        try:
            raw = json.loads(text)
        except Exception:
            return None

    day = str(raw.get("day") or "daily").strip().lower()
    time_value = str(raw.get("time") or "10:00").strip()
    try:
        hours, minutes = [int(part) for part in time_value.split(":", 1)]
    except Exception:
        return None
    if hours < 0 or hours > 23 or minutes < 0 or minutes > 59:
        return None
    return {"day": day, "hour": hours, "minute": minutes}


def _schedule_matches(value, now: datetime) -> bool:
    schedule = _parse_schedule(value)
    if not schedule:
        return False
    if now.hour != schedule["hour"] or now.minute != schedule["minute"]:
        return False
    day = schedule["day"]
    if day == "daily":
        return True
    return DAY_TO_WEEKDAY.get(day) == now.weekday()


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


def _with_vat(value) -> float:
    return float(value or 0) * VAT_RATE


def _parse_delivery_channels(val, user: models.User) -> list[str]:
    allowed = {"telegram", "max", "email"}
    if val is not None and str(val).strip() != "":
        try:
            raw = json.loads(val) if isinstance(val, str) else val
            if isinstance(raw, list):
                return [str(item).strip().lower() for item in raw if str(item).strip().lower() in allowed]
        except Exception:
            pass

    # Legacy fallback: если пользователь ещё не сохранял каналы, отправляем во все привязанные.
    channels = []
    if (user.report_telegram_chat_id or "").strip():
        channels.append("telegram")
    if (getattr(user, "report_max_chat_id", None) or getattr(user, "report_max_user_id", None) or ""):
        channels.append("max")
    if _parse_email_recipients(user.report_email_recipients):
        channels.append("email")
    return channels


def _format_text_report(summary: dict, top_campaigns: list, client_name: str, sd: str, ed: str) -> str:
    lines = [
        f"Отчёт за период {sd} — {ed}",
        f"Проект: {client_name or 'все проекты'}",
        "",
        f"Расходы: {_with_vat(summary.get('expenses')):,.0f} ₽".replace(",", " "),
        f"Показы: {int(summary.get('impressions') or 0):,}".replace(",", " "),
        f"Клики: {int(summary.get('clicks') or 0):,}".replace(",", " "),
        f"Лиды: {int(summary.get('leads') or 0):,}".replace(",", " "),
        f"CPC: {_with_vat(summary.get('cpc')):.2f} ₽",
        f"CPL: {_with_vat(summary.get('cpa')):.2f} ₽",
    ]
    if top_campaigns:
        lines.extend(["", "Топ кампаний по лидам:"])
        for index, campaign in enumerate(top_campaigns[:5], 1):
            name = campaign.get("name") or campaign.get("campaign_name") or "Кампания"
            leads = int(campaign.get("conversions") or 0)
            cost = _with_vat(campaign.get("cost"))
            lines.append(f"{index}. {name}: {leads} лидов, {cost:,.0f} ₽".replace(",", " "))
    return "\n".join(lines)


async def run_scheduled_reports():
    """
    Запускается каждую минуту. Отправляет отчёты пользователям,
    у которых report_schedule совпадает с текущими днём и временем по МСК.
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

        now = datetime.now(MSK)

        # Период: последние 14 дней
        end_date = now.date()
        start_date = end_date - timedelta(days=14)
        start_str = start_date.strftime("%Y-%m-%d")
        end_str = end_date.strftime("%Y-%m-%d")

        for user in users:
            if not _schedule_matches(user.report_schedule, now):
                continue

            channels = _parse_delivery_channels(user.report_delivery_channels, user)
            telegram_chat_id = (user.report_telegram_chat_id or "").strip()
            max_chat_id = (getattr(user, "report_max_chat_id", None) or "").strip()
            max_user_id = (getattr(user, "report_max_user_id", None) or "").strip()
            email_recipients = _parse_email_recipients(user.report_email_recipients)

            if not channels:
                logger.debug(f"User {user.email}: schedule {user.report_schedule} but no report channels configured, skip")
                continue

            # Fetch report data once for all channels
            try:
                summary, top_campaigns, client_name, _, _, _ = _get_report_data(
                    db=db, user_id=user.id, client_id=None,
                    start_date=start_str, end_date=end_str, comment=None,
                )
            except Exception as e:
                logger.exception(f"Scheduled report data failed for user {user.email}: {e}")
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

            # MAX
            if "max" in channels and (max_chat_id or max_user_id):
                try:
                    from backend_api.services import max_reports_bot
                    text_report = _format_text_report(summary, top_campaigns, client_name, start_str, end_str)
                    ok = await max_reports_bot.send_message(
                        text_report,
                        chat_id=max_chat_id or None,
                        user_id=max_user_id or None,
                    )
                    if ok:
                        logger.info(f"Scheduled report sent to MAX for user {user.email}")
                    else:
                        logger.warning(f"Scheduled report MAX send failed for user {user.email}")
                except Exception as e:
                    logger.exception(f"Scheduled report MAX error for user {user.email}: {e}")

            # Email (UniSender Go → SMTP fallback)
            if "email" in channels and email_recipients:
                try:
                    subject = f"Отчёт за период {start_str} — {end_str}"
                    from backend_api.services.unisender import is_configured as unisender_ok, send_report_email as uni_send
                    if unisender_ok():
                        from backend_api.reports.email_template import render_report_email_html
                        email_data = {
                            "summary": summary,
                            "top_campaigns": top_campaigns,
                            "client_name": client_name or "",
                            "ai_comment": "",
                            "start_date": start_str,
                            "end_date": end_str,
                            "generated_at": now.strftime("%Y-%m-%d %H:%M"),
                        }
                        html_body = render_report_email_html(email_data)
                        plain_body = _format_text_report(summary, top_campaigns, client_name, start_str, end_str)
                        ok, err = await uni_send(
                            recipients=email_recipients,
                            subject=subject,
                            html_body=html_body,
                            plain_body=plain_body,
                            pdf_bytes=pdf_bytes,
                            filename=f"report_{start_str}_{end_str}.pdf",
                        )
                    else:
                        from lead_validator.services.email_sender import email_sender
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
