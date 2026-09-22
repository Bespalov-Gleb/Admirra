from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock
import uuid

import pytest
import sqlalchemy as sa
from fastapi import FastAPI
from fastapi.testclient import TestClient

from core import models, security
from core.database import get_db
from lead_validator.services import scoped_stats as stats
from tests.test_durable_work import pg


@pytest.fixture
def scope(pg):
    factory, engine = pg
    models.Base.metadata.create_all(engine)
    now = datetime(2026, 9, 22, 12, tzinfo=timezone.utc)
    with factory.begin() as db:
        owner = models.User(email='stats@example.test', password_hash='synthetic')
        other = models.User(email='other-stats@example.test', password_hash='synthetic')
        db.add_all([owner, other]); db.flush()
        p = models.PhoneProject(owner_id=owner.id, name='Own')
        foreign = models.PhoneProject(owner_id=other.id, name='Foreign')
        db.add_all([p, foreign]); db.flush()
        return SimpleNamespace(factory=factory, engine=engine, owner=owner.id,
            other=other.id, project=p.id, foreign=foreign.id, now=now)


def seed(s, **overrides):
    data = dict(project_id=s.project, phone='never-return-this', status=models.LeadStatus.INVALID,
        validation_reason='captcha_failed: private provider details', created_at=s.now - timedelta(hours=1))
    data.update(overrides)
    with s.factory.begin() as db:
        db.add(models.Lead(**data))


def test_owner_window_pending_and_authoritative_status(scope):
    s = scope
    seed(s)  # Invalid even if legacy is_valid disagrees.
    seed(s, is_valid=True, status=models.LeadStatus.SPAM)
    seed(s, status=models.LeadStatus.VALID, is_valid=False)
    seed(s, status=models.LeadStatus.VALID, is_spam=True)
    seed(s, status=models.LeadStatus.PENDING)
    seed(s, project_id=s.foreign)
    seed(s, created_at=s.now - timedelta(days=7))  # Inclusive lower bound.
    seed(s, created_at=s.now - timedelta(days=7, microseconds=1))
    seed(s, created_at=s.now)  # Exclusive upper bound.
    seed(s, created_at=s.now + timedelta(days=1))
    queries = []
    def capture(conn, cursor, statement, parameters, context, executemany):
        queries.append(statement)
    sa.event.listen(s.engine, 'before_cursor_execute', capture)
    try:
        with s.factory() as db:
            result = stats.project_statistics(db, s.owner, now=s.now)
    finally:
        sa.event.remove(s.engine, 'before_cursor_execute', capture)
    assert len(queries) == 1
    assert result['stats'] == dict(total=5, accepted=1, rejected=4, rejection_rate=80)
    assert len(result['project_stats']) == 1
    assert result['project_stats'][0]['project_id'] == s.project
    assert result['project_stats'][0]['acceptance_rate'] == 20
    assert 'never-return-this' not in str(result) and 'Foreign' not in str(result)


def test_daily_reasons_are_scoped_utc_and_grouped(scope):
    s = scope
    start = s.now.replace(hour=0)
    seed(s, created_at=start, validation_reason='captcha_failed: first')
    seed(s, validation_reason='captcha_failed: second')
    seed(s, validation_reason=None)
    seed(s, project_id=s.foreign, validation_reason='foreign secret')
    seed(s, status=models.LeadStatus.PENDING)
    seed(s, status=models.LeadStatus.VALID)
    seed(s, created_at=start - timedelta(microseconds=1))
    seed(s, created_at=start + timedelta(days=1))
    with s.factory() as db:
        result = stats.daily_rejections(db, s.owner, s.now.date())
    assert result == {'date': '2026-09-22', 'timezone': 'UTC', 'total': 3,
        'by_reason': {'captcha_failed': 2, 'unknown': 1}, 'other_count': 0,
        'by_reason_truncated': False, 'source': 'persisted_project_leads'}


def test_reason_bound_keeps_exact_total(scope, monkeypatch):
    s = scope
    monkeypatch.setattr(stats, 'MAX_REASON_ROWS', 2)
    for reason in ('a', 'a', 'b', 'c', 'd'):
        seed(s, validation_reason=reason)
    with s.factory() as db:
        result = stats.daily_rejections(db, s.owner, s.now.date())
    assert result['total'] == 5 and result['other_count'] == 2
    assert result['by_reason'] == {'a': 2, 'b': 1}
    assert result['by_reason_truncated'] is True


def test_project_bound_rejects_instead_of_partial_totals(scope, monkeypatch):
    s = scope
    monkeypatch.setattr(stats, 'MAX_PROJECT_ROWS', 1)
    seed(s)
    with s.factory.begin() as db:
        second = models.PhoneProject(owner_id=s.owner, name='Second')
        db.add(second); db.flush()
        db.add(models.Lead(project_id=second.id, phone='synthetic', status=models.LeadStatus.VALID))
    with s.factory() as db, pytest.raises(stats.StatsLimitExceeded):
        stats.project_statistics(db, s.owner, now=datetime.now(timezone.utc) + timedelta(seconds=1), days=365)


def test_empty_and_new_owner_never_uses_cached_old_owner(scope):
    s = scope
    seed(s)
    with s.factory() as db:
        assert stats.project_statistics(db, s.other, now=s.now)['stats']['total'] == 0
    with s.factory.begin() as db:
        db.get(models.PhoneProject, s.project).owner_id = s.other
    with s.factory() as db:
        assert stats.project_statistics(db, s.owner, now=s.now)['stats']['total'] == 0
        assert stats.project_statistics(db, s.other, now=s.now)['stats']['total'] == 1


@pytest.mark.parametrize('days', [0, 366, -1, True, '7'])
def test_period_validation_before_sql(days):
    with pytest.raises(ValueError):
        stats.project_statistics(None, uuid.uuid4(), days=days)


def test_missing_owner_and_naive_dates_fail_before_sql():
    with pytest.raises(ValueError, match='owner'):
        stats.project_statistics(None, None)
    with pytest.raises(ValueError, match='aware'):
        stats.project_statistics(None, uuid.uuid4(), now=datetime(2026, 9, 22))


def test_http_auth_date_and_tenant_scope(scope, monkeypatch):
    from importlib import import_module
    routes = import_module('lead_validator.router')
    from backend_api.phone_stats import router as phone_router
    s = scope
    seed(s); seed(s, project_id=s.foreign)
    global_read = AsyncMock(side_effect=AssertionError('Must not read global rejected log'))
    monkeypatch.setattr(routes.trash_logger, 'get_stats', global_read)
    app = FastAPI()
    app.include_router(routes.router)
    app.include_router(phone_router)
    def db():
        with s.factory() as session:
            yield session
    app.dependency_overrides[get_db] = db
    with TestClient(app) as client:
        assert client.get('/lead/stats').status_code in (401, 403)
        app.dependency_overrides[security.get_current_user] = lambda: SimpleNamespace(id=s.owner)
        response = client.get('/lead/stats', params={'date': '2026-09-22'})
        assert response.status_code == 200 and response.json()['total'] == 1
        assert client.get('/lead/stats', params={'date': '../../secret'}).status_code == 422
        assert client.get('/lead/stats', params={'date': '9999-12-31'}).status_code == 422
        assert client.get('/phone-stats/', params={'days': 0}).status_code == 422
        assert client.get('/phone-stats/', params={'days': 366}).status_code == 422
        assert client.get('/phone-stats/', params={'days': 365}).status_code == 200
        monkeypatch.setattr(stats, 'MAX_PROJECT_ROWS', 0)
        assert client.get('/phone-stats/', params={'days': 365}).status_code == 422
    global_read.assert_not_called()
