import json
import uuid
from datetime import timedelta
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from backend_api.services.cloudpayments import CloudPaymentsService
from backend_api.services.subscription import SubscriptionService
from core import models, schemas, security
from core.config import get_config
from core.database import get_db

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


def _plan_to_schema(plan) -> schemas.BillingPlanResponse:
    return schemas.BillingPlanResponse(
        code=plan.code,
        name=plan.name,
        price_rub=plan.price_rub,
        max_projects=plan.max_projects,
        max_ai_requests_per_period=plan.max_ai_requests_per_period,
        period_days=plan.period_days,
        trial_days=plan.trial_days,
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
    db.flush()
    return schemas.BillingSubscriptionResponse(
        plan_code=plan.code,
        plan_name=plan.name,
        status=sub.status.value,
        is_subscribed=bool(current_user.is_subscribed),
        subscription_expires_at=current_user.subscription_expires_at,
        max_projects=plan.max_projects,
        max_ai_requests_per_period=plan.max_ai_requests_per_period,
        ai_requests_used=used,
        ai_requests_remaining=remaining,
        period_days=plan.period_days,
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

    # Для фронта готовим данные виджета, а реальную активацию фиксируем вебхуком.
    return schemas.BillingSubscribeResponse(
        public_id=cfg.cloudpayments.public_id,
        amount=_yearly_price_from_monthly(plan.price_rub) if billing_period == "year" else plan.price_rub,
        currency=cfg.cloudpayments.currency,
        description=f"Подписка {plan.name} ({'год' if billing_period == 'year' else 'месяц'})",
        account_id=str(current_user.id),
        email=current_user.email or "",
        plan_code=plan.code,
        billing_period=billing_period,
        trial_days=plan.trial_days,
        recurrent=_recurrent_for_billing_period(plan, billing_period),
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

    data = await request.json()
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
    elif "cancel" in event_name:
        sub.status = models.SubscriptionStatus.CANCELED
        user.is_subscribed = False
    else:
        sub.status = models.SubscriptionStatus.PAST_DUE
        user.is_subscribed = False

    db.flush()
    db.commit()
    return schemas.CloudPaymentsWebhookResponse(code=0)

