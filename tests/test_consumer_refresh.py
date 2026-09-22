from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
import uuid

import pytest
import sqlalchemy as sa
from fastapi import HTTPException
from automation import consumer_refresh as refresh
from automation.integration_work_scope import require_scope, IntegrationScopeChanged
from automation.work_tables import jobs
from core import models
from core.data_requirements import DataNotReady
from core.job_fence import fenced_job
from tests.test_durable_work import pg, claim
from tests.test_metrika_goal_work import goals, DAY
from tests.test_consumer_freshness import consumer, cover


@pytest.fixture
def refreshable(consumer, monkeypatch):
    monkeypatch.setenv("CONSUMER_REFRESH_ENABLED", "true")
    return consumer


def request(g, consumer="ai", first=DAY, last=DAY, **kwargs):
    with g.factory.begin() as db:
        return refresh.request(db, consumer, g.owner, [g.client], first, last, **kwargs)


def history(g):
    with g.factory() as db:
        return list(db.execute(sa.select(jobs).where(jobs.c.kind == "history.backfill")).mappings())


def test_default_off_does_not_create_work(consumer):
    assert request(consumer) is None
    assert history(consumer) == []


def test_poll_and_different_consumers_share_work(refreshable):
    g = refreshable
    first = request(g)
    assert first["status"] == "waiting"
    assert request(g)["id"] == first["id"]
    second = request(g, "sheets")
    assert second["id"] != first["id"]
    assert len(history(g)) == 1
    row = history(g)[0]
    assert row["queue"] == "sync.backfill" and row["replay_safe"]
    with g.factory() as db:
        assert all(str(row["id"]) in r.state["jobs"] for r in db.scalars(sa.select(models.DataRefreshRequest)))


def test_concurrent_admission_is_deduplicated(refreshable):
    g = refreshable
    with ThreadPoolExecutor(max_workers=2) as pool:
        answers = list(pool.map(lambda _: request(g), range(2)))
    assert len({r["id"] for r in answers}) == 1
    assert len(history(g)) == 1


def test_long_history_owner_cap_and_global_shared_budget(refreshable, monkeypatch):
    g = refreshable
    monkeypatch.setenv("REPORT_REFRESH_GLOBAL_JOBS", "1")
    request(g, first=DAY - timedelta(days=364))
    request(g, "sheets", first=DAY - timedelta(days=364))
    rows = history(g)
    assert len(rows) == 1
    from datetime import date
    p = rows[0]["payload"]
    assert (date.fromisoformat(p["date_to"]) - date.fromisoformat(p["date_from"])).days == 29


def test_deadline_is_persisted_and_no_silent_retry(refreshable):
    g = refreshable
    first = request(g)
    ident = uuid.UUID(first["id"])
    with g.factory.begin() as db:
        row = db.get(models.DataRefreshRequest, ident)
        row.state = {**row.state, "deadline": (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat()}
        assert refresh.public(row)["status"] == "held"  # Even if scheduler is down.
    assert request(g)["reason"] == "deadline_expired"
    assert request(g)["status"] == "held"
    with g.factory.begin() as db:
        row = db.get(models.DataRefreshRequest, ident)
        old_epoch = row.state["epoch"]
        row.next_check_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    assert request(g, retry=True)["status"] == "waiting"
    with g.factory() as db:
        assert db.get(models.DataRefreshRequest, ident).state["epoch"] != old_epoch


def test_expired_request_can_be_retried_without_scheduler_tick(refreshable):
    g = refreshable
    first = request(g)
    with g.factory.begin() as db:
        row = db.get(models.DataRefreshRequest, uuid.UUID(first["id"]))
        row.state = {**row.state, "deadline": (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat()}
        old_epoch = row.state["epoch"]
    result = request(g, retry=True)
    assert result["status"] == "waiting"
    with g.factory() as db:
        assert db.get(models.DataRefreshRequest, uuid.UUID(result["id"])).state["epoch"] != old_epoch


def test_ready_only_after_complete_coverage_and_no_external_retry(refreshable):
    g = refreshable
    first = request(g)
    cover(g)
    assert request(g)["status"] == "ready"
    assert len(history(g)) == 1
    with g.factory() as db:
        assert db.get(models.DataRefreshRequest, uuid.UUID(first["id"])).status == "ready"


@pytest.mark.parametrize("change", ["settings", "access", "deadline", "disabled", "pause", "none"])
def test_worker_revalidates_shared_authorization(refreshable, monkeypatch, change):
    g = refreshable
    first = request(g)
    row = history(g)[0]
    with g.factory.begin() as db:
        db.execute(jobs.update().where(jobs.c.id == g.job).values(state="succeeded"))
    execution = claim(g.factory, row["id"])
    assert execution
    with g.factory.begin() as db:
        if change == "settings":
            db.get(models.Integration, g.id).selected_goals = '["9"]'
        elif change == "access":
            db.get(models.User, g.owner).is_active = False
        elif change == "deadline":
            req = db.get(models.DataRefreshRequest, uuid.UUID(first["id"]))
            req.state = {**req.state, "deadline": (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat()}
        elif change == "pause":
            db.get(models.Client, g.client).status = models.ClientStatus.PAUSED
    if change == "disabled":
        monkeypatch.setenv("CONSUMER_REFRESH_ENABLED", "false")
    with fenced_job(row["id"], execution["lease_token"]), g.factory() as db:
        if change == "none":
            require_scope(db, row["payload"], kind="history.backfill", integration_id=g.id)
        else:
            with pytest.raises(IntegrationScopeChanged):
                require_scope(db, row["payload"], kind="history.backfill", integration_id=g.id)


def test_other_live_consumer_keeps_coalesced_job_authorized(refreshable):
    g = refreshable
    first = request(g)
    request(g, "sheets")
    row = history(g)[0]
    with g.factory.begin() as db:
        db.get(models.DataRefreshRequest, uuid.UUID(first["id"])).status = "held"
        db.execute(jobs.update().where(jobs.c.id == g.job).values(state="succeeded"))
    execution = claim(g.factory, row["id"])
    with fenced_job(row["id"], execution["lease_token"]), g.factory() as db:
        require_scope(db, row["payload"], kind="history.backfill", integration_id=g.id)


def test_failed_job_holds_request_not_fake_ready(refreshable):
    g = refreshable
    request(g)
    with g.factory.begin() as db:
        db.execute(jobs.update().where(jobs.c.kind == "history.backfill").values(state="failed"))
    assert request(g)["reason"] == "refresh_failed"


def test_scheduler_progress_and_scope_change(refreshable):
    g = refreshable
    first = request(g)
    with g.factory.begin() as db:
        db.get(models.Integration, g.id).selected_goals = '["9"]'
        db.get(models.DataRefreshRequest, uuid.UUID(first["id"])).next_check_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    with g.factory.begin() as db:
        refresh.reconcile(db)
    with g.factory() as db:
        assert db.get(models.DataRefreshRequest, uuid.UUID(first["id"])).state["reason"] == "settings_changed"


def test_status_endpoint_cannot_read_other_user_requests(refreshable):
    from backend_api.data_refresh import status
    g = refreshable
    first = request(g)
    with g.factory.begin() as db:
        other = models.User(email="other@example.test", password_hash="synthetic")
        db.add(other)
        db.flush()
        with pytest.raises(HTTPException) as error:
            status(uuid.UUID(first["id"]), other, db)
        assert error.value.status_code == 404
        assert status(uuid.UUID(first["id"]), db.get(models.User, g.owner), db)["status"] == "waiting"


def test_ai_capture_queues_only_missing_history(refreshable):
    from ai.freshness import capture
    g = refreshable
    with g.factory() as db, pytest.raises(DataNotReady) as error:
        capture(db, g.owner, g.client, None, str(DAY), str(DAY), lambda *_: None)
    assert error.value.data_readiness["id"]
    assert g.engine.pool.checkedout() == 0
    assert len(history(g)) == 1


def test_sheets_prepare_queues_history_without_export(refreshable):
    from automation.sheets_freshness import prepare, SheetDataNotReady
    g = refreshable
    with pytest.raises(SheetDataNotReady) as error:
        prepare(g.factory, g.client, g.owner, target=DAY)
    assert error.value.data_readiness["status"] == "waiting"
    assert len(history(g)) <= 2
    assert g.engine.pool.checkedout() == 0


def test_detector_missing_history_queues_without_changing_alerts(refreshable):
    from backend_api.services.detector_freshness import status
    g = refreshable
    with g.factory.begin() as db:
        result = status(db, g.client, DAY, refresh=True)
        assert result["status"] == "waiting_data" and result["refresh"]["status"] == "waiting"
        assert db.scalar(sa.select(sa.func.count()).select_from(models.DetectorAlert)) == 0
    assert 1 <= len(history(g)) <= 2
    with g.factory.begin() as db:
        again = status(db, g.client, DAY)
        assert again["refresh"]["id"] == result["refresh"]["id"]
        row = db.get(models.DataRefreshRequest, uuid.UUID(result["refresh"]["id"]))
        row.status = "held"
    with g.factory() as db:
        assert status(db, g.client, DAY)["refresh"]["status"] == "held"


def test_broken_detector_does_not_block_other_control_work(refreshable, monkeypatch):
    g = refreshable
    first = request(g, "detector")
    cover(g)
    def fail(*args):
        raise RuntimeError("synthetic calculation failure")
    monkeypatch.setattr("backend_api.services.detector_iteration3.run_detector_iteration3", fail)
    with g.factory.begin() as db:
        db.get(models.DataRefreshRequest, uuid.UUID(first["id"])).next_check_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    with g.factory.begin() as db:
        refresh.reconcile(db)
        assert db.scalar(sa.select(sa.literal(1))) == 1
    with g.factory() as db:
        row = db.get(models.DataRefreshRequest, uuid.UUID(first["id"]))
        assert row.status == "held" and row.state["reason"] == "preparation_failed"


def test_request_limits_and_non_owner_are_fail_closed(refreshable):
    g = refreshable
    with g.factory.begin() as db, pytest.raises(DataNotReady):
        refresh.request(db, "ai", uuid.uuid4(), [g.client], DAY, DAY)
    for i in range(8):
        assert request(g, first=DAY - timedelta(days=i))["status"] == "waiting"
    assert request(g, first=DAY - timedelta(days=9))["reason"] == "capacity"
    assert len(history(g)) <= 2


def test_refresh_migration_round_trip(refreshable):
    import importlib.util
    from pathlib import Path
    from alembic.migration import MigrationContext
    from alembic.operations import Operations
    g = refreshable
    path = Path("alembic/versions/f24d5e6f7081_consumer_refresh_requests.py")
    spec = importlib.util.spec_from_file_location("refresh_migration", path)
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    with g.engine.begin() as connection:
        with Operations.context(MigrationContext.configure(connection)):
            migration.downgrade()
            migration.upgrade()
    assert request(g)["status"] == "waiting"
