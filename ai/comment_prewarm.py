"""§9.2: адресный ночной прогрев AI-комментариев.

Кандидат: проект открывали за 7 дней, есть открытый флажок детектора либо
отчёт должен попасть в очередь в ближайшие 24 часа. Видимую AI-квоту это не
расходует; внутренний soft cap лишь снижает частоту авто-вызовов.
"""

import logging
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from core import models
from core.config import get_config
from core.database import SessionLocal

logger = logging.getLogger("ai.prewarm")

_THROTTLE = timedelta(hours=20)
MSK = ZoneInfo("Europe/Moscow")


def _aware(dt):
    if dt is None:
        return None
    return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt


def _schedule_due_within_24h(rule, now_utc: datetime) -> bool:
    try:
        hour, minute = [int(x) for x in str(rule.send_time or "10:00").split(":", 1)]
    except (TypeError, ValueError):
        return False
    now = now_utc.astimezone(MSK)
    end = now + timedelta(hours=24)
    weekday_names = ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")
    day_rule = str(rule.day or "daily").lower()
    for add_days in (0, 1):
        date_value = (now + timedelta(days=add_days)).date()
        candidate = datetime.combine(date_value, datetime.min.time(), tzinfo=MSK).replace(hour=hour, minute=minute)
        weekday = candidate.weekday()
        matches = (
            day_rule == "daily"
            or (day_rule == "weekdays" and weekday <= 4)
            or day_rule == weekday_names[weekday]
        )
        if matches and now <= candidate <= end:
            return True
    return False


def _report_candidate_ids(db, now: datetime) -> set:
    ids = {
        row[0]
        for row in db.query(models.ReportDelivery.client_id).filter(
            models.ReportDelivery.client_id.isnot(None),
            models.ReportDelivery.include_ai_comment.is_(True),
            models.ReportDelivery.status.in_(("pending", "draft", "approved")),
        ).all()
    }
    folder_ids = {
        row[0]
        for row in db.query(models.ReportDelivery.folder_id).filter(
            models.ReportDelivery.folder_id.isnot(None),
            models.ReportDelivery.include_ai_comment.is_(True),
            models.ReportDelivery.status.in_(("pending", "draft", "approved")),
        ).all()
    }
    if folder_ids:
        ids.update(row[0] for row in db.query(models.Client.id).filter(models.Client.folder_id.in_(folder_ids)).all())

    for rule in db.query(models.ReportSchedule).filter(
        models.ReportSchedule.enabled.is_(True),
        models.ReportSchedule.include_ai_comment.is_(True),
    ).all():
        if not _schedule_due_within_24h(rule, now):
            continue
        if rule.scope_client_id:
            ids.add(rule.scope_client_id)
        elif rule.scope_folder_id:
            ids.update(row[0] for row in db.query(models.Client.id).filter(
                models.Client.folder_id == rule.scope_folder_id,
            ).all())
        else:
            ids.update(row[0] for row in db.query(models.Client.id).filter(
                models.Client.owner_id == rule.user_id,
                models.Client.status == models.ClientStatus.ACTIVE,
            ).all())
    return ids


def _model_calls_in_period(db, account_user, sub) -> int:
    from backend_api.services.subscription import SubscriptionService
    owner_ids = SubscriptionService.account_project_owner_ids(db, account_user.id)
    since = _aware(getattr(sub, "current_period_start", None)) or datetime.now(timezone.utc) - timedelta(days=30)
    return (
        db.query(models.AICommentGeneration)
        .join(models.Client, models.Client.id == models.AICommentGeneration.client_id)
        .filter(
            models.Client.owner_id.in_(owner_ids),
            models.AICommentGeneration.generated_at >= since,
        )
        .count()
    )


def _notify_internal_soft_cap(db, account_user, used: int, cap: int, period_start) -> None:
    from backend_api.services.notifications import create_notification
    since = _aware(period_start) or datetime.now(timezone.utc) - timedelta(days=30)
    admins = db.query(models.User).filter(
        models.User.role.in_((models.UserRole.ADMIN, models.UserRole.SUPERADMIN, models.UserRole.DEVELOPER)),
        models.User.is_active.is_(True),
    ).all()
    for admin in admins:
        existing = db.query(models.Notification).filter(
            models.Notification.user_id == admin.id,
            models.Notification.type == "system",
            models.Notification.title == "AI comments soft cap: 80%",
            models.Notification.created_at >= since,
        ).all()
        if any((n.meta or {}).get("account_id") == str(account_user.id) for n in existing):
            continue
        create_notification(
            db, user_id=admin.id, type="system", title="AI comments soft cap: 80%",
            body=f"Аккаунт {account_user.email or account_user.id}: {used}/{cap} вызовов модели.",
            meta={"account_id": str(account_user.id), "used": used, "cap": cap},
        )


async def prewarm_warm_project_comments() -> None:
    from ai.report_generator import generate_report
    from ai.router import _comment_fingerprint, _save_comment_cache
    from ai.comment_periods import standard_periods
    from backend_api.services.subscription import SubscriptionService

    db = SessionLocal()
    try:
        cfg = get_config()
        warm_days = int(getattr(cfg.billing, "warm_window_days", 7) or 7)
        now = datetime.now(timezone.utc)
        warm_since = now - timedelta(days=warm_days)

        warm_ids = {
            row[0]
            for row in db.query(models.Client.id).filter(
                models.Client.status == models.ClientStatus.ACTIVE,
                models.Client.last_dashboard_viewed_at.isnot(None),
                models.Client.last_dashboard_viewed_at >= warm_since,
            ).all()
        }
        alert_ids = {
            row[0]
            for row in db.query(models.DetectorAlert.client_id).join(
                models.Client, models.Client.id == models.DetectorAlert.client_id,
            ).filter(
                models.Client.status == models.ClientStatus.ACTIVE,
                models.Client.detector_enabled.is_(True),
                models.DetectorAlert.status == "open",
            ).distinct().all()
        }
        candidate_ids = warm_ids | alert_ids | _report_candidate_ids(db, now)
        clients = (
            db.query(models.Client)
            .filter(
                models.Client.status == models.ClientStatus.ACTIVE,
                models.Client.id.in_(candidate_ids),
            )
            .all()
        ) if candidate_ids else []
        if not clients:
            logger.info("Прогрев комментариев: тёплых проектов нет")
            return

        d_start, d_end = standard_periods()["this_week"]
        start_s, end_s = d_start.isoformat(), d_end.isoformat()
        soft_cap_cache: dict = {}
        generated = 0

        for client in clients:
            try:
                lcg = _aware(getattr(client, "last_comment_generated_at", None))
                raw_owner = db.query(models.User).filter(models.User.id == client.owner_id).first()
                if raw_owner is None:
                    continue
                account_user = SubscriptionService.get_billing_account_user(db, raw_owner)
                owner_id = account_user.id
                # §9.4: soft_cap на аккаунт. При превышении не блокируем совсем, а
                # снижаем частоту ночного прогрева до раза в трое суток.
                if owner_id not in soft_cap_cache:
                    cap = 0
                    used = 0
                    plan = SubscriptionService.get_user_plan(db, account_user)
                    # Лимит берём из зафиксированной спеки аккаунта, а не из
                    # сегодняшней env-конфигурации прайс-бука.
                    cap = int(plan.comments_soft_cap or (int(plan.max_projects) * 30))
                    sub = SubscriptionService.ensure_default_subscription(db, account_user)
                    used = _model_calls_in_period(db, account_user, sub)
                    if cap and used >= int(cap * 0.8):
                        _notify_internal_soft_cap(db, account_user, used, cap, sub.current_period_start)
                        db.commit()
                    soft_cap_cache[owner_id] = (cap, used)
                cap, used = soft_cap_cache[owner_id]
                over_cap = bool(cap) and used >= cap
                throttle = timedelta(hours=72) if over_cap else _THROTTLE
                if lcg and (now - lcg) < throttle:
                    continue

                # §9.2: только если данные изменились с прошлой генерации.
                fp = _comment_fingerprint(db, owner_id, client.id, start_s, end_s)
                cache = getattr(client, "ai_comment_cache", None) or {}
                from ai.comment_periods import period_key_for
                pk = period_key_for(start_s, end_s)
                entry = cache.get(pk) if isinstance(cache, dict) and pk else None
                if entry and fp and entry.get("fingerprint") == fp:
                    continue

                text = await generate_report(
                    db=db, user_id=account_user.id, client_id=client.id,
                    start_date=start_s, end_date=end_s,
                    report_type="dashboard_comment", trigger="auto_sync",
                )
                if text:
                    _save_comment_cache(db, client.id, start_s, end_s, text, fingerprint=fp)
                    client.last_comment_generated_at = now
                    db.commit()
                    sub = SubscriptionService.ensure_default_subscription(db, account_user)
                    soft_cap_cache[owner_id] = (cap, _model_calls_in_period(db, account_user, sub))
                    generated += 1
            except Exception as e:
                db.rollback()
                logger.warning("Прогрев комментария не удался для проекта %s: %s", client.id, e)

        logger.info("Прогрев комментариев: сгенерировано %d из %d тёплых проектов", generated, len(clients))
    finally:
        db.close()
