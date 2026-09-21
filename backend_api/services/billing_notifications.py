"""Фоновые уведомления экономики подписки."""

import asyncio
import logging
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

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


async def _send_scoped_warning(subscription_id, owner_id, period_end, email, subject, body):
    """No ORM/session survives SMTP; confirmation must target the same period."""
    try:
        sent = await asyncio.to_thread(_send_sync, email, subject, body)
    except Exception as error:
        logger.warning("Scoped overflow email failed (%s)", type(error).__name__)
        raise BillingMaintenanceUncertain("Overflow email was not confirmed") from None
    if not sent:
        raise BillingMaintenanceUncertain("Overflow email was not confirmed")
    with SessionLocal.begin() as db:
        sub = _scoped(db.query(models.Subscription), subscription_id, owner_id).filter(
            models.Subscription.current_period_end == period_end,
        ).with_for_update().first()
        if sub is None:
            raise BillingMaintenanceUncertain("Subscription changed while email was being sent")
        sub.overflow_warning_period_end = period_end
    return 1


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
            if subscription_id is None:
                plan = SubscriptionService.get_user_plan(db, owner)
            else:
                # Scoped preparation is read-only and uses THIS subscription,
                # not an account helper that may create/select another record.
                from core import pricing
                from core.config import get_config
                fallback = pricing.resolve_plan(sub.plan_code or "start", get_config().billing)
                snapshot = sub.price_book_snapshot
                spec = pricing.plan_from_snapshot(snapshot, fallback)
                plan = SubscriptionService.get_plan_from_config(spec.code, spec=spec, price_fixed=bool(snapshot))
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
            if subscription_id is not None:
                args = (sub.id, owner.id, sub.current_period_end, owner.email, subject, body)
                db.close()
                return await _send_scoped_warning(*args)
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


def _recurring_snapshot(sub):
    # Compare the complete row, including pending tariff/slot changes and period.
    # JSON price books must not share mutable references with the ORM instance.
    return {column.key: deepcopy(getattr(sub, column.key)) for column in models.Subscription.__table__.columns}


def _recurring_terms(sub):
    from backend_api.billing import _normalize_billing_period
    from core import pricing
    from core.config import get_config

    pending_code = sub.pending_plan_code
    fallback = pricing.resolve_plan(pending_code or sub.plan_code or "start", get_config().billing)
    snapshot = sub.pending_price_book_snapshot if pending_code else sub.price_book_snapshot
    spec = pricing.plan_from_snapshot(snapshot, fallback)
    plan = SubscriptionService.get_plan_from_config(spec.code, spec=spec, price_fixed=bool(snapshot))
    period = _normalize_billing_period(sub.pending_billing_period or sub.billing_period)
    slots = (max(0, int(sub.pending_purchased_project_slots))
             if sub.pending_purchased_project_slots is not None else SubscriptionService._purchased_slots(sub))
    return plan, period, slots


def _matches_recurring(db, sub, snapshot, email):
    if sub is None or _recurring_snapshot(sub) != snapshot:
        return False
    owner = db.query(models.User).filter(models.User.id == snapshot["user_id"]).first()
    return owner is not None and (owner.email or "") == email


async def _reconcile_scoped_recurring(subscription_id, owner_id):
    """Prepare -> release SQL -> provider IO -> fenced conditional confirmation.

    This detects concurrent cancellation/edits; it does not serialize the legacy
    API's external operations. A changed/unknown result remains uncertain in the
    durable ledger, not an automatic retry or an assertion of provider state.
    """
    from backend_api.billing import _update_recurrent_total

    with SessionLocal.begin() as db:
        sub = _scoped(db.query(models.Subscription), subscription_id, owner_id).filter(
            models.Subscription.recurring_sync_required.is_(True),
            models.Subscription.cancel_at_period_end.is_(False),
            models.Subscription.cloudpayments_subscription_id.isnot(None),
        ).first()
        if sub is None or not str(sub.cloudpayments_subscription_id or "").strip():
            return 0
        owner = db.query(models.User).filter(models.User.id == owner_id).first()
        if owner is None:
            return 0
        snapshot, email = _recurring_snapshot(sub), owner.email or ""
        plan, period, slots = _recurring_terms(sub)

    # Recheck after preparation and validate the execution fence before IO.
    # No session/row lock is held while waiting for the payment provider.
    with SessionLocal.begin() as db:
        sub = _scoped(db.query(models.Subscription), subscription_id, owner_id).first()
        if not _matches_recurring(db, sub, snapshot, email):
            return 0
    try:
        confirmed = await _update_recurrent_total(SimpleNamespace(**deepcopy(snapshot)), plan, period, slots, email)
    except Exception:
        raise BillingMaintenanceUncertain("Recurring update was not confirmed") from None
    if not confirmed:
        raise BillingMaintenanceUncertain("Recurring update was not confirmed")

    with SessionLocal.begin() as db:
        sub = _scoped(db.query(models.Subscription), subscription_id, owner_id).with_for_update().first()
        if not _matches_recurring(db, sub, snapshot, email):
            raise BillingMaintenanceUncertain("Subscription changed during recurring update; reconcile provider state")
        sub.recurring_sync_required = False
    return 1


async def reconcile_recurring_totals(*, subscription_id=None, owner_id=None) -> int:
    """Повторяет временно не принятые CloudPayments изменения суммы."""
    from backend_api.billing import _normalize_billing_period, _update_recurrent_total
    from core import pricing
    from core.config import get_config

    if (subscription_id is None) != (owner_id is None):
        raise ValueError("Subscription and owner must be specified together")
    if subscription_id is not None:
        return await _reconcile_scoped_recurring(subscription_id, owner_id)

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
