from datetime import datetime
import json
import uuid
from unittest.mock import AsyncMock

import pytest
import sqlalchemy as sa

from automation import durable_sync, metrika_sync_work as work
from automation.integration_work_scope import IntegrationScopeChanged
from automation.metrika_goal_work import GoalSettingsChanged
from automation.sync_request import request_params
from automation.work_tables import jobs
from core import models
from core.job_fence import fenced_job, LeaseLost
from tests.test_durable_work import pg
from tests.test_metrika_goal_work import goals, counts, DAY


@pytest.fixture
def current_sync(goals, monkeypatch):
    g = goals
    monkeypatch.setattr(durable_sync, "SessionLocal", g.factory)
    with g.factory.begin() as db:
        integration = db.get(models.Integration, g.id)
        integration.platform = models.IntegrationPlatform.YANDEX_METRIKA
        integration.account_id = "123"
        integration.last_sync_at = datetime(2026, 9, 9)
        params = request_params(integration, integration.client, days=7, force_full=False,
            trigger="manual", date_from=str(DAY), date_to=str(DAY))
        job = models.SyncJob(integration_id=g.id, status=models.SyncJobStatus.QUEUED,
                             params=json.dumps(params))
        db.add(job)
        db.flush()
        g.business = job.id
        g.payload = dict(sync_job_id=str(job.id), client_id=str(g.client),
                         owner_id=str(integration.client.owner_id), after_sync_job_id=None)
        db.execute(jobs.update().where(jobs.c.id == g.job).values(kind="sync", payload=g.payload))
        integration.sync_status = models.IntegrationSyncStatus.PENDING
    g.invalidated, g.detected, g.enriched = [], [], []
    def invalidate(client_id):
        assert g.engine.pool.checkedout() == 0
        assert counts(g) == {"1": 4, "all": 4}
        g.invalidated.append(client_id)
    def detect(db, client_id):
        g.detected.append(client_id)
    async def enrich(factory, client_id, **kwargs):
        assert g.engine.pool.checkedout() == 0
        assert state(g)[0] == models.SyncJobStatus.SUCCESS
        g.enriched.append((client_id, kwargs))
    monkeypatch.setattr("backend_api.cache_service.CacheService.invalidate_client", invalidate)
    monkeypatch.setattr("backend_api.services.detector.run_detector_for_client", detect)
    monkeypatch.setattr("automation.detector_hypothesis_work.execute", enrich)
    return g


async def run(g):
    with fenced_job(g.job, g.token):
        return await work.execute(g.factory, g.payload)


def state(g):
    with g.factory() as db:
        job, integration = db.get(models.SyncJob, g.business), db.get(models.Integration, g.id)
        return job.status, integration.sync_status, integration.last_sync_at, job.error


@pytest.mark.asyncio
@pytest.mark.parametrize("trigger", ["manual", "auto"])
async def test_data_status_and_watermark_committed_together_without_sql_during_io(current_sync, trigger):
    g = current_sync
    with g.factory.begin() as db:
        job = db.get(models.SyncJob, g.business)
        job.params = json.dumps({**json.loads(job.params), "trigger": trigger})
    assert await run(g) == "updated"
    assert counts(g) == {"1": 4, "all": 4}
    assert state(g)[:2] == (models.SyncJobStatus.SUCCESS, models.IntegrationSyncStatus.SUCCESS)
    assert state(g)[2] > datetime(2026, 9, 9)
    with g.factory() as db:
        assert db.get(models.Integration, g.id).last_sync_trigger == trigger
        job = db.get(models.SyncJob, g.business)
        assert (job.progress, job.stage, job.attempt) == (100, "done", 1)
    assert g.detected == [g.client]
    assert g.enriched == [(g.client, {"expected_owner_id": uuid.UUID(g.payload["owner_id"])})]
    assert await run(g) == "already-complete"
    assert len(g.calls) == len(g.invalidated) == 1


def test_real_durable_dispatch_uses_detached_path(current_sync, monkeypatch):
    g = current_sync
    legacy = AsyncMock(side_effect=AssertionError("legacy sync must not run"))
    monkeypatch.setattr("backend_api.sync_jobs.sync_integration", legacy)
    with fenced_job(g.job, g.token):
        assert durable_sync.execute(g.payload) == "updated"
    legacy.assert_not_called()


@pytest.mark.asyncio
async def test_provider_failure_retries_without_sql_and_keeps_old_values(current_sync, monkeypatch):
    g = current_sync
    calls, waits = [], []
    async def failed(*args, **kwargs):
        assert g.engine.pool.checkedout() == 0
        calls.append(True)
        raise RuntimeError("503 sensitive-provider-payload")
    async def pause(seconds):
        assert g.engine.pool.checkedout() == 0
        waits.append(seconds)
    g.api.get_goals_stats = failed
    monkeypatch.setattr(work.asyncio, "sleep", pause)
    with pytest.raises(RuntimeError):
        await run(g)
    assert len(calls) == 3 and waits == [2, 4]
    assert counts(g) == {"1": 34}
    assert state(g)[:3] == (models.SyncJobStatus.FAILED, models.IntegrationSyncStatus.FAILED, datetime(2026, 9, 9))
    assert "sensitive" not in state(g)[3]
    assert not g.invalidated and not g.detected and not g.enriched


@pytest.mark.asyncio
@pytest.mark.parametrize("change", ["owner", "token", "pause", "counter", "params", "lease"])
async def test_inflight_changes_do_not_publish_data_or_success(current_sync, change):
    g = current_sync
    original = g.api.get_goals_stats
    async def changing(*args, **kwargs):
        if change == "lease":
            with g.engine.begin() as db:
                db.execute(jobs.update().where(jobs.c.id == g.job).values(
                    lease_until=sa.func.clock_timestamp() - sa.text("interval '1 second'")))
        else:
            with g.factory.begin() as db:
                integration = db.get(models.Integration, g.id)
                if change == "owner":
                    owner = models.User(email="sync-moved@example.test", password_hash="synthetic")
                    db.add(owner)
                    db.flush()
                    integration.client.owner_id = owner.id
                elif change == "pause":
                    integration.client.status = models.ClientStatus.PAUSED
                elif change == "params":
                    job = db.get(models.SyncJob, g.business)
                    job.params = json.dumps({**json.loads(job.params), "date_from": "2026-09-01"})
                else:
                    setattr(integration, "access_token" if change == "token" else "account_id", "changed")
        return await original(*args, **kwargs)
    g.api.get_goals_stats = changing
    with pytest.raises((LeaseLost, GoalSettingsChanged, IntegrationScopeChanged)):
        await run(g)
    assert counts(g) == {"1": 34} and state(g)[2] == datetime(2026, 9, 9)
    assert state(g)[0] != models.SyncJobStatus.SUCCESS
    assert not g.invalidated and not g.detected and not g.enriched


@pytest.mark.asyncio
async def test_detector_failure_is_isolated_from_successful_data(current_sync, monkeypatch):
    g = current_sync
    def failed(db, client_id):
        db.get(models.Client, client_id).name = "must rollback"
        db.flush()
        raise RuntimeError("synthetic detector failure")
    monkeypatch.setattr("backend_api.services.detector.run_detector_for_client", failed)
    await run(g)
    assert state(g)[0] == models.SyncJobStatus.SUCCESS and counts(g) == {"1": 4, "all": 4}
    with g.factory() as db:
        assert db.get(models.Client, g.client).name == "Synthetic"
    assert not g.enriched


@pytest.mark.asyncio
async def test_optional_llm_failure_does_not_retry_successful_sync(current_sync, monkeypatch):
    g = current_sync
    monkeypatch.setattr("automation.detector_hypothesis_work.execute", AsyncMock(side_effect=RuntimeError("llm failed")))
    await run(g)
    assert state(g)[0] == models.SyncJobStatus.SUCCESS
    assert len(g.calls) == 1


@pytest.mark.asyncio
async def test_accepted_followup_remains_pending_after_success(current_sync):
    g = current_sync
    original = g.api.get_goals_stats
    async def following(*args, **kwargs):
        assert g.engine.pool.checkedout() == 0
        durable_sync.enqueue(g.id, days=7, force_full=True, trigger="manual",
                             date_from="2026-09-01", date_to=str(DAY))
        return await original(*args, **kwargs)
    g.api.get_goals_stats = following
    await run(g)
    assert state(g)[:2] == (models.SyncJobStatus.SUCCESS, models.IntegrationSyncStatus.PENDING)


@pytest.mark.asyncio
@pytest.mark.parametrize("invalid", ["payload", "settings", "missing_fence"])
async def test_invalid_work_does_not_start_provider(current_sync, invalid):
    g = current_sync
    if invalid == "payload":
        g.payload = {**g.payload, "owner_id": str(uuid.uuid4())}
    elif invalid == "settings":
        with g.factory.begin() as db:
            db.get(models.Integration, g.id).selected_goals = '["2"]'
    with pytest.raises((LeaseLost, IntegrationScopeChanged)):
        if invalid == "missing_fence":
            await work.execute(g.factory, g.payload)
        else:
            await run(g)
    assert not g.constructors and counts(g) == {"1": 34}


@pytest.mark.asyncio
async def test_timeout_preserves_old_data_and_records_failure(current_sync, monkeypatch):
    from backend_api.sync_jobs import SyncJobTimeout
    g = current_sync
    async def stuck(*args, **kwargs):
        assert g.engine.pool.checkedout() == 0
        await work.asyncio.Event().wait()
    g.api.get_goals_stats = stuck
    monkeypatch.setattr("backend_api.sync_jobs._JOB_TIMEOUT_SEC", 0.05)
    with pytest.raises(SyncJobTimeout):
        await run(g)
    assert counts(g) == {"1": 34} and state(g)[0] == models.SyncJobStatus.FAILED


@pytest.mark.asyncio
async def test_notification_failure_cannot_erase_failed_status(current_sync, monkeypatch):
    g = current_sync
    async def fail(*args, **kwargs):
        raise ValueError("invalid response")
    def notification(db, **kwargs):
        db.get(models.Client, g.client).name = "must rollback"
        db.flush()
        raise RuntimeError("notification failed")
    g.api.get_goals_stats = fail
    monkeypatch.setattr("backend_api.services.notifications.create_notification", notification)
    with pytest.raises(ValueError):
        await run(g)
    assert state(g)[0] == models.SyncJobStatus.FAILED
    assert counts(g) == {"1": 34}
    with g.factory() as db:
        assert db.get(models.Client, g.client).name == "Synthetic"


@pytest.mark.asyncio
async def test_lease_lost_after_data_flush_rolls_back_data_and_success_together(current_sync, monkeypatch):
    g = current_sync
    def expire_after_rows(db, client_id):
        assert db.scalar(sa.select(models.MetrikaGoals.conversion_count).where(
            models.MetrikaGoals.integration_id == g.id, models.MetrikaGoals.date == DAY,
            models.MetrikaGoals.goal_id == "1")) == 4
        with g.engine.begin() as other:
            other.execute(jobs.update().where(jobs.c.id == g.job).values(
                lease_until=sa.func.clock_timestamp() - sa.text("interval '1 second'")))
    monkeypatch.setattr("backend_api.services.detector.run_detector_for_client", expire_after_rows)
    with pytest.raises(LeaseLost):
        await run(g)
    assert counts(g) == {"1": 34}
    assert state(g)[:3] == (models.SyncJobStatus.RUNNING, models.IntegrationSyncStatus.PENDING, datetime(2026, 9, 9))
    assert not g.invalidated and not g.enriched
