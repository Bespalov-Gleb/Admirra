"""Глобальная лента событий: GET /api/admin/events (ТЗ экран 04)."""
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from core.database import get_db
from core import models
from internal_admin.deps import require_superadmin

router = APIRouter(prefix="/events", tags=["Internal Admin Events"])


@router.get("")
def admin_events(
    type: str | None = None,
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    staff=Depends(require_superadmin),
    db: Session = Depends(get_db),
):
    query = db.query(models.HistoryEvent)
    if type:
        query = query.filter(models.HistoryEvent.event_type == type)
    offset = (page - 1) * limit
    rows = query.order_by(models.HistoryEvent.created_at.desc()).offset(offset).limit(limit).all()
    total = query.count()
    return {
        "items": [
            {
                "id": str(r.id),
                "created_at": r.created_at,
                "user_id": str(r.account_id) if r.account_id else None,
                "event_type": r.event_type,
                "action": r.action,
                "description": r.description,
            }
            for r in rows
        ],
        "page": page,
        "limit": limit,
        "total": total,
    }
