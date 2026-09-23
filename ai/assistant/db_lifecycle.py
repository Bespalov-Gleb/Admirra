"""Short SQL phases for the interactive assistant; no ORM objects across IO."""
from types import SimpleNamespace
from uuid import UUID

from backend_api.access_control import get_accessible_client_ids
from core import models


class AccessChanged(RuntimeError):
    pass


class Snapshot(SimpleNamespace):
    def __repr__(self):
        return '<AssistantSnapshot>'  # May contain encrypted OAuth credentials.


def integration_snapshot(row):
    return Snapshot(**{column.key: getattr(row, column.key)
                       for column in models.Integration.__table__.columns})


def release_reads(db):
    if db.new or db.dirty or db.deleted:
        raise RuntimeError('Assistant cannot discard pending writes')
    db.rollback()


def authorize(db, user_id, *, conversation_id=None, client_id=None):
    user = db.query(models.User).filter(models.User.id == user_id).populate_existing().first()
    if user is None or not user.is_active:
        raise AccessChanged('Доступ к аккаунту изменился. Обновите страницу.')
    if conversation_id is not None and not db.query(models.AiConversation.id).filter(
        models.AiConversation.id == conversation_id, models.AiConversation.user_id == user_id,
    ).first():
        raise AccessChanged('Диалог больше недоступен.')
    if client_id is not None and UUID(str(client_id)) not in get_accessible_client_ids(db, user):
        raise AccessChanged('Доступ к проекту изменился. Выберите доступный проект.')
