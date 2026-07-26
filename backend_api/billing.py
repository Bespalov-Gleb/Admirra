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
from core import models, schemas, security
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
    m = float(monthly_rub or 0)
    if m <= 0:
        return 0
    return int(((m * 12 * 0.7 + 9) // 10) * 10)


def _recurrent_for_billing_period(plan, billing_period: str) -> Optional[schemas.BillingRecurrentParams]:
    if billing_period == "year":
        return schemas.BillingRecurrentParams(interval="Month", period=12)
    return _recurrent_for_plan(plan)


def _billing_period_days(plan, billing_period: str) -> int:
    if billing_period == "year":
        return 365
    return int(plan.period_days or 30)


# Коды тарифов, которые вообще можно оплатить. Используется для сверки суммы:
# по оплаченной сумме мы обязаны сами определить тариф, а не верить клиенту.
PURCHASABLE_PLAN_CODES = ("start", "basic", "standard")


def _expected_amount(plan, billing_period: str) -> int:
    """Цена тарифа за период — единственный источник истины на сервере."""
    if billing_period == "year":
        return int(_yearly_price_from_monthly(plan.price_rub))
    return int(plan.price_rub or 0)


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
# откладывается до конца уже оплаченного периода.
PLAN_RANK = {"start": 1, "basic": 2, "standard": 3, "white_label": 4}

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
        if not already_paid:
            return recent.invoice_id

    invoice_id = uuid.uuid4().hex
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
        )
    )
    return invoice_id


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
    if getattr(plan, "whitelabel_included", False):
        return True
    return str(getattr(plan, "code", "") or "").lower() == "standard"


def _build_cloudpayments_receipt(
    *,
    amount: int,
    description: str,
    customer_email: str,
    cfg,
) -> Dict[str, Any]:
    total = round(float(amount), 2)
    email = (customer_email or "").strip()
    return {
        "items": [
            {
                "label": description,
                "price": total,
                "quantity": 1.0,
                "amount": total,
                # None → null в JSON = «без НДС» (не путать с 0 = «НДС 0%»)
                "vat": cfg.cloudpayments.receipt_vat,
                "method": int(cfg.cloudpayments.receipt_method),
                "object": int(cfg.cloudpayments.receipt_object),
                "measurementUnit": "услуга",
            }
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


def _plan_to_schema(plan) -> schemas.BillingPlanResponse:
    fallback = SubscriptionService.get_plan_from_config(getattr(plan, "code", "start"))
    max_staff = getattr(plan, "max_staff", None) or fallback.max_staff
    max_clients = getattr(plan, "max_clients", None) or fallback.max_clients
    max_cabinets = getattr(plan, "max_cabinets", None) or fallback.max_cabinets
    return schemas.BillingPlanResponse(
        code=plan.code,
        name=plan.name,
        price_rub=plan.price_rub,
        max_projects=plan.max_projects,
        max_cabinets=max_cabinets,
        max_users=max_staff,
        max_staff=max_staff,
        max_clients=max_clients,
        max_ai_requests_per_period=plan.max_ai_requests_per_period,
        period_days=plan.period_days,
        trial_days=plan.trial_days,
        whitelabel_included=_plan_has_whitelabel(plan),
        is_default=plan.is_default,
        is_active=plan.is_active,
    )


@router.get("/plans", response_model=List[schemas.BillingPlanResponse])
def get_plans(
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db),
):
    rows = db.query(models.TariffPlan).filter(models.TariffPlan.is_active.is_(True)).all()
    if rows:
        return [_plan_to_schema(r) for r in rows]
    return [
        _plan_to_schema(SubscriptionService.get_plan_from_config("start")),
        _plan_to_schema(SubscriptionService.get_plan_from_config("basic")),
        _plan_to_schema(SubscriptionService.get_plan_from_config("standard")),
    ]


@router.get("/subscription", response_model=schemas.BillingSubscriptionResponse)
def get_my_subscription(
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db),
):
    sub = SubscriptionService.ensure_default_subscription(db, current_user)
    plan = SubscriptionService.get_user_plan(db, current_user)
    SubscriptionService._ensure_ai_period(current_user, plan)
    used = int(current_user.ai_requests_used or 0)
    remaining = max(int(plan.max_ai_requests_per_period) - used, 0)
    paused_status = getattr(models.ClientStatus, "PAUSED", None)
    # Слоты по правилу папок: проекты вне папок + папки с активными проектами = 1 слот
    projects_used = SubscriptionService.count_project_slots(db, current_user.id)
    paused_projects = db.query(models.Client).filter(
        models.Client.owner_id == current_user.id,
        models.Client.status == paused_status,
    ).count()
    cabinets_used = (
        db.query(func.count(models.Integration.id))
        .join(models.Client, models.Client.id == models.Integration.client_id)
        .filter(models.Client.owner_id == current_user.id)
        .scalar()
        or 0
    )
    users_used = 1 + (
        db.query(func.count(models.TeamMember.id))
        .filter(
            models.TeamMember.account_id == current_user.id,
            models.TeamMember.role == models.TeamMemberRole.MEMBER,
        )
        .scalar()
        or 0
    )
    ai_reset_date = None
    if current_user.ai_requests_period_started_at:
        reset_dt = current_user.ai_requests_period_started_at + timedelta(days=int(plan.period_days or 30))
        ai_reset_date = reset_dt.strftime("%d.%m")
    is_active = SubscriptionService._is_subscription_active(current_user, sub)
    if current_user.is_subscribed != is_active:
        current_user.is_subscribed = is_active
    db.flush()
    return schemas.BillingSubscriptionResponse(
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
        subscription_expires_at=current_user.subscription_expires_at,
        max_projects=plan.max_projects,
        projects_used=projects_used,
        paused_projects=paused_projects,
        max_cabinets=getattr(plan, "max_cabinets", None) or SubscriptionService.cabinet_limit_for_plan(plan.code),
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
    )


@router.post("/subscribe", response_model=schemas.BillingSubscribeResponse)
async def subscribe(
    body: schemas.BillingSubscribeRequest,
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db),
):
    plan = SubscriptionService.get_plan_from_config(body.plan_code)
    billing_period = _normalize_billing_period(body.billing_period)
    cfg = get_config()
    if not cfg.cloudpayments.public_id:
        raise HTTPException(status_code=500, detail="CLOUDPAYMENTS_PUBLIC_ID не настроен")

    amount = _expected_amount(plan, billing_period)
    description = f"Подписка {plan.name} ({'год' if billing_period == 'year' else 'месяц'})"
    receipt = _build_cloudpayments_receipt(
        amount=amount,
        description=description,
        customer_email=current_user.email or "",
        cfg=cfg,
    )

    sub = SubscriptionService.ensure_default_subscription(db, current_user)
    invoice_id = _reuse_or_create_invoice(
        db,
        user=current_user,
        subscription=sub,
        plan_code=plan.code,
        billing_period=billing_period,
        amount=amount,
        currency=cfg.cloudpayments.currency,
    )
    db.commit()

    # Для фронта готовим данные виджета, включая receipt для автоматической фискализации.
    return schemas.BillingSubscribeResponse(
        public_id=cfg.cloudpayments.public_id,
        amount=amount,
        currency=cfg.cloudpayments.currency,
        description=description,
        account_id=str(current_user.id),
        email=current_user.email or "",
        plan_code=plan.code,
        billing_period=billing_period,
        trial_days=plan.trial_days,
        recurrent=_recurrent_for_billing_period(plan, billing_period),
        receipt=receipt,
        invoice_id=invoice_id,
    )


@router.post("/autorenew/cancel")
async def cancel_autorenew(
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db),
):
    """Отключает автопродление: отменяет рекуррент в CloudPayments (если он был создан),
    доступ сохраняется до конца оплаченного периода."""
    sub = SubscriptionService.ensure_default_subscription(db, current_user)
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
        for cp_sub in await CloudPaymentsService.find_subscriptions(str(current_user.id)):
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
        logger.warning("CloudPayments find_subscriptions failed for %s: %s", current_user.id, err)
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

    sub = SubscriptionService.ensure_default_subscription(db, user)
    json_data = _coerce_json_data(data.get("JsonData"))
    if not json_data.get("plan_code"):
        json_data = {**json_data, **_coerce_json_data(data.get("Data"))}
    plan_code = str(json_data.get("plan_code") or sub.plan_code or "start").lower()
    billing_period = _normalize_billing_period(json_data.get("billing_period"))
    plan = SubscriptionService.get_plan_from_config(plan_code)
    event_name = (data.get("Type") or data.get("Event") or "").lower()

    # plan_code и billing_period приходят из JsonData, а его формирует ФРОНТ —
    # значит пользователь может подменить их в браузере и получить дорогой тариф
    # за цену дешёвого. Единственный доверенный факт — фактически списанная
    # сумма, поэтому тариф определяем по ней.
    amount_mismatch = False
    paid = _paid_amount(data)
    if paid is not None:
        expected = Decimal(_expected_amount(plan, billing_period))
        if paid != expected:
            resolved_plan, resolved_period = _resolve_plan_by_paid_amount(paid, billing_period)
            if resolved_plan is not None:
                logger.warning(
                    "CloudPayments webhook: заявлен тариф %s/%s (ожидалось %s), оплачено %s — "
                    "выдаём %s/%s по фактической сумме. user=%s",
                    plan_code, billing_period, expected, paid,
                    resolved_plan.code, resolved_period, user.id,
                )
                plan = resolved_plan
                plan_code = resolved_plan.code
                billing_period = resolved_period
            else:
                amount_mismatch = True
                logger.error(
                    "CloudPayments webhook: сумма %s не соответствует ни одному тарифу "
                    "(заявлен %s/%s, ожидалось %s). Тариф НЕ выдан. user=%s",
                    paid, plan_code, billing_period, expected, user.id,
                )

    expected_currency = (get_config().cloudpayments.currency or "RUB").upper()
    got_currency = str(data.get("Currency") or expected_currency).upper()
    if got_currency != expected_currency:
        amount_mismatch = True
        logger.error(
            "CloudPayments webhook: валюта %s вместо %s — тариф НЕ выдан. user=%s",
            got_currency, expected_currency, user.id,
        )

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

    # Идемпотентность. CloudPayments повторяет доставку, пока не получит code 0,
    # и без этой проверки повтор заново продлевал подписку. Запись в журнал —
    # она же и защита: TransactionId уникален частичным индексом.
    is_new_event = _record_billing_event(
        db,
        user=user,
        subscription=sub,
        event_type=outcome,
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

    # Сумма не сошлась ни с одним тарифом — состояние подписки не трогаем вовсе.
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

    # plan_code меняем ТОЛЬКО при успешной оплате. Раньше он переписывался и на
    # fail/cancel — то есть неудачный платёж за старший тариф всё равно менял
    # тариф пользователя, а от него считаются лимиты.
    prev_plan_code = (sub.plan_code or "").lower()
    new_plan_code = (plan.code or "").lower()
    prev_rank = PLAN_RANK.get(prev_plan_code, 0)
    new_rank = PLAN_RANK.get(new_plan_code, 0)
    is_downgrade = outcome == "pay" and new_rank and prev_rank and new_rank < prev_rank
    if outcome == "pay" and not is_downgrade:
        # Понижение вступает в силу в конце оплаченного периода, поэтому здесь
        # тариф не меняем — см. ветку ниже, где выставляется pending_plan_code.
        sub.plan_code = plan.code
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
            if is_downgrade:
                # Понижение: оплаченный уровень не отбираем досрочно. Текущий
                # тариф доживает до конца периода, новый — приписывается следом
                # и вступает в силу по его окончании (применяется лениво в
                # SubscriptionService при чтении подписки).
                base = max(now, sub.current_period_end) if sub.current_period_end else now
                sub.pending_plan_code = plan.code
                logger.info(
                    "Понижение тарифа %s -> %s отложено до %s (user=%s)",
                    prev_plan_code, new_plan_code, base.date(), user.id,
                )
            elif same_plan:
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
