"""Метрики дашборда суперадмина (ТЗ: churn без триала, MRR только платящие)."""
from datetime import datetime, timedelta, timezone

from sqlalchemy import func
from sqlalchemy.orm import Session

from core import models
from backend_api.services.subscription import SubscriptionService


def _int(v) -> int:
    try:
        return int(v or 0)
    except Exception:
        return 0


def paying_subscriptions_query(db: Session):
    """Активные платные подписки (без триала)."""
    return db.query(models.Subscription).filter(models.Subscription.status == models.SubscriptionStatus.ACTIVE)


def calc_mrr_rub(db: Session) -> int:
    subs = paying_subscriptions_query(db).all()
    return sum(_int(SubscriptionService.get_plan_from_config(s.plan_code or "start").price_rub) for s in subs)


def calc_churn_rate_percent(db: Session, dt_from: datetime, dt_to: datetime) -> float:
    """
    Churn = отписались за период / платящих на начало периода × 100%.
    Триал не учитывается.
    """
    paying_at_start = (
        db.query(func.count(models.Subscription.id))
        .filter(
            models.Subscription.status == models.SubscriptionStatus.ACTIVE,
            models.Subscription.created_at < dt_from,
        )
        .scalar()
        or 0
    )
    if paying_at_start == 0:
        return 0.0
    churned = (
        db.query(func.count(models.Subscription.id))
        .filter(
            models.Subscription.status.in_(
                [models.SubscriptionStatus.CANCELED, models.SubscriptionStatus.EXPIRED]
            ),
            models.Subscription.updated_at >= dt_from,
            models.Subscription.updated_at < dt_to,
        )
        .scalar()
        or 0
    )
    return round(churned / paying_at_start * 100, 2)
