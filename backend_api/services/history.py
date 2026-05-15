import logging
from typing import Any, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from backend_api.access_control import get_team_context
from core import models

logger = logging.getLogger("api.history")


def log_history_event(
    db: Session,
    *,
    actor: Optional[models.User],
    event_type: str,
    action: str,
    description: Optional[str] = None,
    client_id: Optional[UUID] = None,
    target_type: Optional[str] = None,
    target_id: Optional[str] = None,
    meta: Optional[dict[str, Any]] = None,
) -> None:
    """Пишет событие в историю, не валит основной бизнес-флоу при ошибке."""
    try:
        account_id: Optional[UUID] = None
        actor_role: Optional[str] = None
        actor_user_id: Optional[UUID] = None
        actor_email: Optional[str] = None

        actor_name: Optional[str] = None

        if actor is not None:
            ctx = get_team_context(db, actor)
            account_id = ctx.account_id
            actor_role = "owner" if ctx.is_owner else (ctx.team_role or "unknown")
            actor_user_id = actor.id
            actor_email = actor.email
            parts = [actor.first_name or "", actor.last_name or ""]
            actor_name = " ".join(p for p in parts if p).strip() or actor.email

        if not account_id:
            return

        row = models.HistoryEvent(
            account_id=account_id,
            actor_user_id=actor_user_id,
            actor_email=actor_email,
            actor_name=actor_name,
            actor_role=actor_role,
            event_type=event_type,
            action=action,
            description=description,
            client_id=client_id,
            target_type=target_type,
            target_id=target_id,
            meta=meta,
        )
        db.add(row)
        db.flush()
    except Exception as e:
        logger.warning("history event skipped: %s", e)
