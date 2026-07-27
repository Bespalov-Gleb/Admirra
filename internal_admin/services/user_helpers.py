"""Общие хелперы для пользователей SaaS в админке."""
from sqlalchemy.orm import Session
from sqlalchemy import func

from core import models
from backend_api.services.subscription import SubscriptionService


def user_full_name(user: models.User) -> str:
    return (
        " ".join(x for x in [user.first_name or "", user.last_name or ""] if x).strip()
        or user.username
        or user.email
    )


def serialize_saas_user(db: Session, user: models.User) -> dict:
    plan = SubscriptionService.get_user_plan(db, user)
    sub = SubscriptionService.get_user_subscription(db, user.id)
    projects_used = db.query(func.count(models.Client.id)).filter(models.Client.owner_id == user.id).scalar() or 0
    return {
        "user_id": str(user.id),
        "email": user.email,
        "full_name": user_full_name(user),
        "plan_code": plan.code,
        "plan_name": plan.name,
        "subscription_status": sub.status.value if sub else None,
        "projects": {"used": int(projects_used), "limit": int(plan.max_projects)},
        "ai_requests": {
            "used": int(user.ai_requests_used or 0),
            "limit": int(plan.max_ai_requests_per_period),
        },
        "is_active": bool(user.is_active),
        "last_login_at": user.last_login_at,
        "registered_at": user.created_at,
        "registration_utm_source": user.registration_utm_source,
    }
