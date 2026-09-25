import asyncio
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
import json
from unittest.mock import AsyncMock
import uuid
import pytest
import sqlalchemy as sa
from starlette.requests import Request
from starlette.responses import Response
from core import models, schemas
from backend_api import oauth_login as oauth
from tests.test_signup_discount_flow import pg

@pytest.fixture
def env(pg, monkeypatch):
    factory, engine = pg
    models.Base.metadata.create_all(engine)
    monkeypatch.setattr(oauth, 'MAX_WEBHOOK_SECRET', 'synthetic-secret')
    monkeypatch.setattr(oauth, '_send_max_login_message', AsyncMock())
    monkeypatch.setattr(oauth.security, 'get_password_hash', lambda _: 'synthetic-hash')
    monkeypatch.setattr(oauth.SubscriptionService, 'ensure_default_subscription', lambda *a: None)
    monkeypatch.setattr(oauth, '_issue_token_for_user', lambda *a, **k: {'access_token':'synthetic','token_type':'bearer','is_new_user':False})
    return factory

def attempt(factory, user_id=None):
    state, payload = uuid.uuid4().hex, uuid.uuid4().hex
    with factory.begin() as db:
        db.add(models.MaxOAuthLoginAttempt(state_hash=oauth._token_hash(state),payload_hash=oauth._token_hash(payload),
            user_id=user_id,expires_at=datetime.now(timezone.utc)+timedelta(minutes=5)))
    return state,payload

def hook(factory, payload, uid='synthetic-max'):
    body={'update_type':'bot_started','payload':payload,'user':{'user_id':uid,'name':'Synthetic'}}
    async def receive():return {'type':'http.request','body':json.dumps(body).encode()}
    request=Request({'type':'http','headers':[(b'x-max-bot-api-secret',b'synthetic-secret')]}, receive)
    with factory() as db:return asyncio.run(oauth.max_oauth_webhook(request,db))

def status(factory,state):
    with factory() as db:
        result=oauth.max_oauth_status(state,Request({'type':'http','headers':[]}),Response(),db)
        return schemas.MaxOAuthStatusResponse(**result).model_dump()

def test_new_max_flag_survives_duplicate_hook_and_response_model(env):
    state,payload=attempt(env);hook(env,payload);hook(env,payload)
    result=status(env,state)
    assert result['status']=='completed' and result['is_new_user'] is True
    assert status(env,state)['status']=='used'
    state,payload=attempt(env);hook(env,payload)
    assert status(env,state)['is_new_user'] is False

def test_link_existing_even_just_created_is_not_registration(env):
    with env.begin() as db:
        user=models.User(email='existing@example.test',password_hash='synthetic');db.add(user);db.flush();uid=user.id
    state,payload=attempt(env,uid);hook(env,payload)
    assert status(env,state)['is_new_user'] is False

def test_concurrent_max_polls_only_one_completed(env):
    state,payload=attempt(env);hook(env,payload)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results=list(pool.map(lambda _:status(env,state),range(2)))
    assert sorted(r['status'] for r in results)==['completed','used']
    assert sum(r['is_new_user'] is True for r in results)==1

def test_pending_and_old_attempt_default_are_not_signup(env):
    state,_=attempt(env)
    assert status(env,state)['status']=='pending'
    with env() as db:assert db.query(models.MaxOAuthLoginAttempt).one().is_new_user is False

def test_duplicate_hook_cannot_rebind_completed_authorization(env):
    state,payload=attempt(env);hook(env,payload);hook(env,payload,'other-max-user')
    with env() as db:
        assert db.query(models.UserOAuthIdentity).one().provider_user_id=='synthetic-max'
    assert status(env,state)['is_new_user'] is True

def test_additive_migration_preserves_old_rows_and_is_idempotent(pg):
    from ops.migrate_max_signup_flag import migrate, OLD, NEW
    _,engine=pg
    with engine.begin() as c:
        c.execute(sa.text('CREATE TABLE alembic_version (version_num varchar(32) PRIMARY KEY)'))
        c.execute(sa.text('INSERT INTO alembic_version VALUES (:v)'),{'v':OLD})
        c.execute(sa.text('CREATE TABLE max_oauth_login_attempts (id integer PRIMARY KEY)'))
        c.execute(sa.text('INSERT INTO max_oauth_login_attempts VALUES (1)'))
        assert migrate(c)=='applied'
        assert c.execute(sa.text('SELECT is_new_user FROM max_oauth_login_attempts')).scalar_one() is False
        assert c.execute(sa.text('SELECT version_num FROM alembic_version')).scalar_one()==NEW
        assert migrate(c)=='already applied'

def test_migration_refuses_unknown_revision(pg):
    from ops.migrate_max_signup_flag import migrate
    _,engine=pg
    with engine.begin() as c:
        c.execute(sa.text('CREATE TABLE alembic_version (version_num varchar(32) PRIMARY KEY)'))
        c.execute(sa.text("INSERT INTO alembic_version VALUES ('unexpected')"))
        with pytest.raises(AssertionError):migrate(c)
