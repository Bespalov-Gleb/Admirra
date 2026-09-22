from copy import deepcopy
from datetime import datetime, timedelta
from decimal import Decimal
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
import sqlalchemy as sa

from automation import ads_sync_work as ads, metrika_sync_work as work
from automation.integration_work_scope import IntegrationScopeChanged
from automation.metrika_goal_work import GoalSettingsChanged
from automation.sync_request import request_params
from automation.work_tables import jobs
from core import models
from core.job_fence import fenced_job, LeaseLost
from tests.test_durable_work import pg
from tests.test_metrika_goal_work import goals, DAY


@pytest.fixture(params=list(ads.PLATFORMS))
def advertising(goals, monkeypatch, request):
    g = goals
    g.platform = request.param
    g.model = {models.IntegrationPlatform.YANDEX_DIRECT: models.YandexStats,
               models.IntegrationPlatform.VK_ADS: models.VKStats,
               models.IntegrationPlatform.AVITO_ADS: models.AvitoStats}[g.platform]
    with g.factory.begin() as db:
        integration = db.get(models.Integration, g.id)
        integration.platform = g.platform
        integration.selected_goals = None
        integration.account_id = "100"
        integration.platform_client_id = "test-client"
        integration.platform_client_secret = "test-secret"
        integration.last_sync_at = datetime(2026, 9, 9)
        integration.balance = 99
        integration.refresh_token = "test-refresh"
        campaign = models.Campaign(integration_id=g.id, external_id="42", name="Test", is_active=True,
                                  vk_goal_action_id="leadads", vk_goal_action_name="Lead")
        db.add(campaign)
        db.flush()
        g.campaign = campaign.id
        db.add(g.model(client_id=g.client, campaign_id=campaign.id, campaign_name="Test", date=DAY,
                       impressions=100, clicks=10, cost=100, conversions=34))
        params = request_params(integration, integration.client, days=1, force_full=False,
            trigger="manual", date_from=str(DAY), date_to=str(DAY))
        job = models.SyncJob(integration_id=g.id, status=models.SyncJobStatus.QUEUED, params=json.dumps(params))
        db.add(job)
        db.flush()
        g.business = job.id
        g.payload = dict(sync_job_id=str(job.id), client_id=str(g.client), owner_id=str(integration.client.owner_id))
        db.execute(jobs.update().where(jobs.c.id == g.job).values(kind="sync", payload=g.payload))
        integration.sync_status = models.IntegrationSyncStatus.PENDING
    g.row = dict(campaign_id="42", campaign_name="Test", date=str(DAY), impressions=10,
                 clicks=2, cost=Decimal("4"), conversions=1)
    async def outside(value):
        assert g.engine.pool.checkedout() == 0
        return deepcopy(value)
    g.api = SimpleNamespace(strict_sync=False,
        get_campaigns=AsyncMock(side_effect=lambda *a: outside([dict(id="42", name="Test", goal_action_id="leadads")])),
        get_report=AsyncMock(), get_statistics=AsyncMock(), get_campaign_statistics_bundle=AsyncMock(),
        get_goal_actions_from_statistics=AsyncMock(return_value={"42": ("leadads", "Lead")}),
        get_campaign_strategies=AsyncMock(return_value={}), get_balance=AsyncMock())
    # AsyncMock side_effect must itself be async (not return an unawaited coroutine).
    async def campaigns(*a): return await outside([dict(id="42", name="Test", goal_action_id="leadads")])
    async def report(*a, level="campaign", **kw): return await outside([g.row] if level == "campaign" else [])
    async def stats(*a, **kw): return await outside([g.row])
    async def bundle(*a): return await outside(dict(campaigns=[g.row], groups=[], creatives=[]))
    async def balance(*a): return await outside(dict(balance=10, currency="RUB"))
    g.api.get_campaigns.side_effect = campaigns
    g.api.get_report.side_effect = report
    g.api.get_statistics.side_effect = stats
    g.api.get_campaign_statistics_bundle.side_effect = bundle
    g.api.get_balance.side_effect = balance
    monkeypatch.setattr(ads, "make_api", lambda plan: g.api)
    monkeypatch.setattr("core.security.encrypt_token", lambda value: value)
    g.invalidated = []
    def invalidate(client_id):
        assert g.engine.pool.checkedout() == 0
        g.invalidated.append(client_id)
    monkeypatch.setattr("backend_api.cache_service.CacheService.invalidate_client", invalidate)
    monkeypatch.setattr("automation.sync._run_detector_after_sync", lambda *a: False)
    monkeypatch.setattr(ads, "refresh", AsyncMock(return_value=None))
    return g


async def run(g):
    with fenced_job(g.job, g.token):
        return await work.execute(g.factory, g.payload)


def state(g):
    with g.factory() as db:
        integration = db.get(models.Integration, g.id)
        return (list(db.scalars(sa.select(g.model.conversions).where(g.model.campaign_id == g.campaign))),
            integration.last_sync_at, integration.balance, db.get(models.SyncJob, g.business).status)


@pytest.mark.asyncio
@pytest.mark.parametrize("trigger", ["manual", "auto"])
async def test_all_platforms_commit_complete_snapshot_and_replay_without_io(advertising, trigger):
    g = advertising
    with g.factory.begin() as db:
        job = db.get(models.SyncJob, g.business)
        job.params = json.dumps({**json.loads(job.params), "trigger": trigger})
    assert await run(g) == "updated"
    assert state(g)[0] == [1]
    assert state(g)[1] > datetime(2026, 9, 9)
    assert state(g)[2:] == (10, models.SyncJobStatus.SUCCESS)
    g.api.get_campaigns.reset_mock()
    assert await run(g) == "already-complete"
    g.api.get_campaigns.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("bad", ["duplicate", "outside", "metric", "details", "goals"])
async def test_failed_required_source_keeps_all_previous_data_and_watermark(advertising, bad, monkeypatch):
    g = advertising
    original = ads.collect
    async def corrupt(plan):
        result = await original(plan)
        if bad in {"details", "goals"}:
            raise ValueError("synthetic required source failure")
        if bad == "duplicate":
            result["data"]["campaigns"].append(g.row)
        elif bad == "outside":
            result["data"]["campaigns"][0]["date"] = "2025-01-01"
        else:
            result["data"]["campaigns"][0]["cost"] = "NaN"
        return result
    monkeypatch.setattr(ads, "collect", corrupt)
    with pytest.raises(ValueError):
        await run(g)
    assert state(g) == ([34], datetime(2026, 9, 9), 99, models.SyncJobStatus.FAILED)
    assert not g.invalidated


@pytest.mark.asyncio
@pytest.mark.parametrize("change", ["settings", "owner", "lease"])
async def test_inflight_change_rejects_stale_snapshot(advertising, change, monkeypatch):
    g = advertising
    original = ads.collect
    async def moved(plan):
        result = await original(plan)
        with g.engine.begin() as db:
            if change == "settings":
                db.execute(sa.update(models.Integration).where(models.Integration.id == g.id).values(account_id="999"))
            elif change == "owner":
                db.execute(sa.update(models.Client).where(models.Client.id == g.client).values(status=models.ClientStatus.PAUSED))
            else:
                db.execute(jobs.update().where(jobs.c.id == g.job).values(lease_until=sa.func.now() - timedelta(seconds=1)))
        return result
    monkeypatch.setattr(ads, "collect", moved)
    with pytest.raises((GoalSettingsChanged, IntegrationScopeChanged, LeaseLost)):
        await run(g)
    assert state(g)[:3] == ([34], datetime(2026, 9, 9), 99)


@pytest.mark.asyncio
async def test_history_preserves_current_watermark_and_balance(advertising):
    g = advertising
    payload = dict(integration_id=str(g.id), client_id=str(g.client), owner_id=g.payload["owner_id"],
                   date_from=str(DAY), date_to=str(DAY))
    with g.factory.begin() as db:
        db.execute(jobs.update().where(jobs.c.id == g.job).values(kind="history.backfill", payload=payload))
    with fenced_job(g.job, g.token):
        assert await ads.execute_history(g.factory, payload) == "updated"
        assert await ads.execute_history(g.factory, payload) == "updated"
    assert state(g)[:3] == ([1], datetime(2026, 9, 9), 99)


@pytest.mark.asyncio
@pytest.mark.parametrize("advertising", [models.IntegrationPlatform.YANDEX_DIRECT, models.IntegrationPlatform.VK_ADS], indirect=True)
async def test_refresh_restarts_entire_snapshot_not_just_campaign_report(advertising, monkeypatch):
    g = advertising
    original = ads.collect
    calls = []
    async def collect(plan):
        calls.append(plan.credentials["token"])
        if len(calls) == 1:
            raise PermissionError("401 expired")
        return await original(plan)
    async def refresh(plan, error):
        assert g.engine.pool.checkedout() == 0
        return dict(access_token="new-token", refresh_token="new-refresh", expires_in=3600)
    monkeypatch.setattr(ads, "collect", collect)
    monkeypatch.setattr(ads, "refresh", refresh)
    assert await run(g) == "updated"
    assert calls == ["synthetic-direct", "new-token"]
    assert state(g)[0] == [1]


@pytest.mark.asyncio
async def test_confirmed_empty_replaces_only_this_integrations_window(advertising, monkeypatch):
    g = advertising
    original = ads.collect
    async def empty(plan):
        result = await original(plan)
        result["data"] = dict(campaigns=[], groups=[], keywords=[], creatives=[])
        return result
    monkeypatch.setattr(ads, "collect", empty)
    with g.factory.begin() as db:
        db.add(g.model(client_id=g.client, campaign_id=g.campaign, campaign_name="Test",
                       date=DAY - timedelta(days=1), conversions=7))
    await run(g)
    assert state(g)[0] == [7]


@pytest.mark.asyncio
@pytest.mark.parametrize("advertising", [models.IntegrationPlatform.YANDEX_DIRECT, models.IntegrationPlatform.VK_ADS], indirect=True)
async def test_followup_survives_owned_token_rotation(advertising, monkeypatch):
    from automation.sync_request import settings_digest
    g = advertising
    with g.factory.begin() as db:
        current = db.get(models.SyncJob, g.business)
        params = {**json.loads(current.params), "date_from": "2026-09-01"}
        queued = models.SyncJob(integration_id=g.id, status=models.SyncJobStatus.QUEUED, params=json.dumps(params))
        db.add(queued)
        db.flush()
        queued_id = queued.id
    original = ads.collect
    calls = 0
    async def expired(plan):
        nonlocal calls
        calls += 1
        if calls == 1:
            raise PermissionError("401")
        return await original(plan)
    monkeypatch.setattr(ads, "collect", expired)
    monkeypatch.setattr(ads, "refresh", AsyncMock(return_value=dict(access_token="rotated")))
    await run(g)
    with g.factory() as db:
        integration = db.get(models.Integration, g.id)
        queued = db.get(models.SyncJob, queued_id)
        assert json.loads(queued.params)["settings_digest"] == settings_digest(integration, integration.client)
        assert json.loads(queued.params)["date_from"] == "2026-09-01"
        assert queued.status == models.SyncJobStatus.QUEUED
        assert integration.sync_status == models.IntegrationSyncStatus.PENDING


@pytest.mark.asyncio
async def test_actual_required_detail_failure_rolls_back_campaign_level(advertising):
    g = advertising
    if g.platform == models.IntegrationPlatform.YANDEX_DIRECT:
        async def report(*a, level="campaign", **kw):
            if level == "group":
                raise ValueError("malformed group report")
            return [g.row]
        g.api.get_report.side_effect = report
    elif g.platform == models.IntegrationPlatform.AVITO_ADS:
        g.api.get_campaign_statistics_bundle.side_effect = ValueError("missing creative report")
    else:
        g.api.get_statistics.side_effect = ValueError("malformed second ID batch")
    with pytest.raises(ValueError):
        await run(g)
    assert state(g)[:3] == ([34], datetime(2026, 9, 9), 99)


@pytest.mark.asyncio
@pytest.mark.parametrize("advertising", [models.IntegrationPlatform.YANDEX_DIRECT, models.IntegrationPlatform.AVITO_ADS], indirect=True)
async def test_required_metrika_failure_after_ads_fetch_keeps_old_ads(advertising, monkeypatch):
    g = advertising
    from automation.sync_request import settings_digest
    with g.factory.begin() as db:
        integration = db.get(models.Integration, g.id)
        integration.selected_goals = '["1"]'
        integration.metrika_access_token = "test-metrika"
        job = db.get(models.SyncJob, g.business)
        job.params = json.dumps({**json.loads(job.params), "settings_digest": settings_digest(integration, integration.client)})
    monkeypatch.setattr("automation.metrika_goal_work.collect", AsyncMock(side_effect=ValueError("second counter malformed")))
    with pytest.raises(ValueError):
        await run(g)
    assert state(g)[:3] == ([34], datetime(2026, 9, 9), 99)


@pytest.mark.asyncio
@pytest.mark.parametrize("advertising", [models.IntegrationPlatform.YANDEX_DIRECT], indirect=True)
async def test_direct_keywords_replace_legacy_rows_with_stable_campaign_fk(advertising):
    g = advertising
    with g.factory.begin() as db:
        db.add(models.YandexKeywords(client_id=g.client, campaign_name="Test", date=DAY,
                                     keyword="query", impressions=100))
    async def report(*a, level="campaign", **kw):
        if level == "keyword":
            return [{**g.row, "name": "query"}]
        return [g.row] if level == "campaign" else []
    g.api.get_report.side_effect = report
    await run(g)
    with g.factory() as db:
        rows = list(db.scalars(sa.select(models.YandexKeywords)))
        assert len(rows) == 1 and rows[0].campaign_id == g.campaign and rows[0].impressions == 10
