from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock
import uuid

import pytest
import sqlalchemy as sa

from automation import billing_work as work
from automation.work_tables import jobs, outbox
from backend_api.services import billing_notifications as notifications
from core import models
from tests.test_durable_work import pg


@pytest.fixture
def billing_scope(pg, monkeypatch):
    factory, engine = pg
    models.Base.metadata.create_all(engine)
    monkeypatch.setattr(notifications, "SessionLocal", factory)
    with factory.begin() as db:
        owners = [models.User(email=f"billing-{i}@example.test", password_hash="synthetic") for i in range(2)]
        db.add_all(owners)
        db.flush()
        ids = [owner.id for owner in owners]
    return factory, ids


def populate(scope, count=1):
    factory, owners = scope
    now = datetime.now(timezone.utc).replace(second=0, microsecond=0)
    end = now + timedelta(days=7)
    with factory.begin() as db:
        for i in range(1, count + 1):
            db.add(models.Subscription(id=uuid.UUID(int=i), user_id=owners[0], plan_code="start",
                status=models.SubscriptionStatus.ACTIVE, current_period_end=end, recurring_sync_required=True,
                cloudpayments_subscription_id=f"synthetic-{i}"))
    return {"scheduled_at": now.isoformat()}, end


def child(scope, kind):
    with scope[0]() as db:
        return db.scalar(sa.select(jobs.c.payload).where(jobs.c.kind == kind))


def test_billing_plans_bounded_separate_children_and_replays_once(billing_scope):
    factory, owners = billing_scope
    payload, _ = populate(billing_scope, 205)
    result = work.plan_page(factory, payload)
    assert result == {"planned": 200, "scanned": 100, "has_next": True}
    assert work.plan_page(factory, payload) == result
    for cursor in (100, 200):
        with factory() as db:
            continuation = db.scalar(sa.select(jobs.c.payload).where(jobs.c.kind == "billing.maintenance",
                jobs.c.payload["cursor"].astext == str(uuid.UUID(int=cursor))))
        assert continuation
        work.plan_page(factory, continuation)
    with factory() as db:
        rows = db.execute(sa.select(jobs).where(jobs.c.kind != "billing.maintenance")).mappings().all()
        assert len(rows) == 410
        assert all(row["tenant"] == str(owners[0]) and not row["replay_safe"] for row in rows)
        assert len({row["resource"] for row in rows}) == 410
        assert db.scalar(sa.select(sa.func.count()).select_from(outbox)) == 412
        assert all("synthetic-" not in str(row["payload"]) for row in rows)  # No provider IDs/emails in payload.


def test_billing_page_rolls_back_whole_batch(billing_scope, monkeypatch):
    factory, _ = billing_scope
    payload, _ = populate(billing_scope, 105)
    original = work.submit
    calls = 0
    def fail(*args, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 3:
            raise RuntimeError("synthetic rollback")
        return original(*args, **kwargs)
    monkeypatch.setattr(work, "submit", fail)
    with pytest.raises(RuntimeError):
        work.plan_page(factory, payload)
    with factory() as db:
        assert db.scalar(sa.select(sa.func.count()).select_from(jobs)) == 0


@pytest.mark.parametrize("hours", [-25, 1])
def test_expired_or_future_billing_does_not_plan(billing_scope, hours):
    populate(billing_scope)
    payload = {"scheduled_at": (datetime.now(timezone.utc) + timedelta(hours=hours)).isoformat()}
    assert work.plan_page(billing_scope[0], payload) == {"planned": 0, "skipped": "expired_occurrence"}


def test_billing_filters_scope_and_cancelled_recurring(billing_scope):
    factory, owners = billing_scope
    payload, _ = populate(billing_scope, 3)
    with factory.begin() as db:
        db.get(models.Subscription, uuid.UUID(int=2)).user_id = owners[1]
        sub = db.get(models.Subscription, uuid.UUID(int=3))
        sub.cancel_at_period_end = True
        sub.current_period_end = None
    result = work.plan_page(factory, {**payload, "owner_id": str(owners[0])})
    assert result["planned"] == 2
    with factory() as db:
        assert set(db.scalars(sa.select(jobs.c.payload["subscription_id"].astext))) == {str(uuid.UUID(int=1))}


def mock_warning(monkeypatch):
    monkeypatch.setattr(notifications.SubscriptionService, "get_user_plan", lambda *_: SimpleNamespace(name="Start"))
    monkeypatch.setattr(notifications.SubscriptionService, "compute_overflow_state",
                        lambda *_: {"over_limit": True, "current": 4, "effective_projects_limit": 3})
    sender = Mock(return_value=True)
    monkeypatch.setattr(notifications, "_send_sync", sender)
    return sender


@pytest.mark.asyncio
async def test_warning_rechecks_owner_period_and_does_not_repeat_confirmed_send(billing_scope, monkeypatch):
    factory, owners = billing_scope
    payload, end = populate(billing_scope)
    work.plan_page(factory, payload)
    warning = child(billing_scope, "billing.warning")
    sender = mock_warning(monkeypatch)
    assert await work.execute("billing.warning", {**warning, "owner_id": str(owners[1])}) == {"completed": 0}
    assert await work.execute("billing.warning", {**warning, "period_end": (end + timedelta(days=1)).isoformat()}) == {"completed": 0}
    sender.assert_not_called()
    assert await work.execute("billing.warning", warning) == {"completed": 1}
    assert await work.execute("billing.warning", warning) == {"completed": 0}
    sender.assert_called_once()
    assert sender.call_args.args[0] == "billing-0@example.test"


@pytest.mark.asyncio
@pytest.mark.parametrize("failure", [False, TimeoutError("synthetic unknown acceptance")])
async def test_warning_false_or_exception_is_not_success(billing_scope, monkeypatch, failure):
    payload, _ = populate(billing_scope)
    work.plan_page(billing_scope[0], payload)
    sender = mock_warning(monkeypatch)
    if isinstance(failure, Exception):
        sender.side_effect = failure
    else:
        sender.return_value = False
    with pytest.raises(notifications.BillingMaintenanceUncertain):
        await work.execute("billing.warning", child(billing_scope, "billing.warning"))
    with billing_scope[0]() as db:
        assert db.get(models.Subscription, uuid.UUID(int=1)).overflow_warning_period_end is None


@pytest.mark.asyncio
async def test_recurring_rechecks_scope_cancel_and_retains_pending_on_unknown(billing_scope, monkeypatch):
    from backend_api import billing
    factory, owners = billing_scope
    payload, _ = populate(billing_scope)
    work.plan_page(factory, payload)
    request = child(billing_scope, "billing.recurring")
    update = AsyncMock(return_value=False)
    monkeypatch.setattr(billing, "_update_recurrent_total", update)
    assert await work.execute("billing.recurring", {**request, "owner_id": str(owners[1])}) == {"completed": 0}
    update.assert_not_awaited()
    with pytest.raises(notifications.BillingMaintenanceUncertain):
        await work.execute("billing.recurring", request)
    update.assert_awaited_once()
    with factory.begin() as db:
        sub = db.get(models.Subscription, uuid.UUID(int=1))
        assert sub.recurring_sync_required is True
        sub.cancel_at_period_end = True
    assert await work.execute("billing.recurring", request) == {"completed": 0}
    update.assert_awaited_once()  # Never reactivates the cancelled subscription.


@pytest.mark.asyncio
async def test_expired_child_does_not_call_legacy_handler(monkeypatch):
    sender = AsyncMock()
    monkeypatch.setattr(notifications, "send_overflow_renewal_warnings", sender)
    result = await work.execute("billing.warning", {"scheduled_at": (datetime.now(timezone.utc) - timedelta(days=2)).isoformat()})
    assert result == {"skipped": "expired_occurrence"}
    sender.assert_not_awaited()


def test_subscription_and_owner_are_required_together():
    with pytest.raises(ValueError):
        notifications._scoped(Mock(), uuid.uuid4(), None)


@pytest.mark.asyncio
@pytest.mark.parametrize("change_period", [False, True])
async def test_warning_smtp_has_no_sql_connection_and_cannot_mark_new_period(billing_scope, monkeypatch, change_period):
    factory, _ = billing_scope
    payload, end = populate(billing_scope)
    work.plan_page(factory, payload)
    sender = mock_warning(monkeypatch)
    engine = factory.kw["bind"]
    def send(*_):
        assert engine.pool.checkedout() == 0
        if change_period:
            with factory.begin() as db:
                db.get(models.Subscription, uuid.UUID(int=1)).current_period_end = end + timedelta(days=30)
        return True
    sender.side_effect = send
    request = child(billing_scope, "billing.warning")
    if change_period:
        with pytest.raises(notifications.BillingMaintenanceUncertain):
            await work.execute("billing.warning", request)
    else:
        assert await work.execute("billing.warning", request) == {"completed": 1}
    with factory() as db:
        sub = db.get(models.Subscription, uuid.UUID(int=1))
        assert sub.overflow_warning_period_end == (None if change_period else end)


@pytest.mark.asyncio
async def test_warning_confirmation_rejects_expired_execution_lease(billing_scope, monkeypatch):
    from automation import work_ledger
    from core.job_fence import fenced_job, LeaseLost
    factory, _ = billing_scope
    payload, _ = populate(billing_scope)
    work.plan_page(factory, payload)
    with factory.begin() as db:
        job_id = db.scalar(sa.select(jobs.c.id).where(jobs.c.kind == "billing.warning"))
        execution = work_ledger.claim(db, job_id)
    sender = mock_warning(monkeypatch)
    def send(*_):
        # Simulate a lost lease while the external system accepts the message.
        with factory.kw["bind"].begin() as conn:
            conn.execute(jobs.update().where(jobs.c.id == job_id).values(
                lease_until=sa.func.clock_timestamp() - sa.text("interval '1 second'")))
        return True
    sender.side_effect = send
    request = child(billing_scope, "billing.warning")
    with fenced_job(job_id, execution["lease_token"]):
        with pytest.raises(LeaseLost):
            await work.execute("billing.warning", request)
    with factory.begin() as db:
        assert db.get(models.Subscription, uuid.UUID(int=1)).overflow_warning_period_end is None
        assert work_ledger.recover_expired(db) == 1
        assert db.scalar(sa.select(jobs.c.state).where(jobs.c.id == job_id)) == "uncertain"


@pytest.mark.asyncio
async def test_recurring_provider_has_no_checked_out_sql_and_preserves_pricing(billing_scope, monkeypatch):
    from backend_api import billing
    factory, owners = billing_scope
    populate(billing_scope)
    with factory.begin() as db:
        sub = db.get(models.Subscription, uuid.UUID(int=1))
        sub.pending_plan_code = "pro"
        sub.pending_billing_period = "year"
        sub.pending_purchased_project_slots = 2
        plan, period, slots = notifications._recurring_terms(sub)
        amount = billing._subscription_total(plan, period, slots)
    async def send(provider_id, **changes):
        assert factory.kw["bind"].pool.checkedout() == 0
        assert provider_id == "synthetic-1"
        assert changes["Amount"] == amount
        assert changes["Period"] == 12 and changes["Interval"] == "Month"
        assert changes["CustomerReceipt"]["amounts"]["electronic"] == amount
        return {"Success": True}
    sender = AsyncMock(side_effect=send)
    monkeypatch.setattr(billing.CloudPaymentsService, "update_subscription", sender)
    assert await notifications.reconcile_recurring_totals(subscription_id=uuid.UUID(int=1), owner_id=owners[0]) == 1
    assert await notifications.reconcile_recurring_totals(subscription_id=uuid.UUID(int=1), owner_id=owners[0]) == 0
    sender.assert_awaited_once()
    with factory() as db:
        sub = db.get(models.Subscription, uuid.UUID(int=1))
        assert sub.recurring_sync_required is False
        assert sub.pending_plan_code == "pro"  # Confirmation does not apply the future plan early.
        assert sub.pending_purchased_project_slots == 2


@pytest.mark.asyncio
@pytest.mark.parametrize("changed", ["cancel", "provider", "plan", "slots", "period", "snapshot", "owner", "email", "delete"])
async def test_recurring_does_not_confirm_over_concurrent_changes(billing_scope, monkeypatch, changed):
    from backend_api import billing
    factory, owners = billing_scope
    payload, end = populate(billing_scope)
    work.plan_page(factory, payload)
    request = child(billing_scope, "billing.recurring")
    async def send(*_):
        assert factory.kw["bind"].pool.checkedout() == 0
        with factory.begin() as db:
            sub = db.get(models.Subscription, uuid.UUID(int=1))
            if changed == "cancel":
                sub.cancel_at_period_end = True
                sub.cloudpayments_subscription_id = None
            elif changed == "provider":
                sub.cloudpayments_subscription_id = "replacement"
            elif changed == "plan":
                sub.pending_plan_code = "pro"
            elif changed == "slots":
                sub.pending_purchased_project_slots = 5
            elif changed == "period":
                sub.current_period_end = end + timedelta(days=30)
            elif changed == "snapshot":
                sub.pending_price_book_snapshot = {"synthetic": "changed during IO"}
            elif changed == "owner":
                sub.user_id = owners[1]
            elif changed == "email":
                db.get(models.User, owners[0]).email = "new@example.test"
            else:
                db.delete(sub)
        return True
    monkeypatch.setattr(billing, "_update_recurrent_total", AsyncMock(side_effect=send))
    with pytest.raises(notifications.BillingMaintenanceUncertain, match="changed during"):
        await work.execute("billing.recurring", request)
    with factory() as db:
        sub = db.get(models.Subscription, uuid.UUID(int=1))
        if changed == "delete":
            assert sub is None
        else:
            assert sub.recurring_sync_required is True
            if changed == "cancel":
                assert sub.cancel_at_period_end is True and sub.cloudpayments_subscription_id is None


@pytest.mark.asyncio
async def test_recurring_change_during_preparation_skips_provider(billing_scope, monkeypatch):
    from backend_api import billing
    factory, owners = billing_scope
    populate(billing_scope)
    original = notifications._recurring_terms
    def prepare(sub):
        result = original(sub)
        with factory.begin() as db:
            db.get(models.Subscription, sub.id).cancel_at_period_end = True
        return result
    monkeypatch.setattr(notifications, "_recurring_terms", prepare)
    sender = AsyncMock()
    monkeypatch.setattr(billing, "_update_recurrent_total", sender)
    assert await notifications.reconcile_recurring_totals(subscription_id=uuid.UUID(int=1), owner_id=owners[0]) == 0
    sender.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("after_io", [False, True])
async def test_recurring_lease_loss_rejects_send_or_confirmation(billing_scope, monkeypatch, after_io):
    from backend_api import billing
    from automation import work_ledger
    from core.job_fence import fenced_job, LeaseLost
    factory, _ = billing_scope
    payload, _ = populate(billing_scope)
    work.plan_page(factory, payload)
    with factory.begin() as db:
        job_id = db.scalar(sa.select(jobs.c.id).where(jobs.c.kind == "billing.recurring"))
        execution = work_ledger.claim(db, job_id)
    def expire():
        with factory.kw["bind"].begin() as conn:
            conn.execute(jobs.update().where(jobs.c.id == job_id).values(
                lease_until=sa.func.clock_timestamp() - sa.text("interval '1 second'")))
    async def send(*_):
        assert factory.kw["bind"].pool.checkedout() == 0
        expire()
        return True
    sender = AsyncMock(side_effect=send)
    monkeypatch.setattr(billing, "_update_recurrent_total", sender)
    if not after_io:
        expire()
    request = child(billing_scope, "billing.recurring")
    with fenced_job(job_id, execution["lease_token"]):
        with pytest.raises(LeaseLost):
            await work.execute("billing.recurring", request)
    assert sender.await_count == int(after_io)
    with factory.begin() as db:
        assert db.get(models.Subscription, uuid.UUID(int=1)).recurring_sync_required is True
        assert work_ledger.recover_expired(db) == 1
        assert db.scalar(sa.select(jobs.c.state).where(jobs.c.id == job_id)) == "uncertain"


@pytest.mark.asyncio
async def test_recurring_exception_after_provider_acceptance_is_uncertain(billing_scope, monkeypatch):
    from backend_api import billing
    factory, owners = billing_scope
    populate(billing_scope)
    monkeypatch.setattr(billing, "_update_recurrent_total", AsyncMock(side_effect=TimeoutError("synthetic")))
    with pytest.raises(notifications.BillingMaintenanceUncertain):
        await notifications.reconcile_recurring_totals(subscription_id=uuid.UUID(int=1), owner_id=owners[0])
    with factory() as db:
        assert db.get(models.Subscription, uuid.UUID(int=1)).recurring_sync_required is True


def test_recurring_changed_after_io_blocks_redelivery_and_next_occurrence(billing_scope, monkeypatch):
    from backend_api import billing
    from automation import work_executor
    factory, _ = billing_scope
    payload, _ = populate(billing_scope)
    work.plan_page(factory, payload)
    monkeypatch.setattr(work_executor, "engine", factory.kw["bind"])
    async def send(*_):
        with factory.begin() as db:
            db.get(models.Subscription, uuid.UUID(int=1)).pending_purchased_project_slots = 3
        return True
    sender = AsyncMock(side_effect=send)
    monkeypatch.setattr(billing, "_update_recurrent_total", sender)
    with factory() as db:
        job_id = db.scalar(sa.select(jobs.c.id).where(jobs.c.kind == "billing.recurring"))
    assert work_executor.execute_job(job_id) == "finished"
    with factory() as db:
        assert db.scalar(sa.select(jobs.c.state).where(jobs.c.id == job_id)) == "uncertain"
    assert work_executor.execute_job(job_id) == "not_claimed"
    stamp = datetime.fromisoformat(payload["scheduled_at"]) + timedelta(seconds=30)
    work.plan_page(factory, {"scheduled_at": stamp.isoformat()})
    with factory() as db:
        next_id = db.scalar(sa.select(jobs.c.id).where(jobs.c.kind == "billing.recurring", jobs.c.id != job_id))
    assert next_id is not None
    assert work_executor.execute_job(next_id) == "not_claimed"
    sender.assert_awaited_once()
