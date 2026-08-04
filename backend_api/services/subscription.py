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
    price_year_rub: int
    max_projects: int
    max_ai_requests_per_period: int
    period_days: int
    trial_days: int
    max_cabinets: int
    max_staff: int
    max_clients: int
    overflow_allowance_projects: int = 0
    overflow_allowance_cabinets: int = 0
    extra_project_price_month: int = 0
    extra_project_price_year: int = 0
    extra_project_cabinets: int = 3
    max_extra_project_slots: int = 0
    comments_soft_cap: int = 0
    price_fixed: bool = False
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
    def get_plan_from_config(plan_code: str, *, spec: Optional[pricing.PlanSpec] = None, price_fixed: bool = False) -> EffectivePlan:
        """Единый источник — прайс-бук `core.pricing`. Коды basic/standard из
        БД до миграции §7.3 понимаются как agency/pro через алиасы резолвера."""
        cfg = get_config().billing
        spec = spec or pricing.resolve_plan(plan_code, cfg)
        clients_attr = _MAX_CLIENTS_ENV.get(spec.code)
        max_clients = getattr(cfg, clients_attr) if clients_attr else -1
        return EffectivePlan(
            code=spec.code,
            name=spec.title,
            price_rub=spec.price_month,
            price_year_rub=spec.price_year,
            max_projects=spec.projects_limit,
            max_ai_requests_per_period=spec.ai_requests_limit,
            period_days=cfg.ai_period_days,
            trial_days=cfg.trial_days,
            max_cabinets=spec.cabinets_limit,
            max_staff=spec.users_limit,
            max_clients=max_clients,
            overflow_allowance_projects=spec.overflow_allowance_projects,
            overflow_allowance_cabinets=spec.overflow_allowance_cabinets,
            extra_project_price_month=spec.extra_project_price_month,
            extra_project_price_year=spec.extra_project_price_year,
            extra_project_cabinets=spec.extra_project_cabinets,
            max_extra_project_slots=spec.max_extra_project_slots,
            comments_soft_cap=spec.effective_comments_soft_cap,
            price_fixed=price_fixed,
            is_default=spec.is_default,
            is_active=spec.visible,
        )

    @staticmethod
    def get_user_subscription(
        db: Session,
        user_id: uuid.UUID,
        *,
        for_update: bool = False,
    ) -> Optional[models.Subscription]:
        query = (
            db.query(models.Subscription)
            .filter(models.Subscription.user_id == user_id)
            .order_by(models.Subscription.created_at.desc())
        )
        if for_update:
            query = query.with_for_update()
        return query.first()

    @staticmethod
    def get_billing_account_user(db: Session, user: models.User) -> models.User:
        """Возвращает владельца аккаунта, чьи тариф и лимиты делит команда."""
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

    @staticmethod
    def account_project_owner_ids(db: Session, account_id: uuid.UUID) -> list[uuid.UUID]:
        """Владелец плюс активные участники — для совместимости со старыми проектами.

        Новые проекты участника записываются сразу на владельца, но уже созданные
        до исправления нельзя терять из расчёта лимитов.
        """
        rows = (
            db.query(models.TeamMember.user_id)
            .filter(
                models.TeamMember.account_id == account_id,
                models.TeamMember.status == models.TeamMemberStatus.ACTIVE,
                models.TeamMember.user_id.isnot(None),
            )
            .all()
        )
        return [account_id, *[row[0] for row in rows if row[0] != account_id]]

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
        pending_period = getattr(sub, "pending_billing_period", None)
        if pending_period:
            sub.billing_period = pending_period
        pending_slots = getattr(sub, "pending_purchased_project_slots", None)
        if pending_slots is not None:
            sub.purchased_project_slots = max(0, int(pending_slots))
        pending_snapshot = getattr(sub, "pending_price_book_snapshot", None)
        if pending_snapshot:
            sub.price_book_snapshot = pending_snapshot
            sub.price_book_version = int(
                pending_snapshot.get("_price_book_version")
                or pricing.current_price_book_version()
            )
        sub.pending_plan_code = None
        sub.pending_billing_period = None
        sub.pending_purchased_project_slots = None
        sub.pending_price_book_snapshot = None

    @staticmethod
    def ensure_default_subscription(db: Session, user: models.User) -> models.Subscription:
        account_user = SubscriptionService.get_billing_account_user(db, user)
        sub = SubscriptionService.get_user_subscription(db, account_user.id)
        if sub:
            SubscriptionService._apply_pending_plan(sub)
            return sub

        plan = SubscriptionService.get_plan_from_config("start")
        now = SubscriptionService._now()
        sub = models.Subscription(
            user_id=account_user.id,
            plan_code=plan.code,
            status=models.SubscriptionStatus.TRIAL,
            current_period_start=now,
            current_period_end=now + timedelta(days=plan.trial_days),
            cancel_at_period_end=False,
            price_book_version=pricing.current_price_book_version(),
            price_book_snapshot=pricing.plan_snapshot(pricing.resolve_plan(plan.code)),
        )
        db.add(sub)
        account_user.is_subscribed = True
        account_user.subscription_expires_at = sub.current_period_end
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
        account_user = SubscriptionService.get_billing_account_user(db, user)
        sub = SubscriptionService.ensure_default_subscription(db, account_user)
        fallback = pricing.resolve_plan(sub.plan_code or "start", get_config().billing)
        snap = getattr(sub, "price_book_snapshot", None)
        spec = pricing.plan_from_snapshot(snap, fallback)
        if not snap:
            sub.price_book_version = pricing.current_price_book_version()
            sub.price_book_snapshot = pricing.plan_snapshot(spec)
            db.flush()
        return SubscriptionService.get_plan_from_config(
            spec.code,
            spec=spec,
            price_fixed=bool(getattr(sub, "price_book_snapshot", None)) and (
                int(getattr(sub, "price_book_version", 0) or 0)
                != pricing.current_price_book_version()
            ),
        )

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
        account_user = SubscriptionService.get_billing_account_user(db, user)
        sub = SubscriptionService.ensure_default_subscription(db, account_user)
        if SubscriptionService._is_subscription_active(account_user, sub):
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
        owner_ids = SubscriptionService.account_project_owner_ids(db, user_id)
        outside = db.query(models.Client).filter(
            models.Client.owner_id.in_(owner_ids),
            models.Client.status == models.ClientStatus.ACTIVE,
            models.Client.folder_id.is_(None),
        ).count()
        folders_with_active = (
            db.query(models.Client.folder_id)
            .filter(
                models.Client.owner_id.in_(owner_ids),
                models.Client.status == models.ClientStatus.ACTIVE,
                models.Client.folder_id.isnot(None),
            )
            .distinct()
            .count()
        )
        phone_count = db.query(models.PhoneProject).filter(
            models.PhoneProject.owner_id.in_(owner_ids),
            models.PhoneProject.is_active.is_(True),
        ).count()
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
        extra = int(getattr(plan, "extra_project_cabinets", 0) or 3)
        base = int(getattr(plan, "max_cabinets", 0) or SubscriptionService.cabinet_limit_for_plan(plan.code))
        return base + SubscriptionService._purchased_slots(sub) * extra

    @staticmethod
    def compute_overflow_state(db: Session, user: models.User, plan: EffectivePlan, sub) -> dict:
        """Состояние превышения для API экрана подписки (§8.6). Фронт эти значения
        не считает сам."""
        account_user = SubscriptionService.get_billing_account_user(db, user)
        slots = SubscriptionService._purchased_slots(sub)
        effective = SubscriptionService.effective_projects_limit(plan, sub)
        allowance = int(getattr(plan, "overflow_allowance_projects", 0) or 0)
        total = SubscriptionService.count_project_slots(db, account_user.id)
        over_limit = total > effective
        periods = int(getattr(sub, "overflow_periods_count", 0) or 0)
        return {
            "current": total,
            "effective_projects_limit": effective,
            "purchased_slots": slots,
            "base_projects_limit": int(plan.max_projects),
            "slot_price": int(getattr(plan, "extra_project_price_month", 0) or 0),
            "slots_until_parity": max(0, int(getattr(plan, "max_extra_project_slots", 0) or 0) - slots),
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
            "overflow_banner_permanent": over_limit and periods >= 1,
            "overflow_notice_dismissed": bool(getattr(sub, "overflow_notice_dismissed_at", None)),
            "suggested_plan": pricing.next_plan_code(plan.code),
        }

    @staticmethod
    def reconcile_overflow_state(
        db: Session,
        user: models.User,
        *,
        actor: Optional[models.User] = None,
        resolution_method: str = "usage_reduced",
    ) -> bool:
        """Сбрасывает overflow после паузы/удаления/группировки лишних проектов."""
        account_user = SubscriptionService.get_billing_account_user(db, user)
        sub = SubscriptionService.get_user_subscription(db, account_user.id, for_update=True)
        if not sub:
            return False
        plan = SubscriptionService.get_user_plan(db, account_user)
        total = SubscriptionService.count_project_slots(db, account_user.id)
        effective = SubscriptionService.effective_projects_limit(plan, sub)
        if total > effective:
            return False
        had_overflow = bool(
            getattr(sub, "overflow_since", None)
            or int(getattr(sub, "overflow_periods_count", 0) or 0)
            or getattr(sub, "overflow_notice_dismissed_at", None)
        )
        if not had_overflow:
            return False
        started_at = getattr(sub, "overflow_since", None)
        duration_days = None
        if started_at:
            if started_at.tzinfo is None:
                started_at = started_at.replace(tzinfo=timezone.utc)
            duration_days = max(0, (SubscriptionService._now() - started_at).days)
        sub.overflow_since = None
        sub.overflow_periods_count = 0
        sub.overflow_notice_dismissed_at = None
        log_history_event(
            db, actor=actor or account_user, event_type="limit", action="overflow_resolved",
            description="Использование снова укладывается в лимит тарифа",
            target_type="subscription", target_id=str(sub.id),
            meta={
                "current": total,
                "limit": effective,
                "method": resolution_method,
                "duration_days": duration_days,
            },
        )
        return True

    @staticmethod
    def track_project_peak(db: Session, user: models.User, *, actor: Optional[models.User] = None) -> int:
        """Обновляет максимум занятых слотов текущего периода и пишет событие.

        Вызывается в той же транзакции, что и создание/возобновление/разгруппировка,
        поэтому аналитика не теряет короткую ротацию проектов через паузу.
        """
        account_user = SubscriptionService.get_billing_account_user(db, user)
        sub = SubscriptionService.get_user_subscription(db, account_user.id, for_update=True)
        if not sub:
            sub = SubscriptionService.ensure_default_subscription(db, account_user)
        current = SubscriptionService.count_project_slots(db, account_user.id)
        previous = int(getattr(sub, "peak_active_projects", 0) or 0)
        if current > previous:
            sub.peak_active_projects = current
            log_history_event(
                db,
                actor=actor or user,
                event_type="limit",
                action="peak_active_projects",
                description=f"Новый пик активных проектных слотов: {current}",
                target_type="subscription",
                target_id=str(sub.id),
                meta={"previous": previous, "peak": current, "plan_code": sub.plan_code},
            )
        return current

    @staticmethod
    def ensure_can_create_project(db: Session, user: models.User, confirmed_overflow: bool = False) -> None:
        if SubscriptionService.is_admin_bypass(user):
            return
        account_user = SubscriptionService.get_billing_account_user(db, user)
        sub = SubscriptionService.ensure_default_subscription(db, account_user)
        sub = SubscriptionService.get_user_subscription(db, account_user.id, for_update=True) or sub
        plan = SubscriptionService.get_user_plan(db, account_user)
        total = SubscriptionService.count_project_slots(db, account_user.id)
        effective = SubscriptionService.effective_projects_limit(plan, sub)
        if total < effective:
            return
        if not SubscriptionService.billing_enforced():
            return

        allowance = int(getattr(plan, "overflow_allowance_projects", 0) or 0)
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
                    db, actor=user, event_type="limit", action="overflow_entered",
                    description=f"Аккаунт впервые вошёл в запас проектов ({total + 1} из {effective})",
                    target_type="subscription", target_id=str(sub.id),
                    meta={"plan_code": plan.code, "limit": effective,
                          "current_total": total, "allowance": allowance},
                )
            log_history_event(
                db, actor=user, event_type="limit",
                action="overflow_confirmed",
                description=f"Проект сверх лимита ({total + 1} из {effective})",
                target_type="subscription", target_id=str(sub.id),
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
            "slot_price": int(getattr(plan, "extra_project_price_month", 0) or 0),
            "slots_until_parity": max(0, int(getattr(plan, "max_extra_project_slots", 0) or 0) - SubscriptionService._purchased_slots(sub)),
            "suggested_plan": pricing.next_plan_code(plan.code),
            "message": message,
        })

    @staticmethod
    def ensure_project_slot_total(
        db: Session,
        user: models.User,
        requested_total: int,
        *,
        confirmed_overflow: bool = False,
        action: str = "project_slots_changed",
    ) -> None:
        """Проверяет уже рассчитанное число верхнеуровневых слотов.

        Используется для выноса из папки и других операций, где прирост может
        быть больше одного. Правила полностью совпадают с созданием проекта.
        """
        if SubscriptionService.is_admin_bypass(user) or not SubscriptionService.billing_enforced():
            return
        account_user = SubscriptionService.get_billing_account_user(db, user)
        sub = SubscriptionService.ensure_default_subscription(db, account_user)
        sub = SubscriptionService.get_user_subscription(db, account_user.id, for_update=True) or sub
        plan = SubscriptionService.get_user_plan(db, account_user)
        effective = SubscriptionService.effective_projects_limit(plan, sub)
        requested_total = max(0, int(requested_total))
        if requested_total <= effective:
            return
        allowance = int(plan.overflow_allowance_projects or 0)
        periods = int(getattr(sub, "overflow_periods_count", 0) or 0)
        hard_blocked = periods >= 2
        within_allowance = not hard_blocked and requested_total <= effective + allowance
        if within_allowance and confirmed_overflow:
            first_time = not sub.overflow_since
            if first_time:
                sub.overflow_since = SubscriptionService._now()
                log_history_event(
                    db, actor=user, event_type="limit", action="overflow_entered",
                    description=f"Аккаунт впервые вошёл в запас проектов ({requested_total} из {effective})",
                    target_type="subscription", target_id=str(sub.id),
                    meta={"operation": action, "limit": effective,
                          "requested": requested_total, "allowance": allowance},
                )
            log_history_event(
                db, actor=user, event_type="limit", action="overflow_confirmed",
                description=f"Использование увеличено сверх лимита: {requested_total} из {effective}",
                target_type="subscription", target_id=str(sub.id),
                meta={"operation": action, "limit": effective, "requested": requested_total, "allowance": allowance},
            )
            return
        reason = "confirmation_required" if within_allowance else (
            "overflow_hard_blocked" if hard_blocked else "overflow_limit_reached"
        )
        raise HTTPException(status_code=409, detail={
            "reason": reason,
            "type": "project",
            "plan_code": plan.code,
            "plan_name": plan.name,
            "limit": effective,
            "allowance": allowance,
            "current": requested_total,
            "slot_price": int(plan.extra_project_price_month or 0),
            "slots_until_parity": max(0, int(plan.max_extra_project_slots or 0) - SubscriptionService._purchased_slots(sub)),
            "suggested_plan": pricing.next_plan_code(plan.code),
            "message": f"Операция займёт {requested_total} слотов при лимите {effective} и запасе {allowance}.",
        })

    @staticmethod
    def ensure_can_create_cabinet(db: Session, user: models.User) -> None:
        if SubscriptionService.is_admin_bypass(user):
            return
        account_user = SubscriptionService.get_billing_account_user(db, user)
        sub = SubscriptionService.ensure_default_subscription(db, account_user)
        sub = SubscriptionService.get_user_subscription(db, account_user.id, for_update=True) or sub
        plan = SubscriptionService.get_user_plan(db, account_user)
        # Кабинеты получают фиксированный запас +2 (§8.3), но без модалки: тихо
        # пропускаем в пределах запаса, дальше — стоп.
        effective = SubscriptionService.effective_cabinets_limit(plan, sub)
        limit = effective + int(getattr(plan, "overflow_allowance_cabinets", 0) or 0)
        owner_ids = SubscriptionService.account_project_owner_ids(db, account_user.id)
        total = (
            db.query(models.Integration.id)
            .join(models.Client, models.Client.id == models.Integration.client_id)
            .filter(models.Client.owner_id.in_(owner_ids))
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
