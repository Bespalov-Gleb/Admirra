from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import json
import uuid

import pytest
import sqlalchemy as sa

from automation import durable_sync, work_ledger
from automation.work_tables import jobs, outbox
from automation.sync_request import request_params, public_request
from core import models
from tests.test_durable_work import pg


@pytest.fixture
def scope(pg, monkeypatch):
    factory, engine = pg
    models.Base.metadata.create_all(engine)
    monkeypatch.setattr(durable_sync, "SessionLocal", factory)
    with factory.begin() as db:
        owner = models.User(email="followup@example.test", password_hash="synthetic")
        db.add(owner)
        db.flush()
        client = models.Client(name="Synthetic", owner_id=owner.id, status=models.ClientStatus.ACTIVE)
        db.add(client)
        db.flush()
        integration = models.Integration(client_id=client.id, platform=models.IntegrationPlatform.YANDEX_DIRECT,
            access_token="opaque-not-real", selected_goals='["1"]', connection_status="active")
        db.add(integration)
        db.flush()
        return factory, integration.id, client.id, owner.id


def enqueue(scope, start="2026-09-18", end="2026-09-20", **kwargs):
    return durable_sync.enqueue(scope[1], days=7, force_full=False, trigger="manual",
                                date_from=start, date_to=end, **kwargs)


def transport(factory, job_id):
    with factory() as db:
        return db.execute(sa.select(jobs).where(jobs.c.kind == "sync",
            jobs.c.payload["sync_job_id"].astext == str(job_id))).mappings().one()


def start(scope, job_id):
    factory = scope[0]
    with factory.begin() as db:
        row = transport(factory, job_id)
        claimed = work_ledger.claim(db, row["id"])
        assert claimed
        db.get(models.SyncJob, job_id).status = models.SyncJobStatus.RUNNING
    return claimed


def test_unclaimed_window_is_coalesced_and_duplicate_is_same_id(scope):
    factory = scope[0]
    first = enqueue(scope)
    assert enqueue(scope, "2026-09-01") == first
    assert enqueue(scope, "2026-09-10") == first
    with factory() as db:
        job = db.get(models.SyncJob, first)
        assert json.loads(job.params)["date_from"] == "2026-09-01"
        assert db.scalar(sa.select(sa.func.count()).select_from(outbox)) == 1


def test_running_window_gets_one_coalesced_followup_and_cannot_run_early(scope):
    factory = scope[0]
    first = enqueue(scope)
    claimed = start(scope, first)
    second = enqueue(scope, "2026-09-10")
    assert second != first
    assert enqueue(scope, "2026-09-01", "2026-09-21") == second
    with factory.begin() as db:
        assert work_ledger.claim(db, transport(factory, second)["id"]) is None
        assert json.loads(db.get(models.SyncJob, first).params)["date_from"] == "2026-09-18"
        following = db.get(models.SyncJob, second)
        assert public_request(following) == {"date_from": "2026-09-01", "date_to": "2026-09-21", "after_sync_job_id": str(first)}
        db.get(models.SyncJob, first).status = models.SyncJobStatus.FAILED
        assert work_ledger.finish(db, claimed["id"], claimed["lease_token"], error=RuntimeError())
    with factory.begin() as db:
        assert work_ledger.claim(db, transport(factory, second)["id"])


def test_claimed_but_business_not_running_is_never_mutated(scope):
    factory = scope[0]
    first = enqueue(scope)
    with factory.begin() as db:
        assert work_ledger.claim(db, transport(factory, first)["id"])
    second = enqueue(scope, "2026-09-01")
    assert second != first
    with factory() as db:
        assert json.loads(db.get(models.SyncJob, first).params)["date_from"] == "2026-09-18"


def test_concurrent_broader_requests_share_one_followup(scope):
    factory = scope[0]
    first = enqueue(scope)
    start(scope, first)
    with ThreadPoolExecutor(6) as pool:
        ids = list(pool.map(lambda day: enqueue(scope, f"2026-09-{day:02d}"), range(1, 7)))
    assert len(set(ids)) == 1
    with factory() as db:
        assert db.scalar(sa.select(sa.func.count()).select_from(models.SyncJob)) == 2
        assert db.scalar(sa.select(sa.func.count()).select_from(outbox)) == 2
        assert json.loads(db.get(models.SyncJob, ids[0]).params)["date_from"] == "2026-09-01"


def test_settings_change_cannot_join_running_old_settings(scope):
    factory, integration_id, _, _ = scope
    first = enqueue(scope)
    start(scope, first)
    with factory.begin() as db:
        db.get(models.Integration, integration_id).selected_goals = '["2"]'
    second = enqueue(scope)
    assert second != first
    assert enqueue(scope) == second
    with factory() as db:
        for job in db.query(models.SyncJob):
            assert "opaque-not-real" not in job.params
            assert "settings_digest" not in public_request(job)


def test_night_join_is_durable_even_after_manual_job_finishes(scope):
    factory = scope[0]
    first = enqueue(scope)
    occurrence = "2026-09-21T00:00:00+00:00"
    assert enqueue(scope, occurrence=occurrence) == first
    with factory.begin() as db:
        db.get(models.SyncJob, first).status = models.SyncJobStatus.SUCCESS
    assert enqueue(scope, occurrence=occurrence) == first
    with factory() as db:
        assert db.scalar(sa.select(sa.func.count()).select_from(models.SyncJob)) == 1
        assert db.scalar(sa.select(jobs.c.kind).where(jobs.c.dedupe_key.like("night:%"))) == "sync.alias"


def test_queue_and_outbox_coalescing_are_atomic(scope, monkeypatch):
    factory = scope[0]
    first = enqueue(scope)
    def fail(*_, **__):
        raise RuntimeError("synthetic outbox failure")
    monkeypatch.setattr(durable_sync, "submit", fail)
    with pytest.raises(RuntimeError):
        enqueue(scope, "2026-09-01", occurrence="synthetic")
    with factory() as db:
        assert json.loads(db.get(models.SyncJob, first).params)["date_from"] == "2026-09-18"
        assert db.scalar(sa.select(sa.func.count()).select_from(outbox)) == 1


def test_incremental_window_frozen_at_acceptance_and_explicit_range_never_shrinks(scope):
    factory, integration_id, client_id, _ = scope
    with factory() as db:
        integration, client = db.get(models.Integration, integration_id), db.get(models.Client, client_id)
        integration.last_sync_at = datetime(2026, 9, 20, tzinfo=timezone.utc)
        integration.sync_status = models.IntegrationSyncStatus.SUCCESS
        now = datetime(2026, 9, 20, 23, 59, tzinfo=timezone.utc)
        params = request_params(integration, client, days=30, force_full=False, trigger="auto", now=now)
        assert (params["date_from"], params["date_to"]) == ("2026-09-17", "2026-09-20")
        params = request_params(integration, client, days=30, force_full=False, trigger="manual", now=now,
                                date_from="2026-08-01", date_to="2026-09-20")
        assert params["date_from"] == "2026-08-01"


@pytest.mark.parametrize("start,end", [("bad", "2026-09-20"), ("2026-09-21", "2026-09-20"), (None, "2026-09-20")])
def test_invalid_range_has_no_committed_job(scope, start, end):
    with pytest.raises(ValueError):
        enqueue(scope, start, end)
    with scope[0]() as db:
        assert db.scalar(sa.select(sa.func.count()).select_from(outbox)) == 0


@pytest.mark.parametrize("date_from", ["2026-09-01", "2026-09-18"])
def test_manual_request_promotes_unclaimed_nightly_followup(scope, date_from):
    factory, integration_id, _, _ = scope
    first = durable_sync.enqueue(integration_id, days=7, force_full=False, trigger="auto",
                                date_from="2026-09-18", date_to="2026-09-20")
    assert transport(factory, first)["queue"] == "sync.nightly"
    assert enqueue(scope, date_from) == first
    assert transport(factory, first)["queue"] == "sync.manual"


def test_older_completion_keeps_integration_pending(scope):
    from backend_api.sync_jobs import _keep_pending_followup
    factory = scope[0]
    first = enqueue(scope)
    start(scope, first)
    enqueue(scope, "2026-09-01")
    with factory.begin() as db:
        job = db.get(models.SyncJob, first)
        integration = db.get(models.Integration, scope[1])
        job.status = models.SyncJobStatus.SUCCESS
        integration.sync_status = models.IntegrationSyncStatus.SUCCESS
        _keep_pending_followup(db, job, integration)
        assert integration.sync_status == models.IntegrationSyncStatus.PENDING


def test_execution_rechecks_owner_before_legacy_sync(scope, monkeypatch):
    from backend_api import sync_jobs
    factory, _, client_id, _ = scope
    first = enqueue(scope)
    payload = transport(factory, first)["payload"]
    with factory.begin() as db:
        user = models.User(email="new@example.test", password_hash="synthetic")
        db.add(user)
        db.flush()
        db.get(models.Client, client_id).owner_id = user.id
    monkeypatch.setattr(sync_jobs, "_run_job_sync", lambda *_: pytest.fail("must not call provider handler"))
    with pytest.raises(ValueError, match="no longer authorized"):
        durable_sync.execute(payload)
    with factory() as db:
        assert db.get(models.SyncJob, first).status == models.SyncJobStatus.FAILED
