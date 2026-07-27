"""Список и поиск клиентов SaaS для admin/manager API."""
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy import func, or_, cast, String
from sqlalchemy.orm import Session

from core import models
from internal_admin.services.user_helpers import serialize_saas_user


def saas_users_base_query(db: Session):
    return db.query(models.User).filter(models.User.role == models.UserRole.MANAGER)


def list_saas_users(
    db: Session,
    *,
    search: Optional[str] = None,
    plan_code: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 25,
    offset: int = 0,
) -> tuple[list[dict], int]:
    query = saas_users_base_query(db)
    if search:
        q = search.strip()
        like = f"%{q.lower()}%"
        filters = [
            func.lower(models.User.email).like(like),
            func.lower(func.coalesce(models.User.first_name, "")).like(like),
            func.lower(func.coalesce(models.User.last_name, "")).like(like),
        ]
        try:
            project_uuid = UUID(q)
            owner_id = db.query(models.Client.owner_id).filter(models.Client.id == project_uuid).scalar()
            if owner_id:
                filters.append(models.User.id == owner_id)
        except ValueError:
            owner_ids = [
                r[0]
                for r in db.query(models.Client.owner_id)
                .filter(cast(models.Client.id, String).ilike(f"%{q}%"))
                .distinct()
                .all()
            ]
            if owner_ids:
                filters.append(models.User.id.in_(owner_ids))
        query = query.filter(or_(*filters))

    total = query.count()
    rows = query.order_by(models.User.created_at.desc()).offset(offset).limit(limit).all()
    items = [serialize_saas_user(db, u) for u in rows]

    if plan_code:
        items = [i for i in items if i["plan_code"] == plan_code.lower()]
    if status:
        status = status.lower()
        if status == "blocked":
            items = [i for i in items if not i["is_active"]]
        elif status == "active":
            items = [i for i in items if i["is_active"] and i.get("subscription_status") == "ACTIVE"]
        elif status == "trial":
            items = [i for i in items if i.get("subscription_status") == "TRIAL"]
        elif status == "inactive":
            items = [i for i in items if i.get("subscription_status") in (None, "EXPIRED", "CANCELED")]

    return items, total


def manager_dashboard_summary(db: Session) -> dict:
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    yesterday_start = today_start - timedelta(days=1)

    total_users = (
        db.query(func.count(models.User.id))
        .filter(models.User.role == models.UserRole.MANAGER, models.User.is_active.is_(True))
        .scalar()
        or 0
    )
    active_today = (
        db.query(func.count(models.User.id))
        .filter(
            models.User.role == models.UserRole.MANAGER,
            models.User.last_login_at >= today_start,
        )
        .scalar()
        or 0
    )
    active_yesterday = (
        db.query(func.count(models.User.id))
        .filter(
            models.User.role == models.UserRole.MANAGER,
            models.User.last_login_at >= yesterday_start,
            models.User.last_login_at < today_start,
        )
        .scalar()
        or 0
    )
    trial_expiring = (
        db.query(func.count(models.Subscription.id))
        .filter(
            models.Subscription.status == models.SubscriptionStatus.TRIAL,
            models.Subscription.current_period_end.isnot(None),
            models.Subscription.current_period_end <= now + timedelta(days=3),
            models.Subscription.current_period_end >= now,
        )
        .scalar()
        or 0
    )
    return {
        "total_users": int(total_users),
        "active_today": int(active_today),
        "active_today_delta_vs_yesterday": int(active_today - active_yesterday),
        "trial_expiring_soon": int(trial_expiring),
    }
