"""Superadmin: лента активности."""
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from core.database import get_db
from core import models
from internal_admin.deps import require_superadmin
from internal_admin.models import AdminAuditLog

router = APIRouter(prefix="/activity", tags=["Internal Admin Activity"])


@router.get("")
def global_activity(
    days: int = Query(7, ge=1, le=365),
    event_type: str | None = None,
    q: str | None = None,
    limit: int = Query(200, ge=1, le=500),
    staff=Depends(require_superadmin),
    db: Session = Depends(get_db),
):
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
                "actor_email": r.actor_email,
                "event_type": r.event_type,
                "action": r.action,
                "description": r.description,
                "client_id": str(r.client_id) if r.client_id else None,
            }
            for r in rows
        ],
    }


@router.get("/audit")
def audit_log(
    days: int = Query(30, ge=1, le=365),
    limit: int = Query(200, ge=1, le=500),
    staff=Depends(require_superadmin),
    db: Session = Depends(get_db),
):
    dt_from = datetime.now(timezone.utc) - timedelta(days=days)
    rows = (
        db.query(AdminAuditLog)
        .filter(AdminAuditLog.created_at >= dt_from)
        .order_by(AdminAuditLog.created_at.desc())
        .limit(limit)
        .all()
    )
    return {
        "items": [
            {
                "id": str(r.id),
                "created_at": r.created_at,
                "staff_email": r.staff_email,
                "action": r.action,
                "description": r.description,
                "target_type": r.target_type,
                "target_id": r.target_id,
            }
            for r in rows
        ]
    }


