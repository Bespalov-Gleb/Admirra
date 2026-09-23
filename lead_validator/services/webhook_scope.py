"""Authorize legacy URLs against an explicit project, never a global credential."""
import hmac
import uuid

from fastapi import HTTPException
from lead_validator.services.project_intake import require_project, scope, release_read


def authorize(db, request, project_id, secret=None):
    release_read(db)
    if not isinstance(project_id, uuid.UUID):
        raise HTTPException(422, 'Укажите project_id проекта в URL вебхука')
    try:
        project = require_project(db, project_id)
        provided = request.headers.get('x-webhook-secret') or secret
        if not project.webhook_secret:
            raise HTTPException(503, 'Секрет вебхука проекта не настроен')
        if not provided or not hmac.compare_digest(provided.encode(), project.webhook_secret.encode()):
            raise HTTPException(401, 'Неверный секрет вебхука')
        return dict(project_id=project.id, authorization_digest=scope(project),
                    idempotency_key=request.headers.get('idempotency-key'))
    finally:
        db.rollback()
