import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session

from core import models
from core.config import get_config
from backend_api.services.cloudpayments import CloudPaymentsService
from backend_api.services.history import log_history_event
from backend_api.services.notifications import create_notification


@dataclass
class EffectivePlan:
    code: str
    name: str
    price_rub: int
    max_projects: int
    max_ai_requests_per_period: int
    period_days: int
    trial_days: int
    max_staff: int
    max_clients: int
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
                max_staff=cfg.plan_basic_max_staff,
                max_clients=cfg.plan_basic_max_clients,
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
                max_staff=cfg.plan_standard_max_staff,
                max_clients=cfg.plan_standard_max_clients,
            )
        if code in {"white_label", "whitelabel", "white-label"}:
            return EffectivePlan(
                code="white_label",
                name="White Label",
                price_rub=cfg.plan_standard_price_rub,
                max_projects=cfg.plan_standard_max_projects,
                max_ai_requests_per_period=cfg.plan_standard_ai_limit,
                period_days=cfg.ai_period_days,
                trial_days=cfg.trial_days,
                max_staff=cfg.plan_white_label_max_staff,
                max_clients=cfg.plan_white_label_max_clients,
            )
        return EffectivePlan(
            code="start",
            name="Старт",
            price_rub=cfg.plan_start_price_rub,
            max_projects=cfg.plan_start_max_projects,
            max_ai_requests_per_period=cfg.plan_start_ai_limit,
            period_days=cfg.ai_period_days,
            trial_days=cfg.trial_days,
            max_staff=cfg.plan_start_max_staff,
            max_clients=cfg.plan_start_max_clients,
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
                max_staff=getattr(plan_row, "max_staff", get_config().billing.plan_start_max_staff),
                max_clients=getattr(plan_row, "max_clients", get_config().billing.plan_start_max_clients),
                is_default=plan_row.is_default,
                is_active=plan_row.is_active,
            )
        return SubscriptionService.get_plan_from_config(plan_code)

    @staticmethod
    def _period_still_valid(sub: models.Subscription) -> bool:
        if sub.current_period_end is None:
            return True
        return sub.current_period_end >= SubscriptionService._now()

    @staticmethod
    def sync_user_subscription_access(
        db: Session, user: models.User, sub: models.Subscription
    ) -> bool:
        """
        Синхронизирует is_subscribed с оплаченным периодом.
        Отключение автоплатежа (cancel_at_period_end) не обрывает доступ до current_period_end.
        """
        if not SubscriptionService._period_still_valid(sub):
            if sub.status in {
                models.SubscriptionStatus.ACTIVE,
                models.SubscriptionStatus.TRIAL,
                models.SubscriptionStatus.CANCELED,
            }:
                sub.status = models.SubscriptionStatus.EXPIRED
            user.is_subscribed = False
            db.flush()
            return False

        if sub.status in {models.SubscriptionStatus.ACTIVE, models.SubscriptionStatus.TRIAL}:
            user.is_subscribed = True
            user.subscription_expires_at = sub.current_period_end
            db.flush()
            return True

        if sub.status == models.SubscriptionStatus.PAST_DUE:
            user.is_subscribed = False
            db.flush()
            return False

        user.is_subscribed = False
        db.flush()
        return False

    @staticmethod
    def _is_subscription_active(
        db: Session, user: models.User, sub: models.Subscription
    ) -> bool:
        return SubscriptionService.sync_user_subscription_access(db, user, sub)

    @staticmethod
    def subscription_status_label(sub: models.Subscription) -> str:
        if sub.cancel_at_period_end and sub.status in {
            models.SubscriptionStatus.ACTIVE,
            models.SubscriptionStatus.TRIAL,
        }:
            if SubscriptionService._period_still_valid(sub):
                return "Активна (автоплатёж отключён)"
        labels = {
            models.SubscriptionStatus.TRIAL: "Пробный период",
            models.SubscriptionStatus.ACTIVE: "Активна",
            models.SubscriptionStatus.PAST_DUE: "Ожидает оплаты",
            models.SubscriptionStatus.CANCELED: "Отменена",
            models.SubscriptionStatus.EXPIRED: "Истекла",
        }
        return labels.get(sub.status, sub.status.value)

    @staticmethod
    def payment_method_label(sub: models.Subscription) -> str:
        cp_id = (sub.cloudpayments_subscription_id or "").strip()
        if sub.cancel_at_period_end and sub.status in {
            models.SubscriptionStatus.ACTIVE,
            models.SubscriptionStatus.TRIAL,
        }:
            end = sub.current_period_end
            if end:
                return (
                    f"Автоплатёж отключён (доступ до {end.strftime('%d.%m.%Y')})"
                )
            return "Автоплатёж отключён"
        if cp_id and sub.status == models.SubscriptionStatus.ACTIVE:
            return "Банковская карта (автоплатёж CloudPayments)"
        if cp_id and sub.status in {
            models.SubscriptionStatus.PAST_DUE,
            models.SubscriptionStatus.CANCELED,
            models.SubscriptionStatus.EXPIRED,
        }:
            return "Банковская карта (автоплатёж отключён)"
        if sub.status == models.SubscriptionStatus.TRIAL:
            return "Пробный период (карта не привязана)"
        return "Не подключён"

    @staticmethod
    def autopay_enabled(sub: models.Subscription) -> bool:
        if sub.cancel_at_period_end:
            return False
        cp_id = (sub.cloudpayments_subscription_id or "").strip()
        return bool(cp_id) and sub.status in {
            models.SubscriptionStatus.ACTIVE,
            models.SubscriptionStatus.PAST_DUE,
        }

    @staticmethod
    def can_cancel_autopay(sub: models.Subscription) -> bool:
        if sub.cancel_at_period_end:
            return False
        cp_id = (sub.cloudpayments_subscription_id or "").strip()
        if not cp_id:
            return False
        return sub.status in {
            models.SubscriptionStatus.ACTIVE,
            models.SubscriptionStatus.PAST_DUE,
        }

    @staticmethod
    async def cancel_user_autopay(db: Session, user: models.User) -> models.Subscription:
        sub = SubscriptionService.ensure_default_subscription(db, user)
        cp_id = (sub.cloudpayments_subscription_id or "").strip()
        if not cp_id:
            raise HTTPException(
                status_code=400,
                detail="Автоплатёж не подключён — отменять нечего",
            )
        if sub.cancel_at_period_end:
            raise HTTPException(status_code=400, detail="Автоплатёж уже отключён")
        if not SubscriptionService.can_cancel_autopay(sub):
            raise HTTPException(
                status_code=400,
                detail="Нет активного автоплатежа для отмены",
            )

        cfg = get_config().cloudpayments
        if not cfg.api_secret:
            raise HTTPException(status_code=500, detail="CLOUDPAYMENTS_API_SECRET не настроен")

        try:
            result = await CloudPaymentsService.cancel_subscription(cp_id)
        except Exception as exc:
            raise HTTPException(
                status_code=502,
                detail=f"Не удалось отменить подписку в CloudPayments: {exc}",
            ) from exc

        if isinstance(result, dict) and result.get("Success") is False:
            message = str(result.get("Message") or result.get("message") or "Ошибка CloudPayments")
            raise HTTPException(status_code=502, detail=message)

        plan = SubscriptionService.get_user_plan(db, user)
        sub.cancel_at_period_end = True
        if sub.status not in {
            models.SubscriptionStatus.ACTIVE,
            models.SubscriptionStatus.TRIAL,
        }:
            sub.status = models.SubscriptionStatus.ACTIVE
        period_note = ""
        if sub.current_period_end:
            period_note = f" Доступ сохранён до {sub.current_period_end.strftime('%d.%m.%Y')}."
        SubscriptionService.sync_user_subscription_access(db, user, sub)
        create_notification(
            db,
            user_id=user.id,
            type="payment_ok",
            title="Автоплатёж отключён",
            body=f"Повторные списания по карте остановлены.{period_note}",
            meta={"plan_code": plan.code},
        )
        log_history_event(
            db,
            actor=user,
            event_type="billing",
            action="autopay_canceled",
            description="Автоплатёж отключён, подписка активна до конца оплаченного периода",
            target_type="subscription",
            target_id=str(sub.id),
            meta={"plan_code": plan.code, "cloudpayments_subscription_id": cp_id},
        )
        db.flush()
        return sub

    @staticmethod
    def require_active_subscription(db: Session, user: models.User) -> None:
        if SubscriptionService.is_admin_bypass(user):
            return
        sub = SubscriptionService.ensure_default_subscription(db, user)
        if SubscriptionService._is_subscription_active(db, user, sub):
            return
        if not SubscriptionService.billing_enforced():
            return
        raise HTTPException(status_code=402, detail="Подписка неактивна")

    @staticmethod
    def ensure_can_create_project(db: Session, user: models.User) -> None:
        if SubscriptionService.is_admin_bypass(user):
            return
        plan = SubscriptionService.get_user_plan(db, user)
        clients_count = db.query(models.Client).filter(models.Client.owner_id == user.id).count()
        phone_count = db.query(models.PhoneProject).filter(models.PhoneProject.owner_id == user.id).count()
        total = clients_count + phone_count
        if total < plan.max_projects:
            return
        if not SubscriptionService.billing_enforced():
            return
        log_history_event(
            db,
            actor=user,
            event_type="limit",
            action="project_limit_reached",
            description=f"Достигнут лимит проектов ({plan.max_projects})",
            target_type="subscription",
            meta={"plan_code": plan.code, "limit": plan.max_projects, "current_total": total},
        )
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
        quota_user = SubscriptionService._resolve_ai_quota_user(db, user)
        if SubscriptionService.is_admin_bypass(quota_user):
            return
        SubscriptionService.require_active_subscription(db, quota_user)
        plan = SubscriptionService.get_user_plan(db, quota_user)
        SubscriptionService._ensure_ai_period(quota_user, plan)
        used = int(quota_user.ai_requests_used or 0)
        limit = int(plan.max_ai_requests_per_period or 0)
        if used + max(requested, 1) <= limit:
            return
        if not SubscriptionService.billing_enforced():
            return
        # Создаём уведомление о превышении лимита (только если billing_enforced)
        try:
            from backend_api.services.notifications import create_notification
            create_notification(
                db,
                user_id=quota_user.id,
                type="limit_warn",
                title="Лимит AI-запросов исчерпан",
                body=f"Вы использовали все {limit} AI-запросов за текущий период. Перейдите на более высокий тариф.",
                meta={"plan_code": plan.code, "limit": limit},
            )
            db.flush()
        except Exception:
            pass
        log_history_event(
            db,
            actor=user,
            event_type="limit",
            action="ai_limit_reached",
            description=f"Достигнут лимит AI-запросов ({limit})",
            target_type="subscription",
            meta={"plan_code": plan.code, "limit": limit, "used": used},
        )
        raise HTTPException(
            status_code=429,
            detail=f"Превышен лимит AI-запросов для тарифа '{plan.name}' ({limit} за период)",
        )

    @staticmethod
    def increment_ai_usage(db: Session, user: models.User, requested: int = 1) -> None:
        quota_user = SubscriptionService._resolve_ai_quota_user(db, user)
        if SubscriptionService.is_admin_bypass(quota_user):
            return
        plan = SubscriptionService.get_user_plan(db, quota_user)
        SubscriptionService._ensure_ai_period(quota_user, plan)
        quota_user.ai_requests_used = int(quota_user.ai_requests_used or 0) + max(requested, 1)
        db.flush()

    @staticmethod
    def _resolve_ai_quota_user(db: Session, user: models.User) -> models.User:
        membership = (
            db.query(models.TeamMember)
            .filter(
                models.TeamMember.user_id == user.id,
                models.TeamMember.status == models.TeamMemberStatus.ACTIVE,
            )
            .first()
        )
        if membership and membership.account_id:
            owner = db.query(models.User).filter(models.User.id == membership.account_id).first()
            if owner:
                return owner
        return user

