from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
import sqlalchemy as sa

from automation import detector_hypothesis_work as work
from automation.work_tables import jobs
from core import models
from core.job_fence import fenced_job, LeaseLost
from tests.test_durable_work import pg, submit, claim


@pytest.fixture
def hypothesis(pg, monkeypatch):
    factory, engine = pg
    models.Base.metadata.create_all(engine)
    with factory.begin() as db:
        owner = models.User(email="hypothesis@example.test", password_hash="synthetic", global_detector_enabled=True)
        db.add(owner)
        db.flush()
        client = models.Client(owner_id=owner.id, name="Synthetic", detector_enabled=True)
        db.add(client)
        db.flush()
        integration = models.Integration(client_id=client.id, platform=models.IntegrationPlatform.VK_ADS)
        db.add(integration)
        alert = models.DetectorAlert(client_id=client.id, owner_id=owner.id, metric="cpa", mode="baseline",
            actual_value=150, baseline_value=100, deviation_pct=50, hypothesis_text="Deterministic",
            meta={"unchanged": "keep"})
        db.add(alert)
        db.flush()
        client_id, owner_id, alert_id, integration_id = client.id, owner.id, alert.id, integration.id
    job = submit(factory, resource=str(integration_id))
    execution = claim(factory, job)
    cfg = SimpleNamespace(openai=SimpleNamespace(api_key="synthetic-key", base_url="https://provider.invalid/", model="test-model"))
    monkeypatch.setattr(work, "get_config", lambda: cfg)
    invalidations = []
    def invalidate(client):
        assert engine.pool.checkedout() == 0
        invalidations.append(client)
    monkeypatch.setattr("backend_api.cache_service.CacheService.invalidate_client", invalidate)
    calls, constructors, closed = [], [], []
    async def create(**kwargs):
        assert engine.pool.checkedout() == 0
        calls.append(kwargs)
        return SimpleNamespace(content=[SimpleNamespace(text="  Hypothesis 150  ")])
    api = SimpleNamespace(messages=SimpleNamespace(create=create))
    class Managed:
        def __init__(self, **kwargs):
            assert engine.pool.checkedout() == 0
            constructors.append(kwargs)
        async def __aenter__(self):
            return api
        async def __aexit__(self, *args):
            assert engine.pool.checkedout() == 0
            closed.append(True)
    monkeypatch.setattr("anthropic.AsyncAnthropic", Managed)
    return SimpleNamespace(factory=factory, engine=engine, client=client_id, owner=owner_id,
        alert=alert_id, integration=integration_id, job=job, token=execution["lease_token"],
        cfg=cfg, calls=calls, constructors=constructors, api=api, closed=closed, invalidations=invalidations)


async def run(g):
    with fenced_job(g.job, g.token):
        return await work.execute(g.factory, g.client)


def current(g):
    with g.factory() as db:
        alert = db.get(models.DetectorAlert, g.alert)
        return alert.hypothesis_text, alert.meta


@pytest.mark.asyncio
async def test_http_and_cleanup_without_sql_connection_and_cached_replay(hypothesis):
    g = hypothesis
    assert await run(g) == 1
    assert current(g)[0] == "Hypothesis 150"
    assert current(g)[1]["unchanged"] == "keep"
    assert "llm_hypothesis_at" in current(g)[1]
    assert await run(g) == 0
    assert len(g.calls) == len(g.closed) == 1
    assert g.invalidations == [str(g.client)]
    assert g.constructors == [{"api_key": "synthetic-key", "base_url": "https://provider.invalid", "max_retries": 0}]
    assert g.calls[0]["model"] == "test-model"
    assert g.calls[0]["max_tokens"] == 150 and g.calls[0]["temperature"] == 1.0
    with g.factory() as db:
        assert g.calls[0]["messages"][0]["content"] == work._build_prompt(db.get(models.DetectorAlert, g.alert))
    assert g.engine.pool.checkedout() == 0


@pytest.mark.asyncio
@pytest.mark.parametrize("condition", ["no_key", "disabled", "owner_disabled", "paused", "closed", "fresh", *work.DETERMINISTIC_MODES])
async def test_unneeded_generation_never_opens_provider(hypothesis, condition):
    g = hypothesis
    with g.factory.begin() as db:
        alert, client, owner = db.get(models.DetectorAlert, g.alert), db.get(models.Client, g.client), db.get(models.User, g.owner)
        if condition == "no_key": g.cfg.openai.api_key = ""
        elif condition == "disabled": client.detector_enabled = False
        elif condition == "owner_disabled": owner.global_detector_enabled = False
        elif condition == "paused": client.status = models.ClientStatus.PAUSED
        elif condition == "closed": alert.status = "closed"
        elif condition == "fresh": alert.meta = {"llm_hypothesis_at": datetime.now(timezone.utc).isoformat()}
        else: alert.mode = condition
    assert await run(g) == 0
    assert not g.constructors


@pytest.mark.asyncio
@pytest.mark.parametrize("change", ["value", "meta", "dismiss", "text", "checked", "mode", "disabled", "owner_disabled", "owner_changed", "paused", "delete"])
async def test_response_cannot_overwrite_newer_state(hypothesis, change):
    g = hypothesis
    original = g.api.messages.create
    async def changing(**kwargs):
        response = await original(**kwargs)
        with g.factory.begin() as db:
            alert = db.get(models.DetectorAlert, g.alert)
            if change == "value": alert.actual_value = 200
            elif change == "meta": alert.meta = {"newer": True}
            elif change == "dismiss": alert.status = "dismissed"
            elif change == "text": alert.hypothesis_text = "Newer text"
            elif change == "checked": alert.last_checked_at += timedelta(seconds=1)
            elif change == "mode": alert.mode = "plan"
            elif change == "disabled": db.get(models.Client, g.client).detector_enabled = False
            elif change == "owner_disabled": db.get(models.User, g.owner).global_detector_enabled = False
            elif change == "owner_changed":
                other = models.User(email="other@example.test", password_hash="synthetic")
                db.add(other)
                db.flush()
                db.get(models.Client, g.client).owner_id = other.id
            elif change == "paused": db.get(models.Client, g.client).status = models.ClientStatus.PAUSED
            elif change == "delete": db.delete(alert)
        return response
    g.api.messages.create = changing
    assert await run(g) == 0
    assert not g.invalidations
    if change != "delete":
        assert current(g)[0] == ("Newer text" if change == "text" else "Deterministic")
        assert "llm_hypothesis_at" not in current(g)[1]


@pytest.mark.asyncio
async def test_expired_lease_rejects_write_and_closes_http_client(hypothesis):
    g = hypothesis
    original = g.api.messages.create
    async def expiring(**kwargs):
        response = await original(**kwargs)
        with g.engine.begin() as conn:
            conn.execute(jobs.update().where(jobs.c.id == g.job).values(
                lease_until=sa.func.clock_timestamp() - sa.text("interval '1 second'")))
        return response
    g.api.messages.create = expiring
    with pytest.raises(LeaseLost):
        await run(g)
    assert current(g) == ("Deterministic", {"unchanged": "keep"})
    assert g.closed == [True]


@pytest.mark.asyncio
@pytest.mark.parametrize("empty", [False, True])
async def test_provider_failure_or_empty_keeps_fallback_without_replay(hypothesis, empty):
    g = hypothesis
    create = AsyncMock(return_value=SimpleNamespace(content=[])) if empty else AsyncMock(side_effect=RuntimeError("synthetic"))
    g.api.messages.create = create
    assert await run(g) == 0
    assert create.await_count == 1 and g.closed == [True]
    assert current(g) == ("Deterministic", {"unchanged": "keep"})


@pytest.mark.asyncio
async def test_requires_durable_fence(hypothesis):
    with pytest.raises(LeaseLost):
        await work.execute(hypothesis.factory, hypothesis.client)
    assert not hypothesis.constructors


@pytest.mark.asyncio
async def test_sync_caller_commits_completed_detector_before_http(hypothesis, monkeypatch):
    from backend_api import sync_jobs
    g = hypothesis
    monkeypatch.setattr(sync_jobs, "SessionLocal", g.factory)
    async def collected(db, integration, *args, **kwargs):
        assert kwargs == {"defer_hypotheses": True}
        db.get(models.DetectorAlert, g.alert).actual_value = 180
        db.flush()
        assert g.engine.pool.checkedout() == 1
        return True
    monkeypatch.setattr(sync_jobs, "sync_integration", collected)
    with fenced_job(g.job, g.token), g.factory() as db:
        integration = db.get(models.Integration, g.integration)
        await sync_jobs._sync_attempt(db, integration, "2026-09-01", "2026-09-10")
    assert len(g.calls) == 1 and "180" in g.calls[0]["messages"][0]["content"]
    assert current(g)[0] == "Hypothesis 150"


@pytest.mark.asyncio
@pytest.mark.parametrize("failed", [False, True])
async def test_legacy_sync_contract_unchanged(monkeypatch, failed):
    from backend_api import sync_jobs
    execute = AsyncMock(side_effect=RuntimeError("sync") if failed else None)
    monkeypatch.setattr(sync_jobs, "sync_integration", execute)
    if failed:
        with pytest.raises(RuntimeError):
            await sync_jobs._sync_attempt("session", "integration", "start", "end")
    else:
        await sync_jobs._sync_attempt("session", "integration", "start", "end")
    execute.assert_awaited_once_with("session", "integration", "start", "end")


@pytest.mark.asyncio
@pytest.mark.parametrize("outcome", ["detector_failed", "sync_failed", "llm_failed", "lease_lost"])
async def test_sync_enrichment_failure_boundaries(hypothesis, monkeypatch, outcome):
    from backend_api import sync_jobs
    g = hypothesis
    monkeypatch.setattr(sync_jobs, "SessionLocal", g.factory)
    collected = AsyncMock(side_effect=RuntimeError("sync") if outcome == "sync_failed" else None,
        return_value=outcome != "detector_failed")
    enrichment = AsyncMock(side_effect=LeaseLost("lost") if outcome == "lease_lost" else RuntimeError("optional"))
    monkeypatch.setattr(sync_jobs, "sync_integration", collected)
    monkeypatch.setattr(work, "execute", enrichment)
    with fenced_job(g.job, g.token), g.factory() as db:
        integration = db.get(models.Integration, g.integration)
        if outcome in ("sync_failed", "lease_lost"):
            with pytest.raises(LeaseLost if outcome == "lease_lost" else RuntimeError):
                await sync_jobs._sync_attempt(db, integration, "start", "end")
        else:
            await sync_jobs._sync_attempt(db, integration, "start", "end")
    assert collected.await_count == 1
    assert enrichment.await_count == (1 if outcome in ("llm_failed", "lease_lost") else 0)
