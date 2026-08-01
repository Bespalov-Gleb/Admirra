import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session

from core import models, pricing
from core.config import get_config
from backend_api.services.history import log_history_event

# Обратная совместимость: у поля max_clients нет места в новой линейке §4,
# поэтому продолжаем брать его из старого конфига по каноническому коду.
_MAX_CLIENTS_ENV = {
    "start": "plan_start_max_clients",
    "agency": "plan_basic_max_clients",
    "pro": "plan_standard_max_clients",
}


@dataclass
class EffectivePlan:
    code: str
    name: str
    price_rub: int
    max_projects: int
    max_ai_requests_per_period: int
    period_days: int
    trial_days: int
    max_cabinets: int
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
        if user.role in {
            models.UserRole.ADMIN,
            models.UserRole.SUPERADMIN,
            models.UserRole.DEVELOPER,
        }:
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
        """Единый источник — прайс-бук `core.pricing`. Коды basic/standard из
        БД до миграции §7.3 понимаются как agency/pro через алиасы резолвера."""
        cfg = get_config().billing
        spec = pricing.resolve_plan(plan_code, cfg)
        clients_attr = _MAX_CLIENTS_ENV.get(spec.code)
        max_clients = getattr(cfg, clients_attr) if clients_attr else -1
        return EffectivePlan(
            code=spec.code,
            name=spec.title,
            price_rub=spec.price_month,
            max_projects=spec.projects_limit,
            max_ai_requests_per_period=spec.ai_requests_limit,
            period_days=cfg.ai_period_days,
            trial_days=cfg.trial_days,
            max_cabinets=spec.cabinets_limit,
            max_staff=spec.users_limit,
            max_clients=max_clients,
            is_default=spec.is_default,
            is_active=spec.visible,
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
    def _apply_pending_plan(sub: models.Subscription) -> None:
        """Применяет отложенное понижение тарифа, когда оплаченный период истёк.

        Понижение не забирает уже оплаченный уровень: оно записывается в
        pending_plan_code и вступает в силу здесь. Отдельного шедулера в проекте
        нет, поэтому применяем лениво — на любом чтении подписки.
        """
        pending = getattr(sub, "pending_plan_code", None)
        if not pending:
            return
        if sub.current_period_end and sub.current_period_end > SubscriptionService._now():
            return
        sub.plan_code = pending
        sub.pending_plan_code = None

    @staticmethod
    def ensure_default_subscription(db: Session, user: models.User) -> models.Subscription:
        sub = SubscriptionService.get_user_subscription(db, user.id)
        if sub:
            SubscriptionService._apply_pending_plan(sub)
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
        """Единственный источник истины по тарифам — конфигурация (env + дефолты).

        Раньше здесь сначала читалась строка из tariff_plans, и только при её
        отсутствии брался конфиг. На проде таблица пустая, то есть фактически
        всегда работал конфиг, но развилка оставалась молчаливой миной: стоило
        кому-то завести строку — цены и лимиты менялись бы наполовину, потому что
        колонок max_cabinets/max_staff/max_clients в таблице нет вовсе, и они всё
        равно доставались бы из конфига.

        Если понадобится управлять тарифами из БД, это нужно делать осознанно:
        добавить недостающие колонки, засеять таблицу и убрать конфиг — а не
        держать два источника одновременно.
        """
        sub = SubscriptionService.ensure_default_subscription(db, user)
        return SubscriptionService.get_plan_from_config(sub.plan_code or "start")

    @staticmethod
    def _is_subscription_active(user: models.User, sub: models.Subscription) -> bool:
        if sub.status in {models.SubscriptionStatus.ACTIVE, models.SubscriptionStatus.TRIAL}:
            if sub.current_period_end is None:
                return True
            return sub.current_period_end >= SubscriptionService._now()
        # Отменённая подписка сохраняет доступ до конца ОПЛАЧЕННОГО периода — это
        # обещано и в интерфейсе («Доступ сохранится до …»), и в docstring
        # эндпоинта отмены. Раньше CANCELED отсекался сразу, и пользователь терял
        # доступ в тот же момент, хотя период был оплачен: отмена автопродления
        # гасит рекуррент в CloudPayments, оттуда приходит Recurrent(Cancelled),
        # вебхук ставил CANCELED — и require_active_subscription отдавал 402.
        # PAST_DUE — та же логика: неудачное списание не отбирает период, за
        # который уже заплачено. Обычно он к этому моменту истёк, и доступ
        # закроется сам по дате.
        if sub.status in {models.SubscriptionStatus.CANCELED, models.SubscriptionStatus.PAST_DUE}:
            return bool(sub.current_period_end) and sub.current_period_end >= SubscriptionService._now()
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
    def cabinet_limit_for_plan(plan_code: str) -> int:
        return pricing.cabinet_limit_for_plan(plan_code, get_config().billing)

    @staticmethod
    def count_project_slots(db: Session, user_id) -> int:
        """Слоты тарифа считаются по элементам ВЕРХНЕГО уровня списка проектов:
        активные проекты вне папок + папки, содержащие хотя бы один активный проект
        (папка = 1 слот независимо от числа филиалов). Проекты на паузе и папки,
        где все проекты на паузе, слот не занимают."""
        outside = db.query(models.Client).filter(
            models.Client.owner_id == user_id,
            models.Client.status == models.ClientStatus.ACTIVE,
            models.Client.folder_id.is_(None),
        ).count()
        folders_with_active = (
            db.query(models.Client.folder_id)
            .filter(
                models.Client.owner_id == user_id,
                models.Client.status == models.ClientStatus.ACTIVE,
                models.Client.folder_id.isnot(None),
            )
            .distinct()
            .count()
        )
        phone_count = db.query(models.PhoneProject).filter(models.PhoneProject.owner_id == user_id).count()
        return outside + folders_with_active + phone_count

    # --- Граница тарифа: эффективные лимиты и состояние превышения (§8) ---

    @staticmethod
    def _purchased_slots(sub) -> int:
        return int(getattr(sub, "purchased_project_slots", 0) or 0) if sub else 0

    @staticmethod
    def effective_projects_limit(plan: EffectivePlan, sub) -> int:
        # Эффективный лимит = лимит тарифа + докупленные слоты (§8.6).
        return int(plan.max_projects) + SubscriptionService._purchased_slots(sub)

    @staticmethod
    def effective_cabinets_limit(plan: EffectivePlan, sub) -> int:
        # Слот даёт +3 кабинета (§8.2), иначе купленный слот был бы нерабочим.
        extra = pricing.resolve_plan(plan.code).extra_project_cabinets
        base = int(getattr(plan, "max_cabinets", 0) or SubscriptionService.cabinet_limit_for_plan(plan.code))
        return base + SubscriptionService._purchased_slots(sub) * extra

    @staticmethod
    def compute_overflow_state(db: Session, user: models.User, plan: EffectivePlan, sub) -> dict:
        """Состояние превышения для API экрана подписки (§8.6). Фронт эти значения
        не считает сам."""
        spec = pricing.resolve_plan(plan.code)
        slots = SubscriptionService._purchased_slots(sub)
        effective = SubscriptionService.effective_projects_limit(plan, sub)
        allowance = spec.overflow_allowance_projects
        total = SubscriptionService.count_project_slots(db, user.id)
        over_limit = total > effective
        periods = int(getattr(sub, "overflow_periods_count", 0) or 0)
        return {
            "current": total,
            "effective_projects_limit": effective,
            "purchased_slots": slots,
            "slot_price": spec.extra_project_price_month,
            "slots_until_parity": pricing.slots_until_parity(plan.code, slots),
            "over_limit": over_limit,
            "over_by": max(0, total - effective),
            "allowance": allowance,
            "allowance_left": max(0, effective + allowance - total),
            "overflow_deadline": (
                sub.current_period_end.isoformat()
                if over_limit and sub and getattr(sub, "current_period_end", None)
                else None
            ),
            "hard_blocked": over_limit and periods >= 2,
            "suggested_plan": pricing.next_plan_code(plan.code),
        }

    @staticmethod
    def ensure_can_create_project(db: Session, user: models.User, confirmed_overflow: bool = False) -> None:
        if SubscriptionService.is_admin_bypass(user):
            return
        plan = SubscriptionService.get_user_plan(db, user)
        sub = SubscriptionService.get_user_subscription(db, user.id)
        total = SubscriptionService.count_project_slots(db, user.id)
        effective = SubscriptionService.effective_projects_limit(plan, sub)
        if total < effective:
            return
        if not SubscriptionService.billing_enforced():
            return

        spec = pricing.resolve_plan(plan.code)
        allowance = spec.overflow_allowance_projects
        periods = int(getattr(sub, "overflow_periods_count", 0) or 0)
        # 2-е продление подряд в превышении блокирует создание новых (§8.3).
        hard_blocked = periods >= 2
        within_allowance = (not hard_blocked) and (total < effective + allowance)

        if within_allowance and confirmed_overflow:
            now = SubscriptionService._now()
            first_time = sub is not None and not getattr(sub, "overflow_since", None)
            if first_time:
                sub.overflow_since = now
                db.flush()
            log_history_event(
                db, actor=user, event_type="limit",
                action="overflow_entered" if first_time else "overflow_confirmed",
                description=f"Проект сверх лимита ({total + 1} из {effective})",
                target_type="subscription",
                meta={"plan_code": plan.code, "limit": effective, "current_total": total, "allowance": allowance},
            )
            return

        reason = (
            "confirmation_required" if within_allowance
            else "overflow_hard_blocked" if hard_blocked
            else "overflow_limit_reached"
        )
        message = (
            f"Это {total + 1}-й проект из {effective} на тарифе «{plan.name}»."
            if within_allowance
            else f"Достигнут предел проектов на тарифе «{plan.name}»: {effective} + запас {allowance}."
        )
        log_history_event(
            db, actor=user, event_type="limit",
            action="limit_reached" if within_allowance else "overflow_blocked",
            description=message, target_type="subscription",
            meta={"plan_code": plan.code, "limit": effective, "current_total": total,
                  "allowance": allowance, "reason": reason},
        )
        raise HTTPException(status_code=409, detail={
            "reason": reason,
            "type": "project",
            "plan_code": plan.code,
            "plan_name": plan.name,
            "limit": effective,
            "allowance": allowance,
            "allowance_left": max(0, effective + allowance - total),
            "current": total,
            "slot_price": spec.extra_project_price_month,
            "slots_until_parity": pricing.slots_until_parity(plan.code, SubscriptionService._purchased_slots(sub)),
            "suggested_plan": pricing.next_plan_code(plan.code),
            "message": message,
        })

    @staticmethod
    def ensure_can_create_cabinet(db: Session, user: models.User) -> None:
        if SubscriptionService.is_admin_bypass(user):
            return
        plan = SubscriptionService.get_user_plan(db, user)
        sub = SubscriptionService.get_user_subscription(db, user.id)
        # Кабинеты получают фиксированный запас +2 (§8.3), но без модалки: тихо
        # пропускаем в пределах запаса, дальше — стоп.
        effective = SubscriptionService.effective_cabinets_limit(plan, sub)
        limit = effective + 2
        total = (
            db.query(models.Integration.id)
            .join(models.Client, models.Client.id == models.Integration.client_id)
            .filter(models.Client.owner_id == user.id)
            .count()
        )
        if total < limit:
            return
        if not SubscriptionService.billing_enforced():
            return
        log_history_event(
            db,
            actor=user,
            event_type="limit",
            action="cabinet_limit_reached",
            description=f"Достигнут лимит кабинетов ({effective})",
            target_type="subscription",
            meta={"plan_code": plan.code, "limit": effective, "current_total": total},
        )
        raise HTTPException(
            status_code=403,
            detail=f"Достигнут лимит кабинетов для тарифа '{plan.name}' ({effective})",
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
