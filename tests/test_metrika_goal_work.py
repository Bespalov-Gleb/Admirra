from datetime import date
from types import SimpleNamespace
from unittest.mock import AsyncMock
import uuid

import pytest
import sqlalchemy as sa

from automation import metrika_goal_work as work
from automation import work_ledger
from automation.integration_work_scope import IntegrationScopeChanged
from automation.metrika_goal_window import goal_window
from automation.work_tables import jobs
from core import models
from core.job_fence import fenced_job, LeaseLost
from tests.test_durable_work import pg, claim
from tests.test_metrika_goal_batch import InlineQueue

DAY = date(2026, 9, 10)


@pytest.fixture
def goals(pg, monkeypatch):
    factory, engine = pg
    models.Base.metadata.create_all(engine)
    with factory.begin() as db:
        owner = models.User(email="goal-sync@example.test", password_hash="synthetic")
        db.add(owner)
        db.flush()
        client = models.Client(owner_id=owner.id, name="Synthetic")
        db.add(client)
        db.flush()
        integration = models.Integration(client_id=client.id, platform=models.IntegrationPlatform.YANDEX_DIRECT,
            selected_goals='["1"]', selected_counters='["a", "b"]', access_token="synthetic-direct",
            sync_status=models.IntegrationSyncStatus.SUCCESS, account_id="personal-login")
        db.add(integration)
        db.flush()
        id, client_id = integration.id, client.id
        db.add(models.MetrikaGoals(client_id=client_id, integration_id=id, date=DAY,
            goal_id="1", goal_name="Old", conversion_count=34))
        owner_id = owner.id
    payload = dict(integration_id=str(id), client_id=str(client_id), owner_id=str(owner_id),
                   date_from=str(DAY), date_to=str(DAY))
    with factory.begin() as db:
        job = work_ledger.submit(db, kind="goals", queue="sync.manual", key="goals-fixture",
            resource=f"integration:{id}", tenant=owner_id, payload=payload, replay_safe=True)
    execution = claim(factory, job)
    monkeypatch.setattr("core.security.decrypt_token", lambda value: value)
    monkeypatch.setattr("automation.request_queue.get_request_queue", AsyncMock(return_value=InlineQueue()))
    calls = []
    async def metadata(counter):
        assert engine.pool.checkedout() == 0
        return [{"id": "1", "name": "Заявка"}]
    async def stats(counter, start, end, **kwargs):
        assert engine.pool.checkedout() == 0
        calls.append((counter, start, end, kwargs))
        return [{"dimensions": [{"name": str(DAY)}], "metrics": [3 if counter == "a" else 4]}]
    api = SimpleNamespace(get_counter_goals=metadata, get_goals_stats=stats)
    constructors = []
    def make(token, client_login):
        assert engine.pool.checkedout() == 0
        constructors.append((token, client_login))
        return api
    monkeypatch.setattr("automation.yandex_metrica.YandexMetricaAPI", make)
    return SimpleNamespace(factory=factory, engine=engine, id=id, client=client_id, job=job,
        token=execution["lease_token"], api=api, payload=payload, calls=calls, constructors=constructors)


async def run(g):
    with fenced_job(g.job, g.token):
        return await work.execute(g.factory, g.payload)


def counts(g):
    with g.factory() as db:
        return dict(db.execute(sa.select(models.MetrikaGoals.goal_id, models.MetrikaGoals.conversion_count)
            .where(models.MetrikaGoals.date == DAY)).all())


@pytest.mark.asyncio
async def test_short_transactions_collect_all_counters_and_replay_idempotently(goals):
    g = goals
    assert await run(g) == "updated"
    assert counts(g) == {"1": 7, "all": 7}
    assert await run(g) == "updated"
    assert counts(g) == {"1": 7, "all": 7}
    assert g.calls[0][1:3] == ("2026-08-11", "2026-09-10")
    assert g.constructors == [("synthetic-direct", "personal-login")] * 2
    assert g.engine.pool.checkedout() == 0


@pytest.mark.asyncio
async def test_second_counter_failure_keeps_old_data(goals):
    g = goals
    original = g.api.get_goals_stats
    async def failing(counter, *args, **kwargs):
        if counter == "b":
            raise RuntimeError("synthetic provider error")
        return await original(counter, *args, **kwargs)
    g.api.get_goals_stats = failing
    with pytest.raises(RuntimeError):
        await run(g)
    assert counts(g) == {"1": 34}
    assert g.engine.pool.checkedout() == 0


@pytest.mark.asyncio
@pytest.mark.parametrize("field,value", [("selected_goals", '["2"]'), ("selected_counters", '["c"]'),
    ("primary_goal_id", "2"), ("access_token", "rotated"), ("account_id", "other-login"),
    ("connection_status", "revoked"), ("utm_source", "new-source"), ("client_status", models.ClientStatus.PAUSED)])
async def test_settings_change_during_http_discards_all_rows(goals, field, value):
    g = goals
    original = g.api.get_goals_stats
    changed = False
    async def changing(*args, **kwargs):
        nonlocal changed
        assert g.engine.pool.checkedout() == 0
        if not changed:
            changed = True
            with g.factory.begin() as db:
                obj = db.get(models.Client, g.client) if field == "client_status" else db.get(models.Integration, g.id)
                setattr(obj, "status" if field == "client_status" else field, value)
        return await original(*args, **kwargs)
    g.api.get_goals_stats = changing
    with pytest.raises(work.GoalSettingsChanged):
        await run(g)
    assert counts(g) == {"1": 34}


@pytest.mark.asyncio
async def test_owner_change_during_collection_cannot_publish_to_new_owner(goals):
    g = goals
    original = g.api.get_goals_stats
    changed = False
    async def moving(*args, **kwargs):
        nonlocal changed
        if not changed:
            changed = True
            with g.factory.begin() as db:
                owner = models.User(email="new-goal-owner@example.test", password_hash="synthetic")
                db.add(owner)
                db.flush()
                db.get(models.Client, g.client).owner_id = owner.id
        return await original(*args, **kwargs)
    g.api.get_goals_stats = moving
    with pytest.raises(work.GoalSettingsChanged):
        await run(g)
    assert counts(g) == {"1": 34}


@pytest.mark.asyncio
async def test_expired_execution_rolls_back_replacement(goals):
    g = goals
    original = g.api.get_goals_stats
    async def expire(*args, **kwargs):
        with g.engine.begin() as conn:
            conn.execute(jobs.update().where(jobs.c.id == g.job)
                .values(lease_until=sa.func.clock_timestamp() - sa.text("interval '1 second'")))
        return await original(*args, **kwargs)
    g.api.get_goals_stats = expire
    with pytest.raises(LeaseLost):
        await run(g)
    assert counts(g) == {"1": 34}


@pytest.mark.asyncio
async def test_avito_uses_own_grant_login_and_escaped_utm_filter(goals):
    g = goals
    with g.factory.begin() as db:
        obj = db.get(models.Integration, g.id)
        obj.platform = models.IntegrationPlatform.AVITO_ADS
        obj.metrika_access_token, obj.metrika_account_id, obj.utm_source = "synthetic-avito", "avito-owner", "brand's"
    assert await run(g) == "updated"
    assert g.constructors == [("synthetic-avito", "avito-owner")]
    assert g.calls[0][3]["filters"] == "ym:s:UTMSource=='brand\\'s'"
    assert counts(g) == {"1": 7, "all": 7}


@pytest.mark.asyncio
async def test_missing_avito_grant_does_not_fall_back_to_direct(goals):
    g = goals
    with g.factory.begin() as db:
        db.get(models.Integration, g.id).platform = models.IntegrationPlatform.AVITO_ADS
    with pytest.raises(ValueError):
        await run(g)
    assert not g.constructors and counts(g) == {"1": 34}


@pytest.mark.asyncio
async def test_paused_project_does_not_call_provider(goals):
    g = goals
    with g.factory.begin() as db:
        db.get(models.Client, g.client).status = models.ClientStatus.PAUSED
    with pytest.raises(IntegrationScopeChanged):
        await run(g)
    assert not g.constructors and counts(g) == {"1": 34}


@pytest.mark.asyncio
async def test_missing_fence_refused_before_sql_or_http(goals):
    with pytest.raises(LeaseLost):
        await work.execute(goals.factory, goals.payload)
    assert not goals.constructors and goals.engine.pool.checkedout() == 0


def test_plan_repr_never_contains_credentials(goals):
    with goals.factory() as db:
        plan = work.prepare(db, goals.id, str(DAY), str(DAY))
    assert "synthetic-direct" not in repr(plan)


@pytest.mark.parametrize("first,lookback,start", [(True, "30", "2026-06-13"),
    (False, "30", "2026-08-11"), (False, "bad", "2026-09-10"),
    (False, "0", "2026-09-10"), (False, "90", "2026-06-12")])
def test_window_preserves_first_sync_and_legacy_lookback(monkeypatch, first, lookback, start):
    monkeypatch.setenv("METRIKA_GOALS_LOOKBACK_DAYS", lookback)
    days = goal_window(str(DAY), str(DAY), first_sync=first)
    assert days[0].isoformat() == start and days[-1] == DAY
