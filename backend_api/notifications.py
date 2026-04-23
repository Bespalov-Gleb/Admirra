"""
In-app уведомления: список, пометка прочитанными.
"""
import uuid
import logging
from typing import List, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from core.database import get_db
from core import models, security

logger = logging.getLogger("api.notifications")
router = APIRouter(prefix="/notifications", tags=["Notifications"])


class NotificationOut(BaseModel):
    id: uuid.UUID
    type: str
    title: str
    body: Optional[str] = None
    is_read: bool
    created_at: datetime

    class Config:
        from_attributes = True


@router.get("/", response_model=List[NotificationOut])
def list_notifications(
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db),
):
    """Последние 50 уведомлений текущего пользователя (новые первыми)."""
    rows = (
        db.query(models.Notification)
        .filter(models.Notification.user_id == current_user.id)
        .order_by(models.Notification.created_at.desc())
        .limit(50)
        .all()
    )
    return rows


@router.post("/read-all", status_code=204)
def mark_all_read(
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db),
):
    """Пометить все уведомления текущего пользователя прочитанными."""
    db.query(models.Notification).filter(
        models.Notification.user_id == current_user.id,
        models.Notification.is_read.is_(False),
    ).update({"is_read": True}, synchronize_session=False)
    db.commit()


@router.post("/{notification_id}/read", status_code=204)
def mark_one_read(
    notification_id: uuid.UUID,
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db),
):
    """Пометить одно уведомление прочитанным."""
    n = (
        db.query(models.Notification)
        .filter(
            models.Notification.id == notification_id,
            models.Notification.user_id == current_user.id,
        )
        .first()
    )
    if not n:
        raise HTTPException(status_code=404, detail="Уведомление не найдено")
    n.is_read = True
    db.commit()
