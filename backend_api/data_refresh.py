"""User-owned data preparation status. Never retries paid/external actions."""
from datetime import date
import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from core import models, security
from core.database import get_db
from core.data_requirements import DataNotReady
from automation import consumer_refresh as refresh

router = APIRouter(prefix="/data-refresh", tags=["data-refresh"])


def owned(db, ident, user):
    if not refresh.enabled():
        raise HTTPException(409, "Подготовка данных временно отключена")
    row = db.get(models.DataRefreshRequest, ident)
    if (not row or (row.user_id != user.id and row.consumer != "detector")
            or not refresh.authorized(db, user.id, [uuid.UUID(v) for v in row.state["ids"]])):
        raise HTTPException(404, "Подготовка данных не найдена")
    return row


@router.get("/{ident}")
def status(ident: uuid.UUID, user: models.User = Depends(security.get_current_user), db: Session = Depends(get_db)):
    return refresh.public(owned(db, ident, user))


@router.post("/{ident}/retry")
def retry(ident: uuid.UUID, user: models.User = Depends(security.get_current_user), db: Session = Depends(get_db)):
    row = owned(db, ident, user)
    try:
        state = row.state
        # Detector preparation belongs to the project's owner and is shared
        # with authorized teammates; it never runs an external send or payment.
        result = refresh.request(db, row.consumer, row.user_id, [uuid.UUID(v) for v in state["ids"]],
            date.fromisoformat(state["from"]), date.fromisoformat(state["to"]), retry=True)
        db.commit()
    except DataNotReady as exc:
        db.rollback()
        raise HTTPException(409, str(exc)) from None
    if result is None:
        raise HTTPException(409, "Подготовка временно недоступна. Повторите позже.")
    return result
