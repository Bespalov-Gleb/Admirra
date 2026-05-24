"""Superadmin: AI лимиты и расходы."""
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from core.database import get_db
from core import models
from internal_admin.deps import require_superadmin
from backend_api.services.subscription import SubscriptionService
from internal_admin.services import month_ai_cost_usd, get_all_settings
from internal_admin.services.user_helpers import user_full_name

router = APIRouter(prefix="/ai-limits", tags=["Internal Admin AI"])


@router.get("")
@router.get("/usage")
def ai_limits(
    threshold: int = Query(85, ge=1, le=100),
    staff=Depends(require_superadmin),
    db: Session = Depends(get_db),
):
    now = datetime.now(timezone.utc)
    dt_from = now - timedelta(days=30)
    prev_from = dt_from - timedelta(days=30)
    cost_month = month_ai_cost_usd(db, dt_from)
    cost_prev = month_ai_cost_usd(db, prev_from)

    plan_limits = {}
    for code in ("start", "basic", "standard", "white_label"):
        plan_limits[code] = SubscriptionService.get_plan_from_config(code).max_ai_requests_per_period

    items = []
    for u in db.query(models.User).filter(models.User.role == models.UserRole.MANAGER).all():
        plan = SubscriptionService.get_user_plan(db, u)
        used = int(u.ai_requests_used or 0)
        limit = max(int(plan.max_ai_requests_per_period), 1)
        pct = round(used * 100 / limit, 2)
        items.append(
            {
                "user_id": str(u.id),
                "email": u.email,
                "full_name": user_full_name(u),
                "plan_code": plan.code,
                "used": used,
                "limit": limit,
                "used_percent": pct,
                "close_to_limit": pct >= threshold,
            }
        )
    items.sort(key=lambda x: x["used_percent"], reverse=True)
    settings = get_all_settings(db)
    return {
        "threshold_percent": threshold,
        "close_to_limit": [x for x in items if x["close_to_limit"]],
        "items": items,
        "openai_cost_usd_month": cost_month,
        "openai_cost_usd_prev_month": cost_prev,
        "openai_cost_delta_usd": round(cost_month - cost_prev, 2),
        "openai_balance_usd": settings.get("openai_balance_usd"),
        "openai_alert_threshold_usd": settings.get("openai_alert_threshold_usd"),
        "plan_limits": plan_limits,
    }


@router.get("/expenses")
def ai_expenses(staff=Depends(require_superadmin), db: Session = Depends(get_db)):
    data = ai_limits(staff=staff, db=db)
    return {
        "openai_cost_usd_month": data["openai_cost_usd_month"],
        "openai_cost_usd_prev_month": data["openai_cost_usd_prev_month"],
        "openai_cost_delta_usd": data["openai_cost_delta_usd"],
        "openai_balance_usd": data["openai_balance_usd"],
        "openai_alert_threshold_usd": data["openai_alert_threshold_usd"],
    }


@router.get("/plan-limits")
def ai_plan_limits(staff=Depends(require_superadmin), db: Session = Depends(get_db)):
    data = ai_limits(staff=staff, db=db)
    return {"items": [{"plan_code": k, "limit": v} for k, v in data["plan_limits"].items()]}
