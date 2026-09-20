from datetime import datetime, timedelta, timezone
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import AsyncMock
import uuid

import pytest
import sqlalchemy as sa

from automation import calendar_work as calendar, durable_sync
from automation.work_tables import jobs, outbox
from backend_api.reports import scheduler
from core import models
from tests.test_durable_work import pg


@pytest.fixture
def scopes(pg, monkeypatch):
    factory, engine = pg
    models.Base.metadata.create_all(engine)
    monkeypatch.setattr(durable_sync, "SessionLocal", factory)
    monkeypatch.setattr(scheduler, "SessionLocal", factory)
    with factory.begin() as db:
        owners = [models.User(email=f"calendar-{i}@example.test", password_hash="synthetic") for i in range(2)]
        db.add_all(owners)
        db.flush()
        owner_ids = [o.id for o in owners]
        project = models.Client(owner_id=owner_ids[0], name="Synthetic", status=models.ClientStatus.ACTIVE)
        db.add(project)
        db.flush()
        project_id = project.id
    return factory, owner_ids, project_id


def populate(scopes, kind, count):
    factory, owners, project = scopes
    now = datetime.now(timezone.utc).replace(second=0, microsecond=0)
    with factory.begin() as db:
        for i in range(1, count + 1):
            if kind == "nightly.enqueue":
                db.add(models.Integration(id=uuid.UUID(int=i), client_id=project,
                    platform=models.IntegrationPlatform.YANDEX_DIRECT, connection_status="active"))
            else:
                db.add(models.ReportSchedule(id=uuid.UUID(int=i), user_id=owners[0], enabled=True,
                    send_time=now.astimezone(calendar.MSK).strftime("%H:%M"), day="daily", approval_required=True))
    return {"scheduled_at": now.isoformat()}


@pytest.mark.parametrize("kind", ["nightly.enqueue", "reports.rules"])
def test_bounded_pages_replay_and_atomic_continuation(scopes, kind):
    factory, owners, _ = scopes
    payload = populate(scopes, kind, 205)
    first = calendar.plan_page(factory, kind, payload)
    assert first == {"planned": 100, "has_next": True}
    assert calendar.plan_page(factory, kind, payload) == first
    for cursor in (100, 200):
        with factory() as db:
            next_payload = db.scalar(sa.select(jobs.c.payload).where(jobs.c.kind == kind,
                jobs.c.payload["cursor"].astext == str(uuid.UUID(int=cursor))))
        assert next_payload
        calendar.plan_page(factory, kind, next_payload)
    with factory() as db:
        children = db.execute(sa.select(jobs).where(jobs.c.kind != kind)).mappings().all()
        assert len(children) == 205
        assert all(child["tenant"] == str(owners[0]) for child in children)
        assert all(child["replay_safe"] == (kind == "nightly.enqueue") for child in children)
        assert db.scalar(sa.select(sa.func.count()).select_from(outbox)) == 207


def test_page_failure_rolls_back_children_and_continuation(scopes, monkeypatch):
    factory, _, _ = scopes
    payload = populate(scopes, "nightly.enqueue", 105)
    original = calendar.submit
    calls = 0
    def fail(*args, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 4:
            raise RuntimeError("synthetic planning crash")
        return original(*args, **kwargs)
    monkeypatch.setattr(calendar, "submit", fail)
    with pytest.raises(RuntimeError):
        calendar.plan_page(factory, "nightly.enqueue", payload)
    with factory() as db:
        assert db.scalar(sa.select(sa.func.count()).select_from(jobs)) == 0
        assert db.scalar(sa.select(sa.func.count()).select_from(outbox)) == 0


def test_parallel_planners_do_not_duplicate_children(scopes):
    factory, _, _ = scopes
    payload = populate(scopes, "nightly.enqueue", 12)
    with ThreadPoolExecutor(4) as pool:
        list(pool.map(lambda _: calendar.plan_page(factory, "nightly.enqueue", payload), range(4)))
    with factory() as db:
        assert db.scalar(sa.select(sa.func.count()).select_from(jobs)) == 12
        assert db.scalar(sa.select(sa.func.count()).select_from(outbox)) == 12


def test_report_scope_and_disabled_rules(scopes):
    factory, owners, _ = scopes
    payload = populate(scopes, "reports.rules", 3)
    with factory.begin() as db:
        db.get(models.ReportSchedule, uuid.UUID(int=2)).enabled = False
        db.get(models.ReportSchedule, uuid.UUID(int=3)).user_id = owners[1]
    result = calendar.plan_page(factory, "reports.rules", {**payload, "owner_id": str(owners[0])})
    assert result["planned"] == 1
    with factory() as db:
        assert db.scalar(sa.select(jobs.c.payload))["rule_id"] == str(uuid.UUID(int=1))


@pytest.mark.parametrize("offset", [-16, 2])
def test_report_expired_or_future_tick_does_not_plan(scopes, offset):
    factory, _, _ = scopes
    populate(scopes, "reports.rules", 1)
    result = calendar.plan_page(factory, "reports.rules", {
        "scheduled_at": (datetime.now(timezone.utc) + timedelta(minutes=offset)).isoformat()})
    assert result == {"planned": 0, "skipped": "expired_occurrence"}


def test_occurrence_requires_timezone():
    with pytest.raises(ValueError):
        calendar.scheduled_time({"scheduled_at": "2026-09-20T10:00:00"})


def test_nightly_child_deduplicates_and_rechecks_ownership(scopes):
    factory, owners, project = scopes
    payload = populate(scopes, "nightly.enqueue", 1)
    payload.update(integration_id=str(uuid.UUID(int=1)), owner_id=str(owners[0]))
    first = calendar.enqueue_nightly(payload)
    assert first == calendar.enqueue_nightly(payload)
    with factory.begin() as db:
        assert db.scalar(sa.select(sa.func.count()).select_from(models.SyncJob)) == 1
        db.get(models.Client, project).owner_id = owners[1]
    assert calendar.enqueue_nightly(payload) is None


@pytest.mark.asyncio
async def test_report_child_only_processes_its_schedule(scopes, monkeypatch):
    factory, owners, _ = scopes
    payload = populate(scopes, "reports.rules", 2)
    payload.update(rule_id=str(uuid.UUID(int=1)), owner_id=str(owners[0]))
    build = AsyncMock()
    send = AsyncMock()
    monkeypatch.setattr(scheduler, "build_delivery_snapshot", build)
    monkeypatch.setattr(scheduler, "send_report_delivery", send)
    await calendar.run_report({**payload, "owner_id": str(owners[1])})
    build.assert_not_awaited()
    await calendar.run_report(payload)
    await calendar.run_report(payload)
    assert build.await_count == 1
    send.assert_not_awaited()  # Approval required remains approval required.
    with factory() as db:
        assert db.scalar(sa.select(sa.func.count()).select_from(models.ReportDelivery)) == 1


@pytest.mark.asyncio
async def test_report_child_failure_is_not_silently_successful(scopes, monkeypatch):
    _, owners, _ = scopes
    payload = populate(scopes, "reports.rules", 1)
    payload.update(rule_id=str(uuid.UUID(int=1)), owner_id=str(owners[0]))
    monkeypatch.setattr(scheduler, "build_delivery_snapshot", AsyncMock(side_effect=RuntimeError("synthetic")))
    with pytest.raises(RuntimeError):
        await calendar.run_report(payload)


@pytest.mark.asyncio
async def test_failed_send_remains_failed_and_is_not_repeated(scopes, monkeypatch):
    factory, owners, _ = scopes
    payload = populate(scopes, "reports.rules", 1)
    payload.update(rule_id=str(uuid.UUID(int=1)), owner_id=str(owners[0]))
    with factory.begin() as db:
        rule = db.get(models.ReportSchedule, uuid.UUID(int=1))
        rule.approval_required = False
        rule.channels = '["email"]'
    monkeypatch.setattr(scheduler, "build_delivery_snapshot", AsyncMock())
    sender = AsyncMock(return_value={"email": False, "errors": {"email": "synthetic timeout"}})
    monkeypatch.setattr(scheduler, "send_report_delivery", sender)
    with pytest.raises(RuntimeError):
        await calendar.run_report(payload)
    await calendar.run_report(payload)
    assert sender.await_count == 1
    with factory() as db:
        assert db.scalar(sa.select(models.ReportDelivery.status)) == "failed"


def test_reconciliation_is_bounded_and_tenant_scoped(scopes):
    factory, owners, _ = scopes
    with factory.begin() as db:
        for i in range(106):
            db.add(models.ReportDelivery(user_id=owners[0] if i < 105 else owners[1], status="sending",
                start_date=datetime.now(timezone.utc).date(), end_date=datetime.now(timezone.utc).date(),
                updated_at=datetime.now(timezone.utc) - timedelta(hours=1)))
    with factory.begin() as db:
        assert scheduler.recover_stale_report_deliveries(db, owner_id=owners[0]) == 100
    with factory() as db:
        assert db.scalar(sa.select(sa.func.count()).select_from(models.ReportDelivery).where(
            models.ReportDelivery.status == "sending")) == 6
