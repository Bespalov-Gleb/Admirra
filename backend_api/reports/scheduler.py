"""
Планировщик автоматической отправки отчётов по расписанию пользователей.
Запускается каждую минуту, проверяет report_schedule и отправляет отчёты.
"""
import json
import logging
import secrets
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import or_
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


def _is_avito_platform(value) -> bool:
    return str(value or "").strip().lower() in {"avito", "avito_ads"}


def _campaign_platform(campaign: dict) -> str:
    platform = campaign.get("platform") or campaign.get("channel")
    if platform:
        return str(platform)
    name = str(campaign.get("name") or campaign.get("campaign_name") or "").lower()
    if name.startswith("[avito]") or name.startswith("[авито]"):
        return "avito"
    return ""


def _with_channel_vat(value, platform=None) -> float:
    raw = float(value or 0)
    return raw if _is_avito_platform(platform) else raw * VAT_RATE


def _with_cost_breakdown_vat(value, cost_by_platform: dict | None, platform=None) -> float:
    if isinstance(cost_by_platform, dict):
        return (
            float(cost_by_platform.get("yandex") or 0) * VAT_RATE
            + float(cost_by_platform.get("vk") or 0) * VAT_RATE
            + float(cost_by_platform.get("avito") or 0)
        )
    return _with_channel_vat(value, platform)


def _summary_platform(campaigns: list) -> str:
    if campaigns and all(_is_avito_platform(_campaign_platform(c)) for c in campaigns):
        return "avito"
    return ""


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
    summary_platform = _summary_platform(top_campaigns)
    summary_expenses = _with_cost_breakdown_vat(summary.get("expenses"), summary.get("cost_by_platform"), summary_platform)
    # CPL — от лидового расхода (ТЗ VK п.3/№10), не от всего расхода канала.
    summary_lead_expenses = _with_cost_breakdown_vat(
        summary.get("expenses"), summary.get("lead_cost_by_platform") or summary.get("cost_by_platform"), summary_platform
    )
    summary_cpc = summary_expenses / float(summary.get("clicks") or 0) if summary.get("clicks") else _with_channel_vat(summary.get("cpc"), summary_platform)
    summary_cpa = summary_lead_expenses / float(summary.get("leads") or 0) if summary.get("leads") else _with_channel_vat(summary.get("cpa"), summary_platform)
    lines = [
        f"Отчёт за период {sd} — {ed}",
        f"Проект: {client_name or 'все проекты'}",
        "",
        f"Расходы: {summary_expenses:,.0f} ₽".replace(",", " "),
        f"Показы: {int(summary.get('impressions') or 0):,}".replace(",", " "),
        f"Клики: {int(summary.get('clicks') or 0):,}".replace(",", " "),
        f"Лиды: {int(summary.get('leads') or 0):,}".replace(",", " "),
        f"CPC: {summary_cpc:.2f} ₽",
        f"CPL: {summary_cpa:.2f} ₽",
    ]
    if top_campaigns:
        lines.extend(["", "Топ кампаний по лидам:"])
        for index, campaign in enumerate(top_campaigns[:5], 1):
            name = campaign.get("name") or campaign.get("campaign_name") or "Кампания"
            leads = int(campaign.get("conversions") or 0)
            cost = _with_channel_vat(campaign.get("cost"), _campaign_platform(campaign))
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

            # Opt-in блок «Динамика» — хранится в JSON расписания пользователя.
            include_dynamics = False
            try:
                import json as _json
                _sched = _json.loads(user.report_schedule) if user.report_schedule else {}
                include_dynamics = bool(_sched.get("include_dynamics"))
            except Exception:
                include_dynamics = False

            try:
                pdf_bytes = generate_report_pdf(
                    db=db,
                    user_id=user.id,
                    client_id=None,
                    start_date=start_str,
                    end_date=end_str,
                    comment=None,
                    include_dynamics=include_dynamics,
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


# ══════════ Проектная автоотправка (report_schedules) ══════════
# Финальная система: ровно одна настройка на проект/папку. Legacy-функция выше
# оставлена только для совместимости импорта и не регистрируется в приложении.

def _rule_matches(rule, now: datetime) -> bool:
    try:
        hours, minutes = [int(p) for p in str(rule.send_time or "10:00").split(":", 1)]
    except Exception:
        return False
    if now.hour != hours or now.minute != minutes:
        return False
    day = str(rule.day or "daily").lower()
    if day == "daily":
        return True
    if day == "weekdays":
        return now.weekday() <= 4
    return DAY_TO_WEEKDAY.get(day) == now.weekday()


def _rule_already_sent_today(rule, now: datetime) -> bool:
    if not rule.last_sent_at:
        return False
    last = rule.last_sent_at
    if last.tzinfo is None:
        from datetime import timezone as _tz
        last = last.replace(tzinfo=_tz.utc)
    return last.astimezone(MSK).date() == now.date()


def _rule_already_processed_today(db: Session, rule, now: datetime) -> bool:
    return db.query(models.ReportDelivery.id).filter(
        models.ReportDelivery.schedule_id == rule.id,
        models.ReportDelivery.end_date == now.date(),
    ).first() is not None


def _jlist(raw, default=None):
    if default is None:
        default = []
    try:
        val = json.loads(raw) if isinstance(raw, str) and raw else raw
        return val if isinstance(val, list) else default
    except Exception:
        return default


def _rule_blocking_anomaly(db: Session, rule) -> str | None:
    """Возвращает причину остановки автоотправки, если детектор нашёл проблему."""
    q = db.query(models.DetectorAlert).filter(
        models.DetectorAlert.owner_id == rule.user_id,
        models.DetectorAlert.status == "open",
        models.DetectorAlert.severity == "problem",
        # Iteration 3: only a red plan/fact or actual critical failure blocks
        # an unattended client report. Historical/baseline noise never does.
        models.DetectorAlert.mode.in_(("plan", "critical_balance", "critical_stopped", "critical_tracking")),
    )
    if rule.scope_client_id:
        q = q.filter(models.DetectorAlert.client_id == rule.scope_client_id)
    elif rule.scope_folder_id:
        client_ids = [
            row.id for row in db.query(models.Client.id).filter(
                models.Client.folder_id == rule.scope_folder_id,
                models.Client.owner_id == rule.user_id,
            ).all()
        ]
        if not client_ids:
            return None
        q = q.filter(models.DetectorAlert.client_id.in_(client_ids))
    alert = q.order_by(models.DetectorAlert.opened_at.desc()).first()
    if not alert:
        return None
    metric = alert.metric or "метрика"
    pct = f" {alert.deviation_pct}%" if alert.deviation_pct is not None else ""
    return f"Детектор остановил автоотправку: {metric}{pct}"


def create_pending_delivery_for_schedule(db: Session, rule, *, reason: str | None = None, source: str = "auto"):
    now = datetime.now(MSK)
    end_date = now.date()
    start_date = end_date - timedelta(days=max(int(rule.period_days or 7) - 1, 0))
    existing = db.query(models.ReportDelivery).filter(
        models.ReportDelivery.user_id == rule.user_id,
        models.ReportDelivery.schedule_id == rule.id,
        models.ReportDelivery.start_date == start_date,
        models.ReportDelivery.end_date == end_date,
        models.ReportDelivery.status == "pending",
    ).first()
    if existing:
        return existing
    delivery = models.ReportDelivery(
        user_id=rule.user_id,
        schedule_id=rule.id,
        client_id=rule.scope_client_id,
        folder_id=rule.scope_folder_id,
        status="pending",
        source="detector" if reason else source,
        platform=rule.platform or "all",
        start_date=start_date,
        end_date=end_date,
        channels=rule.channels or "[]",
        email_recipients=getattr(rule, "email_recipients", None) or "[]",
        chat_targets=rule.chat_targets,
        report_format=rule.report_format or "desktop",
        # The composition tag is intentionally disabled in the UI.  Keep old
        # schedules from silently bringing the experimental block back.
        include_dynamics=False,
        include_ai_comment=bool(getattr(rule, "include_ai_comment", True)),
        sections=rule.sections,
        chart_metrics=rule.chart_metrics,
        dynamics_metrics=rule.dynamics_metrics,
        anomaly_reason=reason,
    )
    db.add(delivery)
    return delivery


def delivery_status_from_results(results: dict | None, channels=None, target_ids=None) -> str:
    """Итог по всем запрошенным маршрутам: sent только когда успешны все."""
    results = results or {}
    outcomes = []
    for channel in (channels or []):
        outcomes.append(results.get(channel) is True)
    target_results = results.get("targets") if isinstance(results.get("targets"), dict) else {}
    for target_id in (target_ids or []):
        item = target_results.get(str(target_id)) or {}
        outcomes.append(item.get("ok") is True)
    if not outcomes:
        return "failed"
    succeeded = sum(1 for value in outcomes if value)
    if succeeded == len(outcomes):
        return "sent"
    if succeeded:
        return "partial"
    return "failed"


def _delivery_succeeded(results) -> bool:
    """Backward-compatible helper: error metadata never counts as delivery."""
    if not results:
        return False
    for key in ("telegram", "max", "email"):
        if results.get(key) is True:
            return True
    targets = results.get("targets") if isinstance(results.get("targets"), dict) else {}
    if any(isinstance(value, dict) and value.get("ok") is True for value in targets.values()):
        return True
    try:
        return int(str(results.get("groups") or "0/0").split("/", 1)[0]) > 0
    except Exception:
        return False


def _json_safe(value):
    return json.loads(json.dumps(value, ensure_ascii=False, default=str))


def _scope_email_rows(db: Session, delivery, user_id):
    """Email recipients belonging to the exact project/folder delivery scope."""
    query = db.query(models.ReportEmailRecipient).filter(
        models.ReportEmailRecipient.user_id == user_id,
    )
    if delivery.folder_id:
        return query.filter(models.ReportEmailRecipient.folder_id == delivery.folder_id).all()
    if delivery.client_id:
        return query.filter(models.ReportEmailRecipient.client_id == delivery.client_id).all()
    return query.filter(
        models.ReportEmailRecipient.client_id.is_(None),
        models.ReportEmailRecipient.folder_id.is_(None),
    ).all()


def _email_values(value) -> list[str]:
    """Normalise legacy JSON arrays and the new recipient objects to emails."""
    emails = []
    for item in _jlist(value, []):
        email = item.get("email") if isinstance(item, dict) else item
        email = str(email or "").strip().lower()
        if email and email not in emails:
            emails.append(email)
    return emails


def _delivery_target_details(db: Session, delivery, user) -> tuple[list[dict], list[dict]]:
    target_ids = [str(value) for value in _jlist(delivery.chat_targets, [])]
    chat_details = []
    if target_ids:
        targets = db.query(models.ReportChatTarget).filter(
            models.ReportChatTarget.user_id == user.id,
            models.ReportChatTarget.id.in_(target_ids),
        ).all()
        for target in targets:
            chat_details.append({
                "id": str(target.id),
                "key": f"target:{target.id}",
                "kind": target.kind,
                "title": target.title or ("Telegram" if target.kind == "telegram" else "MAX"),
                "target_type": target.target_type,
                "status": getattr(target, "status", None) or "active",
                "last_error": getattr(target, "last_error", None),
            })

    selected = set(_email_values(getattr(delivery, "email_recipients", None)))
    email_details = []
    for recipient in _scope_email_rows(db, delivery, user.id):
        email = str(recipient.email).strip().lower()
        if email in selected:
            email_details.append({
                "id": str(recipient.id),
                "key": f"email:{email}",
                "kind": "email",
                "title": recipient.title or email,
                "email": email,
                "target_type": "email",
                "status": recipient.status or "active",
                "last_error": recipient.last_error,
            })
            selected.discard(email)
    # A queued delivery remains reproducible even if a recipient is later
    # deleted from settings. The historical route is then explicitly marked
    # unavailable instead of being silently lost.
    for email in sorted(selected):
        email_details.append({
            "id": email,
            "key": f"email:{email}",
            "kind": "email",
            "title": email,
            "email": email,
            "target_type": "email",
            "status": "unavailable",
            "last_error": "Получатель был удалён из настроек проекта",
        })
    return chat_details, email_details


def _delivery_cpl_target(db: Session, delivery, template: str | None = None) -> float | None:
    """Freeze a single matching CPA target alongside each template snapshot."""
    if not delivery.client_id:
        return None
    platform_map = {
        "yandex": models.IntegrationPlatform.YANDEX_DIRECT,
        "vk": models.IntegrationPlatform.VK_ADS,
        "avito": models.IntegrationPlatform.AVITO_ADS,
    }
    query = db.query(models.ProjectTargetCPA).filter(
        models.ProjectTargetCPA.client_id == delivery.client_id,
        models.ProjectTargetCPA.target_cpa.isnot(None),
        models.ProjectTargetCPA.period_start <= delivery.end_date,
        models.ProjectTargetCPA.period_end >= delivery.start_date,
    )
    channel = platform_map.get(template or delivery.platform or "all")
    if channel:
        query = query.filter(or_(
            models.ProjectTargetCPA.channel == channel,
            models.ProjectTargetCPA.channel.is_(None),
        ))
    else:
        query = query.filter(models.ProjectTargetCPA.channel.is_(None))
    row = query.order_by(
        models.ProjectTargetCPA.is_summary.desc(),
        models.ProjectTargetCPA.created_at.desc(),
    ).first()
    return float(row.target_cpa) if row else None


def _delivery_message_text(delivery, snapshot: dict) -> str:
    """One client-facing message, used unchanged by preview and all messengers."""
    from backend_api.reports.export_service import _with_cost_breakdown_vat
    from core.public_domain import resolve_frontend_url

    summary = snapshot.get("summary") or {}
    platform = snapshot.get("platform") or delivery.platform or "all"
    cost = _with_cost_breakdown_vat(
        summary.get("expenses"), summary.get("cost_by_platform"), platform
    )
    lead_cost = _with_cost_breakdown_vat(
        summary.get("expenses"), summary.get("lead_cost_by_platform") or summary.get("cost_by_platform"), platform
    )
    leads = int(summary.get("leads") or 0)
    cpl = lead_cost / leads if leads else None
    label = snapshot.get("client_name") or "Отчёт по рекламе"
    lines = [
        f"📊 {label}",
        f"Период: {delivery.start_date.isoformat()} — {delivery.end_date.isoformat()}",
        f"Расход: {cost:,.0f} ₽".replace(",", " "),
    ]
    balance = summary.get("balance")
    if isinstance(balance, (int, float)):
        lines.append(f"Остаток: {float(balance):,.0f} ₽".replace(",", " "))
    lines.append(f"Заявки: {leads:,}".replace(",", " "))
    if cpl is not None:
        cpl_line = f"CPL: {cpl:,.0f} ₽".replace(",", " ")
        target = snapshot.get("cpl_target")
        if isinstance(target, (int, float)) and target > 0:
            cpl_line += f" · план до {float(target):,.0f} ₽".replace(",", " ")
        lines.append(cpl_line)
    trend = (summary.get("trends") or {}).get("cpa") if isinstance(summary.get("trends"), dict) else None
    if isinstance(trend, (int, float)):
        sign = "+" if trend > 0 else ""
        lines.append(f"Динамика CPL: {sign}{trend:.1f}%")
    comment = (delivery.comment or snapshot.get("ai_comment") or "").strip()
    if comment:
        lines.extend(["", comment])
    token = delivery.public_token
    if token:
        url = f"{resolve_frontend_url().rstrip('/')}/api/reports/deliveries/public/{token}/pdf"
        lines.extend(["", f"Полный отчёт: {url}"])
    return "\n".join(lines)


def refresh_delivery_messages(delivery) -> None:
    """Refresh only presentation text after a comment/template change.

    No stats query is performed here: all values come from the immutable JSON
    snapshot that was stored before a report entered the approval queue.
    """
    snapshot = dict(delivery.snapshot_data or {})
    if not snapshot:
        return
    text = _delivery_message_text(delivery, snapshot)
    from backend_api.reports.email_template import render_report_email_html
    email_data = {
        "summary": snapshot.get("summary") or {},
        "top_campaigns": snapshot.get("top_campaigns") or [],
        "client_name": snapshot.get("client_name") or "",
        "ai_comment": (delivery.comment or "").strip(),
        "start_date": delivery.start_date.isoformat(),
        "end_date": delivery.end_date.isoformat(),
        "generated_at": (delivery.snapshot_created_at or datetime.now(MSK)).strftime("%Y-%m-%d %H:%M"),
    }
    subject = f"Отчёт за {delivery.start_date.isoformat()} — {delivery.end_date.isoformat()}"
    snapshot["ai_comment"] = (delivery.comment or "").strip()
    snapshot["delivery_messages"] = {
        "telegram": {"text": text},
        "max": {"text": text},
        "email": {"subject": subject, "text": text, "html": render_report_email_html(email_data)},
    }
    delivery.snapshot_data = _json_safe(snapshot)


def refresh_delivery_snapshot_files(delivery) -> None:
    """Re-render selected fixed data after an editor action, never live stats."""
    from backend_api.reports.pdf_service import generate_report_pdf_from_snapshot
    from backend_api.reports.export_service import pdf_full_png
    snapshot = dict(delivery.snapshot_data or {})
    if not snapshot:
        return
    snapshot["ai_comment"] = (delivery.comment or "").strip()
    delivery.snapshot_data = _json_safe(snapshot)
    delivery.pdf_snapshot = generate_report_pdf_from_snapshot(snapshot, delivery.comment)
    try:
        delivery.png_snapshot = pdf_full_png(delivery.pdf_snapshot)
    except Exception as exc:
        logger.warning("Delivery %s PNG snapshot skipped: %s", delivery.id, exc)
        delivery.png_snapshot = None
    refresh_delivery_messages(delivery)


async def build_delivery_snapshot(db: Session, delivery, user) -> None:
    """Freeze all template variants, recipients and presentation before queueing."""
    if delivery.pdf_snapshot and delivery.snapshot_data:
        return
    sections = _jlist(delivery.sections, ["kpi", "chart", "channels", "campaigns"])
    chart_metrics = _jlist(delivery.chart_metrics, ["cost", "clicks"])
    dynamics_metrics = _jlist(delivery.dynamics_metrics, ["cost"])
    folder_id = str(delivery.folder_id) if delivery.folder_id else None
    start_str = delivery.start_date.isoformat()
    end_str = delivery.end_date.isoformat()
    delivery.public_token = delivery.public_token or secrets.token_urlsafe(32)
    delivery.public_expires_at = datetime.now(MSK) + timedelta(days=30)
    delivery.snapshot_created_at = datetime.now(MSK)
    target_details, email_details = _delivery_target_details(db, delivery, user)
    template_snapshots = {}
    supported_templates = ("all", "yandex", "vk", "avito")
    for template in supported_templates:
        try:
            _pdf, render_data = generate_report_pdf(
                db=db,
                user_id=user.id,
                client_id=delivery.client_id,
                start_date=start_str,
                end_date=end_str,
                comment=delivery.comment,
                include_dynamics=False,
                folder_id=folder_id,
                platform=template,
                layout=delivery.report_format or "desktop",
                sections=sections,
                chart_metrics=chart_metrics,
                dynamics_metrics=dynamics_metrics,
                return_data=True,
                render_pdf=False,
            )
            # The selected template bytes are rendered below from this exact
            # fixed data; other variants need no eager PDF generation.
            render_data["cpl_target"] = _delivery_cpl_target(db, delivery, template)
            template_snapshots[template] = _json_safe(render_data)
        except Exception as exc:
            logger.info("Delivery %s template %s unavailable: %s", delivery.id, template, exc)
    selected = delivery.platform or "all"
    if selected not in template_snapshots:
        raise ValueError("Не удалось сформировать выбранный шаблон отчёта")
    snapshot = dict(template_snapshots[selected])
    snapshot["template_snapshots"] = template_snapshots
    snapshot["delivery_targets"] = target_details
    snapshot["email_target_details"] = email_details
    delivery.snapshot_data = _json_safe(snapshot)
    refresh_delivery_snapshot_files(delivery)


def _snapshot_caption(delivery) -> str:
    return ((delivery.snapshot_data or {}).get("delivery_messages") or {}).get("telegram", {}).get("text") or _delivery_message_text(delivery, delivery.snapshot_data or {})


def _retry_channels(
    delivery,
    retry_failed_only: bool,
    *,
    retry_email: str | None = None,
    retry_channel: str | None = None,
    retry_chat_target_id: str | None = None,
) -> tuple[list[str], list[str]]:
    """Return only routes intended for this attempt.

    A retry from an individual history badge must be strictly scoped to that
    recipient.  The generic retry path still retries every failed route, but
    never successful ones.
    """
    channels = _jlist(delivery.channels, [])
    targets = [str(value) for value in _jlist(delivery.chat_targets, [])]
    if retry_failed_only and delivery.delivery_results:
        previous = delivery.delivery_results or {}
        channels = [channel for channel in channels if previous.get(channel) is not True]
        target_results = previous.get("targets") if isinstance(previous.get("targets"), dict) else {}
        targets = [target_id for target_id in targets if (target_results.get(target_id) or {}).get("ok") is not True]

    if retry_email:
        channels = [channel for channel in channels if channel == "email"]
        targets = []
    elif retry_channel:
        channels = [channel for channel in channels if channel == retry_channel]
        targets = []
    elif retry_chat_target_id:
        channels = []
        targets = [target_id for target_id in targets if target_id == str(retry_chat_target_id)]
    return channels, targets


def switch_delivery_template(delivery, template: str) -> None:
    """Select an already frozen template; this must never query live stats."""
    template = str(template or "").strip().lower()
    if template not in {"all", "yandex", "vk", "avito"}:
        raise ValueError("Неизвестный шаблон отчёта")
    current = dict(delivery.snapshot_data or {})
    snapshots = current.get("template_snapshots") or {}
    if template not in snapshots:
        raise ValueError("Для этого шаблона нет сохранённого снимка")
    selected = dict(snapshots[template])
    selected["template_snapshots"] = snapshots
    selected["delivery_targets"] = current.get("delivery_targets") or []
    selected["email_target_details"] = current.get("email_target_details") or []
    delivery.platform = template
    delivery.snapshot_data = _json_safe(selected)
    refresh_delivery_snapshot_files(delivery)


async def _generate_automatic_comment_if_needed(db: Session, delivery, user) -> None:
    """Only unattended automatic sends may spend an AI credit implicitly.

    Opening a preview and sending a report after human approval never call this
    function. That keeps the Draft → Edited → Approved workflow explicit.
    """
    if getattr(delivery, "source", "manual") != "auto" or not getattr(delivery, "include_ai_comment", False) or (getattr(delivery, "comment", None) or "").strip():
        return
    try:
        from backend_api.services.subscription import SubscriptionService
        from ai.report_generator import generate_report
        SubscriptionService.ensure_can_use_ai(db, user, requested=1)
        delivery.comment = (await generate_report(
            db=db,
            user_id=user.id,
            client_id=delivery.client_id,
            start_date=delivery.start_date.isoformat(),
            end_date=delivery.end_date.isoformat(),
            report_type="comment",
            folder_id=str(delivery.folder_id) if delivery.folder_id else None,
            platform=delivery.platform or "all",
        ) or "").strip() or None
        delivery.comment_status = "draft" if delivery.comment else "none"
        SubscriptionService.increment_ai_usage(db, user, requested=1)
        refresh_delivery_snapshot_files(delivery)
    except Exception as exc:
        # A report is still useful without AI, and automatic delivery must not
        # turn into a false failed delivery merely because commentary is absent.
        logger.warning("Delivery %s automatic AI comment skipped: %s", delivery.id, exc)


async def _send_telegram_report_attachment(
    *,
    chat_id: str,
    png_snapshot: bytes | None,
    pdf_snapshot: bytes,
    filename_stem: str,
    caption: str,
) -> tuple[bool, str | None]:
    """Предпочитаем компактный PNG, но не теряем отчёт при ошибке preview."""
    from lead_validator.services.telegram import telegram_notifier, get_last_delivery_error

    pdf_filename = f"{filename_stem}.pdf"
    if png_snapshot:
        ok = await telegram_notifier.send_photo(chat_id=chat_id, photo=png_snapshot, caption=caption)
        if ok:
            return True, None
        preview_error = get_last_delivery_error() or "Telegram не подтвердил отправку PNG"
        if pdf_snapshot:
            ok = await telegram_notifier.send_document(
                chat_id=chat_id, document=pdf_snapshot, filename=pdf_filename, caption=caption,
            )
            if ok:
                logger.info("Telegram report PNG failed, PDF fallback succeeded")
                return True, None
            pdf_error = get_last_delivery_error() or "Telegram не подтвердил отправку PDF"
            return False, f"{preview_error}; повтор с PDF: {pdf_error}"
        return False, preview_error

    ok = await telegram_notifier.send_document(
        chat_id=chat_id, document=pdf_snapshot, filename=pdf_filename, caption=caption,
    )
    return ok, None if ok else (get_last_delivery_error() or "Telegram не подтвердил отправку PDF")


async def _send_max_report_attachment(
    *,
    chat_id: str | None,
    user_id: str | None,
    png_snapshot: bytes | None,
    pdf_snapshot: bytes,
    filename_stem: str,
    caption: str,
) -> tuple[bool, str | None]:
    """MAX принимает PNG как image; при проблеме с ним отправляем PDF-файл."""
    from backend_api.services import max_reports_bot

    if png_snapshot:
        ok = await max_reports_bot.send_document(
            png_snapshot,
            f"{filename_stem}.png",
            caption=caption,
            content_type="image/png",
            chat_id=chat_id,
            user_id=user_id,
        )
        if ok:
            return True, None
        preview_error = max_reports_bot.get_last_delivery_error() or "MAX не подтвердил отправку PNG"
        if pdf_snapshot:
            ok = await max_reports_bot.send_document(
                pdf_snapshot,
                f"{filename_stem}.pdf",
                caption=caption,
                content_type="application/pdf",
                chat_id=chat_id,
                user_id=user_id,
            )
            if ok:
                logger.info("MAX report PNG failed, PDF fallback succeeded")
                return True, None
            pdf_error = max_reports_bot.get_last_delivery_error() or "MAX не подтвердил отправку PDF"
            return False, f"{preview_error}; повтор с PDF: {pdf_error}"
        return False, preview_error

    ok = await max_reports_bot.send_document(
        pdf_snapshot,
        f"{filename_stem}.pdf",
        caption=caption,
        content_type="application/pdf",
        chat_id=chat_id,
        user_id=user_id,
    )
    return ok, None if ok else (max_reports_bot.get_last_delivery_error() or "MAX не подтвердил отправку PDF")


def _recipient_is_permanently_unavailable(error: str | None) -> bool:
    """Не отключаем получателя из-за временного сбоя API или вложения."""
    text = str(error or "").lower()
    return any(marker in text for marker in (
        "chat not found",
        "recipient not found",
        "bot was blocked",
        "user is deactivated",
        "forbidden: bot",
        "получатель не найден",
        "бот заблокирован",
        "пользователь деактивирован",
    ))


async def send_report_delivery(
    db: Session,
    delivery,
    user,
    *,
    retry_failed_only: bool = False,
    retry_email: str | None = None,
    retry_channel: str | None = None,
    retry_chat_target_id: str | None = None,
) -> dict:
    """Отправляет строго сохранённый снимок; при retry — только упавшие маршруты."""
    await build_delivery_snapshot(db, delivery, user)
    await _generate_automatic_comment_if_needed(db, delivery, user)
    channels, target_ids = _retry_channels(
        delivery,
        retry_failed_only,
        retry_email=retry_email,
        retry_channel=retry_channel,
        retry_chat_target_id=retry_chat_target_id,
    )
    previous = dict(delivery.delivery_results or {}) if retry_failed_only else {}
    results = {
        "telegram": previous.get("telegram"),
        "max": previous.get("max"),
        "email": previous.get("email"),
        "targets": dict(previous.get("targets") or {}),
        "email_targets": dict(previous.get("email_targets") or {}),
        "errors": dict(previous.get("errors") or {}),
    }
    def checkpoint() -> None:
        delivery.delivery_results = _json_safe(results)
        db.commit()
    caption = _snapshot_caption(delivery)
    expires = delivery.public_expires_at
    if expires and expires.tzinfo is None:
        from datetime import timezone as _timezone
        expires = expires.replace(tzinfo=_timezone.utc)
    if not delivery.public_token or not expires or expires <= datetime.now(MSK):
        delivery.public_token = secrets.token_urlsafe(32)
        delivery.public_expires_at = datetime.now(MSK) + timedelta(days=30)
        db.commit()
    if "telegram" in channels:
        results["errors"].pop("telegram", None)
        chat_id = (user.report_telegram_chat_id or "").strip()
        if not chat_id:
            results["telegram"] = False
            results["errors"]["telegram"] = "Telegram не привязан"
        else:
            try:
                results["telegram"], error = await _send_telegram_report_attachment(
                    chat_id=chat_id,
                    png_snapshot=delivery.png_snapshot,
                    pdf_snapshot=delivery.pdf_snapshot,
                    filename_stem=f"report_{delivery.start_date}_{delivery.end_date}",
                    caption=caption,
                )
                if error:
                    results["errors"]["telegram"] = error
            except Exception as exc:
                results["telegram"] = False
                results["errors"]["telegram"] = str(exc)
        checkpoint()

    if "max" in channels:
        results["errors"].pop("max", None)
        max_chat_id = (getattr(user, "report_max_chat_id", None) or "").strip()
        max_user_id = (getattr(user, "report_max_user_id", None) or "").strip()
        if not max_chat_id and not max_user_id:
            results["max"] = False
            results["errors"]["max"] = "MAX не привязан"
        else:
            try:
                results["max"], error = await _send_max_report_attachment(
                    chat_id=max_chat_id or None,
                    user_id=max_user_id or None,
                    png_snapshot=delivery.png_snapshot,
                    pdf_snapshot=delivery.pdf_snapshot,
                    filename_stem=f"report_{delivery.start_date}_{delivery.end_date}",
                    caption=caption,
                )
                if error:
                    results["errors"]["max"] = error
            except Exception as exc:
                results["max"] = False
                results["errors"]["max"] = str(exc)
        checkpoint()

    if "email" in channels:
        results["errors"].pop("email", None)
        recipients = _email_values(getattr(delivery, "email_recipients", None))
        if retry_email:
            requested = str(retry_email).strip().lower()
            recipients = [email for email in recipients if email == requested]
        elif retry_failed_only:
            recipients = [email for email in recipients if not (results["email_targets"].get(email) or {}).get("ok")]
        if not recipients:
            # There may simply be no failed address left after a retry.
            results["email"] = all((value or {}).get("ok") is True for value in results["email_targets"].values())
            if not results["email"]:
                results["errors"]["email"] = "Email-получатели проекта не указаны"
        else:
            email_rows = {str(row.email).strip().lower(): row for row in _scope_email_rows(db, delivery, user.id)}
            message = ((delivery.snapshot_data or {}).get("delivery_messages") or {}).get("email") or {}
            for email in recipients:
                ok, error = False, None
                try:
                    from backend_api.services.unisender import is_configured as unisender_ok, send_report_email as uni_send
                    if unisender_ok():
                        ok, error = await uni_send(
                            recipients=[email],
                            subject=message.get("subject") or f"Отчёт за {delivery.start_date} — {delivery.end_date}",
                            html_body=message.get("html") or "",
                            plain_body=message.get("text") or caption,
                            pdf_bytes=delivery.pdf_snapshot,
                            filename=f"report_{delivery.start_date}_{delivery.end_date}.pdf",
                        )
                    else:
                        from lead_validator.services.email_sender import email_sender
                        ok, error = await email_sender.send_report_email(
                            recipients=[email],
                            subject=message.get("subject") or f"Отчёт за {delivery.start_date} — {delivery.end_date}",
                            body=message.get("text") or caption,
                            pdf_bytes=delivery.pdf_snapshot,
                            filename=f"report_{delivery.start_date}_{delivery.end_date}.pdf",
                        )
                except Exception as exc:
                    error = str(exc)
                error = str(error) if error else (None if ok else "Email-провайдер не подтвердил отправку")
                results["email_targets"][email] = {"ok": bool(ok), **({"error": error} if error else {})}
                row = email_rows.get(email)
                if row:
                    row.status = "active" if ok else "unavailable"
                    row.last_error = error
                    row.last_delivery_at = datetime.now(MSK)
            results["email"] = bool(recipients) and all(
                (results["email_targets"].get(email) or {}).get("ok") is True
                for email in _email_values(getattr(delivery, "email_recipients", None))
            )
            if not results["email"]:
                failed = [email for email, item in results["email_targets"].items() if not item.get("ok")]
                results["errors"]["email"] = "; ".join(failed) or "Email-провайдер не подтвердил отправку"
        checkpoint()

    if target_ids:
        targets_query = db.query(models.ReportChatTarget).filter(
            models.ReportChatTarget.user_id == user.id,
            models.ReportChatTarget.id.in_(target_ids),
        )
        if delivery.folder_id:
            targets_query = targets_query.filter(models.ReportChatTarget.folder_id == delivery.folder_id)
        elif delivery.client_id:
            targets_query = targets_query.filter(models.ReportChatTarget.client_id == delivery.client_id)
        else:
            targets_query = targets_query.filter(
                models.ReportChatTarget.client_id.is_(None), models.ReportChatTarget.folder_id.is_(None)
            )
        targets = targets_query.all()
        by_id = {str(target.id): target for target in targets}
        for target_id in target_ids:
            target = by_id.get(str(target_id))
            ok = False
            error = None
            if not target:
                error = "Получатель не найден или отвязан"
            else:
                try:
                    if target.kind == "telegram":
                        ok, error = await _send_telegram_report_attachment(
                            chat_id=target.chat_id,
                            png_snapshot=delivery.png_snapshot,
                            pdf_snapshot=delivery.pdf_snapshot,
                            filename_stem=f"report_{delivery.start_date}_{delivery.end_date}",
                            caption=caption,
                        )
                    elif target.kind == "max":
                        is_user_target = str(target.chat_id).startswith("user:")
                        ok, error = await _send_max_report_attachment(
                            chat_id=None if is_user_target else target.chat_id,
                            user_id=str(target.chat_id).split(":", 1)[1] if is_user_target else None,
                            png_snapshot=delivery.png_snapshot,
                            pdf_snapshot=delivery.pdf_snapshot,
                            filename_stem=f"report_{delivery.start_date}_{delivery.end_date}",
                            caption=caption,
                        )
                    else:
                        error = "Неподдерживаемый канал получателя"
                    if not ok and not error:
                        error = "Провайдер не подтвердил отправку"
                except Exception as exc:
                    error = str(exc)
            results["targets"][str(target_id)] = {
                "ok": bool(ok),
                "kind": getattr(target, "kind", None),
                "title": getattr(target, "title", None),
                **({"error": error} if error else {}),
            }
            if target:
                # Сетевой сбой MAX/Telegram не делает чат невалидным. Иначе
                # один временный ответ API блокировал получателя в настройках
                # и мешал повторить отправку после восстановления сервиса.
                if ok:
                    target.status = "active"
                elif _recipient_is_permanently_unavailable(error):
                    target.status = "unavailable"
                target.last_error = error
                target.last_delivery_at = datetime.now(MSK)
            checkpoint()
    results["groups"] = f"{sum(1 for v in results['targets'].values() if v.get('ok'))}/{len(results['targets'])}"
    return results


async def send_report_for_schedule(db: Session, rule, user) -> dict:
    """Формирует и отправляет отчёт по одному правилу. Используется планировщиком
    и кнопкой «Отправить сейчас» (проверка настройки)."""
    from backend_api.reports.pdf_service import generate_report_pdf

    now = datetime.now(MSK)
    end_date = now.date()
    start_date = end_date - timedelta(days=max(int(rule.period_days or 7) - 1, 0))
    start_str = start_date.strftime("%Y-%m-%d")
    end_str = end_date.strftime("%Y-%m-%d")

    try:
        channels = json.loads(rule.channels) if isinstance(rule.channels, str) else (rule.channels or [])
    except Exception:
        channels = []

    results = {"telegram": None, "max": None, "email": None}

    def _jlist(raw, default):
        try:
            val = json.loads(raw) if isinstance(raw, str) and raw else raw
            return val if isinstance(val, list) and val else default
        except Exception:
            return default

    target_ids = _jlist(getattr(rule, "chat_targets", None), [])
    # Правило может слать ТОЛЬКО в группу — личные каналы не обязательны
    if not channels and not target_ids:
        return results

    client_id = rule.scope_client_id
    folder_id = str(rule.scope_folder_id) if rule.scope_folder_id else None
    platform = rule.platform or "all"
    approved_comment = (getattr(rule, "comment", None) or "").strip() or None

    pdf_bytes = generate_report_pdf(
        db=db,
        user_id=user.id,
        client_id=client_id,
        start_date=start_str,
        end_date=end_str,
        comment=approved_comment,
        include_dynamics=False,
        folder_id=folder_id,
        platform=platform,
        layout=rule.report_format or "desktop",
        sections=_jlist(getattr(rule, "sections", None), ["kpi", "chart", "channels", "campaigns"]),
        chart_metrics=_jlist(getattr(rule, "chart_metrics", None), ["cost", "clicks"]),
        dynamics_metrics=_jlist(getattr(rule, "dynamics_metrics", None), ["cost"]),
    )

    # Данные для текстового варианта (MAX) и темы письма
    summary, top_campaigns, client_name, _, _, _ = _get_report_data(
        db, user.id, client_id, start_str, end_str, approved_comment, folder_id=folder_id,
    )
    rule_title = (rule.name or "").strip()
    caption = f"Отчёт{f' «{rule_title}»' if rule_title else ''} за {start_str} — {end_str}"
    filename = f"report_{start_str}_{end_str}.pdf"

    telegram_chat_id = (user.report_telegram_chat_id or "").strip()
    max_chat_id = (getattr(user, "report_max_chat_id", None) or "").strip()
    max_user_id = (getattr(user, "report_max_user_id", None) or "").strip()
    email_recipients = _parse_email_recipients(user.report_email_recipients)

    if "telegram" in channels and telegram_chat_id:
        try:
            from lead_validator.services.telegram import telegram_notifier
            results["telegram"] = await telegram_notifier.send_document(
                chat_id=telegram_chat_id, document=pdf_bytes, filename=filename, caption=caption,
            )
        except Exception as e:
            logger.exception("Rule %s: telegram failed: %s", rule.id, e)
            results["telegram"] = False

    if "max" in channels and (max_chat_id or max_user_id):
        try:
            from backend_api.services import max_reports_bot
            # PDF-файлом, как в Telegram; текст — только запасной вариант
            results["max"] = await max_reports_bot.send_document(
                pdf_bytes, filename, caption=caption,
                chat_id=max_chat_id or None, user_id=max_user_id or None,
            )
            if not results["max"]:
                text_report = _format_text_report(summary, top_campaigns, client_name, start_str, end_str)
                results["max"] = await max_reports_bot.send_message(
                    text_report, chat_id=max_chat_id or None, user_id=max_user_id or None,
                )
        except Exception as e:
            logger.exception("Rule %s: MAX failed: %s", rule.id, e)
            results["max"] = False

    if "email" in channels and email_recipients:
        try:
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
                ok, err = await uni_send(
                    recipients=email_recipients,
                    subject=caption,
                    html_body=render_report_email_html(email_data),
                    plain_body=_format_text_report(summary, top_campaigns, client_name, start_str, end_str),
                    pdf_bytes=pdf_bytes,
                    filename=filename,
                )
            else:
                from lead_validator.services.email_sender import email_sender
                ok, err = await email_sender.send_report_email(
                    recipients=email_recipients, subject=caption,
                    body=f"Отчёт за период {start_str} — {end_str}.",
                    pdf_bytes=pdf_bytes, filename=filename,
                )
            results["email"] = ok
            if err:
                logger.warning("Rule %s: email error: %s", rule.id, err)
        except Exception as e:
            logger.exception("Rule %s: email failed: %s", rule.id, e)
            results["email"] = False

    # Групповые чаты (бот добавлен в группу TG/MAX)
    if target_ids:
        targets = (
            db.query(models.ReportChatTarget)
            .filter(
                models.ReportChatTarget.user_id == user.id,
                models.ReportChatTarget.id.in_([t for t in target_ids]),
            )
            .all()
        )
        group_ok = 0
        for target in targets:
            try:
                if target.kind == "telegram":
                    from lead_validator.services.telegram import telegram_notifier
                    ok = await telegram_notifier.send_document(
                        chat_id=target.chat_id, document=pdf_bytes, filename=filename, caption=caption,
                    )
                elif target.kind == "max":
                    from backend_api.services import max_reports_bot
                    ok = await max_reports_bot.send_document(
                        pdf_bytes, filename, caption=caption, chat_id=target.chat_id,
                    )
                else:
                    ok = False
                group_ok += 1 if ok else 0
            except Exception as e:
                logger.exception("Rule %s: group %s failed: %s", rule.id, target.id, e)
        results["groups"] = f"{group_ok}/{len(targets)}"

    rule.last_sent_at = datetime.now(MSK)
    return results


async def run_scheduled_report_rules():
    """Каждую минуту обрабатывает единственную настройку каждого проекта/папки."""
    db: Session = SessionLocal()
    try:
        now = datetime.now(MSK)
        stale_before = now - timedelta(minutes=15)
        stale_deliveries = db.query(models.ReportDelivery).filter(
            models.ReportDelivery.status == "sending",
            models.ReportDelivery.updated_at < stale_before,
        ).all()
        for delivery in stale_deliveries:
            delivery.status = "failed"
            previous = dict(delivery.delivery_results or {})
            errors = dict(previous.get("errors") or {})
            errors["system"] = "Отправка прервана. Можно безопасно повторить неуспешные маршруты."
            previous["errors"] = errors
            delivery.delivery_results = previous
        if stale_deliveries:
            db.commit()
        weekday_name = ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")[now.weekday()]
        allowed_days = ["daily", weekday_name]
        if now.weekday() <= 4:
            allowed_days.append("weekdays")
        rules = db.query(models.ReportSchedule).filter(
            models.ReportSchedule.enabled.is_(True),
            models.ReportSchedule.send_time == now.strftime("%H:%M"),
            models.ReportSchedule.day.in_(allowed_days),
        ).all()
        for rule in rules:
            if not _rule_matches(rule, now):
                continue
            if _rule_already_processed_today(db, rule, now):
                continue
            user = db.query(models.User).filter(
                models.User.id == rule.user_id,
                models.User.is_active == True,
            ).first()
            if not user:
                continue
            try:
                reason = _rule_blocking_anomaly(db, rule)
                delivery = create_pending_delivery_for_schedule(db, rule, reason=reason)
                db.flush()
                await build_delivery_snapshot(db, delivery, user)
                if bool(getattr(rule, "approval_required", True)) or reason:
                    delivery.status = "pending"
                    db.commit()
                    logger.info("Report rule %s queued for approval: delivery=%s reason=%s", rule.id, delivery.id, reason)
                else:
                    delivery.status = "sending"
                    db.commit()
                    results = await send_report_delivery(db, delivery, user)
                    delivery.delivery_results = results
                    delivery.status = delivery_status_from_results(
                        results, _jlist(delivery.channels, []), _jlist(delivery.chat_targets, []),
                    )
                    delivery.sent_at = datetime.now(MSK) if delivery.status in ("sent", "partial") else None
                    if delivery.status in ("sent", "partial"):
                        rule.last_sent_at = datetime.now(MSK)
                    db.commit()
                    logger.info("Report rule %s completed for %s: status=%s", rule.id, user.email, delivery.status)
            except Exception as e:
                db.rollback()
                logger.exception("Report rule %s failed for user %s: %s", rule.id, rule.user_id, e)
    finally:
        db.close()
