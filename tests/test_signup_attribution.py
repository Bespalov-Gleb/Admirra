import asyncio
import importlib.util
import json
from pathlib import Path
import time
from unittest.mock import AsyncMock
from urllib.parse import quote, urlparse, parse_qs

import pytest
import sqlalchemy as sa
from starlette.requests import Request
from starlette.responses import Response
from core import models, schemas
from backend_api import auth, oauth_login as oauth
from backend_api.services.signup_attribution import registration_attribution
from tests.test_oauth_signup_analytics import env, hook


def request(source='yandex', **overrides):
    value = dict(utm_source=source, utm_medium='cpc', utm_campaign='Тест 123', expires=int(time.time()*1000)+86400000)
    value.update(overrides)
    cookie = 'admirra_signup_utm=' + quote(json.dumps(value))
    return Request({'type':'http','headers':[(b'cookie',cookie.encode())]})


@pytest.mark.parametrize('raw', ['bad%', '{}', 'null', '[]', '{"expires":true}', 'x'*12001])
def test_malformed_cookie_never_breaks_registration(raw):
    req = Request({'type':'http','headers':[(b'cookie',('admirra_signup_utm='+raw).encode())]})
    assert registration_attribution(req) == {}


def test_expired_cookie_ignored_and_control_characters_bounded():
    assert registration_attribution(request(expires=0)) == {}
    assert registration_attribution(request(source='abc\n\x00xyz'))['registration_utm_source'] == 'abc  xyz'
    assert len(registration_attribution(request(source='a'*1000))['registration_utm_source']) == 256
    assert registration_attribution(request(), {'registration_utm_source':'explicit'})['registration_utm_source'] == 'explicit'


@pytest.mark.parametrize('provider', ['email','yandex','vk','max'])
def test_new_account_attribution_is_present_at_insert_and_existing_login_does_not_rewrite(env, monkeypatch, provider):
    inserted = []
    def capture(mapper, connection, user):
        inserted.append((user.registration_utm_source,user.registration_utm_medium,user.registration_utm_campaign))
    sa.event.listen(models.User, 'after_insert', capture)
    monkeypatch.setattr(auth, 'smtp_delivery_active', lambda: False)
    monkeypatch.setattr(auth, 'smtp_enabled', lambda: False)
    monkeypatch.setattr(auth, '_activate_pending_team_invites', lambda *a: None)
    monkeypatch.setattr(oauth, '_verify_oauth_state', lambda *a: None)
    monkeypatch.setattr(oauth, '_optional_current_user', lambda *a: None)
    monkeypatch.setattr(oauth, '_yandex_exchange_code', AsyncMock(return_value='synthetic'))
    monkeypatch.setattr(oauth, '_yandex_login_info', AsyncMock(return_value={'id':'new-yandex','default_email':'yandex@example.com','login':'Test'}))
    monkeypatch.setattr(oauth, 'VK_LOGIN_CLIENT_ID', 'synthetic')
    monkeypatch.setattr(oauth, '_vk_id_exchange_code_for_login', AsyncMock(return_value={'access_token':'synthetic'}))
    monkeypatch.setattr(oauth, '_vk_id_user_info', AsyncMock(return_value={'user_id':'new-vk','email':'vk@example.com'}))
    monkeypatch.setattr(oauth, 'MAX_BOT_TOKEN', 'synthetic')
    monkeypatch.setattr(oauth, '_resolve_max_bot_name', AsyncMock(return_value='test'))
    body = schemas.OAuthLoginCallbackRequest(code='test',state='test',redirect_uri='https://test.invalid',device_id='test',code_verifier='x'*43)
    def run(source):
        with env() as db:
            if provider == 'email':
                return asyncio.run(auth.register_user(schemas.UserCreate(email='email@example.com',password='synthetic'), request(source), db))
            if provider == 'max':
                data = asyncio.run(oauth.max_oauth_authorize_url(request(source), db))
                payload = parse_qs(urlparse(data['url']).query)['start'][0]
            else:
                fn = oauth.yandex_oauth_callback if provider == 'yandex' else oauth.vk_oauth_callback
                return asyncio.run(fn(body, request(source), Response(), db))
        hook(env, payload)  # A webhook has NO browser cookie; metadata comes from attempt.
    try:
        run('yandex')
        assert inserted == [('yandex','cpc','Тест 123')]
        if provider != 'email':
            run('vk')
            assert len(inserted) == 1
        with env() as db:
            user = db.query(models.User).one()
            assert user.registration_utm_source == 'yandex'
            # Actual bot formatter receives fields already persisted before outbox delivery.
            spec = importlib.util.spec_from_file_location('registration_formatter', Path(__file__).parents[1]/'ops/registration-notifier/notifier.py')
            import sys
            module = importlib.util.module_from_spec(spec); sys.modules[spec.name]=module; spec.loader.exec_module(module)
            message = module.format_message(dict(id=user.id,email=user.email,registration_utm_source=user.registration_utm_source,
                registration_utm_medium=user.registration_utm_medium,registration_utm_campaign=user.registration_utm_campaign))
            assert 'Источник: yandex' in message and 'UTM medium: cpc' in message and 'Кампания: Тест 123' in message
    finally:
        sa.event.remove(models.User, 'after_insert', capture)


def test_max_legacy_attempt_without_attribution_still_registers(env):
    from tests.test_oauth_signup_analytics import attempt
    _, payload = attempt(env)
    hook(env, payload)
    with env() as db:
        assert db.query(models.User).one().registration_utm_source is None


def test_expand_keeps_schema_revision_and_old_rows(pg):
    from ops.migrate_signup_attribution import migrate
    _, engine = pg
    with engine.begin() as c:
        c.execute(sa.text('CREATE TABLE alembic_version (version_num varchar(32) PRIMARY KEY)'))
        c.execute(sa.text("INSERT INTO alembic_version VALUES ('f68b92a3b4c5')"))
        c.execute(sa.text('CREATE TABLE max_oauth_login_attempts (id int PRIMARY KEY)'))
        c.execute(sa.text('INSERT INTO max_oauth_login_attempts VALUES (1)'))
        assert migrate(c) == 'applied'
        assert migrate(c) == 'already applied'
        assert c.execute(sa.text('SELECT registration_attribution FROM max_oauth_login_attempts')).scalar_one() is None
        assert c.execute(sa.text('SELECT version_num FROM alembic_version')).scalar_one() == 'f68b92a3b4c5'


from tests.test_signup_discount_flow import pg
