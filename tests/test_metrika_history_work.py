from datetime import datetime

import pytest
import sqlalchemy as sa

from automation import backfill_work, metrika_goal_work
from automation.integration_work_scope import IntegrationScopeChanged
from automation.work_tables import jobs
from core import models
from core.job_fence import LeaseLost, fenced_job
from tests.test_durable_work import pg
from tests.test_metrika_goal_work import goals, counts, DAY


@pytest.fixture
def history(goals, monkeypatch):
    g = goals
    monkeypatch.setattr("core.database.SessionLocal", g.factory)
    with g.factory.begin() as db:
        integration = db.get(models.Integration, g.id)
        integration.platform = models.IntegrationPlatform.YANDEX_METRIKA
        integration.account_id = "123"
        integration.agency_client_login = "unknown"
        integration.last_sync_at = datetime(2026, 9, 15)
        integration.last_sync_trigger = "manual"
        db.execute(jobs.update().where(jobs.c.id == g.job).values(kind="history.backfill", queue="sync.backfill"))
    g.invalidated = []
    def invalidate(client_id):
        assert g.engine.pool.checkedout() == 0
        g.invalidated.append((client_id, counts(g)))
    monkeypatch.setattr("backend_api.cache_service.CacheService.invalidate_client", invalidate)
    return g


async def run(g):
    with fenced_job(g.job, g.token):
        return await backfill_work.execute(g.payload)


def watermark(g):
    with g.factory() as db:
        i = db.get(models.Integration, g.id)
        return i.sync_status, i.last_sync_at, i.last_sync_trigger


@pytest.mark.asyncio
async def test_history_releases_sql_during_all_provider_calls_and_keeps_current_watermark(history):
    g = history
    previous = watermark(g)
    assert await run(g) == "updated"
    assert counts(g) == {"1": 4, "all": 4}
    assert g.constructors == [("synthetic-direct", None)]
    assert g.calls[0][:3] == ("123", "2026-08-11", "2026-09-10")
    assert watermark(g) == previous
    assert g.invalidated == [(str(g.client), {"1": 4, "all": 4})]
    assert g.engine.pool.checkedout() == 0


@pytest.mark.asyncio
@pytest.mark.parametrize("failure", ["metadata", "statistics", "malformed", "expired_lease"])
async def test_failure_preserves_old_history_and_does_not_invalidate_or_advance_status(history, failure):
    g = history
    previous = watermark(g)
    original = g.api.get_goals_stats
    async def fail(*args, **kwargs):
        assert g.engine.pool.checkedout() == 0
        if failure == "malformed":
            return [{"dimensions": [{"name": str(DAY)}], "metrics": [-1]}]
        if failure == "expired_lease":
            with g.engine.begin() as db:
                db.execute(jobs.update().where(jobs.c.id == g.job).values(
                    lease_until=sa.func.clock_timestamp() - sa.text("interval '1 second'")))
            return await original(*args, **kwargs)
        raise RuntimeError("synthetic provider failure")
    if failure == "metadata":
        g.api.get_counter_goals = fail
    else:
        g.api.get_goals_stats = fail
    expected = LeaseLost if failure == "expired_lease" else ValueError if failure == "malformed" else RuntimeError
    with pytest.raises(expected):
        await run(g)
    assert counts(g) == {"1": 34} and watermark(g) == previous
    assert not g.invalidated and g.engine.pool.checkedout() == 0


@pytest.mark.asyncio
@pytest.mark.parametrize("change", ["owner", "project", "pause", "counter", "goals", "token", "platform"])
async def test_inflight_scope_or_settings_change_cannot_publish_history(history, change):
    g = history
    previous = watermark(g)
    original = g.api.get_goals_stats
    async def changing(*args, **kwargs):
        with g.factory.begin() as db:
            i = db.get(models.Integration, g.id)
            if change in {"owner", "project"}:
                owner = models.User(email="moved-history@example.test", password_hash="synthetic")
                db.add(owner)
                db.flush()
                if change == "owner":
                    db.get(models.Client, g.client).owner_id = owner.id
                else:
                    client = models.Client(owner_id=owner.id, name="Moved")
                    db.add(client)
                    db.flush()
                    i.client_id = client.id
            elif change == "pause":
                db.get(models.Client, g.client).status = models.ClientStatus.PAUSED
            else:
                field, value = {"counter": ("account_id", "456"), "goals": ("selected_goals", '["2"]'),
                                "token": ("access_token", "new-token"),
                                "platform": ("platform", models.IntegrationPlatform.YANDEX_DIRECT)}[change]
                setattr(i, field, value)
        return await original(*args, **kwargs)
    g.api.get_goals_stats = changing
    with pytest.raises(metrika_goal_work.GoalSettingsChanged):
        await run(g)
    assert counts(g) == {"1": 34} and watermark(g) == previous
    assert not g.invalidated and g.engine.pool.checkedout() == 0


@pytest.mark.asyncio
async def test_preparation_cannot_switch_to_a_different_platform(history, monkeypatch):
    g = history
    original = metrika_goal_work.prepare
    def changing(db, *args):
        with g.factory.begin() as other:
            other.get(models.Integration, g.id).platform = models.IntegrationPlatform.YANDEX_DIRECT
        db.expire_all()
        return original(db, *args)
    monkeypatch.setattr(metrika_goal_work, "prepare", changing)
    with pytest.raises(IntegrationScopeChanged, match="during goals preparation"):
        await run(g)
    assert counts(g) == {"1": 34}
    assert not g.constructors and not g.invalidated


@pytest.mark.asyncio
async def test_standalone_without_selection_collects_all_goals(history):
    g = history
    with g.factory.begin() as db:
        db.get(models.Integration, g.id).selected_goals = None
    async def metadata(*args):
        assert g.engine.pool.checkedout() == 0
        return [{"id": "1", "name": "One"}, {"id": "2", "name": "Two"}]
    async def stats(*args, **kwargs):
        assert g.engine.pool.checkedout() == 0
        assert kwargs["metrics"] == "ym:s:goal1visits,ym:s:goal2visits"
        return [{"dimensions": [{"name": str(DAY)}], "metrics": [3, 4]}]
    g.api.get_counter_goals, g.api.get_goals_stats = metadata, stats
    await run(g)
    assert counts(g) == {"1": 3, "2": 4, "all": 7}


@pytest.mark.asyncio
async def test_first_sync_preserves_90_day_collection_window(history):
    g = history
    with g.factory.begin() as db:
        db.get(models.Integration, g.id).sync_status = models.IntegrationSyncStatus.NEVER
    previous = watermark(g)
    await run(g)
    assert g.calls[0][1:3] == ("2026-06-13", "2026-09-10")
    assert watermark(g) == previous


@pytest.mark.asyncio
async def test_authorization_link_is_not_a_counter_and_does_not_advance_watermark(history):
    g = history
    with g.factory.begin() as db:
        db.get(models.Integration, g.id).account_id = "profile-login"
    previous = watermark(g)
    assert await run(g) == "skipped"
    assert not g.constructors and not g.invalidated
    assert counts(g) == {"1": 34} and watermark(g) == previous
