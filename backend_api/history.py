from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend_api.access_control import get_accessible_client_ids, get_team_context
from core import models, schemas, security
from core.database import get_db

router = APIRouter(prefix="/history", tags=["History"])


@router.get("/", response_model=list[schemas.HistoryEventResponse])
def get_history(
    days: int = 30,
    client_id: Optional[UUID] = None,
    event_type: Optional[str] = None,
    limit: int = 200,
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db),
):
    ctx = get_team_context(db, current_user)
    q = db.query(models.HistoryEvent).filter(models.HistoryEvent.account_id == ctx.account_id)

    days = max(1, min(days, 365))
    dt_from = datetime.utcnow() - timedelta(days=days)
    q = q.filter(models.HistoryEvent.created_at >= dt_from)

    if event_type:
        q = q.filter(models.HistoryEvent.event_type == event_type)

    if client_id:
        q = q.filter(models.HistoryEvent.client_id == client_id)

    if not ctx.is_owner:
        allowed_ids = get_accessible_client_ids(db, current_user)
        q = q.filter(
            (models.HistoryEvent.client_id.is_(None))
            | (models.HistoryEvent.client_id.in_(allowed_ids if allowed_ids else []))
        )

    limit = max(1, min(limit, 500))
    return q.order_by(models.HistoryEvent.created_at.desc()).limit(limit).all()
