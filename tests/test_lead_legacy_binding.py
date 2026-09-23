from unittest.mock import AsyncMock
import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from core import models
from core.database import get_db
from lead_validator.schemas import ValidationResult
from lead_validator.validators import lead_validator
from tests.test_durable_work import pg
from tests.test_lead_scoped_stats import scope


@pytest.mark.parametrize('route', ['/lead/', '/webhook/tilda/', '/webhook/marquiz/'])
@pytest.mark.parametrize('auth', ['good', 'wrong', 'missing_project', 'missing_secret', 'legacy'])
def test_legacy_urls_bind_to_project_and_never_global_credentials(scope, monkeypatch, route, auth):
    from importlib import import_module
    s = scope
    monkeypatch.setenv('LEAD_DELIVERY_GUARDS', 'false' if auth == 'legacy' else 'true')
    with s.factory.begin() as db:
        db.get(models.PhoneProject, s.project).webhook_secret = 'synthetic-secret'
    app = FastAPI()
    app.include_router(import_module('lead_validator.router').router)
    app.include_router(import_module('lead_validator.webhook_router').router)
    def session():
        with s.factory() as db: yield db
    app.dependency_overrides[get_db] = session
    async def validate(*a, **kw):
        assert s.engine.pool.checkedout() == 0
        if auth != 'legacy':
            assert kw['project_id'] == s.project and len(kw['authorization_digest']) == 64
            assert kw['idempotency_key'] == 'event-1'
            if route != '/lead/': assert kw['skip_antibot_validation']
        return ValidationResult(success=True, execution_time_ms=0)
    spy = AsyncMock(side_effect=validate)
    monkeypatch.setattr(lead_validator, 'validate', spy)
    params = {} if auth in ('missing_project', 'legacy') else {'project_id': str(s.project)}
    headers = {'idempotency-key': 'event-1'}
    if auth != 'missing_secret': headers['x-webhook-secret'] = 'wrong' if auth == 'wrong' else 'synthetic-secret'
    with TestClient(app) as client:
        response = client.post(route, json={'phone': '+79000000001'}, params=params, headers=headers)
    assert response.status_code == (200 if auth in ('good', 'legacy') else 422 if auth == 'missing_project' else 401)
    assert spy.await_count == (1 if auth in ('good', 'legacy') else 0)
