from datetime import date, datetime, timedelta, timezone
import importlib.util
from pathlib import Path
import uuid

import pytest
import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations

from core import models
from core import sync_coverage as coverage
from core.job_fence import fenced_job, LeaseLost
from tests.test_durable_work import pg, expire
from tests.test_metrika_goal_work import goals, DAY, run as run_goals, counts
from tests.test_ads_sync_work import advertising, run as run_ads

NOW = datetime(2026, 9, 22, 12, tzinfo=timezone.utc)
START, END = date(2026, 9, 1), date(2026, 9, 30)


def write(g, start=START, end=END, *, stage="metrika_goals", complete=True, observed=NOW):
    with fenced_job(g.job, g.token), g.factory.begin() as db:
        client = db.scalar(sa.select(models.Client).where(models.Client.id == g.client).with_for_update())
        integration = db.scalar(sa.select(models.Integration).where(models.Integration.id == g.id).with_for_update())
        coverage.replace_window(db, integration, client, stage, start, end, observed, complete=complete)


def read(g, start=START, end=END, *, stages=("metrika_goals",), since=NOW, owner=None):
    with g.factory.begin() as db:
        owner = owner or db.get(models.Client, g.client).owner_id
        return coverage.assess(db, integration_id=g.id, client_id=g.client, owner_id=owner,
                               stages=stages, start=start, end=end, not_before=since)


def windows(g):
    with g.factory() as db:
        return db.execute(sa.select(models.SyncCoverage.date_from, models.SyncCoverage.date_to)
                          .order_by(models.SyncCoverage.date_from)).all()


def test_fail_closed_without_coverage_or_freshness(goals):
    g = goals
    assert read(g).reason == "missing_or_stale"  # integration already SUCCESS
    write(g)
    assert read(g).ready
    assert not read(g, since=NOW + timedelta(seconds=1)).ready
    assert read(g, stages=("campaigns", "metrika_goals")).missing_stages == ("campaigns",)
    with pytest.raises(ValueError):
        read(g, since=NOW.replace(tzinfo=None))
    with pytest.raises(ValueError):
        read(g, stages=())


def test_interval_union_holes_and_replay(goals):
    g = goals
    write(g, END, END)
    write(g, START, END - timedelta(days=2))
    assert not read(g).ready
    write(g, END - timedelta(days=1), END - timedelta(days=1))
    assert read(g).ready
    write(g)
    write(g)
    assert windows(g) == [(START, END)]


def test_overlap_settings_switch_cannot_resurrect_old_evidence(goals):
    g = goals
    write(g)
    with g.factory.begin() as db:
        db.get(models.Integration, g.id).selected_goals = '["2"]'
    assert not read(g).ready
    write(g, DAY, DAY)
    assert read(g, DAY, DAY).ready
    assert not read(g).ready
    with g.factory.begin() as db:
        db.get(models.Integration, g.id).selected_goals = '["1"]'
    assert not read(g, DAY, DAY).ready
    assert read(g, START, DAY - timedelta(days=1)).ready
    assert read(g, DAY + timedelta(days=1), END).ready
    assert len(windows(g)) == 3


@pytest.mark.parametrize("start,end", [(START, DAY), (DAY, END), (START, END), (DAY, DAY)])
def test_incomplete_replacement_invalidates_only_replaced_dates(goals, start, end):
    g = goals
    write(g)
    write(g, start, end, complete=False)
    assert not read(g, start, end).ready
    if start > START:
        assert read(g, START, start - timedelta(days=1)).ready
    if end < END:
        assert read(g, end + timedelta(days=1), END).ready


def test_credentials_rotation_not_semantic_but_binding_is(goals):
    g = goals
    write(g)
    with g.factory.begin() as db:
        integration = db.get(models.Integration, g.id)
        integration.access_token = "new-synthetic"
        integration.refresh_token = "rotated-synthetic"
    assert read(g).ready
    with g.factory.begin() as db:
        db.get(models.Integration, g.id).account_id = "different-cabinet"
    assert not read(g).ready


def test_scope_and_pause_never_reuse_evidence(goals):
    g = goals
    write(g)
    assert read(g, owner=uuid.uuid4()).reason == "scope_unavailable"
    with g.factory.begin() as db:
        db.get(models.Client, g.client).status = models.ClientStatus.PAUSED
    assert read(g).reason == "scope_unavailable"


def test_fence_and_atomic_rollback(goals):
    g = goals
    with g.factory.begin() as db, pytest.raises(LeaseLost):
        coverage.replace_window(db, db.get(models.Integration, g.id), db.get(models.Client, g.client),
                                "campaigns", START, END, NOW)
    expire(g.factory, g.job)
    with pytest.raises(LeaseLost):
        write(g)
    assert windows(g) == []


def test_reader_reloads_identity_map_after_scope_changes(goals):
    g = goals
    write(g)
    with g.factory.begin() as db:
        client = db.get(models.Client, g.client)
        integration = db.get(models.Integration, g.id)
        with g.factory.begin() as other:
            other.get(models.Integration, g.id).account_id = "different-account"
        assert integration.account_id == "personal-login"
        result = coverage.assess(db, integration_id=g.id, client_id=g.client, owner_id=client.owner_id,
            stages=("metrika_goals",), start=START, end=END, not_before=NOW)
        assert not result.ready


@pytest.mark.asyncio
async def test_lost_lease_rolls_back_facts_and_coverage_together(goals):
    g = goals
    original = g.api.get_goals_stats
    async def expired(*args, **kwargs):
        expire(g.factory, g.job)
        return await original(*args, **kwargs)
    g.api.get_goals_stats = expired
    with pytest.raises(LeaseLost):
        await run_goals(g)
    assert counts(g) == {"1": 34}
    assert windows(g) == []


def test_bounded_fail_closed_reader(goals, monkeypatch):
    g = goals
    write(g, START, START)
    write(g, END, END)
    monkeypatch.setattr(coverage, "MAX_WINDOWS", 1)
    assert read(g).reason == "fragmentation_limit"


@pytest.mark.asyncio
async def test_goals_record_actual_lookback_window_and_confirmed_zero(goals):
    g = goals
    async def empty(*args, **kwargs): return []
    g.api.get_goals_stats = empty
    before = datetime.now(timezone.utc)
    assert await run_goals(g) == "updated"
    assert counts(g)["all"] == 0
    assert read(g, DAY - timedelta(days=30), DAY, since=before).ready
    assert not read(g, DAY - timedelta(days=31), DAY, since=before).ready
    with g.factory() as db:
        row = db.scalar(sa.select(models.SyncCoverage))
        assert row.execution_id == g.job
        assert row.observed_at <= row.recorded_at


@pytest.mark.asyncio
async def test_failed_collection_does_not_advance_evidence(goals):
    g = goals
    await run_goals(g)
    original = windows(g)
    before = datetime.now(timezone.utc)
    async def failed(*args, **kwargs): raise RuntimeError("synthetic provider failure")
    g.api.get_goals_stats = failed
    with pytest.raises(RuntimeError):
        await run_goals(g)
    assert windows(g) == original
    assert not read(g, DAY, DAY, since=before).ready
    assert counts(g)["1"] == 7


@pytest.mark.asyncio
async def test_missing_goal_invalidates_previously_complete_evidence(goals):
    g = goals
    await run_goals(g)
    assert windows(g)
    async def empty(*args, **kwargs): return []
    g.api.get_counter_goals = empty
    await run_goals(g)
    assert windows(g) == []


@pytest.mark.asyncio
async def test_each_advertising_source_records_required_stages(advertising):
    g = advertising
    before = datetime.now(timezone.utc)
    await run_ads(g)
    stages = {models.IntegrationPlatform.YANDEX_DIRECT: ("campaigns", "groups", "keywords"),
              models.IntegrationPlatform.VK_ADS: ("campaigns",),
              models.IntegrationPlatform.AVITO_ADS: ("campaigns", "groups", "creatives")}[g.platform]
    assert read(g, DAY, DAY, stages=stages, since=before).ready
    assert not read(g, DAY, DAY, since=before).ready  # no Metrika goals selected


def test_migration_matches_orm_and_is_reversible(goals):
    g = goals
    spec = importlib.util.spec_from_file_location("coverage_migration", Path(__file__).resolve().parents[1] /
                                               "alembic/versions/f02b3c4d5e6f_sync_coverage.py")
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    with g.engine.begin() as connection:
        models.SyncCoverage.__table__.drop(connection)
        with Operations.context(MigrationContext.configure(connection)):
            migration.upgrade()
            inspector = sa.inspect(connection)
            assert {c["name"] for c in inspector.get_columns("sync_coverage")} == set(models.SyncCoverage.__table__.columns.keys())
            assert {c["name"] for c in inspector.get_indexes("sync_coverage")} == {"ix_sync_coverage_window"}
            migration.downgrade()
            assert not sa.inspect(connection).has_table("sync_coverage")
