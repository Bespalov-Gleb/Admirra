from types import SimpleNamespace
from unittest.mock import AsyncMock
import uuid

import pytest
import sqlalchemy as sa

from automation import backfill_work, durable_sync, metrika_goal_work, work_ledger
from automation.integration_work_scope import IntegrationScopeChanged
from automation.work_tables import jobs
from core import models
from core.job_fence import fenced_job, LeaseLost
from tests.test_durable_work import pg


@pytest.fixture(params=["goals", "history.backfill"])
def source_job(pg, monkeypatch, request):
    factory, engine = pg
    models.Base.metadata.create_all(engine)
    monkeypatch.setattr("core.database.SessionLocal", factory)
    with factory.begin() as db:
        owners = [models.User(email=f"scope-{i}@example.test", password_hash="synthetic") for i in range(2)]
        db.add_all(owners)
        db.flush()
        clients = [models.Client(owner_id=o.id, name="Synthetic", status=models.ClientStatus.ACTIVE) for o in owners]
        db.add_all(clients)
        db.flush()
        integration = models.Integration(client_id=clients[0].id, platform=models.IntegrationPlatform.YANDEX_DIRECT,
                                         connection_status="active")
        db.add(integration)
        db.flush()
        owner_ids, client_ids, iid = [o.id for o in owners], [c.id for c in clients], integration.id
        payload = dict(integration_id=str(iid), owner_id=str(owner_ids[0]), client_id=str(client_ids[0]),
                       date_from="2026-09-01", date_to="2026-09-02")
        queue = "sync.manual" if request.param == "goals" else "sync.backfill"
        job_id = work_ledger.submit(db, kind=request.param, queue=queue, key="scope-test",
            resource=f"integration:{iid}", tenant=owner_ids[0], payload=payload, replay_safe=True)
    with factory.begin() as db:
        claim = work_ledger.claim(db, job_id)
    invoked = []
    async def collect(factory, accepted):
        assert engine.pool.checkedout() == 0
        invoked.append(dict(accepted))
    provider = AsyncMock(side_effect=collect)
    monkeypatch.setattr("automation.ads_sync_work.execute_history", provider)
    # Goals preparation occurs only after the guard. Record this as the boundary
    # before credential decryption/provider construction, without network work.
    prepared = []
    def plan(*args):
        prepared.append(True)
        return None
    monkeypatch.setattr(metrika_goal_work, "prepare", plan)
    return SimpleNamespace(factory=factory, engine=engine, kind=request.param, owners=owner_ids, clients=client_ids,
                           integration=iid, job=job_id, token=claim["lease_token"], payload=payload,
                           provider=provider, prepared=prepared, invoked=invoked)


async def run(g, payload=None):
    with fenced_job(g.job, g.token):
        if g.kind == "goals":
            return await metrika_goal_work.execute(g.factory, payload or g.payload)
        return await backfill_work.execute(payload or g.payload)


@pytest.mark.asyncio
async def test_valid_authoritative_scope_reaches_only_selected_integration(source_job):
    g = source_job
    await run(g)
    if g.kind == "goals":
        assert g.prepared == [True]
    else:
        g.provider.assert_awaited_once()
        assert g.invoked == [g.payload]


@pytest.mark.asyncio
@pytest.mark.parametrize("change", ["owner", "project", "same_owner_project", "pause", "disconnect", "delete", "tenant", "resource", "kind", "legacy_payload"])
async def test_changed_queued_scope_is_rejected_before_preparation_or_provider(source_job, change):
    g = source_job
    with g.factory.begin() as db:
        if change == "owner":
            db.get(models.Client, g.clients[0]).owner_id = g.owners[1]
        elif change in {"project", "same_owner_project"}:
            if change == "same_owner_project":
                db.get(models.Client, g.clients[1]).owner_id = g.owners[0]
            db.get(models.Integration, g.integration).client_id = g.clients[1]
        elif change == "pause":
            db.get(models.Client, g.clients[0]).status = models.ClientStatus.PAUSED
        elif change == "disconnect":
            db.get(models.Integration, g.integration).connection_status = "revoked"
        elif change == "delete":
            db.delete(db.get(models.Integration, g.integration))
        elif change == "legacy_payload":
            g.payload.pop("owner_id")
            db.execute(jobs.update().where(jobs.c.id == g.job).values(payload=g.payload))
        else:
            value = str(g.owners[1]) if change == "tenant" else "other-scope"
            db.execute(jobs.update().where(jobs.c.id == g.job).values(**{change: value}))
    with pytest.raises(IntegrationScopeChanged):
        await run(g)
    assert not g.prepared
    g.provider.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("field", ["owner_id", "client_id", "integration_id", "date_from"])
async def test_arguments_cannot_expand_authoritative_queued_payload(source_job, field):
    g = source_job
    altered = {**g.payload, field: "2020-01-01" if field == "date_from" else str(uuid.uuid4())}
    with pytest.raises(IntegrationScopeChanged):
        await run(g, altered)
    assert not g.prepared
    g.provider.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("invalid", ["expired", "token", "state", "missing"])
async def test_invalid_execution_does_not_start_external_work(source_job, invalid):
    g = source_job
    with g.factory.begin() as db:
        if invalid == "missing":
            db.execute(jobs.delete().where(jobs.c.id == g.job))
        else:
            patch = {"lease_until": sa.func.clock_timestamp() - sa.text("interval '1 second'")} if invalid == "expired" else (
                {"lease_token": uuid.uuid4()} if invalid == "token" else {"state": "failed"})
            db.execute(jobs.update().where(jobs.c.id == g.job).values(**patch))
    with pytest.raises(LeaseLost):
        await run(g)
    assert not g.prepared
    g.provider.assert_not_awaited()


@pytest.mark.asyncio
async def test_handler_cannot_be_called_without_execution_lease(source_job):
    g = source_job
    with pytest.raises(LeaseLost):
        if g.kind == "goals":
            await metrika_goal_work.execute(g.factory, g.payload)
        else:
            await backfill_work.execute(g.payload)
    assert not g.prepared
    g.provider.assert_not_awaited()


def test_goal_enqueue_binds_owner_project_and_never_persists_credentials(source_job, monkeypatch):
    g = source_job
    monkeypatch.setattr(durable_sync, "SessionLocal", g.factory)
    with g.factory.begin() as db:
        db.get(models.Integration, g.integration).access_token = "never-queue-this-secret"
    durable_sync.enqueue_goals(g.integration, "2026-09-01", "2026-09-02")
    with g.factory() as db:
        entry = db.execute(sa.select(jobs).where(jobs.c.id != g.job)).mappings().one()
        assert entry["tenant"] == entry["payload"]["owner_id"] == str(g.owners[0])
        assert entry["payload"]["client_id"] == str(g.clients[0])
        assert "never-queue-this-secret" not in str(entry["payload"])


def test_startup_rejects_unbound_legacy_work_without_rebinding_current_owner(source_job):
    from automation.work_preflight import check_integration_bindings
    g = source_job
    with g.factory.begin() as db:
        check_integration_bindings(db)
        legacy = {k: v for k, v in g.payload.items() if k != "owner_id"}
        db.execute(jobs.update().where(jobs.c.id == g.job).values(payload=legacy))
        with pytest.raises(RuntimeError, match="Unbound legacy"):
            check_integration_bindings(db)
        assert db.scalar(sa.select(jobs.c.payload).where(jobs.c.id == g.job)) == legacy
        db.execute(jobs.update().where(jobs.c.id == g.job).values(state="failed"))
        check_integration_bindings(db)  # Terminal evidence may be retained.
