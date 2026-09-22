from datetime import date, datetime, timedelta, timezone
import uuid

import pytest
import sqlalchemy as sa
from fastapi import HTTPException

from automation import report_refresh
from automation.integration_work_scope import require_scope, IntegrationScopeChanged
from automation.work_tables import jobs
from backend_api.reports import freshness, route_ledger
from backend_api.reports.router import refresh_report_delivery_data
from core import models
from core.job_fence import fenced_job
from tests.test_durable_work import pg, claim
from tests.test_metrika_goal_work import goals, DAY
from tests.test_report_freshness import report, build
from tests.test_sync_coverage import write


def refresh_rows(g):
    with g.factory() as db:
        return list(db.execute(sa.select(jobs).where(jobs.c.kind == "history.backfill")).mappings())


def test_interval_gaps_are_clipped_and_unioned():
    first, last = date(2026, 1, 1), date(2026, 1, 31)
    assert report_refresh.gaps(first, last, []) == [(first, last)]
    assert report_refresh.gaps(first, last, [(first - timedelta(days=5), last)]) == []
    assert report_refresh.gaps(first, last, [(first, first), (first + timedelta(days=3), last)]) == [
        (first + timedelta(days=1), first + timedelta(days=2))]


@pytest.mark.asyncio
async def test_refresh_deduplicates_polls_and_uses_low_priority_scope(report):
    g = report
    await build(g, wait=True)
    await build(g, wait=True)
    rows = refresh_rows(g)
    assert len(rows) == 1
    row = rows[0]
    assert row["queue"] == "sync.backfill" and row["replay_safe"]
    assert row["resource"] == f"integration:{g.id}" and row["tenant"] == str(g.owner)
    assert row["payload"]["date_from"] == str(DAY - timedelta(days=1))
    assert row["payload"]["date_to"] == str(DAY)
    assert row["payload"]["report_refresh"]["viewer_id"] == str(g.owner)


@pytest.mark.asyncio
async def test_only_uncovered_dates_are_requested(report):
    g = report
    for stage in ("campaigns", "metrika_goals"):
        write(g, DAY, DAY, stage=stage, observed=datetime.now(timezone.utc))
    await build(g, wait=True)
    rows = refresh_rows(g)
    assert len(rows) == 1
    assert rows[0]["payload"]["date_from"] == rows[0]["payload"]["date_to"] == str(DAY - timedelta(days=1))


@pytest.mark.asyncio
async def test_bounded_chunks_and_owner_pressure(report):
    g = report
    with g.factory.begin() as db:
        db.get(models.ReportDelivery, g.delivery).start_date = DAY - timedelta(days=89)
    await build(g, wait=True)
    rows = refresh_rows(g)
    assert len(rows) == 2
    for row in rows:
        p = row["payload"]
        assert (date.fromisoformat(p["date_to"]) - date.fromisoformat(p["date_from"])).days <= 29
    await build(g, wait=True)
    assert len(refresh_rows(g)) == 2


@pytest.mark.asyncio
async def test_global_cap_cannot_be_bypassed_by_repeated_polls(report, monkeypatch):
    g = report
    monkeypatch.setenv("REPORT_REFRESH_GLOBAL_JOBS", "1")
    with g.factory.begin() as db:
        db.get(models.ReportDelivery, g.delivery).start_date = DAY - timedelta(days=89)
    await build(g, wait=True)
    await build(g, wait=True)
    assert len(refresh_rows(g)) == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("change", [None, "cancel", "deadline", "settings", "epoch", "access", "disabled"])
async def test_refresh_revalidates_before_external_io(report, monkeypatch, change):
    g = report
    await build(g, wait=True)
    row = refresh_rows(g)[0]
    # Fixture's unrelated synthetic goals execution occupies the same integration.
    with g.factory.begin() as db:
        db.execute(jobs.update().where(jobs.c.id == g.job).values(state="succeeded", lease_until=None))
    execution = claim(g.factory, row["id"])
    assert execution
    with g.factory.begin() as db:
        d = db.get(models.ReportDelivery, g.delivery)
        if change == "cancel": d.status = "cancelled"
        if change == "deadline": d.data_readiness = {**d.data_readiness, "deadline": (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat()}
        if change == "settings": db.get(models.Integration, g.id).selected_goals = '["2"]'
        if change == "epoch": d.data_readiness = {**d.data_readiness, "request_epoch": str(uuid.uuid4())}
        if change == "access": db.get(models.User, g.owner).is_active = False
    if change == "disabled": monkeypatch.setenv("REPORT_FRESHNESS_GUARDS", "false")
    with fenced_job(row["id"], execution["lease_token"]), g.factory() as db:
        if change:
            with pytest.raises(IntegrationScopeChanged):
                require_scope(db, row["payload"], kind="history.backfill", integration_id=str(g.id))
        else:
            assert require_scope(db, row["payload"], kind="history.backfill", integration_id=str(g.id))[0].id == g.id


@pytest.mark.asyncio
async def test_expired_wait_explicit_retry_is_manual_and_changes_epoch(report):
    g = report
    route_ledger.metadata.create_all(g.engine)
    old, _ = await build(g, wait=True)
    with g.factory.begin() as db:
        d = db.get(models.ReportDelivery, g.delivery)
        d.source = "auto"
        d.data_readiness = {**d.data_readiness, "status": "held", "reason": "deadline_expired"}
    with g.factory() as db:
        response = await refresh_report_delivery_data(g.delivery, db.get(models.User, g.owner), db)
        assert response.source == "manual" and response.data_readiness["status"] == "waiting"
    with g.factory() as db:
        d = db.get(models.ReportDelivery, g.delivery)
        assert d.data_readiness["request_epoch"] != old["request_epoch"]
        assert d.data_readiness["previous_wait"]["request_epoch"] == old["request_epoch"]
    assert not g.sends


@pytest.mark.asyncio
async def test_retry_cannot_erase_unknown_send_history(report):
    g = report
    route_ledger.metadata.create_all(g.engine)
    await build(g, wait=True)
    with g.factory.begin() as db:
        d = db.get(models.ReportDelivery, g.delivery)
        d.data_readiness = {**d.data_readiness, "status": "held", "reason": "deadline_expired"}
        db.execute(route_ledger.routes.insert().values(delivery_id=d.id, route_key="x" * 64,
            channel="telegram", state="uncertain", token=uuid.uuid4()))
    with g.factory() as db, pytest.raises(HTTPException) as error:
        await refresh_report_delivery_data(g.delivery, db.get(models.User, g.owner), db)
    assert error.value.status_code == 409
