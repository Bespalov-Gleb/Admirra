"""Diagnostics must not act as a public proxy to shared service credentials."""
import asyncio
from importlib import import_module
import os
from types import SimpleNamespace
from unittest.mock import AsyncMock
import uuid

import httpx
import pytest
import sqlalchemy as sa
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from core import models, security
from core.database import get_db
from internal_admin.security import create_admin_access_token
from lead_validator.services import diagnostics as checks
from tests.test_lead_scoped_stats import scope
from tests.test_durable_work import pg

routes = import_module('lead_validator.router')


@pytest.fixture
def api(scope, monkeypatch):
    s = scope
    app = FastAPI()
    app.include_router(routes.router)
    def database():
        with s.factory() as db:
            yield db
    app.dependency_overrides[get_db] = database
    async def bounded(_):
        assert s.engine.pool.checkedout() == 0, 'SQL held during external IO'
    monkeypatch.setattr(routes, 'reserve_check', AsyncMock(side_effect=bounded))
    with s.factory.begin() as db:
        user = db.get(models.User, s.owner)
        user.email_verified = True
        email = user.email
    # Use the real auth dependencies, not an override of the access gate.
    user_token = security.create_access_token({'sub': email})
    with TestClient(app) as client:
        yield SimpleNamespace(client=client, s=s, app=app,
            headers={'Authorization': f'Bearer {user_token}'})


@pytest.mark.parametrize('endpoint', ['test-telegram', 'test-captcha-api', 'test-metrica'])
def test_shared_probes_require_internal_admin_token(api, monkeypatch, endpoint):
    probe = AsyncMock(return_value={'ok': True})
    monkeypatch.setattr(routes, 'provider_probe', probe)
    assert api.client.get('/lead/' + endpoint).status_code == 401
    assert api.client.get('/lead/' + endpoint, headers=api.headers).status_code in (401, 403)
    probe.assert_not_called()
    with api.s.factory.begin() as db:
        user = db.get(models.User, api.s.owner)
        user.role = models.UserRole.SUPERADMIN
        user.staff_status = models.StaffStatus.ACTIVE
        token = create_admin_access_token(user.id, user.email, 'SUPERADMIN')
    assert api.client.get('/lead/' + endpoint, headers=api.headers).status_code == 401
    response = api.client.get('/lead/' + endpoint, headers={'Authorization': f'Bearer {token}'})
    assert response.status_code == 200 and response.json() == {'ok': True}
    probe.assert_awaited_once()


@pytest.mark.parametrize('binding', ['foreign', 'missing', 'inactive', 'foreign_client'])
def test_invalid_project_rejected_before_provider_io(api, monkeypatch, binding):
    pid = api.s.project
    if binding == 'foreign':
        pid = api.s.foreign
    elif binding == 'missing':
        pid = uuid.uuid4()
    else:
        with api.s.factory.begin() as db:
            p = db.get(models.PhoneProject, pid)
            if binding == 'inactive':
                p.is_active = False
            else:
                c = models.Client(owner_id=api.s.other, name='Not owned')
                db.add(c); db.flush(); p.client_id = c.id
    from lead_validator.services.dadata import dadata_service
    provider = AsyncMock()
    monkeypatch.setattr(dadata_service, 'validate_phone', provider)
    response = api.client.post('/lead/test-validate', params={'phone': '+79990000000', 'project_id': str(pid)}, headers=api.headers)
    assert response.status_code == 404
    provider.assert_not_called()
    routes.reserve_check.assert_not_called()


@pytest.mark.parametrize('with_project', [False, True])
def test_dry_run_no_exports_or_shared_dedup_and_no_sql_during_io(api, monkeypatch, with_project):
    from lead_validator.services.dadata import dadata_service
    from lead_validator.services.telegram import telegram_notifier
    from lead_validator.services.redis_service import redis_service
    from lead_validator.services.social_checker import social_checker
    from lead_validator.services.bitrix_service import bitrix_service
    async def phone(_):
        assert api.s.engine.pool.checkedout() == 0
        return SimpleNamespace(type='MOBILE', provider='test', region='test', qc=0)
    monkeypatch.setattr(dadata_service, 'validate_phone', AsyncMock(side_effect=phone))
    monkeypatch.setattr(dadata_service, 'is_phone_valid', lambda _: True)
    spies = []
    for obj, method in [(telegram_notifier, 'send_new_lead'), (redis_service, 'is_duplicate'),
                        (redis_service, 'mark_phone'), (social_checker, 'check_phone'),
                        (bitrix_service, 'find_duplicates')]:
        spy = AsyncMock(); spies.append(spy); monkeypatch.setattr(obj, method, spy)
    params = {'phone': '+79990000000'}
    if with_project:
        with api.s.factory.begin() as db:
            p = db.get(models.PhoneProject, api.s.project)
            p.enable_spam_check = False
            p.enable_social_check = False
            p.enable_bitrix_check = True  # Global CRM must still not be queried.
        params['project_id'] = str(api.s.project)
    response = api.client.post('/lead/test-validate', params=params, headers=api.headers)
    assert response.status_code == 200 and response.json()['overall_valid'] is True
    for spy in spies:
        spy.assert_not_called()
    with api.s.factory() as db:
        assert db.scalar(sa.select(sa.func.count()).select_from(models.Lead)) == 0


def test_bad_input_and_limiter_prevent_paid_calls(api, monkeypatch):
    from lead_validator.services.dadata import dadata_service
    spy = AsyncMock(); monkeypatch.setattr(dadata_service, 'validate_phone', spy)
    assert api.client.get('/lead/check-phone', params={'phone': 'x' * 33}, headers=api.headers).status_code == 422
    assert api.client.get('/lead/check-phone', params={'phone': 'x' * 10}, headers=api.headers).status_code == 422
    assert api.client.post('/lead/test-validate', params={'phone': 'x' * 10}, headers=api.headers).json()['overall_valid'] is False
    monkeypatch.setattr(routes, 'reserve_check', AsyncMock(side_effect=HTTPException(429, 'limit')))
    assert api.client.get('/lead/check-phone', params={'phone': '+79990000000'}, headers=api.headers).status_code == 429
    spy.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize('provider', ['telegram', 'captcha', 'metrica'])
@pytest.mark.parametrize('failure', ['http', 'transport', 'invalid_json', 'ok'])
async def test_probes_only_read_and_never_expose_credentials(monkeypatch, provider, failure):
    from lead_validator.services.telegram import telegram_notifier
    from lead_validator.services.metrica_service import metrica_service
    secret = 'synthetic-private-provider-token'
    monkeypatch.setattr(telegram_notifier, 'token', secret)
    monkeypatch.setattr(metrica_service, 'enabled', True)
    monkeypatch.setattr(metrica_service, 'oauth_token', secret)
    monkeypatch.setattr(metrica_service, 'counter_id', '123')
    monkeypatch.setenv('YANDEX_IAM_TOKEN', secret)
    monkeypatch.setenv('YANDEX_FOLDER_ID', 'folder')
    requests = []
    def handle(request):
        requests.append(request)
        assert request.method == 'GET' and 'sendMessage' not in str(request.url)
        if failure == 'transport':
            raise httpx.ConnectError(secret, request=request)
        if failure == 'http':
            return httpx.Response(403, text=secret)
        if failure == 'invalid_json':
            return httpx.Response(200, text=secret)
        return httpx.Response(200, json={'ok': True, 'resources': [], 'counter': {}, 'secret': secret})
    real_client = httpx.AsyncClient
    monkeypatch.setattr(checks.httpx, 'AsyncClient', lambda **kw: real_client(transport=httpx.MockTransport(handle), **kw))
    response = await checks.provider_probe(provider)
    assert secret not in str(response) and len(requests) == 1
    assert response['ok'] is (failure == 'ok')
    if provider == 'telegram' and failure == 'ok':
        assert response['test_message_sent'] is False


@pytest.mark.asyncio
async def test_limiter_fails_closed(monkeypatch):
    monkeypatch.setattr(checks.redis_service, '_get_client', AsyncMock(return_value=None))
    with pytest.raises(HTTPException) as error:
        await checks.reserve_check(uuid.uuid4())
    assert error.value.status_code == 503


@pytest.mark.asyncio
async def test_real_shared_limiter_concurrent_reservations_and_ttl(monkeypatch):
    from redis.asyncio import Redis
    url = os.getenv('ISOLATED_REDIS_URL')
    assert os.getenv('WW_TEST') == '1' and url.startswith('redis://test-redis:')
    client = Redis.from_url(url, decode_responses=True)
    await client.flushdb()  # Dedicated synthetic DB 15 only.
    monkeypatch.setattr(checks.redis_service, '_get_client', AsyncMock(return_value=client))
    owner = uuid.uuid4()
    try:
        results = await asyncio.gather(*(checks.reserve_check(owner) for _ in range(20)), return_exceptions=True)
        assert sum(r is None for r in results) == 10
        assert all(r is None or isinstance(r, HTTPException) and r.status_code == 429 for r in results)
        assert await client.get(f'lead:diagnostic:user:{owner}:day') == '10'
        assert 0 < await client.ttl(f'lead:diagnostic:user:{owner}:minute') <= 60
        other = uuid.uuid4()
        await checks.reserve_check(other)
        await client.set(f'lead:diagnostic:user:{other}:day', 100, ex=86400)
        with pytest.raises(HTTPException) as error:
            await checks.reserve_check(other)
        assert error.value.status_code == 429
        assert 86000 < int(error.value.headers['Retry-After']) <= 86400
        await client.set('lead:diagnostic:global:minute', 60, ex=60)
        with pytest.raises(HTTPException):
            await checks.reserve_check(uuid.uuid4())
    finally:
        await client.flushdb()
        await client.aclose()
