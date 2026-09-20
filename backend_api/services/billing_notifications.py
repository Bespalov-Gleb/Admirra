"""Фоновые уведомления экономики подписки."""

import asyncio
import logging
from datetime import datetime, timedelta, timezone

from core import models
from core.database import SessionLocal
from backend_api.services.auth_mail import _send_sync
from backend_api.services.subscription import SubscriptionService

logger = logging.getLogger("billing.notifications")


class BillingMaintenanceUncertain(RuntimeError):
    """An attempted external operation was not confirmed; do not replay blindly."""


def _scoped(query, subscription_id, owner_id):
    if (subscription_id is None) != (owner_id is None):
        raise ValueError("Subscription and owner must be specified together")
    if subscription_id is not None:
        query = query.filter(models.Subscription.id == subscription_id, models.Subscription.user_id == owner_id)
    return query


async def send_overflow_renewal_warnings(*, subscription_id=None, owner_id=None, expected_period_end=None) -> int:
    """Одно письмо владельцу за 7 дней до продления в состоянии overflow."""
    db = SessionLocal()
    sent_count = 0
    try:
        now = datetime.now(timezone.utc)
        window_start = now + timedelta(days=6)
        window_end = now + timedelta(days=8)
        query = _scoped(db.query(models.Subscription), subscription_id, owner_id).filter(
            models.Subscription.current_period_end >= window_start,
            models.Subscription.current_period_end < window_end,
            models.Subscription.status.in_((models.SubscriptionStatus.ACTIVE, models.SubscriptionStatus.TRIAL)),
        )
        if expected_period_end is not None:
            query = query.filter(models.Subscription.current_period_end == expected_period_end)
        subscriptions = query.all()
        for sub in subscriptions:
            owner = db.query(models.User).filter(models.User.id == sub.user_id).first()
            if not owner or not owner.email:
                continue
            warned_for = getattr(sub, "overflow_warning_period_end", None)
            if warned_for and sub.current_period_end:
                warned = warned_for.replace(tzinfo=timezone.utc) if warned_for.tzinfo is None else warned_for
                period_end = sub.current_period_end.replace(tzinfo=timezone.utc) if sub.current_period_end.tzinfo is None else sub.current_period_end
                if abs((warned - period_end).total_seconds()) < 60:
                    continue
            plan = SubscriptionService.get_user_plan(db, owner)
            state = SubscriptionService.compute_overflow_state(db, owner, plan, sub)
            if not state["over_limit"]:
                continue
            subject = "AdMirra: превышение лимита перед продлением"
            body = (
                f"Здравствуйте!\n\nДо продления тарифа «{plan.name}» осталось 7 дней. "
                f"Сейчас используется {state['current']} проектных слотов при постоянном лимите "
                f"{state['effective_projects_limit']}.\n\nДо продления выберите один из вариантов:\n"
                "1. Докупить постоянный слот: https://admirra.ru/tariffs\n"
                "2. Перейти на старший тариф: https://admirra.ru/tariffs\n"
                "3. Поставить лишний проект на паузу, удалить его или объединить проекты в папку: "
                "https://admirra.ru/projects\n\n"
                "После второго продления подряд в превышении создание новых проектов будет приостановлено."
            )
            try:
                sent = await asyncio.to_thread(_send_sync, owner.email, subject, body)
            except Exception as error:
                logger.warning("Overflow warning email failed for account %s (%s)", owner.id, type(error).__name__)
                sent = False
            if sent:
                sub.overflow_warning_period_end = sub.current_period_end
                sent_count += 1
                db.commit()
            elif subscription_id is not None:
                raise BillingMaintenanceUncertain("Overflow email was not confirmed")
        return sent_count
    finally:
        db.close()


async def reconcile_recurring_totals(*, subscription_id=None, owner_id=None) -> int:
    """Повторяет временно не принятые CloudPayments изменения суммы."""
    from backend_api.billing import _normalize_billing_period, _update_recurrent_total
    from core import pricing
    from core.config import get_config

    db = SessionLocal()
    repaired = 0
    try:
        rows = _scoped(db.query(models.Subscription), subscription_id, owner_id).filter(
            models.Subscription.recurring_sync_required.is_(True),
            models.Subscription.cancel_at_period_end.is_(False),
            models.Subscription.cloudpayments_subscription_id.isnot(None),
        ).all()
        for sub in rows:
            owner = db.query(models.User).filter(models.User.id == sub.user_id).first()
            if not owner:
                continue
            pending_code = getattr(sub, "pending_plan_code", None)
            plan_code = pending_code or sub.plan_code or "start"
            fallback = pricing.resolve_plan(plan_code, get_config().billing)
            snapshot = (
                getattr(sub, "pending_price_book_snapshot", None)
                if pending_code
                else getattr(sub, "price_book_snapshot", None)
            )
            spec = pricing.plan_from_snapshot(snapshot, fallback)
            plan = SubscriptionService.get_plan_from_config(
                spec.code, spec=spec, price_fixed=bool(snapshot),
            )
            period = _normalize_billing_period(
                getattr(sub, "pending_billing_period", None) or sub.billing_period,
            )
            pending_slots = getattr(sub, "pending_purchased_project_slots", None)
            slots = (
                max(0, int(pending_slots))
                if pending_slots is not None
                else SubscriptionService._purchased_slots(sub)
            )
            if await _update_recurrent_total(sub, plan, period, slots, owner.email or ""):
                repaired += 1
                db.commit()
            else:
                db.rollback()
                if subscription_id is not None:
                    raise BillingMaintenanceUncertain("Recurring update was not confirmed")
        return repaired
    finally:
        db.close()
