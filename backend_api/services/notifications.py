"""
Вспомогательные функции для создания in-app уведомлений.
"""
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from core import models

logger = logging.getLogger("api.notifications")


def create_notification(
    db: Session,
    user_id: uuid.UUID,
    type: str,
    title: str,
    body: Optional[str] = None,
    meta: Optional[dict] = None,
) -> models.Notification:
    """Создать in-app уведомление для пользователя и немедленно зафиксировать в сессии (flush)."""
    try:
        n = models.Notification(
            user_id=user_id,
            type=type,
            title=title,
            body=body,
            meta=meta,
        )
        db.add(n)
        db.flush()
        return n
    except Exception as e:
        logger.exception("Failed to create notification for user %s: %s", user_id, e)
        raise
