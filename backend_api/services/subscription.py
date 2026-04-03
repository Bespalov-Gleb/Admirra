import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session

from core import models
from core.config import get_config


@dataclass
class EffectivePlan:
    code: str
    name: str
    price_rub: int
    max_projects: int
    max_ai_requests_per_period: int
    period_days: int
    trial_days: int
    is_default: bool = False
    is_active: bool = True


class SubscriptionService:
    @staticmethod
    def _now() -> datetime:
        return datetime.now(timezone.utc)

    @staticmethod
    def _admin_whitelist() -> set[str]:
        cfg = get_config()
        raw = (cfg.billing.billing_admin_whitelist or "").strip()
        if not raw:
            return set()
        return {x.strip().lower() for x in raw.split(",") if x.strip()}

    @staticmethod
    def is_admin_bypass(user: models.User) -> bool:
        if user.role == models.UserRole.ADMIN:
            return True
        whitelist = SubscriptionService._admin_whitelist()
        if not whitelist:
            return False
        return str(user.id).lower() in whitelist or (user.email or "").lower() in whitelist

    @staticmethod
    def billing_enabled() -> bool:
        return get_config().billing.billing_enabled

    @staticmethod
    def billing_enforced() -> bool:
        cfg = get_config()
        return cfg.billing.billing_enabled and cfg.billing.billing_enforce_limits

    @staticmethod
    def get_plan_from_config(plan_code: str) -> EffectivePlan:
        cfg = get_config().billing
        code = (plan_code or "start").strip().lower()
        if code == "basic":
            return EffectivePlan(
                code="basic",
                name="Базовый",
                price_rub=cfg.plan_basic_price_rub,
                max_projects=cfg.plan_basic_max_projects,
                max_ai_requests_per_period=cfg.plan_basic_ai_limit,
                period_days=cfg.ai_period_days,
                trial_days=cfg.trial_days,
            )
        if code == "standard":
            return EffectivePlan(
                code="standard",
                name="Стандартный",
                price_rub=cfg.plan_standard_price_rub,
                max_projects=cfg.plan_standard_max_projects,
                max_ai_requests_per_period=cfg.plan_standard_ai_limit,
                period_days=cfg.ai_period_days,
                trial_days=cfg.trial_days,
            )
        return EffectivePlan(
            code="start",
            name="Старт",
            price_rub=cfg.plan_start_price_rub,
            max_projects=cfg.plan_start_max_projects,
            max_ai_requests_per_period=cfg.plan_start_ai_limit,
            period_days=cfg.ai_period_days,
            trial_days=cfg.trial_days,
            is_default=True,
        )

    @staticmethod
    def get_user_subscription(db: Session, user_id: uuid.UUID) -> Optional[models.Subscription]:
        return (
            db.query(models.Subscription)
            .filter(models.Subscription.user_id == user_id)
            .order_by(models.Subscription.created_at.desc())
            .first()
        )

    @staticmethod
    def ensure_default_subscription(db: Session, user: models.User) -> models.Subscription:
        sub = SubscriptionService.get_user_subscription(db, user.id)
        if sub:
            return sub

        plan = SubscriptionService.get_plan_from_config("start")
        now = SubscriptionService._now()
        sub = models.Subscription(
            user_id=user.id,
            plan_code=plan.code,
            status=models.SubscriptionStatus.TRIAL,
            current_period_start=now,
            current_period_end=now + timedelta(days=plan.trial_days),
            cancel_at_period_end=False,
        )
        db.add(sub)
        user.is_subscribed = True
        user.subscription_expires_at = sub.current_period_end
        db.flush()
        return sub

    @staticmethod
    def get_user_plan(db: Session, user: models.User) -> EffectivePlan:
        sub = SubscriptionService.ensure_default_subscription(db, user)
        plan_code = sub.plan_code or "start"

        plan_row = (
            db.query(models.TariffPlan)
            .filter(models.TariffPlan.code == plan_code, models.TariffPlan.is_active.is_(True))
            .first()
        )
        if plan_row:
            return EffectivePlan(
                code=plan_row.code,
                name=plan_row.name,
                price_rub=plan_row.price_rub,
                max_projects=plan_row.max_projects,
                max_ai_requests_per_period=plan_row.max_ai_requests_per_period,
                period_days=plan_row.period_days,
                trial_days=plan_row.trial_days,
                is_default=plan_row.is_default,
                is_active=plan_row.is_active,
            )
        return SubscriptionService.get_plan_from_config(plan_code)

    @staticmethod
    def _is_subscription_active(user: models.User, sub: models.Subscription) -> bool:
        if sub.status in {models.SubscriptionStatus.ACTIVE, models.SubscriptionStatus.TRIAL}:
            if sub.current_period_end is None:
                return True
            return sub.current_period_end >= SubscriptionService._now()
        return False

    @staticmethod
    def require_active_subscription(db: Session, user: models.User) -> None:
        if SubscriptionService.is_admin_bypass(user):
            return
        sub = SubscriptionService.ensure_default_subscription(db, user)
        if SubscriptionService._is_subscription_active(user, sub):
            return
        if not SubscriptionService.billing_enforced():
            return
        raise HTTPException(status_code=402, detail="Подписка неактивна")

    @staticmethod
    def ensure_can_create_project(db: Session, user: models.User) -> None:
        if SubscriptionService.is_admin_bypass(user):
            return
        plan = SubscriptionService.get_user_plan(db, user)
        projects_count = db.query(models.Client).filter(models.Client.owner_id == user.id).count()
        if projects_count < plan.max_projects:
            return
        if not SubscriptionService.billing_enforced():
            return
        raise HTTPException(
            status_code=403,
            detail=f"Достигнут лимит проектов для тарифа '{plan.name}' ({plan.max_projects})",
        )

    @staticmethod
    def _ensure_ai_period(user: models.User, plan: EffectivePlan) -> None:
        now = SubscriptionService._now()
        started = user.ai_requests_period_started_at
        if started is None:
            user.ai_requests_period_started_at = now
            user.ai_requests_used = 0
            return
        if started.tzinfo is None:
            started = started.replace(tzinfo=timezone.utc)
        if now - started >= timedelta(days=plan.period_days):
            user.ai_requests_period_started_at = now
            user.ai_requests_used = 0

    @staticmethod
    def ensure_can_use_ai(db: Session, user: models.User, requested: int = 1) -> None:
        if SubscriptionService.is_admin_bypass(user):
            return
        SubscriptionService.require_active_subscription(db, user)
        plan = SubscriptionService.get_user_plan(db, user)
        SubscriptionService._ensure_ai_period(user, plan)
        used = int(user.ai_requests_used or 0)
        limit = int(plan.max_ai_requests_per_period or 0)
        if used + max(requested, 1) <= limit:
            return
        if not SubscriptionService.billing_enforced():
            return
        raise HTTPException(
            status_code=429,
            detail=f"Превышен лимит AI-запросов для тарифа '{plan.name}' ({limit} за период)",
        )

    @staticmethod
    def increment_ai_usage(db: Session, user: models.User, requested: int = 1) -> None:
        if SubscriptionService.is_admin_bypass(user):
            return
        plan = SubscriptionService.get_user_plan(db, user)
        SubscriptionService._ensure_ai_period(user, plan)
        user.ai_requests_used = int(user.ai_requests_used or 0) + max(requested, 1)
        db.flush()

