"""Superadmin: дашборд (ТЗ v1.0)."""
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from core.database import get_db
from core import models
from internal_admin.deps import require_superadmin
from internal_admin.services import month_ai_cost_usd, get_all_settings
from internal_admin.services.dashboard_metrics import calc_churn_rate_percent, calc_mrr_rub, _int

router = APIRouter(prefix="/dashboard", tags=["Internal Admin Dashboard"])


def _build_kpi(db: Session, days: int) -> dict:
    now = datetime.now(timezone.utc)
    dt_from = now - timedelta(days=days)
    prev_from = dt_from - timedelta(days=days)

    users_total = _int(
        db.query(func.count(models.User.id)).filter(models.User.role == models.UserRole.MANAGER).scalar()
    )
    users_new = _int(
        db.query(func.count(models.User.id))
        .filter(models.User.role == models.UserRole.MANAGER, models.User.created_at >= dt_from)
        .scalar()
    )
    users_new_prev = _int(
        db.query(func.count(models.User.id))
        .filter(
            models.User.role == models.UserRole.MANAGER,
            models.User.created_at >= prev_from,
            models.User.created_at < dt_from,
        )
        .scalar()
    )

    mrr = calc_mrr_rub(db)
    ai_used_sum = _int(db.query(func.coalesce(func.sum(models.User.ai_requests_used), 0)).scalar())
    ai_cost_month = month_ai_cost_usd(db, dt_from)
    churn_rate = calc_churn_rate_percent(db, dt_from, now)

    utm_rows = (
        db.query(models.User.registration_utm_source, func.count(models.User.id))
        .filter(
            models.User.created_at >= dt_from,
            models.User.registration_utm_source.isnot(None),
            models.User.role == models.UserRole.MANAGER,
        )
        .group_by(models.User.registration_utm_source)
        .order_by(func.count(models.User.id).desc())
        .limit(10)
        .all()
    )
    utm_total = sum(_int(c) for _, c in utm_rows) or 1
    utm_sources = [
        {"source": src or "unknown", "count": _int(cnt), "percent": round(_int(cnt) * 100 / utm_total, 1)}
        for src, cnt in utm_rows
    ]

    tariff_rows = (
        db.query(models.Subscription.plan_code, func.count(models.Subscription.id))
        .filter(models.Subscription.status == models.SubscriptionStatus.ACTIVE)
        .group_by(models.Subscription.plan_code)
        .all()
    )
    tariffs = [{"plan_code": p or "start", "count": _int(c)} for p, c in tariff_rows]

    platform_rows = (
        db.query(models.Integration.platform, func.count(models.Integration.id))
        .group_by(models.Integration.platform)
        .all()
    )
    integrations = [{"platform": p.value if p else "unknown", "count": _int(c)} for p, c in platform_rows]

    settings = get_all_settings(db)

    return {
        "period_days": days,
        "users_total": users_total,
        "users_new": users_new,
        "users_new_delta_vs_prev_period": users_new - users_new_prev,
        "mrr_rub": mrr,
        "ai_requests_total": ai_used_sum,
        "openai_cost_usd_month": ai_cost_month,
        "openai_balance_usd": settings.get("openai_balance_usd"),
        "churn_rate_percent": churn_rate,
        "utm_sources": utm_sources,
        "tariffs": tariffs,
        "integrations": integrations,
    }


@router.get("/overview")
@router.get("/kpi")
def dashboard_kpi(
    period: str = Query("month"),
    days: int = Query(30, ge=1, le=365),
    staff=Depends(require_superadmin),
    db: Session = Depends(get_db),
):
    if period == "month":
        days = 30
    return _build_kpi(db, days)


@router.get("/utm-sources")
def dashboard_utm(period: str = Query("month"), staff=Depends(require_superadmin), db: Session = Depends(get_db)):
    data = _build_kpi(db, 30 if period == "month" else 30)
    return {"items": data["utm_sources"]}


@router.get("/plans-distribution")
def dashboard_plans(staff=Depends(require_superadmin), db: Session = Depends(get_db)):
    data = _build_kpi(db, 30)
    return {"items": data["tariffs"]}


@router.get("/integrations-distribution")
def dashboard_integrations(staff=Depends(require_superadmin), db: Session = Depends(get_db)):
    data = _build_kpi(db, 30)
    return {"items": data["integrations"]}
