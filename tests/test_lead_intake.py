import time
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock
import uuid

import pytest
import sqlalchemy as sa
from fastapi import HTTPException

from core import models
from automation.work_tables import jobs
from lead_validator.schemas import LeadInput, ValidationResult
from lead_validator.services import project_intake as intake
from tests.test_durable_work import pg
from tests.test_lead_scoped_stats import scope


def start(s, db, key='event', **fields):
    lead = LeadInput(phone='+79000000001', **fields)
    return lead, intake.begin(db, s.project, lead, form_data=None, user_agent=None, referer=None, key=key)


def test_admission_idempotency_bounds_and_private_ledger(scope):
    s = scope
    with s.factory() as db:
        lead, ctx = start(s, db)
        assert s.engine.pool.checkedout() == 0
        with pytest.raises(HTTPException) as error:
            start(s, db)
        assert error.value.status_code == 409
        result = ctx.finish(lead, False, 'captcha_failed: private details', time.time(), None, {})
        assert result.lead_id and not result.success
        _, replay = start(s, db)
        assert replay == result
        with pytest.raises(HTTPException):
            start(s, db, name='different')
        with pytest.raises(HTTPException) as error:
            start(s, db, 'oversize', name='x' * 5000)
        assert error.value.status_code == 413
    with s.factory() as db:
        row = db.scalar(sa.select(models.LeadIntake))
        assert row.state == 'done' and len(row.key_digest) == 64
        assert '+79000000001' not in str(row.result)
        record = db.get(models.Lead, ctx.lead_id)
        assert record.status == models.LeadStatus.INVALID and record.validation_reason == 'captcha_failed'


def test_authorization_is_not_transferred_to_changed_project(scope):
    s = scope
    with s.factory() as db:
        original = intake.scope(db.get(models.PhoneProject, s.project))
        db.rollback()
        with s.factory.begin() as other:
            other.get(models.PhoneProject, s.project).webhook_secret = 'rotated'
        with pytest.raises(HTTPException) as error:
            intake.begin(db, s.project, LeadInput(phone='+79000000001'), form_data=None,
                user_agent=None, referer=None, authorization_digest=original)
        assert error.value.status_code == 409
        assert db.scalar(sa.select(sa.func.count()).select_from(models.LeadIntake)) == 0


@pytest.mark.parametrize('change', ['settings', 'deadline', 'disabled', 'owner'])
def test_changed_scope_never_finalizes_or_exports(scope, change):
    s = scope
    with s.factory() as db:
        lead, ctx = start(s, db)
        with s.factory.begin() as other:
            project = other.get(models.PhoneProject, s.project)
            if change == 'settings': project.telegram_chat_id = 'changed'
            if change == 'disabled': project.is_active = False
            if change == 'owner': project.owner_id = s.other
            if change == 'deadline': other.get(models.LeadIntake, ctx.intake_id).deadline = sa.func.now() - sa.text("interval '1 minute'")
        with pytest.raises(HTTPException):
            ctx.finish(lead, True, 'passed', time.time(), None, {})
    with s.factory() as db:
        assert db.get(models.Lead, ctx.lead_id).status == models.LeadStatus.PENDING
        assert db.scalar(sa.select(sa.func.count()).select_from(jobs)) == 0


def test_scoped_dedup_and_atomic_job_submission(scope, monkeypatch):
    s = scope
    with s.factory.begin() as db:
        db.get(models.PhoneProject, s.project).telegram_chat_id = 'synthetic'
    with s.factory() as db:
        lead, ctx = start(s, db)
        result = ctx.finish(lead, True, 'passed', time.time(), None, {})
        assert result.success
        lead2, ctx2 = start(s, db, 'second')
        duplicate = ctx2.finish(lead2, True, 'passed', time.time(), None, {})
        assert duplicate.rejection_reason == 'duplicate_contact'
        lead3, ctx3 = start(s, db, 'third')
        monkeypatch.setattr(intake, 'submit', lambda *a, **k: (_ for _ in ()).throw(RuntimeError('outbox down')))
        with pytest.raises(RuntimeError): ctx3.finish(lead3, False, 'invalid', time.time(), None, {})
    with s.factory() as db:
        assert db.get(models.Lead, ctx3.lead_id).status == models.LeadStatus.PENDING
        assert db.get(models.LeadIntake, ctx3.intake_id).state == 'processing'
        rows = db.execute(sa.select(jobs)).mappings().all()
        assert len(rows) == 2 and all(not row['replay_safe'] and row['max_attempts'] == 1 for row in rows)
        assert '+79000000001' not in str(rows)


def test_blacklist_reason_preserved(scope):
    with scope.factory() as db:
        lead, ctx = start(scope, db)
        ctx.finish(lead, False, 'utm_invalid:blacklisted_placement', time.time(), None, {})
    with scope.factory() as db:
        assert db.get(models.Lead, ctx.lead_id).validation_reason == 'utm_invalid:blacklisted_placement'


@pytest.mark.parametrize('change', ['blacklist', 'manual_status'])
def test_current_placement_and_manual_status_rechecked(scope, monkeypatch, change):
    from datetime import datetime, timezone
    from lead_validator.services.scoped_placements import key, dimensions
    s = scope
    monkeypatch.setattr(intake.settings, 'UTM_VALIDATION_ENABLED', True)
    with s.factory() as db:
        lead, ctx = start(s, db)
        with s.factory.begin() as other:
            if change == 'blacklist':
                now = datetime.now(timezone.utc)
                values = dimensions(None, None, None)
                other.add(models.LeadPlacementBlock(owner_id=s.owner, project_id=s.project,
                    placement_key=key(values), source=values[0], campaign=values[1], content=values[2],
                    reason='synthetic', created_at=now, expires_at=now + timedelta(hours=1)))
            else:
                other.get(models.Lead, ctx.lead_id).status = models.LeadStatus.SPAM
        if change == 'blacklist':
            result = ctx.finish(lead, True, 'passed', time.time(), None, {})
            assert not result.success and result.rejection_reason == 'utm_invalid:blacklisted_placement'
        else:
            with pytest.raises(HTTPException): ctx.finish(lead, True, 'passed', time.time(), None, {})
            assert db.get(models.Lead, ctx.lead_id).status == models.LeadStatus.SPAM


def test_concurrent_admissions_and_final_decisions(scope):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier
    s = scope
    barrier = Barrier(4)
    def admit(_):
        with s.factory() as db:
            barrier.wait()
            try:
                return start(s, db)[1].lead_id
            except HTTPException as error:
                assert error.status_code == 409
                return None
    with ThreadPoolExecutor(4) as pool:
        ids = list(pool.map(admit, range(4)))
    assert sum(x is not None for x in ids) == 1
    barrier = Barrier(4)
    def decide(i):
        with s.factory() as db:
            lead, ctx = start(s, db, f'parallel-{i}')
            barrier.wait()
            return ctx.finish(lead, True, 'passed', time.time(), None, {}).success
    with ThreadPoolExecutor(4) as pool:
        assert sum(pool.map(decide, range(4))) == 1
    with s.factory() as db:
        foreign = LeadInput(phone='+79000000001')
        context = intake.begin(db, s.foreign, foreign, form_data=None, user_agent=None, referer=None)
        assert context.finish(foreign, True, 'passed', time.time(), None, {}).success


@pytest.mark.asyncio
async def test_enrichment_without_sql(scope, monkeypatch):
    from lead_validator.services import lead_enrichment as e
    from lead_validator.services.social_checker import SocialCheckResult
    s = scope
    with s.factory.begin() as db:
        project = db.get(models.PhoneProject, s.project)
        project.enable_social_check = project.enable_gosuslugi_check = project.enable_lead_scoring = True
    async def social(*a):
        assert s.engine.pool.checkedout() == 0
        return SocialCheckResult(phone='+79000000001', has_telegram=True)
    async def gos(*a):
        assert s.engine.pool.checkedout() == 0
        return SimpleNamespace(has_registration=True, name='Synthetic', surname='Test')
    monkeypatch.setattr(e.social_checker, 'check_phone', social)
    monkeypatch.setattr(e.gosuslugi_checker, 'check', gos)
    with s.factory() as db:
        lead, ctx = start(s, db)
        result = await ctx.accept(lead, None, time.time())
        assert result.success and result.lead_score > 0
    with s.factory() as db:
        row = db.get(models.Lead, ctx.lead_id)
        assert row.name == 'Synthetic' and row.has_telegram and row.has_gosuslugi


@pytest.mark.asyncio
@pytest.mark.parametrize('secret', [None, 'wrong', 'correct'])
async def test_project_webhook_auth_before_validation(scope, monkeypatch, secret):
    from starlette.requests import Request
    from lead_validator.webhook_router import phone_project_webhook, lead_validator
    s = scope
    monkeypatch.setenv('LEAD_DELIVERY_GUARDS', 'true')
    with s.factory.begin() as db:
        db.get(models.PhoneProject, s.project).webhook_secret = 'correct'
    spy = AsyncMock(return_value=ValidationResult(success=False, execution_time_ms=0))
    monkeypatch.setattr(lead_validator, 'validate', spy)
    headers = [(b'idempotency-key', b'event-1')]
    if secret: headers.append((b'x-webhook-secret', secret.encode()))
    request = Request({'type': 'http', 'headers': headers, 'client': ('127.0.0.1', 1234)})
    with s.factory() as db:
        call = phone_project_webhook(str(s.project), request, {'phone': '+79000000001'}, db)
        if secret != 'correct':
            with pytest.raises(HTTPException) as error: await call
            assert error.value.status_code == 401
            spy.assert_not_awaited()
        else:
            await call
            assert spy.call_args.kwargs['idempotency_key'] == 'event-1'


@pytest.mark.asyncio
async def test_intake_limiter_is_atomic_and_fails_closed(monkeypatch):
    import asyncio
    import redis.asyncio as redis
    from lead_validator.services.redis_service import redis_service
    client = redis.from_url('redis://test-redis:6379/0')
    owner = uuid.uuid4()
    monkeypatch.setattr(redis_service, '_get_client', AsyncMock(return_value=client))
    monkeypatch.setenv('LEAD_INTAKE_PER_MINUTE', '3')
    async def attempt():
        try:
            await intake.reserve_intake(owner)
            return True
        except HTTPException as error:
            assert error.status_code == 429 and 1 <= int(error.headers['Retry-After']) <= 60
            return False
    try:
        assert sum(await asyncio.gather(*(attempt() for _ in range(12)))) == 3
        monkeypatch.setattr(redis_service, '_get_client', AsyncMock(side_effect=OSError('redis unavailable')))
        with pytest.raises(HTTPException) as error: await intake.reserve_intake(owner)
        assert error.value.status_code == 503
    finally:
        await client.delete(f'lead:intake:{owner}:minute', f'lead:intake:{owner}:hour', 'lead:intake:global:minute')
        await client.aclose()


@pytest.mark.asyncio
@pytest.mark.parametrize('stage', ['captcha', 'headers', 'antibot', 'quality', 'dadata', 'spam', 'utm', 'valid', 'timeout'])
async def test_validator_persists_every_decision_without_sql_during_io(scope, monkeypatch, stage):
    from lead_validator import validators as v
    from lead_validator.services import project_captcha, lead_enrichment
    s = scope
    monkeypatch.setenv('LEAD_DELIVERY_GUARDS', 'true')
    monkeypatch.setenv('DURABLE_TASKS', 'true')
    monkeypatch.setattr(intake, 'reserve_intake', AsyncMock())
    async def answer(value):
        assert s.engine.pool.checkedout() == 0
        return value
    async def captcha(*a): return await answer((stage != 'captcha', 'invalid'))
    async def dadata(*a):
        assert s.engine.pool.checkedout() == 0
        if stage == 'timeout': raise TimeoutError('synthetic')
        return SimpleNamespace(qc=0, type=None, provider=None, region=None, city=None)
    async def spam(*a): return await answer(SimpleNamespace(is_spam=stage == 'spam', category='test', is_whitelisted=False))
    async def utm(*a, **kw):
        assert kw['db'] is None
        return await answer(SimpleNamespace(is_valid=stage != 'utm', reason='test', warning=None))
    async def enrich(*a): return await answer({})
    monkeypatch.setattr(project_captcha, 'validate', captcha)
    monkeypatch.setattr(v.request_validator, 'validate', lambda *a: SimpleNamespace(is_valid=stage != 'headers', rejection_reason='request_invalid'))
    monkeypatch.setattr(v.LeadValidator, '_check_antibot', AsyncMock(return_value='honeypot_filled' if stage == 'antibot' else None))
    monkeypatch.setattr(v.LeadValidator, '_check_data_quality', lambda *a: 'bad_phone' if stage == 'quality' else None)
    monkeypatch.setattr(v.dadata_service, 'validate_phone', dadata)
    monkeypatch.setattr(v.dadata_service, 'is_phone_valid', lambda *a: stage != 'dadata')
    monkeypatch.setattr(v.spam_checker, 'check_phone', spam)
    monkeypatch.setattr(v.utm_validator, 'validate', utm)
    monkeypatch.setattr(v.settings, 'UTM_VALIDATION_ENABLED', True)
    monkeypatch.setattr(lead_enrichment, 'enrich', enrich)
    with s.factory() as db:
        call = v.LeadValidator().validate(LeadInput(phone='+79000000001'), user_agent='synthetic', project_id=s.project, db=db)
        if stage == 'timeout':
            with pytest.raises(TimeoutError): await call
        else:
            result = await call
            assert bool(result.success) == (stage == 'valid') and result.lead_id
        assert s.engine.pool.checkedout() == 0
    with s.factory() as db:
        record = db.scalar(sa.select(models.Lead))
        assert (record.status == models.LeadStatus.PENDING) == (stage == 'timeout')


def test_schema_preflight_and_migration(scope, monkeypatch):
    from importlib import util
    from pathlib import Path
    from alembic.migration import MigrationContext
    from alembic.operations import Operations
    from automation.work_preflight import check_lead_delivery_bindings
    s = scope
    spec = util.spec_from_file_location('intake_migration', Path(__file__).resolve().parents[1] / 'alembic/versions/f57a8192a3b4_lead_intakes.py')
    migration = util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    with s.engine.begin() as db:
        db.execute(sa.text('DROP TABLE lead_intakes, lead_export_receipts'))
        monkeypatch.setenv('LEAD_DELIVERY_GUARDS', 'true')
        with pytest.raises(RuntimeError): check_lead_delivery_bindings(db)
        monkeypatch.setattr(migration, 'op', Operations(MigrationContext.configure(db)))
        migration.upgrade()
        check_lead_delivery_bindings(db)
    with s.factory() as db: start(s, db)
    monkeypatch.setenv('LEAD_DELIVERY_GUARDS', 'false')
    with s.factory() as db, pytest.raises(RuntimeError): check_lead_delivery_bindings(db)


def test_operator_status_is_bounded_scoped_and_redacted(scope):
    from ops.lead_status import snapshot
    s = scope
    with s.factory() as db:
        start(s, db, 'one')
        start(s, db, 'two')
        state = snapshot(db, owner_id=s.owner, limit=1)
        assert len(state['intakes']) == 1 and state['intakes_truncated']
        assert '+79000000001' not in str(state) and 'key_digest' not in str(state)
        assert snapshot(db, owner_id=s.other)['intakes'] == []
