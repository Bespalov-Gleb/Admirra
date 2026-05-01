from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, case
from sqlalchemy.orm import Session

from core import models, security
from core.database import get_db
from backend_api.services.subscription import SubscriptionService

router = APIRouter(prefix="/admin", tags=["Admin"])


def _require_admin(current_user: models.User) -> None:
    if current_user.role != models.UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Доступ только для супер-админа")


def _to_float(v) -> float:
    try:
        return float(v or 0)
    except Exception:
        return 0.0


def _to_int(v) -> int:
    try:
        return int(v or 0)
    except Exception:
        return 0


@router.get("/dashboard/overview")
def admin_dashboard_overview(
    days: int = Query(30, ge=1, le=365),
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db),
):
    _require_admin(current_user)
    now = datetime.now(timezone.utc)
    dt_from = now - timedelta(days=days)
    prev_from = dt_from - timedelta(days=days)

    users_total = _to_int(db.query(func.count(models.User.id)).scalar())
    users_new = _to_int(db.query(func.count(models.User.id)).filter(models.User.created_at >= dt_from).scalar())

    active_subs = (
        db.query(models.Subscription)
        .filter(models.Subscription.status.in_([models.SubscriptionStatus.ACTIVE, models.SubscriptionStatus.TRIAL]))
        .all()
    )
    mrr = 0
    for sub in active_subs:
        plan = SubscriptionService.get_plan_from_config(sub.plan_code or "start")
        mrr += _to_int(plan.price_rub)

    ai_used_sum = _to_int(db.query(func.coalesce(func.sum(models.User.ai_requests_used), 0)).scalar())
    active_cnt = len(active_subs)
    canceled_period = _to_int(
        db.query(func.count(models.Subscription.id))
        .filter(
            models.Subscription.status == models.SubscriptionStatus.CANCELED,
            models.Subscription.updated_at >= dt_from,
        )
        .scalar()
    )
    churn_rate = round((canceled_period / active_cnt * 100), 2) if active_cnt else 0.0

    utm_rows = (
        db.query(models.Lead.utm_source, func.count(models.Lead.id))
        .filter(models.Lead.created_at >= dt_from, models.Lead.utm_source.isnot(None))
        .group_by(models.Lead.utm_source)
        .order_by(func.count(models.Lead.id).desc())
        .limit(10)
        .all()
    )
    utm_sources = [{"source": src or "unknown", "count": _to_int(cnt)} for src, cnt in utm_rows]

    tariff_rows = db.query(models.Subscription.plan_code, func.count(models.Subscription.id)).group_by(models.Subscription.plan_code).all()
    tariffs = [{"plan_code": p or "start", "count": _to_int(c)} for p, c in tariff_rows]

    platform_rows = (
        db.query(models.Integration.platform, func.count(models.Integration.id))
        .group_by(models.Integration.platform)
        .all()
    )
    integrations = [{"platform": p.value if p else "unknown", "count": _to_int(c)} for p, c in platform_rows]

    return {
        "period_days": days,
        "users_total": users_total,
        "users_new": users_new,
        "mrr_rub": mrr,
        "ai_requests_total": ai_used_sum,
        "churn_rate_percent": churn_rate,
        "utm_sources": utm_sources,
        "tariffs": tariffs,
        "integrations": integrations,
        "previous_period_start": prev_from.isoformat(),
        "current_period_start": dt_from.isoformat(),
    }


@router.get("/users")
def admin_users(
    q: str | None = None,
    plan_code: str | None = None,
    status: str | None = None,  # active | blocked | trial | inactive
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db),
):
    _require_admin(current_user)
    sub_q = db.query(models.Subscription).subquery()
    rows = (
        db.query(models.User, sub_q.c.plan_code, sub_q.c.status)
        .outerjoin(sub_q, sub_q.c.user_id == models.User.id)
        .order_by(models.User.created_at.desc())
    )
    if q:
        like = f"%{q.strip().lower()}%"
        rows = rows.filter(
            func.lower(models.User.email).like(like)
            | func.lower(func.coalesce(models.User.first_name, "")).like(like)
            | func.lower(func.coalesce(models.User.last_name, "")).like(like)
        )
    if plan_code:
        rows = rows.filter(sub_q.c.plan_code == plan_code.lower())

    payload = []
    for user, row_plan_code, row_sub_status in rows.offset(offset).limit(limit).all():
        current_plan = SubscriptionService.get_user_plan(db, user)
        projects_count = _to_int(db.query(func.count(models.Client.id)).filter(models.Client.owner_id == user.id).scalar())
        item = {
            "user_id": str(user.id),
            "email": user.email,
            "full_name": " ".join([x for x in [user.first_name or "", user.last_name or ""] if x]).strip() or user.username or user.email,
            "is_active": bool(user.is_active),
            "created_at": user.created_at,
            "plan_code": (row_plan_code or current_plan.code or "start"),
            "subscription_status": row_sub_status.value if row_sub_status else None,
            "projects": {"used": projects_count, "limit": _to_int(current_plan.max_projects)},
            "ai_requests": {"used": _to_int(user.ai_requests_used), "limit": _to_int(current_plan.max_ai_requests_per_period)},
        }
        payload.append(item)

    if status:
        status = status.lower()
        filtered = []
        for item in payload:
            if status == "blocked" and not item["is_active"]:
                filtered.append(item)
            elif status == "active" and item["is_active"]:
                filtered.append(item)
            elif status == "trial" and item["subscription_status"] == models.SubscriptionStatus.TRIAL.value:
                filtered.append(item)
            elif status == "inactive" and item["subscription_status"] in [None, models.SubscriptionStatus.EXPIRED.value]:
                filtered.append(item)
        payload = filtered

    return {"items": payload, "count": len(payload), "offset": offset, "limit": limit}


@router.get("/users/{user_id}")
def admin_user_card(
    user_id: UUID,
    history_limit: int = Query(20, ge=1, le=200),
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db),
):
    _require_admin(current_user)
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")

    plan = SubscriptionService.get_user_plan(db, user)
    projects_count = _to_int(db.query(func.count(models.Client.id)).filter(models.Client.owner_id == user.id).scalar())
    integrations = (
        db.query(models.Integration)
        .join(models.Client, models.Client.id == models.Integration.client_id)
        .filter(models.Client.owner_id == user.id)
        .all()
    )
    history = (
        db.query(models.HistoryEvent)
        .filter((models.HistoryEvent.account_id == user.id) | (models.HistoryEvent.actor_user_id == user.id))
        .order_by(models.HistoryEvent.created_at.desc())
        .limit(history_limit)
        .all()
    )

    return {
        "user": {
            "id": str(user.id),
            "email": user.email,
            "full_name": " ".join([x for x in [user.first_name or "", user.last_name or ""] if x]).strip() or user.username or user.email,
            "registered_at": user.created_at,
            "is_active": user.is_active,
            "email_verified": user.email_verified,
        },
        "subscription": {
            "plan_code": plan.code,
            "plan_name": plan.name,
            "projects": {"used": projects_count, "limit": _to_int(plan.max_projects)},
            "ai_requests": {"used": _to_int(user.ai_requests_used), "limit": _to_int(plan.max_ai_requests_per_period)},
            "is_subscribed": bool(user.is_subscribed),
            "expires_at": user.subscription_expires_at,
        },
        "integrations": [
            {
                "id": str(i.id),
                "platform": i.platform.value,
                "account_id": i.account_id,
                "sync_status": i.sync_status.value if i.sync_status else None,
                "last_sync_at": i.last_sync_at,
                "error_message": i.error_message,
            }
            for i in integrations
        ],
        "history": [
            {
                "id": str(h.id),
                "created_at": h.created_at,
                "event_type": h.event_type,
                "action": h.action,
                "description": h.description,
                "client_id": str(h.client_id) if h.client_id else None,
            }
            for h in history
        ],
    }


@router.get("/ai-limits")
def admin_ai_limits(
    threshold: int = Query(85, ge=1, le=100),
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db),
):
    _require_admin(current_user)
    items = []
    for u in db.query(models.User).all():
        plan = SubscriptionService.get_user_plan(db, u)
        used = _to_int(u.ai_requests_used)
        limit = max(_to_int(plan.max_ai_requests_per_period), 1)
        pct = round(used * 100 / limit, 2)
        items.append(
            {
                "user_id": str(u.id),
                "email": u.email,
                "full_name": " ".join([x for x in [u.first_name or "", u.last_name or ""] if x]).strip() or u.username or u.email,
                "plan_code": plan.code,
                "used": used,
                "limit": limit,
                "used_percent": pct,
                "close_to_limit": pct >= threshold,
            }
        )
    items.sort(key=lambda x: x["used_percent"], reverse=True)
    flagged = [x for x in items if x["close_to_limit"]]
    return {"threshold_percent": threshold, "close_to_limit_count": len(flagged), "items": items}


@router.get("/activity")
def admin_activity(
    days: int = Query(7, ge=1, le=365),
    event_type: str | None = None,
    q: str | None = None,
    limit: int = Query(200, ge=1, le=500),
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db),
):
    _require_admin(current_user)
    dt_from = datetime.now(timezone.utc) - timedelta(days=days)
    query = db.query(models.HistoryEvent).filter(models.HistoryEvent.created_at >= dt_from)
    if event_type:
        query = query.filter(models.HistoryEvent.event_type == event_type)
    if q:
        like = f"%{q.strip().lower()}%"
        query = query.filter(func.lower(func.coalesce(models.HistoryEvent.description, "")).like(like))

    rows = query.order_by(models.HistoryEvent.created_at.desc()).limit(limit).all()
    return {
        "period_days": days,
        "items": [
            {
                "id": str(r.id),
                "created_at": r.created_at,
                "account_id": str(r.account_id),
                "actor_user_id": str(r.actor_user_id) if r.actor_user_id else None,
                "actor_email": r.actor_email,
                "event_type": r.event_type,
                "action": r.action,
                "description": r.description,
                "client_id": str(r.client_id) if r.client_id else None,
                "meta": r.meta,
            }
            for r in rows
        ],
    }


@router.get("/integrations/summary")
def admin_integrations_summary(
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db),
):
    _require_admin(current_user)
    rows = (
        db.query(
            models.Integration.platform,
            func.count(models.Integration.id),
            func.sum(case((models.Integration.sync_status == models.IntegrationSyncStatus.FAILED, 1), else_=0)),
        )
        .group_by(models.Integration.platform)
        .all()
    )
    items = []
    for platform, total, failed in rows:
        items.append(
            {
                "platform": platform.value if platform else "unknown",
                "total_connected": _to_int(total),
                "failed_sync_count": _to_int(failed),
            }
        )
    return {"items": items}

