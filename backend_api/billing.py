import json
import logging
import uuid
from datetime import timedelta
from typing import Any, Dict, List, Optional
from urllib.parse import parse_qs

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import func
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
                "vat": int(cfg.cloudpayments.receipt_vat),
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
    active_status = getattr(models.ClientStatus, "ACTIVE", None)
    paused_status = getattr(models.ClientStatus, "PAUSED", None)
    projects_used = db.query(models.Client).filter(
        models.Client.owner_id == current_user.id,
        models.Client.status == active_status,
    ).count()
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
        billing_period="year" if sub.current_period_start and sub.current_period_end and (sub.current_period_end - sub.current_period_start).days >= 330 else "month",
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
        payment_method=None,
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

    amount = _yearly_price_from_monthly(plan.price_rub) if billing_period == "year" else plan.price_rub
    description = f"Подписка {plan.name} ({'год' if billing_period == 'year' else 'месяц'})"
    receipt = _build_cloudpayments_receipt(
        amount=amount,
        description=description,
        customer_email=current_user.email or "",
        cfg=cfg,
    )

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
    )


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
    success = bool(data.get("Success", True))

    sub.plan_code = plan.code
    sub.cloudpayments_subscription_id = str(data.get("SubscriptionId") or sub.cloudpayments_subscription_id or "")
    sub.cloudpayments_transaction_id = str(data.get("TransactionId") or sub.cloudpayments_transaction_id or "")
    now = SubscriptionService._now()

    if success and ("pay" in event_name or "recurrent" in event_name or not event_name):
        sub.status = models.SubscriptionStatus.ACTIVE
        sub.current_period_start = now
        sub.current_period_end = now + timedelta(days=_billing_period_days(plan, billing_period))
        user.is_subscribed = True
        user.subscription_expires_at = sub.current_period_end
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
        # Рекуррент (автосписание) — фоновое, клиента нет: шлём subscription_renewal
        # и payment_success с сервера. Первое/ручное списание: payment_success шлёт
        # клиент на странице успеха, поэтому с сервера шлём только trial_to_paid.
        try:
            from backend_api.services.metrika_conversions import upload_offline_conversion
            _amount = data.get("Amount") or data.get("Price")
            _amount = float(_amount) if _amount not in (None, "") else None
            _currency = str(data.get("Currency") or "RUB")
            _cid = getattr(user, "metrika_client_id", None)
            _yclid = getattr(user, "metrika_yclid", None)
            if "recurrent" in event_name:
                await upload_offline_conversion(target="subscription_renewal", price=_amount,
                                                currency=_currency, client_id=_cid, yclid=_yclid)
                await upload_offline_conversion(target="payment_success", price=_amount,
                                                currency=_currency, client_id=_cid, yclid=_yclid)
            else:
                await upload_offline_conversion(target="trial_to_paid", price=_amount,
                                                currency=_currency, client_id=_cid, yclid=_yclid)
        except Exception as _conv_err:
            logger.warning("Metrika offline conversion hook error: %s", _conv_err)
    elif "cancel" in event_name:
        sub.status = models.SubscriptionStatus.CANCELED
        user.is_subscribed = False
        create_notification(
            db,
            user_id=user.id,
            type="payment_failed",
            title="Подписка отменена",
            body="Ваша подписка была отменена. Вы можете оформить её заново в разделе «Тарифы».",
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
        user.is_subscribed = False
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
