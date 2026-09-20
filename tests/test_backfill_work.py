from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
import importlib.util
from pathlib import Path
from unittest.mock import AsyncMock, Mock
import uuid

from alembic.migration import MigrationContext
from alembic.operations import Operations
import pytest
import sqlalchemy as sa

from automation import backfill_work as history, work_ledger as work, sync
from automation.work_tables import jobs
from tests.test_durable_work import pg
from tests.test_sync import direct


@pytest.fixture
def backfills(pg, monkeypatch):
    factory, engine = pg
    monkeypatch.setenv("DYNAMICS_BACKFILL_THROTTLE_SEC", "0")
    with engine.begin() as db:
        db.execute(sa.text("CREATE TABLE clients (id UUID PRIMARY KEY)"))
        spec = importlib.util.spec_from_file_location("history_migration", Path(__file__).resolve().parents[1] /
            "alembic/versions/ff6a7b8c9d0e_durable_history_backfill.py")
        migration = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(migration)
        with Operations.context(MigrationContext.configure(db)):
            migration.upgrade()
    return factory, engine, migration


def project(backfills):
    factory, _, _ = backfills
    client_id = uuid.uuid4()
    with factory.begin() as db:
        db.execute(sa.text("INSERT INTO clients VALUES (:id)"), {"id": client_id})
    return client_id


def submit(backfills, client, integrations=None):
    factory, _, _ = backfills
    with factory.begin() as db:
        db.execute(sa.text("SELECT id FROM clients WHERE id = :id FOR UPDATE"), {"id": client})
        return history.submit_project(db, client, integrations or [uuid.uuid4()],
            [(date(2026, 1, 1), date(2026, 3, 31)), (date(2026, 4, 1), date(2026, 6, 30))], 6, 3600,
            tenant_id=client)


def test_concurrent_api_requests_create_only_one_run(backfills):
    factory, _, _ = backfills
    client = project(backfills)
    with ThreadPoolExecutor(6) as pool:
        results = list(pool.map(lambda _: submit(backfills, client), range(6)))
    assert results.count("started") == 1
    assert results.count("already_running") == 5
    with factory() as db:
        assert db.scalar(sa.select(sa.func.count()).select_from(jobs)) == 2


def test_failure_is_partial_and_persistent_after_restart(backfills):
    factory, _, _ = backfills
    client = project(backfills)
    submit(backfills, client)
    with factory.begin() as db:
        ids = db.execute(sa.select(jobs.c.id).order_by(jobs.c.payload["date_from"].astext)).scalars().all()
        assert work.claim(db, ids[1]) is None  # newer window cannot jump queue
        first = work.claim(db, ids[0])
    with factory.begin() as db:
        work.finish(db, ids[0], first["lease_token"])
    with factory.begin() as db:
        second = work.claim(db, ids[1])
    with factory.begin() as db:
        work.finish(db, ids[1], second["lease_token"], error=ValueError("failed"))
        history.reconcile(db)
    # A new Session/process sees the same result, not an empty in-memory dict.
    with factory() as db:
        row = db.execute(sa.select(history.runs)).mappings().one()
        assert row["status"] == "partial"
        assert row["steps_done"] == row["steps_failed"] == 1
        assert row["finished_at"] is not None
    assert submit(backfills, client) == "cooldown"


def test_durable_outbox_and_run_rollback_together(backfills):
    factory, _, _ = backfills
    client = project(backfills)
    with factory() as db:
        history.submit_project(db, client, [uuid.uuid4()], [(date(2026, 1, 1), date(2026, 1, 31))], 1, 3600,
                               tenant_id=client)
        db.rollback()
    with factory() as db:
        assert db.scalar(sa.select(sa.func.count()).select_from(history.runs)) == 0
        assert db.scalar(sa.select(sa.func.count()).select_from(jobs)) == 0


def test_history_uses_account_quota_not_project_id(backfills):
    factory, _, _ = backfills
    client, owner = project(backfills), uuid.uuid4()
    with factory.begin() as db:
        history.submit_project(db, client, [uuid.uuid4()],
            [(date(2026, 1, 1), date(2026, 1, 31))], 1, 3600, tenant_id=owner)
        assert db.scalar(sa.select(jobs.c.tenant)) == str(owner)


def test_manual_queue_has_priority_and_backfill_global_cap(backfills):
    factory, _, _ = backfills
    a, b = project(backfills), project(backfills)
    submit(backfills, a)
    submit(backfills, b)
    with factory.begin() as db:
        manual = work.submit(db, kind="goals", queue="sync.manual", key="manual", resource="manual-int",
            tenant="owner", payload={}, replay_safe=True)
        historic = db.execute(sa.select(jobs.c.id).where(jobs.c.kind == "history.backfill")
            .order_by(jobs.c.payload["date_from"].astext)).scalars().all()
        assert work.claim(db, historic[0]) is None
    published = []
    work.publish_pending(factory, lambda id, queue: published.append((id, queue)), batch_size=1)
    assert published == [(str(manual), "sync.manual")]
    with factory.begin() as db:
        running = work.claim(db, manual)
        h = work.claim(db, historic[0])
        assert h is not None  # leaves capacity for current work
        assert work.claim(db, historic[1]) is None  # only one history chunk globally


def test_history_preserves_integration_resource_lock(backfills):
    factory, _, _ = backfills
    client, integration_id = project(backfills), uuid.uuid4()
    submit(backfills, client, [integration_id])
    with factory.begin() as db:
        manual = work.submit(db, kind="goals", queue="sync.manual", key="manual", resource=f"integration:{integration_id}",
            tenant=client, payload={}, replay_safe=True)
        work.claim(db, manual)
        for id in db.execute(sa.select(jobs.c.id).where(jobs.c.kind == "history.backfill")).scalars():
            assert work.claim(db, id) is None


def test_retention_preserves_active_group_progress_and_safe_downgrade(backfills):
    factory, _, migration = backfills
    client = project(backfills)
    submit(backfills, client)
    with factory.begin() as db:
        ids = db.execute(sa.select(jobs.c.id)).scalars().all()
        db.execute(jobs.update().where(jobs.c.id == ids[0]).values(state="succeeded",
            finished_at=sa.func.now() - sa.text("interval '31 days'")))
        work.prune_completed(db)
        history.reconcile(db)
        assert db.scalar(sa.select(sa.func.count()).select_from(jobs)) == 2
        with Operations.context(MigrationContext.configure(db.connection())):
            with pytest.raises(RuntimeError): migration.downgrade()
        db.execute(jobs.update().where(jobs.c.id == ids[1]).values(state="succeeded", finished_at=sa.func.now()))
        history.reconcile(db)
        row = db.execute(sa.select(history.runs)).mappings().one()
        assert row["status"] == "done" and row["steps_done"] == 2
        assert db.scalar(sa.select(sa.func.count()).select_from(jobs)) == 1
        with Operations.context(MigrationContext.configure(db.connection())):
            migration.downgrade()


@pytest.mark.asyncio
@pytest.mark.parametrize("empty", [True, False])
async def test_history_does_not_overwrite_current_sync_status_or_run_detector(direct, monkeypatch, empty):
    db, integration, api, _ = direct
    integration.sync_status, integration.last_sync_at = "original", "original-date"
    if not empty:
        api.get_report.side_effect = [[{"campaign_id": "1", "campaign_name": "fixture"}], [], []]
        monkeypatch.setattr("backend_api.services.project_settings.update_actual_start_date", lambda *_: None)
    detector = Mock(side_effect=AssertionError("historical chunk must not run detector"))
    monkeypatch.setattr(sync, "_run_detector_after_sync", detector)
    await sync.sync_integration(db, integration, "2026-01-01", "2026-03-31", historical=True)
    assert integration.sync_status == "original"
    assert integration.last_sync_at == "original-date"
    detector.assert_not_called()


@pytest.mark.asyncio
async def test_history_fails_if_campaign_catalog_is_unavailable(direct):
    db, integration, api, _ = direct
    api.get_campaigns.side_effect = ValueError("catalog failed")
    with pytest.raises(ValueError, match="catalog failed"):
        await sync.sync_integration(db, integration, "2026-01-01", "2026-03-31", historical=True)


@pytest.mark.asyncio
async def test_history_does_not_hide_selected_goal_failure(direct, monkeypatch):
    db, integration, _, _ = direct
    integration.sync_status = "original"
    integration.selected_goals, integration.selected_counters = '["1"]', '["2"]'
    monkeypatch.setattr(sync, "_sync_metrika_goals_for_direct", AsyncMock(side_effect=ValueError("goals failed")))
    with pytest.raises(ValueError, match="goals failed"):
        await sync.sync_integration(db, integration, "2026-01-01", "2026-03-31", historical=True)
    assert integration.sync_status == "original"
