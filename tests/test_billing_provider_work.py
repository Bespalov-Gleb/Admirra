"""Account-order/failure tests. All provider calls are synthetic and offline."""
import uuid
from unittest.mock import AsyncMock
import pytest
import sqlalchemy as sa
from core import models, billing_intents as intent
from core.job_fence import fenced_job
from automation import billing_provider_work as work, work_ledger as ledger
from automation.work_tables import jobs
from automation.work_errors import RejectedBeforeExternalIO
from backend_api.services.cloudpayments import CloudPaymentsService as CP
from tests.test_durable_work import pg, claim, expire
from tests.test_billing_work import billing_scope, populate


@pytest.fixture
def ordered(billing_scope, monkeypatch):
    monkeypatch.setenv('DURABLE_TASKS', 'true')
    monkeypatch.setenv('BILLING_PROVIDER_QUEUE', 'true')
    populate(billing_scope)
    factory, owners = billing_scope
    async def find(owner):
        assert factory.kw['bind'].pool.checkedout() == 0
        return [{'Id': 'synthetic-1', 'AccountId': owner, 'Status': 'Active'}]
    async def mutate(*args, **kwargs):
        assert factory.kw['bind'].pool.checkedout() == 0
    monkeypatch.setattr(CP, 'find_subscriptions', AsyncMock(side_effect=find))
    monkeypatch.setattr(CP, 'update_subscription', AsyncMock(side_effect=mutate))
    monkeypatch.setattr(CP, 'cancel_subscription', AsyncMock(side_effect=mutate))
    return billing_scope


def enqueue(scope, command, target=None):
    with scope[0].begin() as db:
        sub = db.get(models.Subscription, uuid.UUID(int=1))
        if command == 'cancel_all':
            sub.cancel_at_period_end = True
        op = intent.enqueue(db, sub, command, target)
        return op.id, op.job_id


async def execute(scope, job_id, finish=True):
    factory = scope[0]
    job = claim(factory, job_id)
    assert job
    error = None
    try:
        with fenced_job(job_id, job['lease_token']):
            return await work.execute(factory, job['payload'])
    except Exception as exc:
        error = exc
        raise
    finally:
        if finish:
            with factory.begin() as db:
                ledger.finish(db, job_id, job['lease_token'], error=error)


@pytest.mark.asyncio
async def test_coalesces_and_updates_without_sql_over_http(ordered):
    op, job = enqueue(ordered, 'update')
    assert enqueue(ordered, 'update') == (op, job)
    assert await execute(ordered, job) == 'confirmed'
    CP.update_subscription.assert_awaited_once()
    with ordered[0]() as db:
        assert db.get(models.BillingProviderOperation, op).status == 'confirmed'
        assert not db.get(models.Subscription, uuid.UUID(int=1)).recurring_sync_required


@pytest.mark.asyncio
async def test_fifo_cancel_wins_over_stale_update(ordered):
    _, update = enqueue(ordered, 'update')
    _, cancel = enqueue(ordered, 'cancel_all')
    assert claim(ordered[0], cancel) is None
    assert await execute(ordered, update) == 'superseded'
    assert await execute(ordered, cancel) == 'confirmed'
    CP.update_subscription.assert_not_called()
    CP.cancel_subscription.assert_awaited_once_with('synthetic-1')
    with ordered[0]() as db:
        assert db.get(models.Subscription, uuid.UUID(int=1)).cloudpayments_subscription_id is None


@pytest.mark.asyncio
async def test_timeout_blocks_later_intent_and_preserves_card(ordered):
    CP.update_subscription.side_effect = TimeoutError('synthetic')
    op, job = enqueue(ordered, 'update')
    with pytest.raises(work.BillingProviderUncertain):
        await execute(ordered, job)
    _, cancel = enqueue(ordered, 'cancel_all')
    assert claim(ordered[0], cancel) is None
    with ordered[0]() as db:
        assert db.get(models.BillingProviderOperation, op).status == 'uncertain'
        assert db.get(models.Subscription, uuid.UUID(int=1)).cloudpayments_subscription_id == 'synthetic-1'
        with pytest.raises(Exception) as exc:
            intent.assert_checkout_allowed(db, ordered[1][0])
        assert exc.value.status_code == 409


@pytest.mark.asyncio
async def test_find_error_is_not_empty_success(ordered):
    CP.find_subscriptions.side_effect = RuntimeError('synthetic')
    op, job = enqueue(ordered, 'cancel_all')
    with pytest.raises(RejectedBeforeExternalIO):
        await execute(ordered, job)
    CP.cancel_subscription.assert_not_called()
    with ordered[0]() as db:
        assert db.get(models.BillingProviderOperation, op).status == 'rejected'
        assert db.get(models.Subscription, uuid.UUID(int=1)).cloudpayments_subscription_id


@pytest.mark.asyncio
async def test_never_reactivates_inactive_subscription(ordered):
    CP.find_subscriptions.side_effect = None
    CP.find_subscriptions.return_value = [{'Id': 'synthetic-1', 'Status': 'Cancelled'}]
    _, job = enqueue(ordered, 'update')
    with pytest.raises(RejectedBeforeExternalIO):
        await execute(ordered, job)
    CP.update_subscription.assert_not_called()


@pytest.mark.asyncio
async def test_crash_after_confirmation_recovers_ack_not_payment(ordered):
    _, job = enqueue(ordered, 'update')
    assert await execute(ordered, job, finish=False) == 'confirmed'
    expire(ordered[0], job)
    with ordered[0].begin() as db:
        ledger.recover_expired(db)
    with ordered[0]() as db:
        assert db.scalar(sa.select(jobs.c.state).where(jobs.c.id == job)) == 'succeeded'
    CP.update_subscription.assert_awaited_once()


@pytest.mark.asyncio
async def test_api_cancellation_only_records_intent(ordered, monkeypatch):
    from backend_api import billing
    monkeypatch.setattr(billing.SubscriptionService, 'get_billing_account_user', lambda db, user: user)
    monkeypatch.setattr(billing.SubscriptionService, 'ensure_default_subscription',
        lambda db, user: db.get(models.Subscription, uuid.UUID(int=1)))
    monkeypatch.setattr(billing, 'log_history_event', lambda *a, **kw: None)
    with ordered[0]() as db:
        sub = db.get(models.Subscription, uuid.UUID(int=1))
        sub.card_last4 = '1234'
        db.commit()
        result = await billing.cancel_autorenew(db.get(models.User, ordered[1][0]), db)
        assert result['cancellation_pending'] and not result['recurrent_cancelled']
        assert sub.card_last4 == '1234'
    CP.find_subscriptions.assert_not_called()
    CP.cancel_subscription.assert_not_called()


@pytest.mark.asyncio
async def test_sdk_rejects_legacy_direct_mutations(monkeypatch):
    monkeypatch.setenv('BILLING_PROVIDER_QUEUE', 'true')
    monkeypatch.setenv('DURABLE_TASKS', 'true')
    with pytest.raises(RuntimeError, match='durable account queue'):
        await CP.update_subscription('synthetic', Amount=1)
    with pytest.raises(RuntimeError, match='durable account queue'):
        await CP.cancel_subscription('synthetic')


@pytest.mark.asyncio
async def test_changed_terms_in_flight_enqueue_new_desired_state(ordered):
    async def change(*_, **__):
        with ordered[0].begin() as db:
            db.get(models.Subscription, uuid.UUID(int=1)).pending_purchased_project_slots = 2
    CP.update_subscription.side_effect = change
    op, job = enqueue(ordered, 'update')
    await execute(ordered, job)
    with ordered[0]() as db:
        pending = intent.pending(db, ordered[1][0])
        assert pending and pending.id != op and pending.command == 'update'
        assert db.get(models.Subscription, uuid.UUID(int=1)).recurring_sync_required


@pytest.mark.asyncio
async def test_partial_cancel_never_replays_confirmed_recipient(ordered):
    CP.find_subscriptions.side_effect = None
    CP.find_subscriptions.return_value = [{'Id': i, 'Status': 'Active'} for i in ['first', 'second']]
    CP.cancel_subscription.side_effect = [None, TimeoutError('synthetic')]
    op, job = enqueue(ordered, 'cancel_all')
    with pytest.raises(work.BillingProviderUncertain):
        await execute(ordered, job)
    with ordered[0]() as db:
        steps = db.get(models.BillingProviderOperation, op).evidence['steps']
        assert steps == [{'id': 'first', 'status': 'confirmed'}, {'id': 'second', 'status': 'sending'}]
    assert claim(ordered[0], job) is None


@pytest.mark.asyncio
async def test_lost_lease_cannot_commit_confirmation(ordered):
    from core.job_fence import LeaseLost
    op, job = enqueue(ordered, 'update')
    async def lose(*_, **__):
        # External actor, not a write under the expired worker's fence.
        from core.job_fence import current_fence
        token = current_fence.set(None)
        try:
            expire(ordered[0], job)
        finally:
            current_fence.reset(token)
    CP.update_subscription.side_effect = lose
    with pytest.raises(LeaseLost):
        await execute(ordered, job)
    with ordered[0].begin() as db:
        ledger.recover_expired(db)
    with ordered[0]() as db:
        assert db.get(models.BillingProviderOperation, op).status == 'dispatching'
        assert db.scalar(sa.select(jobs.c.state).where(jobs.c.id == job)) == 'uncertain'


@pytest.mark.asyncio
async def test_operator_requires_current_observation_and_audits_new_intent(ordered):
    from ops.billing.reconcile_operations import inspect, retry_current
    CP.update_subscription.side_effect = TimeoutError('synthetic')
    op, job = enqueue(ordered, 'update')
    with pytest.raises(work.BillingProviderUncertain):
        await execute(ordered, job)
    observation = await inspect(ordered[0], op)
    arguments = dict(version=observation['version'], provider_fingerprint=observation['provider_fingerprint'],
        actor='operator@example.test', reason='Synthetic test reconciliation', settled_reference='CP case synthetic settled')
    with pytest.raises(ValueError, match='changed'):
        await retry_current(ordered[0], op, **{**arguments, 'version': 'stale'})
    result = await retry_current(ordered[0], op, **arguments)
    assert result['next_operation'] != str(op)
    assert CP.update_subscription.await_count == 1  # Inspect/resolve never write to CP.
    with ordered[0]() as db:
        old = db.get(models.BillingProviderOperation, op)
        assert old.status == 'superseded'
        assert old.evidence['resolution']['actor'] == arguments['actor']
        assert db.scalar(sa.select(jobs.c.state).where(jobs.c.id == job)) == 'failed'
        new = db.get(models.BillingProviderOperation, uuid.UUID(result['next_operation']))
        next_job = new.job_id
    assert claim(ordered[0], next_job)


def test_queue_rollback_is_atomic(ordered):
    with ordered[0]() as db:
        intent.enqueue(db, db.get(models.Subscription, uuid.UUID(int=1)), 'update')
        db.rollback()
    with ordered[0]() as db:
        assert db.scalar(sa.select(sa.func.count()).select_from(models.BillingProviderOperation)) == 0
        assert db.scalar(sa.select(sa.func.count()).select_from(jobs)) == 0


def test_status_scope_and_preflight_cannot_hide_pending(ordered, monkeypatch):
    from backend_api import billing
    from automation.work_preflight import check_billing_bindings
    monkeypatch.setattr(billing.SubscriptionService, 'get_billing_account_user', lambda db, user: user)
    enqueue(ordered, 'update')
    with ordered[0]() as db:
        assert billing.get_provider_operation(db.get(models.User, ordered[1][0]), db)['operation']
        assert billing.get_provider_operation(db.get(models.User, ordered[1][1]), db)['operation'] is None
        check_billing_bindings(db)
        monkeypatch.setenv('BILLING_PROVIDER_QUEUE', 'false')
        with pytest.raises(RuntimeError, match='Cannot disable'):
            check_billing_bindings(db)


def test_late_payment_does_not_reenable_cancellation(ordered):
    from types import SimpleNamespace
    from datetime import timedelta
    op, _ = enqueue(ordered, 'cancel_all')
    with ordered[0]() as db:
        sub = db.get(models.Subscription, uuid.UUID(int=1))
        cancelled = db.get(models.BillingProviderOperation, op).created_at
        assert intent.cancellation_wins(db, sub, None)
        assert intent.cancellation_wins(db, sub, SimpleNamespace(created_at=cancelled - timedelta(seconds=1)))
        assert not intent.cancellation_wins(db, sub, SimpleNamespace(created_at=cancelled + timedelta(seconds=1)))


def test_legacy_unknown_cannot_be_bypassed(ordered):
    _, job = enqueue(ordered, 'update')
    with ordered[0].begin() as db:
        old = ledger.submit(db, kind='billing.recurring', queue='maintenance', key='old',
            resource='old-recurring-resource', tenant=str(ordered[1][0]), payload={})
        db.execute(jobs.update().where(jobs.c.id == old).values(state='uncertain'))
    assert claim(ordered[0], job) is None


def test_additive_migration_and_evidence_survives_downgrade(pg, monkeypatch):
    import importlib.util
    from pathlib import Path
    from alembic.migration import MigrationContext
    from alembic.operations import Operations
    spec = importlib.util.spec_from_file_location('billing_operation_migration', Path(__file__).resolve().parents[1] /
        'alembic/versions/f35e6f708192_billing_provider_operations.py')
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    with pg[1].begin() as connection:
        monkeypatch.setattr(migration, 'op', Operations(MigrationContext.configure(connection)))
        migration.upgrade()
        columns = {c['name'] for c in sa.inspect(connection).get_columns('billing_provider_operations')}
        assert columns == set(models.BillingProviderOperation.__table__.columns.keys())
        migration.downgrade()
        assert sa.inspect(connection).has_table('billing_provider_operations')


@pytest.mark.asyncio
@pytest.mark.parametrize('status,provider', [('Active', 'synthetic-1'), ('Cancelled', 'old-replaced')])
async def test_late_recurrent_webhooks_cannot_undo_cancel_or_new_subscription(ordered, monkeypatch, status, provider):
    from backend_api import billing
    from tests.test_signup_discount_flow import request
    monkeypatch.setattr(CP, 'validate_webhook_signature', lambda *args: True)
    enqueue(ordered, 'cancel_all')
    with ordered[0]() as db:
        result = await billing.cloudpayments_webhook(request({'AccountId': str(ordered[1][0]),
            'Id': provider, 'Status': status}), db)
        assert result.code == 0
        sub = db.get(models.Subscription, uuid.UUID(int=1))
        assert sub.cancel_at_period_end
        assert sub.cloudpayments_subscription_id == 'synthetic-1'
        assert sub.status == models.SubscriptionStatus.ACTIVE
    CP.cancel_subscription.assert_not_called()
    CP.update_subscription.assert_not_called()
