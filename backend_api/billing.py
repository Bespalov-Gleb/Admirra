import json
import logging
import uuid
from datetime import timedelta
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, List, Optional
from urllib.parse import parse_qs

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend_api.services.cloudpayments import CloudPaymentsService
from backend_api.services.notifications import create_notification
from backend_api.services.history import log_history_event
from backend_api.services.subscription import SubscriptionService
from core import models, pricing, schemas, security
from core.config import get_config
from core.database import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/billing", tags=["Billing"])


def _coerce_json_data(raw: Any) -> Dict[str, Any]:
    if raw is None:
        return {}
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str):
        s = raw.strip()
        if not s:
            return {}
        try:
            parsed = json.loads(s)
            return parsed if isinstance(parsed, dict) else {}
        except json.JSONDecodeError:
            return {}
    return {}


def _parse_webhook_payload(raw_body: bytes, content_type: str) -> Dict[str, Any]:
    body = (raw_body or b"").decode("utf-8", errors="ignore").strip()
    if not body:
        return {}

    # CloudPayments обычно шлет JSON, но может прийти и form-urlencoded.
    if "application/json" in (content_type or "").lower():
        try:
            parsed = json.loads(body)
            return parsed if isinstance(parsed, dict) else {}
        except json.JSONDecodeError:
            return {}

    try:
        parsed = json.loads(body)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass

    form = parse_qs(body, keep_blank_values=True)
    if not form:
        return {}

    data: Dict[str, Any] = {k: (v[-1] if isinstance(v, list) and v else v) for k, v in form.items()}
    # В form-data поля JsonData/Data часто приходят строкой JSON.
    for key in ("JsonData", "Data"):
        if key in data:
            maybe = _coerce_json_data(data.get(key))
            if maybe:
                data[key] = maybe
    if isinstance(data.get("Success"), str):
        data["Success"] = data["Success"].strip().lower() in {"1", "true", "yes", "ok"}
    return data


def _recurrent_for_plan(plan) -> Optional[schemas.BillingRecurrentParams]:
    d = int(plan.period_days or 30)
    if d >= 28:
        return schemas.BillingRecurrentParams(interval="Month", period=1)
    if d >= 7:
        return schemas.BillingRecurrentParams(interval="Week", period=max(1, d // 7))
    return schemas.BillingRecurrentParams(interval="Day", period=max(1, d))


def _normalize_billing_period(raw: Any) -> str:
    return "year" if str(raw or "").strip().lower() == "year" else "month"


def _yearly_price_from_monthly(monthly_rub: Any) -> int:
    # Единая формула годовой цены живёт в прайс-буке (−17%, §4.1).
    return pricing.yearly_from_monthly(int(float(monthly_rub or 0)))


def _recurrent_for_billing_period(plan, billing_period: str) -> Optional[schemas.BillingRecurrentParams]:
    if billing_period == "year":
        return schemas.BillingRecurrentParams(interval="Month", period=12)
    return _recurrent_for_plan(plan)


def _billing_period_days(plan, billing_period: str) -> int:
    if billing_period == "year":
        return 365
    return int(plan.period_days or 30)


# Коды тарифов, которые вообще можно оплатить онлайн. Используется для сверки
# суммы: по оплаченной сумме мы обязаны сами определить тариф, а не верить
# клиенту. White Label оплачивается по заявке, в онлайн-оплате не участвует (§5.1).
PURCHASABLE_PLAN_CODES = ("start", "agency", "pro")


def _expected_amount(plan, billing_period: str) -> int:
    """Цена тарифа за период — единственный источник истины на сервере.
    Годовая берётся из прайс-бука (у реальных тарифов задана явно, у тестовых
    выводится из месячной)."""
    if billing_period == "year":
        locked = getattr(plan, "price_year_rub", None)
        if locked is not None:
            return int(locked)
        spec = pricing.resolve_plan(getattr(plan, "code", ""), get_config().billing)
        return int(spec.price_year)
    return int(plan.price_rub or 0)


def _slot_period_unit(plan, billing_period: str) -> int:
    if billing_period == "year":
        return int(getattr(plan, "extra_project_price_year", 0) or 0)
    return int(getattr(plan, "extra_project_price_month", 0) or 0)


def _subscription_total(plan, billing_period: str, slots: int = 0) -> int:
    return _expected_amount(plan, billing_period) + max(0, int(slots or 0)) * _slot_period_unit(plan, billing_period)


def _paid_amount(data: Dict[str, Any]) -> Optional[Decimal]:
    raw = data.get("Amount")
    if raw is None or str(raw).strip() == "":
        return None
    try:
        return Decimal(str(raw).replace(",", ".").strip())
    except (InvalidOperation, ValueError):
        return None


def _resolve_plan_by_paid_amount(paid: Decimal, billing_period: str):
    """Ищет тариф, чья цена за период совпадает с фактически оплаченной суммой.

    Возвращает (plan, billing_period) либо (None, None), если однозначного
    совпадения нет. Период тоже перебираем: клиент мог заявить 'year', заплатив
    месячную цену.
    """
    matches = []
    for period in (billing_period, "year" if billing_period == "month" else "month"):
        for code in PURCHASABLE_PLAN_CODES:
            candidate = SubscriptionService.get_plan_from_config(code)
            if Decimal(_expected_amount(candidate, period)) == paid:
                matches.append((candidate, period))
        if matches:
            break
    if len(matches) == 1:
        return matches[0]
    return None, None


# Порядок тарифов: апгрейд начинает период заново (решение владельца), понижение
# откладывается до конца уже оплаченного периода. Старые коды (basic/standard)
# оставлены на время миграции §7.3 — в БД у тестовых аккаунтов ещё они.
PLAN_RANK = {
    "start": 1,
    "basic": 2, "agency": 2,
    "standard": 3, "pro": 3,
    "white_label": 4,
}

# Окно, в течение которого повторный клик по оплате переиспользует тот же заказ,
# а не создаёт второй независимый платёж.
INVOICE_REUSE_WINDOW = timedelta(minutes=15)


def _reuse_or_create_invoice(
    db: Session,
    *,
    user: models.User,
    subscription: models.Subscription,
    plan_code: str,
    billing_period: str,
    amount: int,
    currency: str,
    purpose: str = "plan",
    intent_payload: Optional[Dict[str, Any]] = None,
) -> str:
    """Возвращает invoice_id для виджета, переиспользуя недавнее неоплаченное намерение.

    Без этого второй клик по «Оплатить» создавал полностью независимый платёж:
    у CloudPayments не было ключа, по которому он мог бы понять, что это тот же
    заказ.
    """
    now = SubscriptionService._now()
    recent = (
        db.query(models.BillingEvent)
        .filter(
            models.BillingEvent.user_id == user.id,
            models.BillingEvent.event_type == "intent",
            models.BillingEvent.plan_code == plan_code,
            models.BillingEvent.billing_period == billing_period,
            models.BillingEvent.amount == amount,
            models.BillingEvent.currency == currency,
            models.BillingEvent.created_at >= now - INVOICE_REUSE_WINDOW,
        )
        .order_by(models.BillingEvent.created_at.desc())
        .first()
    )
    if recent and recent.invoice_id:
        already_paid = (
            db.query(models.BillingEvent.id)
            .filter(
                models.BillingEvent.invoice_id == recent.invoice_id,
                models.BillingEvent.event_type == "pay",
            )
            .first()
        )
        recent_payload = _coerce_json_data(recent.payload)
        same_business_order = recent_payload.get("purpose") == purpose
        for key, value in (intent_payload or {}).items():
            if recent_payload.get(key) != value:
                same_business_order = False
                break
        if not already_paid and same_business_order:
            return recent.invoice_id

    invoice_id = uuid.uuid4().hex
    payload = {"purpose": purpose, **(intent_payload or {})}
    db.add(
        models.BillingEvent(
            user_id=user.id,
            subscription_id=subscription.id,
            event_type="intent",
            invoice_id=invoice_id,
            amount=amount,
            currency=currency,
            plan_code=plan_code,
            billing_period=billing_period,
            payload=payload,
        )
    )
    return invoice_id


def _find_payment_intent(db: Session, *, user_id, invoice_id: str) -> Optional[models.BillingEvent]:
    if not invoice_id:
        return None
    return (
        db.query(models.BillingEvent)
        .filter(
            models.BillingEvent.user_id == user_id,
            models.BillingEvent.invoice_id == invoice_id,
            models.BillingEvent.event_type == "intent",
        )
        .with_for_update()
        .order_by(models.BillingEvent.created_at.desc())
        .first()
    )


def _reserved_slot_count(db: Session, subscription_id) -> int:
    """Неоплаченные недавние заказы тоже резервируют слот до истечения окна."""
    intents = (
        db.query(models.BillingEvent)
        .filter(
            models.BillingEvent.subscription_id == subscription_id,
            models.BillingEvent.event_type == "intent",
            models.BillingEvent.created_at >= SubscriptionService._now() - INVOICE_REUSE_WINDOW,
        )
        .all()
    )
    reserved = 0
    for intent in intents:
        payload = _coerce_json_data(intent.payload)
        if payload.get("purpose") != "slot_purchase" or not intent.invoice_id:
            continue
        paid = db.query(models.BillingEvent.id).filter(
            models.BillingEvent.invoice_id == intent.invoice_id,
            models.BillingEvent.event_type == "pay",
        ).first()
        if not paid:
            reserved += max(1, int(payload.get("slot_count") or 1))
    return reserved


def _record_billing_event(
    db: Session,
    *,
    user: models.User,
    subscription: Optional[models.Subscription],
    event_type: str,
    data: Dict[str, Any],
    plan_code: Optional[str],
    billing_period: Optional[str],
    amount: Optional[Decimal],
) -> bool:
    """Пишет денежное событие в журнал.

    Возвращает False, если событие с таким TransactionId уже записано — это и
    есть идемпотентность: CloudPayments повторяет доставку, пока не получит
    code 0, и без такой проверки повтор заново продлевал подписку.
    """
    transaction_id = str(data.get("TransactionId") or "").strip() or None
    if transaction_id:
        seen = (
            db.query(models.BillingEvent.id)
            .filter(models.BillingEvent.transaction_id == transaction_id)
            .first()
        )
        if seen:
            return False

    db.add(
        models.BillingEvent(
            user_id=user.id,
            subscription_id=subscription.id if subscription is not None else None,
            event_type=event_type,
            invoice_id=str(data.get("InvoiceId") or "").strip() or None,
            transaction_id=transaction_id,
            cp_subscription_id=str(data.get("SubscriptionId") or data.get("Id") or "").strip() or None,
            amount=amount,
            currency=str(data.get("Currency") or "") or None,
            plan_code=plan_code,
            billing_period=billing_period,
            payload=data,
        )
    )
    try:
        db.flush()
    except IntegrityError:
        # Гонка: два одинаковых вебхука пришли одновременно. Уникальный индекс по
        # transaction_id отсекает второй — это ожидаемо, а не ошибка.
        db.rollback()
        return False
    return True


def _cabinet_limit_for_plan(plan_code: str) -> int:
    return SubscriptionService.cabinet_limit_for_plan(plan_code)


def _plan_has_whitelabel(plan) -> bool:
    # White Label — отдельный продукт/тариф (§5.1), а не привязка к старшему.
    if getattr(plan, "whitelabel_included", False):
        return True
    return pricing.resolve_plan(getattr(plan, "code", "") or "").white_label


def _build_cloudpayments_receipt(
    *,
    amount: int,
    description: str,
    customer_email: str,
    cfg,
) -> Dict[str, Any]:
    return _build_cloudpayments_receipt_items(
        items=[(description, amount)], customer_email=customer_email, cfg=cfg,
    )


def _build_cloudpayments_receipt_items(
    *,
    items: List[tuple[str, int]],
    customer_email: str,
    cfg,
) -> Dict[str, Any]:
    normalized = [(label, round(float(amount), 2)) for label, amount in items if float(amount) > 0]
    total = round(sum(amount for _, amount in normalized), 2)
    email = (customer_email or "").strip()
    return {
        "items": [
            {
                "label": label,
                "price": item_amount,
                "quantity": 1.0,
                "amount": item_amount,
                # None → null в JSON = «без НДС» (не путать с 0 = «НДС 0%»)
                "vat": cfg.cloudpayments.receipt_vat,
                "method": int(cfg.cloudpayments.receipt_method),
                "object": int(cfg.cloudpayments.receipt_object),
                "measurementUnit": "услуга",
            }
            for label, item_amount in normalized
        ],
        "taxationSystem": int(cfg.cloudpayments.receipt_taxation_system),
        "email": email,
        "amounts": {
            "electronic": total,
            "advancePayment": 0.0,
            "credit": 0.0,
            "provision": 0.0,
        },
    }


def _subscription_receipt(plan, billing_period: str, slots: int, email: str, cfg) -> Dict[str, Any]:
    period_label = "год" if billing_period == "year" else "месяц"
    items: List[tuple[str, int]] = [
        (f"Подписка {plan.name} ({period_label})", _expected_amount(plan, billing_period)),
    ]
    if slots > 0:
        items.append((
            f"Дополнительные слоты проектов: {slots} ({period_label})",
            _slot_period_unit(plan, billing_period) * slots,
        ))
    return _build_cloudpayments_receipt_items(items=items, customer_email=email, cfg=cfg)


async def _update_recurrent_total(sub, plan, billing_period: str, slots: int, email: str) -> bool:
    # CloudPayments трактует update отменённой подписки как повторную активацию.
    # После явного отключения автопродления будущую сумму хранит наш pending-state,
    # но внешний рекуррент не трогаем и тем самым не включаем списания обратно.
    if bool(getattr(sub, "cancel_at_period_end", False)):
        return True
    cp_id = str(getattr(sub, "cloudpayments_subscription_id", "") or "").strip()
    if not cp_id:
        return True
    cfg = get_config()
    recurrent = _recurrent_for_billing_period(plan, billing_period)
    try:
        await CloudPaymentsService.update_subscription(
            cp_id,
            Amount=_subscription_total(plan, billing_period, slots),
            Currency=cfg.cloudpayments.currency,
            Description=f"AdMirra: {plan.name} + {slots} доп. слот(ов)",
            CustomerReceipt=_subscription_receipt(plan, billing_period, slots, email, cfg),
            Interval=recurrent.interval if recurrent else None,
            Period=recurrent.period if recurrent else None,
        )
        sub.recurring_sync_required = False
        return True
    except Exception as exc:
        sub.recurring_sync_required = True
        logger.exception("Не удалось обновить рекуррент CloudPayments %s: %s", cp_id, exc)
        return False


def _spec_to_schema(
    spec: pricing.PlanSpec,
    *,
    card_state: str = "available",
    price_fixed: bool = False,
) -> schemas.BillingPlanResponse:
    cfg = get_config().billing
    return schemas.BillingPlanResponse(
        code=spec.code,
        name=spec.title,
        price_rub=spec.price_month,
        price_year_rub=spec.price_year,
        max_projects=spec.projects_limit,
        max_cabinets=spec.cabinets_limit,
        max_users=spec.users_limit,
        max_staff=spec.users_limit,
        max_clients=-1 if spec.white_label else 0,
        max_ai_requests_per_period=spec.ai_requests_limit,
        period_days=cfg.ai_period_days,
        trial_days=cfg.trial_days,
        overflow_allowance_projects=spec.overflow_allowance_projects,
        extra_project_price_month=spec.extra_project_price_month,
        extra_project_price_year=spec.extra_project_price_year,
        extra_project_cabinets=spec.extra_project_cabinets,
        max_extra_project_slots=spec.max_extra_project_slots,
        white_label=spec.white_label,
        recommended=spec.recommended,
        visible=spec.visible,
        whitelabel_included=spec.white_label,
        is_default=spec.is_default,
        is_active=spec.visible,
        request_only=spec.white_label,
        card_state=card_state,
        price_fixed=price_fixed,
    )


@router.get("/plans", response_model=List[schemas.BillingPlanResponse])
def get_plans(
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db),
):
    # Единый источник — прайс-бук. Таблица tariff_plans пустая и не используется
    # (см. get_user_plan): раньше на неё был молчаливый fallback, теперь линейка
    # всегда из конфига.
    account_user = SubscriptionService.get_billing_account_user(db, current_user)
    sub = SubscriptionService.ensure_default_subscription(db, account_user)
    current_plan = SubscriptionService.get_user_plan(db, account_user)
    current_rank = PLAN_RANK.get(current_plan.code, 0)
    is_trial = sub.status == models.SubscriptionStatus.TRIAL
    result = []
    for spec in pricing.list_plans(visible_only=True):
        if is_trial and not spec.white_label:
            state = "trial"
        elif spec.code == current_plan.code:
            state = "current"
        elif spec.white_label:
            state = "request"
        else:
            state = "upgrade" if PLAN_RANK.get(spec.code, 0) > current_rank else "downgrade"
        if spec.code == current_plan.code and getattr(sub, "price_book_snapshot", None):
            spec = pricing.plan_from_snapshot(sub.price_book_snapshot, spec)
        result.append(_spec_to_schema(spec, card_state=state, price_fixed=(state == "current" and current_plan.price_fixed)))
    # ensure_default_subscription/get_user_plan лениво создают подписку и
    # фиксируют snapshot цены для старых аккаунтов. GET-зависимость сама не
    # коммитит, поэтому сохраняем эту продуктовую миграцию явно.
    db.commit()
    return result


@router.get("/subscription", response_model=schemas.BillingSubscriptionResponse)
def get_my_subscription(
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db),
):
    account_user = SubscriptionService.get_billing_account_user(db, current_user)
    sub = SubscriptionService.ensure_default_subscription(db, account_user)
    plan = SubscriptionService.get_user_plan(db, account_user)
    SubscriptionService._ensure_ai_period(account_user, plan)
    used = int(account_user.ai_requests_used or 0)
    remaining = max(int(plan.max_ai_requests_per_period) - used, 0)
    paused_status = getattr(models.ClientStatus, "PAUSED", None)
    # Слоты по правилу папок: проекты вне папок + папки с активными проектами = 1 слот
    projects_used = SubscriptionService.count_project_slots(db, account_user.id)
    owner_ids = SubscriptionService.account_project_owner_ids(db, account_user.id)
    paused_projects = db.query(models.Client).filter(
        models.Client.owner_id.in_(owner_ids),
        models.Client.status == paused_status,
    ).count()
    cabinets_used = (
        db.query(func.count(models.Integration.id))
        .join(models.Client, models.Client.id == models.Integration.client_id)
        .filter(models.Client.owner_id.in_(owner_ids))
        .scalar()
        or 0
    )
    users_used = 1 + (
        db.query(func.count(models.TeamMember.id))
        .filter(
            models.TeamMember.account_id == account_user.id,
            models.TeamMember.role == models.TeamMemberRole.MEMBER,
            models.TeamMember.status.in_((models.TeamMemberStatus.ACTIVE, models.TeamMemberStatus.PENDING)),
        )
        .scalar()
        or 0
    )
    ai_reset_date = None
    if account_user.ai_requests_period_started_at:
        reset_dt = account_user.ai_requests_period_started_at + timedelta(days=int(plan.period_days or 30))
        ai_reset_date = reset_dt.strftime("%d.%m")
    is_active = SubscriptionService._is_subscription_active(account_user, sub)
    if account_user.is_subscribed != is_active:
        account_user.is_subscribed = is_active
    db.flush()
    overflow = SubscriptionService.compute_overflow_state(db, account_user, plan, sub)
    response = schemas.BillingSubscriptionResponse(
        plan_code=plan.code,
        plan_name=plan.name,
        status=sub.status.value,
        is_subscribed=is_active,
        billing_period=(
            _normalize_billing_period(getattr(sub, "billing_period", None))
            if getattr(sub, "billing_period", None)
            # Фоллбэк для старых подписок, где период оплаты не сохранён
            else ("year" if sub.current_period_start and sub.current_period_end and (sub.current_period_end - sub.current_period_start).days >= 330 else "month")
        ),
        subscription_expires_at=account_user.subscription_expires_at,
        # Плашка хедера показывает ЭФФЕКТИВНЫЙ лимит (тариф + докупленные слоты) —
        # «12 / 13», а не «12 / 10» (§8.5). Базовый лимит тарифа виден в /plans.
        max_projects=overflow["effective_projects_limit"],
        projects_used=projects_used,
        paused_projects=paused_projects,
        max_cabinets=SubscriptionService.effective_cabinets_limit(plan, sub),
        cabinets_used=int(cabinets_used),
        max_users=getattr(plan, "max_staff", None) or 1,
        users_used=int(users_used),
        max_staff=getattr(plan, "max_staff", None) or 1,
        max_clients=getattr(plan, "max_clients", None) or 0,
        max_ai_requests_per_period=plan.max_ai_requests_per_period,
        ai_requests_used=used,
        ai_requests_remaining=remaining,
        ai_reset_date=ai_reset_date,
        period_days=plan.period_days,
        autorenew=not bool(sub.cancel_at_period_end),
        payment_method=(
            {
                "last4": sub.card_last4,
                "brand": sub.card_type or "",
                "exp": sub.card_exp or "",
            }
            if getattr(sub, "card_last4", None)
            else None
        ),
        whitelabel_available=_plan_has_whitelabel(plan),
        effective_projects_limit=overflow["effective_projects_limit"],
        base_projects_limit=overflow["base_projects_limit"],
        purchased_slots=overflow["purchased_slots"],
        slot_price=overflow["slot_price"],
        slots_until_parity=overflow["slots_until_parity"],
        over_limit=overflow["over_limit"],
        over_by=overflow["over_by"],
        allowance_left=overflow["allowance_left"],
        overflow_deadline=overflow["overflow_deadline"],
        hard_blocked=overflow["hard_blocked"],
        overflow_banner_permanent=overflow["overflow_banner_permanent"],
        overflow_notice_dismissed=overflow["overflow_notice_dismissed"],
        suggested_plan=overflow["suggested_plan"],
        pending_plan_code=getattr(sub, "pending_plan_code", None),
        pending_billing_period=getattr(sub, "pending_billing_period", None),
        pending_purchased_slots=getattr(sub, "pending_purchased_project_slots", None),
        price_book_version=getattr(sub, "price_book_version", None),
        price_fixed=plan.price_fixed,
        recurring_sync_required=bool(getattr(sub, "recurring_sync_required", False)),
    )
    # Сохраняет ленивый snapshot прайс-бука, сброс AI-периода и синхронизацию
    # is_subscribed. Без commit изменения исчезали при закрытии GET-сессии.
    db.commit()
    return response


@router.get("/overview", response_model=schemas.BillingOverviewResponse)
def get_billing_overview(
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db),
):
    """Единый атомарный ответ для экрана тарифов: карточки + подписка."""
    return schemas.BillingOverviewResponse(
        plans=get_plans(current_user=current_user, db=db),
        subscription=get_my_subscription(current_user=current_user, db=db),
    )


@router.post("/overflow/dismiss")
def dismiss_overflow_banner(
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db),
):
    account_user = SubscriptionService.get_billing_account_user(db, current_user)
    sub = SubscriptionService.ensure_default_subscription(db, account_user)
    sub = SubscriptionService.get_user_subscription(db, account_user.id, for_update=True) or sub
    plan = SubscriptionService.get_user_plan(db, account_user)
    state = SubscriptionService.compute_overflow_state(db, account_user, plan, sub)
    if not state["over_limit"]:
        return {"ok": True, "dismissed": False}
    if state["overflow_banner_permanent"] or state["hard_blocked"]:
        raise HTTPException(status_code=409, detail={
            "reason": "permanent_banner",
            "message": "После первого продления в превышении предупреждение нельзя скрыть.",
        })
    sub.overflow_notice_dismissed_at = SubscriptionService._now()
    log_history_event(
        db, actor=current_user, event_type="limit", action="overflow_banner_dismissed",
        description="Пользователь временно закрыл предупреждение о превышении",
        target_type="subscription", target_id=str(sub.id),
    )
    db.commit()
    return {"ok": True, "dismissed": True}


@router.post("/overflow/decline")
def decline_overflow_offer(
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db),
):
    """Фиксирует отказ именно в модалке создания сверх лимита (§11.1)."""
    account_user = SubscriptionService.get_billing_account_user(db, current_user)
    sub = SubscriptionService.ensure_default_subscription(db, account_user)
    sub = SubscriptionService.get_user_subscription(db, account_user.id, for_update=True) or sub
    plan = SubscriptionService.get_user_plan(db, account_user)
    state = SubscriptionService.compute_overflow_state(db, account_user, plan, sub)
    log_history_event(
        db,
        actor=current_user,
        event_type="limit",
        action="overflow_declined",
        description="Пользователь отказался создавать проект за пределами лимита",
        target_type="subscription",
        target_id=str(sub.id),
        meta={
            "plan_code": plan.code,
            "limit": state["effective_projects_limit"],
            "current": state["current"],
            "allowance": state["allowance"],
        },
    )
    db.commit()
    return {"ok": True}


@router.get("/can-add", response_model=schemas.BillingCanAddResponse)
def can_add(
    type: str = "project",
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db),
):
    """Можно ли добавить проект и на каких условиях (§8.5). Фронт по этому ответу
    решает: создавать молча, показать модалку с запасом или предложить апгрейд."""
    account_user = SubscriptionService.get_billing_account_user(db, current_user)
    plan = SubscriptionService.get_user_plan(db, account_user)
    sub = SubscriptionService.get_user_subscription(db, account_user.id)
    if SubscriptionService.is_admin_bypass(current_user) or not SubscriptionService.billing_enforced():
        return schemas.BillingCanAddResponse(can_add=True, plan_name=plan.name)

    st = SubscriptionService.compute_overflow_state(db, account_user, plan, sub)
    current = st["current"]
    effective = st["effective_projects_limit"]
    allowance = st["allowance"]
    base = dict(
        effective_projects_limit=effective, current=current, allowance=allowance,
        allowance_left=st["allowance_left"], slot_price=st["slot_price"],
        slots_until_parity=st["slots_until_parity"], suggested_plan=st["suggested_plan"],
        plan_name=plan.name,
    )
    if current < effective:
        return schemas.BillingCanAddResponse(can_add=True, **base)
    if st["hard_blocked"]:
        return schemas.BillingCanAddResponse(
            can_add=False, reason="overflow_hard_blocked",
            message=f"На тарифе «{plan.name}» создание новых проектов приостановлено до снятия превышения.",
            **base,
        )
    if current < effective + allowance:
        return schemas.BillingCanAddResponse(
            can_add=True, needs_confirmation=True, reason="confirmation_required",
            message=f"Это {current + 1}-й проект из {effective} на тарифе «{plan.name}».",
            **base,
        )
    return schemas.BillingCanAddResponse(
        can_add=False, reason="overflow_limit_reached",
        message=f"Достигнут предел проектов на тарифе «{plan.name}»: {effective} + запас {allowance}.",
        **base,
    )


@router.post("/subscribe", response_model=schemas.BillingSubscribeResponse)
async def subscribe(
    body: schemas.BillingSubscribeRequest,
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db),
):
    account_user = SubscriptionService.get_billing_account_user(db, current_user)
    try:
        requested_spec = pricing.resolve_plan_strict(body.plan_code, get_config().billing)
    except ValueError:
        raise HTTPException(status_code=404, detail="Тариф не найден")
    if requested_spec.white_label or requested_spec.code not in PURCHASABLE_PLAN_CODES:
        raise HTTPException(
            status_code=409,
            detail={
                "reason": "request_only",
                "message": "White Label подключается только по заявке — онлайн-оплата недоступна.",
            },
        )
    billing_period = _normalize_billing_period(body.billing_period)
    cfg = get_config()
    if not cfg.cloudpayments.public_id:
        raise HTTPException(status_code=500, detail="CLOUDPAYMENTS_PUBLIC_ID не настроен")

    sub = SubscriptionService.ensure_default_subscription(db, account_user)
    sub = SubscriptionService.get_user_subscription(db, account_user.id, for_update=True) or sub
    cur_plan = SubscriptionService.get_user_plan(db, account_user)
    plan = (
        cur_plan
        if requested_spec.code == cur_plan.code
        else SubscriptionService.get_plan_from_config(requested_spec.code, spec=requested_spec)
    )
    current_rank = PLAN_RANK.get(cur_plan.code, 0)
    requested_rank = PLAN_RANK.get(plan.code, 0)
    is_downgrade = requested_rank < current_rank
    used = SubscriptionService.count_project_slots(db, account_user.id)

    # Понижение не оплачивается сегодня: новый тариф и новая сумма рекуррента
    # вступают в силу на следующем продлении.
    if is_downgrade:
        if not SubscriptionService.is_admin_bypass(account_user):
            allowed = int(plan.max_projects) + int(plan.overflow_allowance_projects)
            if used > allowed:
                raise HTTPException(status_code=409, detail={
                    "reason": "downgrade_blocked",
                    "message": f"На тарифе «{plan.name}» доступно {plan.max_projects} проектов "
                               f"и временный запас {plan.overflow_allowance_projects}, "
                               f"сейчас у вас {used}. Поставьте лишние на паузу или удалите, "
                               f"затем понижайте тариф.",
                })
        snapshot = pricing.plan_snapshot(requested_spec)
        recurrent_ok = await _update_recurrent_total(
            sub, plan, billing_period, 0, account_user.email or "",
        )
        if not recurrent_ok and sub.cloudpayments_subscription_id:
            db.rollback()
            raise HTTPException(
                status_code=502,
                detail="Не удалось обновить следующее списание в CloudPayments. Попробуйте ещё раз.",
            )
        sub.pending_plan_code = plan.code
        sub.pending_billing_period = billing_period
        sub.pending_purchased_project_slots = 0
        sub.pending_price_book_snapshot = snapshot
        log_history_event(
            db,
            actor=current_user,
            event_type="billing",
            action="downgrade_scheduled",
            description=f"Переход на тариф {plan.code} запланирован на конец периода",
            target_type="subscription",
            target_id=str(sub.id),
            meta={"from": cur_plan.code, "to": plan.code, "billing_period": billing_period},
        )
        db.commit()
        return schemas.BillingSubscribeResponse(
            public_id="",
            amount=0,
            currency=cfg.cloudpayments.currency,
            description=f"Переход на {plan.name} запланирован",
            account_id=str(account_user.id),
            email=account_user.email or "",
            plan_code=plan.code,
            billing_period=billing_period,
            trial_days=0,
            recurrent=None,
            requires_payment=False,
            action="scheduled_downgrade",
            effective_at=sub.current_period_end,
        )

    target_slots = SubscriptionService._purchased_slots(sub)
    if requested_rank > current_rank:
        target_slots = max(0, used - int(plan.max_projects))
        if target_slots > int(plan.max_extra_project_slots):
            raise HTTPException(status_code=409, detail={
                "reason": "upgrade_usage_exceeds",
                "message": "Текущее использование не помещается даже с дополнительными слотами выбранного тарифа.",
            })
    amount = _subscription_total(plan, billing_period, target_slots)
    description = f"Подписка {plan.name} ({'год' if billing_period == 'year' else 'месяц'})"
    receipt = _subscription_receipt(
        plan, billing_period, target_slots, account_user.email or "", cfg,
    )

    purchase_snapshot = (
        dict(sub.price_book_snapshot)
        if requested_spec.code == cur_plan.code and isinstance(getattr(sub, "price_book_snapshot", None), dict)
        else pricing.plan_snapshot(requested_spec)
    )
    invoice_id = _reuse_or_create_invoice(
        db,
        user=account_user,
        subscription=sub,
        plan_code=plan.code,
        billing_period=billing_period,
        amount=amount,
        currency=cfg.cloudpayments.currency,
        purpose="plan",
        intent_payload={
            "target_slots": target_slots,
            "price_book_version": pricing.current_price_book_version(),
            "price_book_snapshot": purchase_snapshot,
        },
    )
    db.commit()

    # Для фронта готовим данные виджета, включая receipt для автоматической фискализации.
    return schemas.BillingSubscribeResponse(
        public_id=cfg.cloudpayments.public_id,
        amount=amount,
        currency=cfg.cloudpayments.currency,
        description=description,
        account_id=str(account_user.id),
        email=account_user.email or "",
        plan_code=plan.code,
        billing_period=billing_period,
        trial_days=plan.trial_days,
        recurrent=_recurrent_for_billing_period(plan, billing_period),
        receipt=receipt,
        invoice_id=invoice_id,
    )


# --- Докупка слотов проектов (§8.6) ---

def _slot_unit_price(plan, billing_period: str = "month") -> int:
    return _slot_period_unit(plan, billing_period)


def _slot_remaining_days(plan, sub):
    from datetime import timezone as _tz
    now = SubscriptionService._now()
    billing_period = _normalize_billing_period(getattr(sub, "billing_period", None))
    period_days = 365 if billing_period == "year" else int(getattr(plan, "period_days", 30) or 30)
    end = getattr(sub, "current_period_end", None)
    if end is not None:
        if end.tzinfo is None:
            end = end.replace(tzinfo=_tz.utc)
        remaining = max(0, (end - now).days)
    else:
        remaining = period_days
    return remaining, period_days


def _slot_proration_amount(plan, sub, count: int) -> int:
    # Пропорция за остаток периода (§8.6): цена слота × остаток дней / длина периода.
    billing_period = _normalize_billing_period(getattr(sub, "billing_period", None))
    unit = _slot_unit_price(plan, billing_period)
    remaining, period_days = _slot_remaining_days(plan, sub)
    amt = unit * count if period_days <= 0 else round(unit * count * remaining / period_days)
    return max(1, int(amt))


@router.post("/slots/quote", response_model=schemas.BillingSlotQuoteResponse)
def slots_quote(
    body: schemas.BillingSlotQuoteRequest,
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db),
):
    account_user = SubscriptionService.get_billing_account_user(db, current_user)
    plan = SubscriptionService.get_user_plan(db, account_user)
    sub = SubscriptionService.get_user_subscription(db, account_user.id)
    count = max(1, int(body.count or 1))
    billing_period = _normalize_billing_period(getattr(sub, "billing_period", None))
    unit = _slot_unit_price(plan, billing_period)
    remaining, period_days = _slot_remaining_days(plan, sub)
    slots_now = SubscriptionService._purchased_slots(sub)
    reserved = _reserved_slot_count(db, sub.id)
    parity = max(0, int(plan.max_extra_project_slots) - slots_now - reserved)
    active_recurring = bool(
        getattr(sub, "status", None) == models.SubscriptionStatus.ACTIVE
        and (getattr(sub, "cloudpayments_subscription_id", None) or "").strip()
        and not bool(getattr(sub, "cancel_at_period_end", False))
    )
    can_buy = active_recurring and unit > 0 and parity > 0 and count <= parity
    reason = None
    message = None
    if not active_recurring:
        reason = "active_subscription_required"
        message = (
            "Дополнительные места подключаются только к активной подписке "
            "с автопродлением. Сначала оплатите или возобновите тариф."
        )
    elif not can_buy:
        reason = "parity"
        message = "Докупка достигла паритета — выгоднее перейти на старший тариф."
    return schemas.BillingSlotQuoteResponse(
        count=count,
        unit_price=unit,
        remaining_days=remaining,
        period_days=period_days,
        amount=_slot_proration_amount(plan, sub, count),
        effective_limit_after=int(plan.max_projects) + slots_now + count,
        monthly_after=int(plan.price_rub) + (slots_now + count) * int(plan.extra_project_price_month),
        recurring_after=_subscription_total(plan, billing_period, slots_now + count),
        billing_period=billing_period,
        slots_until_parity=parity,
        can_buy=can_buy,
        reason=reason,
        message=message,
        suggested_plan=pricing.next_plan_code(plan.code) if not can_buy else None,
    )


@router.post("/slots/purchase", response_model=schemas.BillingSubscribeResponse)
def slots_purchase(
    body: schemas.BillingSlotQuoteRequest,
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db),
):
    account_user = SubscriptionService.get_billing_account_user(db, current_user)
    plan = SubscriptionService.get_user_plan(db, account_user)
    sub = SubscriptionService.ensure_default_subscription(db, account_user)
    sub = SubscriptionService.get_user_subscription(db, account_user.id, for_update=True) or sub
    cfg = get_config()
    if not cfg.cloudpayments.public_id:
        raise HTTPException(status_code=500, detail="CLOUDPAYMENTS_PUBLIC_ID не настроен")
    if (
        getattr(sub, "status", None) != models.SubscriptionStatus.ACTIVE
        or not (getattr(sub, "cloudpayments_subscription_id", None) or "").strip()
        or bool(getattr(sub, "cancel_at_period_end", False))
    ):
        raise HTTPException(status_code=409, detail={
            "reason": "active_subscription_required",
            "message": (
                "Дополнительные места подключаются только к активной подписке "
                "с автопродлением. Сначала оплатите или возобновите тариф."
            ),
        })
    count = max(1, int(body.count or 1))
    billing_period = _normalize_billing_period(getattr(sub, "billing_period", None))
    unit = _slot_unit_price(plan, billing_period)
    slots_now = SubscriptionService._purchased_slots(sub)
    reserved = _reserved_slot_count(db, sub.id)
    parity = max(0, int(plan.max_extra_project_slots) - slots_now - reserved)
    if unit <= 0 or parity <= 0 or count > parity:
        # Достигнут паритет со старшим тарифом — докупка невыгодна (§8.1).
        raise HTTPException(status_code=409, detail={
            "reason": "parity",
            "suggested_plan": pricing.next_plan_code(plan.code),
            "message": "Докупка достигла паритета — выгоднее перейти на старший тариф.",
        })
    amount = _slot_proration_amount(plan, sub, count)
    description = f"Докупка {count} слот(ов) проекта (тариф {plan.name})"
    receipt = _build_cloudpayments_receipt(
        amount=amount, description=description, customer_email=account_user.email or "", cfg=cfg,
    )
    invoice_id = _reuse_or_create_invoice(
        db,
        user=account_user,
        subscription=sub,
        plan_code=plan.code,
        billing_period=billing_period,
        amount=amount,
        currency=cfg.cloudpayments.currency,
        purpose="slot_purchase",
        intent_payload={
            "slot_count": count,
            "slots_before": slots_now,
            "reserved_before": reserved,
            "slots_after": slots_now + count,
            "recurring_after": _subscription_total(plan, billing_period, slots_now + count),
            "price_book_snapshot": dict(sub.price_book_snapshot) if isinstance(sub.price_book_snapshot, dict) else None,
        },
    )
    db.commit()
    return schemas.BillingSubscribeResponse(
        public_id=cfg.cloudpayments.public_id,
        amount=amount,
        currency=cfg.cloudpayments.currency,
        description=description,
        account_id=str(account_user.id),
        email=account_user.email or "",
        plan_code=plan.code,
        billing_period=billing_period,
        trial_days=0,
        recurrent=None,
        receipt=receipt,
        invoice_id=invoice_id,
        purpose="slot_purchase",
        slot_count=count,
        expected_purchased_slots=slots_now + count,
    )


@router.post("/slots/reduce")
async def slots_reduce(
    body: schemas.BillingSlotReduceRequest,
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db),
):
    account_user = SubscriptionService.get_billing_account_user(db, current_user)
    plan = SubscriptionService.get_user_plan(db, account_user)
    sub = SubscriptionService.ensure_default_subscription(db, account_user)
    sub = SubscriptionService.get_user_subscription(db, account_user.id, for_update=True) or sub
    if not body.confirm_no_refund:
        raise HTTPException(status_code=409, detail={
            "reason": "confirmation_required",
            "message": "Слоты останутся доступны до конца оплаченного периода. Возврат за текущий период не выполняется.",
        })
    count = max(1, int(body.count or 1))
    slots = SubscriptionService._purchased_slots(sub)
    new_slots = max(0, slots - count)
    total = SubscriptionService.count_project_slots(db, account_user.id)
    new_effective = int(plan.max_projects) + new_slots
    allowed = new_effective + int(plan.overflow_allowance_projects)
    if total > allowed:
        raise HTTPException(status_code=409, detail={
            "reason": "usage_exceeds",
            "message": f"После уменьшения будет доступно {new_effective} проектов и запас "
                       f"{plan.overflow_allowance_projects}, а используется {total}. "
                       "Сначала уберите лишние проекты или поставьте на паузу.",
        })
    billing_period = _normalize_billing_period(getattr(sub, "billing_period", None))
    recurrent_ok = await _update_recurrent_total(
        sub, plan, billing_period, new_slots, account_user.email or "",
    )
    if not recurrent_ok and sub.cloudpayments_subscription_id:
        db.rollback()
        raise HTTPException(status_code=502, detail="Не удалось обновить следующее списание в CloudPayments")
    sub.pending_purchased_project_slots = new_slots
    log_history_event(
        db, actor=current_user, event_type="billing", action="slot_removed",
        description=f"Уменьшение слотов до {new_slots} запланировано со следующего периода",
        target_type="subscription", target_id=str(sub.id),
        meta={"from": slots, "to": new_slots, "effective_at": sub.current_period_end.isoformat() if sub.current_period_end else None},
    )
    db.commit()
    return {
        "purchased_slots": slots,
        "pending_purchased_slots": new_slots,
        "effective_at": sub.current_period_end,
    }


@router.post("/autorenew/cancel")
async def cancel_autorenew(
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db),
):
    """Отключает автопродление: отменяет рекуррент в CloudPayments (если он был создан),
    доступ сохраняется до конца оплаченного периода."""
    account_user = SubscriptionService.get_billing_account_user(db, current_user)
    sub = SubscriptionService.ensure_default_subscription(db, account_user)
    cp_sub_id = (sub.cloudpayments_subscription_id or "").strip()
    cancelled_ids = []
    # Если рекуррент в CloudPayments отменить не удалось, списания продолжатся.
    # Раньше об этом знал только лог, а пользователю показывался бодрый тост
    # «карта отвязана, списаний не будет» — теперь отдаём правду наверх.
    failed_ids = []
    if cp_sub_id:
        try:
            await CloudPaymentsService.cancel_subscription(cp_sub_id)
            cancelled_ids.append(cp_sub_id)
        except Exception as err:
            failed_ids.append(cp_sub_id)
            logger.warning("CloudPayments cancel_subscription failed for %s: %s", cp_sub_id, err)
    # Подстраховка: отменяем ВСЕ активные рекурренты аккаунта в CP. Закрывает гонку
    # «нажал отмену раньше, чем вебхук записал SubscriptionId» и осиротевшие подписки
    # от смены карты — иначе списания продолжатся, хотя у нас всё выглядит отменённым.
    try:
        for cp_sub in await CloudPaymentsService.find_subscriptions(str(account_user.id)):
            sid = str(cp_sub.get("Id") or "").strip()
            status = str(cp_sub.get("Status") or "").lower()
            if sid and sid not in cancelled_ids and status in ("active", "pastdue"):
                try:
                    await CloudPaymentsService.cancel_subscription(sid)
                    cancelled_ids.append(sid)
                    logger.info("Cancelled orphan CP subscription %s for user %s", sid, current_user.id)
                except Exception as err:
                    failed_ids.append(sid)
                    logger.warning("Failed to cancel orphan CP subscription %s: %s", sid, err)
    except Exception as err:
        # Не смогли даже получить список рекуррентов — значит не можем утверждать,
        # что списаний не будет.
        failed_ids.append("unknown")
        logger.warning("CloudPayments find_subscriptions failed for %s: %s", account_user.id, err)
    sub.cancel_at_period_end = True
    # Отмена автопродления = отвязка карты: рекуррент в CP отменён, токен карты больше
    # не используется — убираем и отображаемую маску, чтобы UI показал «Карта не привязана».
    sub.card_last4 = None
    sub.card_type = None
    sub.card_exp = None
    sub.cloudpayments_subscription_id = None
    recurrent_cancelled = not failed_ids
    log_history_event(
        db,
        actor=current_user,
        event_type="billing",
        action="autorenew_canceled",
        description=(
            "Автопродление отключено пользователем (карта отвязана)"
            if recurrent_cancelled
            else "Автопродление отключено, но рекуррент в CloudPayments отменить не удалось"
        ),
        target_type="subscription",
        target_id=str(sub.id),
        meta={
            "plan_code": sub.plan_code,
            "cancelled_cp_ids": cancelled_ids,
            "failed_cp_ids": failed_ids,
        },
    )
    db.commit()
    if not recurrent_cancelled:
        logger.error(
            "Автопродление отключено в БД, но рекурренты %s в CloudPayments активны — "
            "списания продолжатся. user=%s",
            failed_ids, current_user.id,
        )
    return {
        "ok": True,
        "autorenew": False,
        "recurrent_cancelled": recurrent_cancelled,
        "warning": (
            None
            if recurrent_cancelled
            else "Автопродление отключено в личном кабинете, но отменить подписку "
                 "в платёжной системе не удалось. Списание возможно — напишите в поддержку."
        ),
    }


@router.post("/cloudpayments/webhook", response_model=schemas.CloudPaymentsWebhookResponse)
async def cloudpayments_webhook(
    request: Request,
    db: Session = Depends(get_db),
):
    raw_body = await request.body()
    sign = request.headers.get("Content-HMAC") or request.headers.get("X-Content-HMAC")
    if not CloudPaymentsService.validate_webhook_signature(raw_body, sign):
        raise HTTPException(status_code=401, detail="Invalid webhook signature")

    data = _parse_webhook_payload(raw_body, request.headers.get("Content-Type", ""))
    if not data:
        return schemas.CloudPaymentsWebhookResponse(code=0)
    account_id = str(data.get("AccountId") or "").strip()
    if not account_id:
        return schemas.CloudPaymentsWebhookResponse(code=0)

    try:
        user_uuid = uuid.UUID(account_id)
    except ValueError:
        return schemas.CloudPaymentsWebhookResponse(code=0)

    user = db.query(models.User).filter(models.User.id == user_uuid).first()
    if not user:
        return schemas.CloudPaymentsWebhookResponse(code=0)

    account_user = SubscriptionService.get_billing_account_user(db, user)
    # AccountId виджета всегда указывает на владельца биллингового аккаунта.
    # Для старых платежей участника нормализуем пользователя до владельца.
    user = account_user
    sub = SubscriptionService.ensure_default_subscription(db, account_user)
    sub = SubscriptionService.get_user_subscription(db, account_user.id, for_update=True) or sub
    event_name = (data.get("Type") or data.get("Event") or "").lower()

    # Pay/Fail/Recurrent/Cancel приходят на ОДИН URL, а поля Type у CloudPayments нет —
    # классифицируем по реальному составу уведомления (см. developers.cloudpayments.ru):
    #  - Recurrent: есть Id подписки и Status (Active/PastDue/Cancelled/...), нет TransactionId
    #  - Fail: есть ReasonCode != 0 (причина отказа)
    #  - Pay: успешный платёж (Status Completed/Authorized)
    status_field = str(data.get("Status") or "").strip().lower()
    reason_code = str(data.get("ReasonCode") or "").strip()
    is_recurrent_report = bool(data.get("Id")) and not data.get("TransactionId")
    failed = (
        not bool(data.get("Success", True))
        or (reason_code not in ("", "0"))
        or status_field == "declined"
    )
    if is_recurrent_report and status_field in ("cancelled", "canceled", "rejected", "expired"):
        outcome = "cancel"
    elif is_recurrent_report and status_field == "pastdue":
        outcome = "fail"
    elif "cancel" in event_name:
        outcome = "cancel"
    elif failed or "fail" in event_name:
        outcome = "fail"
    else:
        outcome = "pay"

    invoice_id = str(data.get("InvoiceId") or "").strip()
    intent = _find_payment_intent(db, user_id=account_user.id, invoice_id=invoice_id)
    # Повторные списания CloudPayments могут наследовать InvoiceId первого
    # платежа. Если этот server-intent уже погашен, новый TransactionId с
    # SubscriptionId — это продление, а не повторное применение старого заказа.
    if intent and data.get("SubscriptionId") and data.get("TransactionId"):
        intent_paid = db.query(models.BillingEvent.id).filter(
            models.BillingEvent.invoice_id == intent.invoice_id,
            models.BillingEvent.event_type == "pay",
        ).first()
        if intent_paid:
            intent = None
    intent_payload = _coerce_json_data(getattr(intent, "payload", None)) if intent else {}
    purpose = str(intent_payload.get("purpose") or "").strip()
    is_recurring_charge = bool(data.get("SubscriptionId")) and bool(data.get("TransactionId")) and intent is None

    if intent:
        plan_code = pricing.normalize_code(intent.plan_code)
        billing_period = _normalize_billing_period(intent.billing_period)
        fallback_spec = pricing.resolve_plan(plan_code, get_config().billing)
        intent_spec = pricing.plan_from_snapshot(intent_payload.get("price_book_snapshot"), fallback_spec)
        plan = SubscriptionService.get_plan_from_config(
            intent_spec.code,
            spec=intent_spec,
            price_fixed=bool(intent_payload.get("price_book_snapshot")),
        )
        expected_amount = Decimal(intent.amount) if intent.amount is not None else None
        expected_currency = str(intent.currency or get_config().cloudpayments.currency).upper()
    elif is_recurring_charge:
        plan_code = pricing.normalize_code(getattr(sub, "pending_plan_code", None) or sub.plan_code or "start")
        billing_period = _normalize_billing_period(
            getattr(sub, "pending_billing_period", None) or getattr(sub, "billing_period", None)
        )
        fallback_spec = pricing.resolve_plan(plan_code, get_config().billing)
        snapshot = getattr(sub, "pending_price_book_snapshot", None) or getattr(sub, "price_book_snapshot", None)
        recurring_spec = pricing.plan_from_snapshot(snapshot, fallback_spec)
        plan = SubscriptionService.get_plan_from_config(
            recurring_spec.code, spec=recurring_spec, price_fixed=bool(snapshot),
        )
        target_slots = getattr(sub, "pending_purchased_project_slots", None)
        if target_slots is None:
            target_slots = SubscriptionService._purchased_slots(sub)
        expected_amount = Decimal(_subscription_total(plan, billing_period, target_slots))
        expected_currency = str(get_config().cloudpayments.currency or "RUB").upper()
    elif is_recurrent_report:
        plan = SubscriptionService.get_user_plan(db, account_user)
        plan_code = plan.code
        billing_period = _normalize_billing_period(getattr(sub, "billing_period", None))
        expected_amount = None
        expected_currency = str(get_config().cloudpayments.currency or "RUB").upper()
    else:
        # Ручной Pay без созданного сервером InvoiceId не может менять доступ.
        plan_code = pricing.normalize_code(sub.plan_code or "start")
        billing_period = _normalize_billing_period(getattr(sub, "billing_period", None))
        plan = SubscriptionService.get_user_plan(db, account_user)
        expected_amount = None
        expected_currency = str(get_config().cloudpayments.currency or "RUB").upper()

    paid = _paid_amount(data)
    got_currency = str(data.get("Currency") or expected_currency).upper()
    amount_mismatch = False
    if outcome == "pay" and not is_recurrent_report:
        amount_mismatch = (
            expected_amount is None
            or paid is None
            or paid != expected_amount
            or got_currency != expected_currency
        )
        if amount_mismatch:
            logger.error(
                "CloudPayments webhook rejected: invoice=%s purpose=%s paid=%s/%s expected=%s/%s user=%s",
                invoice_id, purpose, paid, got_currency, expected_amount, expected_currency, user.id,
            )

    # Один invoice можно погасить только один раз, даже если CloudPayments
    # прислал новую TransactionId после повторной оплаты тем же заказом.
    intent_already_paid = bool(intent and outcome == "pay" and db.query(models.BillingEvent.id).filter(
        models.BillingEvent.invoice_id == intent.invoice_id,
        models.BillingEvent.event_type == "pay",
    ).first())
    if intent_already_paid:
        logger.warning("CloudPayments: invoice %s уже погашен, повтор не применяется", invoice_id)
        db.commit()
        return schemas.CloudPaymentsWebhookResponse(code=0)

    # Идемпотентность. CloudPayments повторяет доставку, пока не получит code 0,
    # и без этой проверки повтор заново продлевал подписку. Запись в журнал —
    # она же и защита: TransactionId уникален частичным индексом.
    is_new_event = _record_billing_event(
        db,
        user=user,
        subscription=sub,
        event_type="rejected" if amount_mismatch and outcome == "pay" else outcome,
        data=data,
        plan_code=plan_code,
        billing_period=billing_period,
        amount=paid,
    )
    if not is_new_event:
        logger.info(
            "CloudPayments webhook: повторная доставка транзакции %s — пропущена",
            data.get("TransactionId"),
        )
        db.commit()
        return schemas.CloudPaymentsWebhookResponse(code=0)

    # Сумма/валюта/invoice не сошлись с серверным заказом — доступ не меняем.
    # Возвращаем code 0, чтобы CloudPayments не долбил повторами: платёж уже
    # прошёл, разбираться нужно руками по логу и уведомлению.
    if amount_mismatch and outcome == "pay":
        log_history_event(
            db,
            actor=user,
            event_type="billing",
            action="payment_amount_mismatch",
            description="Оплаченная сумма не соответствует ни одному тарифу — доступ не выдан",
            target_type="subscription",
            target_id=str(sub.id),
            meta={
                "claimed_plan_code": plan_code,
                "claimed_billing_period": billing_period,
                "paid_amount": str(paid) if paid is not None else None,
                "currency": got_currency,
                "transaction_id": str(data.get("TransactionId") or ""),
            },
        )
        db.commit()
        return schemas.CloudPaymentsWebhookResponse(code=0)

    # Докупка слотов определяется только доверенным серверным intent. JsonData
    # виджета намеренно игнорируется.
    if outcome == "pay" and purpose == "slot_purchase":
        add = max(1, int(intent_payload.get("slot_count") or 1))
        slots_before = SubscriptionService._purchased_slots(sub)
        new_slots = slots_before + add
        if new_slots > int(plan.max_extra_project_slots):
            sub.recurring_sync_required = True
            log_history_event(
                db, actor=user, event_type="billing", action="slot_purchase_conflict",
                description="Оплаченная покупка слотов конфликтует с актуальным лимитом",
                target_type="subscription", target_id=str(sub.id),
                meta={"before": slots_before, "add": add, "maximum": plan.max_extra_project_slots},
            )
            db.commit()
            return schemas.CloudPaymentsWebhookResponse(code=0)
        sub.purchased_project_slots = new_slots
        sub.pending_purchased_project_slots = None
        used = SubscriptionService.count_project_slots(db, user.id)
        if used <= SubscriptionService.effective_projects_limit(plan, sub):
            SubscriptionService.reconcile_overflow_state(
                db, user, actor=user, resolution_method="slot_purchased",
            )
        recurrent_ok = await _update_recurrent_total(
            sub, plan, billing_period, new_slots, user.email or "",
        )
        log_history_event(
            db, actor=user, event_type="billing", action="slot_purchased",
            description=f"Докуплено слотов: {add}", target_type="subscription",
            target_id=str(sub.id),
            meta={
                "count": add,
                "slots_after": new_slots,
                "amount": str(paid) if paid is not None else None,
                "recurrent_updated": recurrent_ok,
            },
        )
        db.commit()
        return schemas.CloudPaymentsWebhookResponse(code=0)

    if outcome == "pay" and intent and purpose not in {"plan", "slot_purchase"}:
        logger.error("CloudPayments: неизвестное назначение server intent %s", purpose)
        db.commit()
        return schemas.CloudPaymentsWebhookResponse(code=0)

    old_plan_code = pricing.normalize_code(sub.plan_code or "start")
    old_purchased_slots = SubscriptionService._purchased_slots(sub)

    # Применяем запланированный downgrade/уменьшение слотов только после
    # успешного следующего рекуррентного списания.
    pending_applied = False
    if outcome == "pay" and is_recurring_charge and (
        getattr(sub, "pending_plan_code", None)
        or getattr(sub, "pending_purchased_project_slots", None) is not None
    ):
        if getattr(sub, "pending_plan_code", None):
            sub.plan_code = sub.pending_plan_code
        if getattr(sub, "pending_billing_period", None):
            sub.billing_period = sub.pending_billing_period
        if getattr(sub, "pending_purchased_project_slots", None) is not None:
            sub.purchased_project_slots = max(0, int(sub.pending_purchased_project_slots))
        if getattr(sub, "pending_price_book_snapshot", None):
            sub.price_book_snapshot = sub.pending_price_book_snapshot
            sub.price_book_version = int(
                sub.pending_price_book_snapshot.get("_price_book_version")
                or pricing.current_price_book_version()
            )
        sub.pending_plan_code = None
        sub.pending_billing_period = None
        sub.pending_purchased_project_slots = None
        sub.pending_price_book_snapshot = None
        pending_applied = True

    # plan_code меняем ТОЛЬКО при успешной оплате доверенного заказа.
    prev_plan_code = old_plan_code
    new_plan_code = (plan.code or "").lower()
    if outcome == "pay" and not is_recurrent_report:
        sub.plan_code = plan.code
        if intent and purpose == "plan":
            snapshot = intent_payload.get("price_book_snapshot")
            if isinstance(snapshot, dict):
                sub.price_book_snapshot = snapshot
            target_slots = max(0, int(intent_payload.get("target_slots") or 0))
            sub.purchased_project_slots = target_slots
            sub.pending_purchased_project_slots = None
            sub.price_book_version = int(
                (snapshot.get("_price_book_version") if isinstance(snapshot, dict) else None)
                or pricing.current_price_book_version()
            )
        elif getattr(sub, "price_book_version", None) is None:
            sub.price_book_version = pricing.current_price_book_version()
            sub.price_book_snapshot = pricing.plan_snapshot(pricing.resolve_plan(plan.code))
        if PLAN_RANK.get(new_plan_code, 0) > PLAN_RANK.get(prev_plan_code, 0) and old_purchased_slots > 0:
            log_history_event(
                db,
                actor=user,
                event_type="billing",
                action="upgrade_after_slots",
                description=f"Апгрейд после докупки {old_purchased_slots} слот(ов)",
                target_type="subscription",
                target_id=str(sub.id),
                meta={
                    "from": prev_plan_code,
                    "to": new_plan_code,
                    "slots_before_upgrade": old_purchased_slots,
                },
            )
        if PLAN_RANK.get(new_plan_code, 0) > PLAN_RANK.get(prev_plan_code, 0):
            SubscriptionService.reconcile_overflow_state(
                db, user, actor=user, resolution_method="upgrade",
            )
    prev_cp_sub_id = (sub.cloudpayments_subscription_id or "").strip()
    sub.cloudpayments_subscription_id = str(
        data.get("SubscriptionId")
        or (data.get("Id") if is_recurrent_report else None)
        or sub.cloudpayments_subscription_id
        or ""
    )
    # Смена карты/тарифа = новая оплата = НОВАЯ подписка CP. Старый рекуррент при этом
    # продолжил бы списывать параллельно — отменяем его, чтобы не было двойных списаний.
    new_cp_sub_id = (str(data.get("SubscriptionId") or "")).strip()
    if prev_cp_sub_id and new_cp_sub_id and prev_cp_sub_id != new_cp_sub_id:
        try:
            await CloudPaymentsService.cancel_subscription(prev_cp_sub_id)
            logger.info("Cancelled previous CP subscription %s (replaced by %s)", prev_cp_sub_id, new_cp_sub_id)
        except Exception as _cancel_err:
            logger.warning("Failed to cancel previous CP subscription %s: %s", prev_cp_sub_id, _cancel_err)
    sub.cloudpayments_transaction_id = str(data.get("TransactionId") or sub.cloudpayments_transaction_id or "")
    # Маска карты из уведомления — чтобы показывать «Карта привязана **** 1234» в кабинете.
    if data.get("CardLastFour"):
        sub.card_last4 = str(data.get("CardLastFour"))[:4]
        sub.card_type = str(data.get("CardType") or "")[:32] or sub.card_type
        sub.card_exp = str(data.get("CardExpDate") or "")[:8] or sub.card_exp
    now = SubscriptionService._now()

    if outcome == "pay":
        # Recurrent(Active) — только статус подписки, период НЕ продлеваем: продление
        # периода происходит по реальному списанию (уведомление Pay).
        extend_period = not is_recurrent_report or not sub.current_period_end
        sub.status = models.SubscriptionStatus.ACTIVE
        # Успешная оплата снова включает автопродление. Раньше cancel_at_period_end
        # выставлялся в True при отмене и НИКОГДА не сбрасывался: после повторной
        # оплаты UI продолжал показывать «автопродление отключено», хотя рекуррент
        # в CloudPayments был создан заново и списания шли.
        sub.cancel_at_period_end = False
        if extend_period:
            sub.billing_period = billing_period
            days = _billing_period_days(plan, billing_period)
            same_plan = prev_plan_code == new_plan_code
            if same_plan or is_recurring_charge or pending_applied:
                # Продление того же тарифа прибавляется к остатку периода.
                base = max(now, sub.current_period_end) if sub.current_period_end else now
                sub.pending_plan_code = None
            else:
                # Апгрейд: период начинается заново, остаток старого сгорает —
                # решение владельца продукта от 2026-07-26.
                base = now
                sub.pending_plan_code = None
            sub.current_period_start = now
            sub.current_period_end = base + timedelta(days=days)
            # §8.3: трекинг превышения при старте нового оплаченного периода. 1-е
            # продление в превышении → баннер постоянный; 2-е подряд → блок создания
            # новых (см. ensure_can_create_project).
            _slots = SubscriptionService.count_project_slots(db, user.id)
            _eff = SubscriptionService.effective_projects_limit(plan, sub)
            if _slots > _eff:
                if not sub.overflow_since:
                    sub.overflow_since = now
                sub.overflow_periods_count = int(sub.overflow_periods_count or 0) + 1
            else:
                was_overflow = bool(sub.overflow_since or sub.overflow_periods_count)
                sub.overflow_since = None
                sub.overflow_periods_count = 0
                sub.overflow_notice_dismissed_at = None
                if was_overflow:
                    log_history_event(
                        db, actor=user, event_type="limit", action="overflow_resolved",
                        description="Превышение устранено к новому периоду",
                        target_type="subscription", target_id=str(sub.id),
                    )
            # Новый оплаченный период — новая точка отсчёта пикового использования.
            sub.peak_active_projects = _slots
            sub.overflow_warning_period_end = None
        user.is_subscribed = True
        user.subscription_expires_at = sub.current_period_end
        if extend_period:
            create_notification(
                db,
                user_id=user.id,
                type="payment_ok",
                title=f"Оплата прошла — тариф «{plan.name}»",
                body=f"Ваша подписка активна до {sub.current_period_end.strftime('%d.%m.%Y')}.",
                meta={"plan_code": plan.code, "billing_period": billing_period},
            )
        log_history_event(
            db,
            actor=user,
            event_type="billing",
            action="payment_succeeded",
            description=f"Оплата подтверждена, тариф {plan.code}",
            target_type="subscription",
            target_id=str(sub.id),
            meta={"plan_code": plan.code, "billing_period": billing_period},
        )

        # Серверная офлайн-конверсия в Метрику (выручка → рекламный источник).
        # Повторное списание по подписке CP приходит как Pay с SubscriptionId —
        # это фоновый рекуррент, клиента нет: шлём subscription_renewal и
        # payment_success с сервера. Первое/ручное списание: payment_success шлёт
        # клиент на странице успеха, поэтому с сервера шлём только trial_to_paid.
        try:
            from backend_api.services.metrika_conversions import upload_offline_conversion
            _amount = data.get("Amount") or data.get("Price")
            _amount = float(_amount) if _amount not in (None, "") else None
            _currency = str(data.get("Currency") or "RUB")
            _cid = getattr(user, "metrika_client_id", None)
            _yclid = getattr(user, "metrika_yclid", None)
            _is_recurring_charge = bool(data.get("SubscriptionId")) or "recurrent" in event_name
            if _is_recurring_charge and extend_period:
                await upload_offline_conversion(target="subscription_renewal", price=_amount,
                                                currency=_currency, client_id=_cid, yclid=_yclid)
                await upload_offline_conversion(target="payment_success", price=_amount,
                                                currency=_currency, client_id=_cid, yclid=_yclid)
            elif extend_period:
                await upload_offline_conversion(target="trial_to_paid", price=_amount,
                                                currency=_currency, client_id=_cid, yclid=_yclid)
        except Exception as _conv_err:
            logger.warning("Metrika offline conversion hook error: %s", _conv_err)
    elif outcome == "cancel":
        sub.status = models.SubscriptionStatus.CANCELED
        # Оплаченный период отменой не сгорает: и UI, и docstring эндпоинта
        # отмены обещают доступ до его конца. Раньше здесь безусловно стоял
        # is_subscribed = False, и пользователь терял доступ в тот же миг.
        period_still_paid = bool(sub.current_period_end) and sub.current_period_end >= now
        user.is_subscribed = period_still_paid
        if period_still_paid:
            user.subscription_expires_at = sub.current_period_end
        create_notification(
            db,
            user_id=user.id,
            type="payment_failed",
            title="Подписка отменена",
            body=(
                f"Автопродление отключено. Доступ сохранится до "
                f"{sub.current_period_end.strftime('%d.%m.%Y')}."
                if period_still_paid
                else "Ваша подписка была отменена. Вы можете оформить её заново в разделе «Тарифы»."
            ),
        )
        log_history_event(
            db,
            actor=user,
            event_type="billing",
            action="subscription_canceled",
            description="Подписка отменена",
            target_type="subscription",
            target_id=str(sub.id),
            meta={"plan_code": plan.code},
        )
    else:
        sub.status = models.SubscriptionStatus.PAST_DUE
        # Неудачное списание не отбирает уже оплаченный период. Обычно неудача
        # приходит уже после его конца, но если период ещё идёт — доступ остаётся.
        user.is_subscribed = bool(sub.current_period_end) and sub.current_period_end >= now
        create_notification(
            db,
            user_id=user.id,
            type="payment_failed",
            title="Ошибка оплаты",
            body="Не удалось провести платёж. Проверьте данные карты или выберите другой способ оплаты.",
            meta={"plan_code": plan.code},
        )
        log_history_event(
            db,
            actor=user,
            event_type="billing",
            action="payment_failed",
            description="Ошибка оплаты подписки",
            target_type="subscription",
            target_id=str(sub.id),
            meta={"plan_code": plan.code},
        )

    db.flush()
    db.commit()
    return schemas.CloudPaymentsWebhookResponse(code=0)
