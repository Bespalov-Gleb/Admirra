import time
import uuid
from importlib import util
from pathlib import Path

import pytest
import sqlalchemy as sa
from fastapi import HTTPException
from alembic.migration import MigrationContext
from alembic.operations import Operations

from core import models
from core.job_fence import fenced_job
from automation import work_ledger as ledger, lead_export_work as exports
from automation.work_tables import jobs, outbox, lead_exports, lead_resolutions
from lead_validator.services import project_intake as intake
from lead_validator.schemas import LeadInput
from ops import reconcile_leads as ops
from tests.test_durable_work import pg, expire
from tests.test_lead_scoped_stats import scope
from tests.test_lead_intake import start
from tests.test_lead_export_work import prepared


AUDIT = dict(actor='test-operator', reason='Synthetic operator acceptance', evidence_ref='synthetic-provider-case-123')


def version(s, kind, identifier):
    return ops.inspect(s.factory, kind, identifier, s.owner)['version']


def expired_intake(s):
    with s.factory() as db:
        lead, ctx = start(s, db)
    with s.factory.begin() as db:
        db.get(models.LeadIntake, ctx.intake_id).deadline = sa.func.now() - sa.text("interval '1 second'")
    return lead, ctx


def test_intake_close_preserves_unverified_and_prevents_late_writes(scope):
    s = scope
    lead, ctx = expired_intake(s)
    observed = ops.inspect(s.factory, 'intake', ctx.intake_id, s.owner)
    assert observed['deadline_expired'] and '+79000000001' not in str(observed)
    result = ops.resolve(s.factory, 'intake', ctx.intake_id, s.owner, version=observed['version'],
        decision='close_unverified', **AUDIT)
    assert result['resent'] is False
    with s.factory() as db:
        assert db.get(models.Lead, ctx.lead_id).status == models.LeadStatus.PENDING
        assert db.scalar(sa.select(sa.func.count()).select_from(lead_resolutions)) == 1
        _, replay = start(s, db)
        assert not replay.success and replay.rejection_reason == 'validation_closed_unverified'
        ctx.db = db
        with pytest.raises(HTTPException): ctx.finish(lead, True, 'passed', time.time(), None, {})
        assert db.scalar(sa.select(sa.func.count()).select_from(jobs)) == 0
    with pytest.raises(ValueError):
        ops.resolve(s.factory, 'intake', ctx.intake_id, s.owner, version=observed['version'], decision='close_unverified', **AUDIT)


@pytest.mark.parametrize('case', ['active', 'changed', 'owner', 'missing_evidence', 'wrong_decision'])
def test_intake_rejects_unsafe_operator_actions(scope, case):
    s = scope
    with s.factory() as db:
        lead, ctx = start(s, db)
    initial = version(s, 'intake', ctx.intake_id)
    if case != 'active':
        with s.factory.begin() as db:
            db.get(models.LeadIntake, ctx.intake_id).deadline = sa.func.now() - sa.text("interval '1 second'")
    if case != 'changed': initial = version(s, 'intake', ctx.intake_id)
    audit = {**AUDIT, 'evidence_ref': ''} if case == 'missing_evidence' else AUDIT
    with pytest.raises(ValueError):
        ops.resolve(s.factory, 'intake', ctx.intake_id, s.other if case == 'owner' else s.owner,
            version=initial, decision='confirm_delivered' if case == 'wrong_decision' else 'close_unverified', **audit)
    with s.factory() as db:
        assert db.scalar(sa.select(sa.func.count()).select_from(lead_resolutions)) == 0


async def uncertain(s):
    async def send(snapshot): return False, None
    with fenced_job(s.job, s.token), pytest.raises(RuntimeError):
        await exports.execute(s.factory, s.payload, sender=send)
    expire(s.factory, s.job)
    with s.factory.begin() as db: ledger.recover_expired(db)


@pytest.mark.asyncio
@pytest.mark.parametrize('decision', ['confirm_delivered', 'close_without_resend'])
async def test_export_resolution_updates_receipt_and_audit_without_requeue(prepared, decision):
    from ops.lead_status import snapshot
    s = prepared
    await uncertain(s)
    old_version = version(s, 'export', s.job)
    assert ops.resolve(s.factory, 'export', s.job, s.owner, version=old_version, decision=decision, **AUDIT)['resent'] is False
    with s.factory() as db:
        assert db.get(models.Lead, s.lead).exported_to_crm == (decision == 'confirm_delivered')
        assert db.scalar(sa.select(lead_exports.c.state)) == ('sent' if decision == 'confirm_delivered' else 'closed')
        assert db.scalar(sa.select(sa.func.count()).select_from(outbox)) == 0
        assert db.scalar(sa.select(sa.func.count()).select_from(lead_resolutions)) == 1
        assert snapshot(db)['exports'] == []
    with pytest.raises(ValueError):
        ops.resolve(s.factory, 'export', s.job, s.owner, version=old_version, decision=decision, **AUDIT)


@pytest.mark.asyncio
@pytest.mark.parametrize('change', ['active_worker', 'owner', 'body', 'settings', 'version'])
async def test_export_confirmation_cannot_forge_current_delivery(prepared, change):
    s = prepared
    if change != 'active_worker': await uncertain(s)
    before = version(s, 'export', s.job)
    with s.factory.begin() as db:
        if change == 'owner': db.get(models.PhoneProject, s.project).owner_id = s.other
        if change == 'settings': db.get(models.PhoneProject, s.project).crm_webhook_url = 'https://changed.example.test/'
        if change in ('body', 'version'): db.get(models.Lead, s.lead).name = 'changed'
    if change != 'version': before = version(s, 'export', s.job)
    with pytest.raises(ValueError):
        ops.resolve(s.factory, 'export', s.job, s.owner, version=before, decision='confirm_delivered', **AUDIT)
    with s.factory() as db: assert not db.get(models.Lead, s.lead).exported_to_crm


@pytest.mark.asyncio
async def test_confirmed_receipt_can_recover_lost_job_ack_but_not_be_downgraded(prepared):
    s = prepared
    async def send(snapshot): return True, None
    with fenced_job(s.job, s.token): await exports.execute(s.factory, s.payload, sender=send)
    # Simulate a connection error reported after the successful final COMMIT.
    with s.factory.begin() as db: ledger.finish(db, s.job, s.token, error=RuntimeError('lost acknowledgement'))
    before = version(s, 'export', s.job)
    with pytest.raises(ValueError):
        ops.resolve(s.factory, 'export', s.job, s.owner, version=before, decision='close_without_resend', **AUDIT)
    assert ops.resolve(s.factory, 'export', s.job, s.owner, version=before, decision='confirm_delivered', **AUDIT)['resent'] is False
    with s.factory() as db: assert db.scalar(sa.select(jobs.c.state)) == 'succeeded'


def test_two_operators_cannot_resolve_same_admission_twice(scope):
    from concurrent.futures import ThreadPoolExecutor
    s = scope
    _, ctx = expired_intake(s)
    before = version(s, 'intake', ctx.intake_id)
    def act(_):
        try:
            ops.resolve(s.factory, 'intake', ctx.intake_id, s.owner, version=before, decision='close_unverified', **AUDIT)
            return True
        except ValueError: return False
    with ThreadPoolExecutor(2) as pool: assert sum(pool.map(act, range(2))) == 1


def test_guard_cannot_be_disabled_after_a_settled_admission(scope, monkeypatch):
    from automation.work_preflight import check_lead_delivery_bindings
    s = scope
    with s.factory() as db:
        lead, ctx = start(s, db)
        ctx.finish(lead, False, 'test_rejection', time.time(), None, {})
    monkeypatch.setenv('LEAD_DELIVERY_GUARDS', 'false')
    with s.factory() as db, pytest.raises(RuntimeError, match='persisted admissions'):
        check_lead_delivery_bindings(db)


def test_resolution_migration(scope):
    path = Path(__file__).resolve().parents[1] / 'alembic/versions/f68b92a3b4c5_lead_reconciliation.py'
    spec = util.spec_from_file_location('lead_reconciliation_migration', path)
    migration = util.module_from_spec(spec); spec.loader.exec_module(migration)
    with scope.engine.begin() as db:
        lead_resolutions.drop(db)
        with Operations.context(MigrationContext.configure(db)):
            migration.upgrade()
            migration.downgrade()
        assert sa.inspect(db).has_table('lead_operation_resolutions')


def test_closed_intake_is_not_listed_as_rejected(scope, monkeypatch):
    from types import SimpleNamespace
    from backend_api.phone_leads import list_phone_leads, get_phone_lead_detail
    s = scope
    monkeypatch.setenv('LEAD_DELIVERY_GUARDS', 'true')
    lead, ctx = expired_intake(s)
    with s.factory() as db:
        pending = get_phone_lead_detail(ctx.lead_id, current_user=SimpleNamespace(id=s.owner), db=db)
        assert pending.validation_state == 'held'
    ops.resolve(s.factory, 'intake', ctx.intake_id, s.owner, version=version(s, 'intake', ctx.intake_id),
        decision='close_unverified', **AUDIT)
    with s.factory() as db:
        user = SimpleNamespace(id=s.owner)
        args = dict(project_id=None, start_date=None, end_date=None, current_user=user, db=db)
        assert list_phone_leads(is_accepted=False, **args) == []
        row = list_phone_leads(is_accepted=None, **args)[0]
        assert row.status == 'PENDING' and row.validation_state == 'closed'
        detail = get_phone_lead_detail(ctx.lead_id, current_user=user, db=db)
        assert detail.validation_state == 'closed' and not detail.is_accepted
