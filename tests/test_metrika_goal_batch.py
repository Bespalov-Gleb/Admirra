from datetime import date
from types import SimpleNamespace
from unittest.mock import AsyncMock
import uuid

import pytest
from sqlalchemy import create_engine, event, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from automation.metrika_goal_batch import collect_goal_rows, latest_goal_names, replace_goal_window
from automation.sync import _sync_metrika_goals_for_direct
from core import models

DAYS = [date(2026, 9, 9), date(2026, 9, 10)]


class InlineQueue:
    async def enqueue(self, kind, fn, *args, **kwargs):
        assert kind == "metrica"
        return await fn(*args, **kwargs)


def api_with_counts(counts):
    async def stats(counter, start, end, **kwargs):
        count = counts[counter]
        if isinstance(count, Exception):
            raise count
        return [{"dimensions": [{"name": start}], "metrics": [count]}]
    return SimpleNamespace(
        get_counter_goals=AsyncMock(return_value=[{"id": "1", "name": "Заявка"}]),
        get_goals_stats=stats,
    )


@pytest.mark.asyncio
async def test_multiple_counters_accumulate_without_duplicate_rows():
    rows, missing = await collect_goal_rows(api_with_counts({"a": 3, "b": 4}), InlineQueue(),
                                            ["a", "a", "b"], ["1"], DAYS, {})
    assert missing == []
    assert len(rows) == 4
    values = {(row["date"], row["goal_id"]): row["conversion_count"] for row in rows}
    assert values == {(DAYS[0], "1"): 7, (DAYS[0], "all"): 7,
                      (DAYS[1], "1"): 0, (DAYS[1], "all"): 0}


@pytest.mark.asyncio
async def test_failure_on_second_counter_never_returns_partial_result():
    with pytest.raises(RuntimeError, match="provider unavailable"):
        await collect_goal_rows(api_with_counts({"a": 3, "b": RuntimeError("provider unavailable")}),
                                InlineQueue(), ["a", "b"], ["1"], DAYS, {})


@pytest.mark.asyncio
@pytest.mark.parametrize("metrics", [[], [-1], [2.4], [None], [True], [1, 2]])
async def test_invalid_counts_are_not_silently_zero_filled(metrics):
    api = api_with_counts({"a": 1})
    api.get_goals_stats = AsyncMock(return_value=[{"dimensions": [{"name": DAYS[0].isoformat()}], "metrics": metrics}])
    with pytest.raises((ValueError, TypeError)):
        await collect_goal_rows(api, InlineQueue(), ["a"], ["1"], DAYS, {})


@pytest.mark.asyncio
async def test_empty_success_response_is_legitimate_zero():
    api = api_with_counts({"a": 1})
    api.get_goals_stats = AsyncMock(return_value=[])
    rows, _ = await collect_goal_rows(api, InlineQueue(), ["a"], ["1"], DAYS, {})
    assert len(rows) == 4
    assert all(row["conversion_count"] == 0 for row in rows)


@pytest.mark.asyncio
async def test_all_goals_is_explicit_and_empty_selection_stays_empty():
    api = api_with_counts({"a": 7})
    rows, missing = await collect_goal_rows(api, InlineQueue(), ["a"], None, DAYS, {})
    assert not missing
    assert next(row for row in rows if row["date"] == DAYS[0] and row["goal_id"] == "all") == {
        "date": DAYS[0], "goal_id": "all", "goal_name": "All Goals", "conversion_count": 7}
    api.get_goals_stats = AsyncMock()
    rows, _ = await collect_goal_rows(api, InlineQueue(), ["a"], [], DAYS, {})
    api.get_goals_stats.assert_not_awaited()
    assert len(rows) == 2 and all(row["conversion_count"] == 0 for row in rows)


@pytest.mark.asyncio
@pytest.mark.parametrize("metadata", [None, {}, [None], [{}], [{"id": None}], [{"id": True}],
    [{"id": 0}], [{"id": "1 OR 1"}], [{"id": "١"}], [{"id": "1", "name": []}], [{"id": 1}, {"id": "1"}]])
async def test_malformed_metadata_does_not_become_empty_goals(metadata):
    api = api_with_counts({"a": 1})
    api.get_counter_goals = AsyncMock(return_value=metadata)
    with pytest.raises(ValueError):
        await collect_goal_rows(api, InlineQueue(), ["a"], None, DAYS, {})


@pytest.mark.asyncio
async def test_goal_on_second_counter_is_not_reported_missing():
    api = api_with_counts({"b": 1})
    api.get_counter_goals = AsyncMock(side_effect=[[], [{"id": "1", "name": "Заявка"}]])
    _, missing = await collect_goal_rows(api, InlineQueue(), ["a", "b"], ["1", "2"], DAYS, {})
    assert missing == ["2"]


@pytest.fixture
def goal_db():
    # SQLite suffices for SQL semantics here; PostgreSQL tests use the same
    # fixture below when an explicitly isolated DB is requested.
    import os
    url = os.getenv("ISOLATED_POSTGRES_URL")
    if url:
        from urllib.parse import urlsplit
        assert os.getenv("WW_TEST") == "1" and urlsplit(url).hostname == "test-db"
    engine = create_engine(url or "sqlite:///:memory:")
    conn = engine.connect()
    id_type = "BIGSERIAL" if url else "INTEGER"
    uuid_type = "UUID" if url else "VARCHAR(32)"
    conn.execute(text(f"""CREATE TEMP TABLE metrika_goals (
        id {id_type} PRIMARY KEY, integration_id {uuid_type}, client_id {uuid_type},
        date DATE NOT NULL, goal_id VARCHAR NOT NULL, goal_name VARCHAR,
        conversion_count INTEGER CHECK (conversion_count >= 0)
    )"""))
    conn.commit()
    db = sessionmaker(bind=conn, autoflush=False)()
    integration = SimpleNamespace(id=uuid.uuid4(), client_id=uuid.uuid4(), selected_goals='["1"]',
                                  primary_goal_id=None, selected_counters='["a","b"]',
                                  sync_status=models.IntegrationSyncStatus.SUCCESS)
    db.bulk_insert_mappings(models.MetrikaGoals, [{"id": 100, "integration_id": integration.id,
        "client_id": integration.client_id, "date": DAYS[0], "goal_id": "1",
        "goal_name": "Прежняя цель", "conversion_count": 34}])
    db.commit()
    try:
        yield db, integration
    finally:
        db.close()
        conn.close()
        engine.dispose()


def no_notification(*_):
    pass


def test_write_failure_preserves_old_rows_even_after_outer_commit(goal_db):
    db, integration = goal_db
    invalid = [{"date": DAYS[0], "goal_id": "1", "goal_name": "New", "conversion_count": -1}]
    with pytest.raises(IntegrityError):
        replace_goal_window(db, integration, DAYS, invalid, [], {}, no_notification)
    db.commit()
    assert db.query(models.MetrikaGoals.conversion_count).scalar() == 34


def test_notification_failure_rolls_back_replacement(goal_db):
    db, integration = goal_db
    def fail(*_):
        raise RuntimeError("notification failed")
    valid = [{"date": DAYS[0], "goal_id": "1", "goal_name": "New", "conversion_count": 65}]
    with pytest.raises(RuntimeError):
        replace_goal_window(db, integration, DAYS, valid, [], {}, fail)
    db.commit()
    assert db.query(models.MetrikaGoals.conversion_count).scalar() == 34


@pytest.mark.asyncio
async def test_api_failure_preserves_existing_rows_in_real_sync_entrypoint(goal_db, monkeypatch):
    db, integration = goal_db
    monkeypatch.setattr("automation.yandex_metrica.YandexMetricaAPI", lambda *args, **kwargs: api_with_counts(
        {"a": 10, "b": RuntimeError("upstream failed")}))
    monkeypatch.setattr("automation.request_queue.get_request_queue", AsyncMock(return_value=InlineQueue()))
    with pytest.raises(RuntimeError, match="upstream failed"):
        await _sync_metrika_goals_for_direct(db, integration, DAYS[0].isoformat(), DAYS[-1].isoformat(), "dummy")
    # Mimic caller swallowing failure and committing another channel's work.
    db.commit()
    assert db.query(models.MetrikaGoals.conversion_count).scalar() == 34


def test_latest_name_selected_once_and_bulk_write_has_no_per_row_select(goal_db):
    db, integration = goal_db
    queries = []
    def record(conn, cursor, statement, *args):
        queries.append(statement)
    event.listen(db.bind, "before_cursor_execute", record)
    assert latest_goal_names(db, integration.id, ["1"]) == {"1": "Прежняя цель"}
    rows = [{"date": day, "goal_id": str(goal), "goal_name": "New", "conversion_count": 2}
            for day in DAYS for goal in range(30)]
    replace_goal_window(db, integration, DAYS, rows, [], {}, no_notification)
    db.commit()
    event.remove(db.bind, "before_cursor_execute", record)
    assert sum(statement.lstrip().upper().startswith("SELECT") for statement in queries) == 1
    assert db.query(models.MetrikaGoals).count() == 60
    # Repeat delivery of the same window must not double its values.
    replace_goal_window(db, integration, DAYS, rows, [], {}, no_notification)
    db.commit()
    assert db.query(models.MetrikaGoals).count() == 60


@pytest.fixture
def standalone(goal_db, monkeypatch):
    from datetime import datetime
    from automation import sync
    db, integration = goal_db
    integration.platform = models.IntegrationPlatform.YANDEX_METRIKA
    integration.access_token = "test-only"
    integration.account_id = "123"
    integration.agency_client_login = None
    integration.client = SimpleNamespace(status=models.ClientStatus.ACTIVE, owner_id=None)
    integration.last_sync_at = datetime(2026, 8, 1)
    monkeypatch.setattr(sync.security, "decrypt_token", lambda _: "test-only")
    monkeypatch.setattr(sync, "_notify_missing_metrika_goals", no_notification)
    monkeypatch.setattr(sync, "_run_detector_after_sync", lambda *_: False)
    monkeypatch.setattr("backend_api.services.project_settings.update_actual_start_date", lambda *_: None)
    monkeypatch.setattr("backend_api.cache_service.CacheService.invalidate_client", lambda *_: None)
    monkeypatch.setattr("automation.request_queue.get_request_queue", AsyncMock(return_value=InlineQueue()))
    return db, integration


@pytest.mark.asyncio
@pytest.mark.parametrize("failure", ["metadata", "late_batch", "bad_metrics", "bad_date", "duplicate_date"])
async def test_standalone_keeps_old_window_even_if_caller_commits_failure(standalone, monkeypatch, failure):
    import json
    from automation import sync
    db, integration = standalone
    integration.selected_goals = json.dumps([str(i) for i in range(1, 22)])
    previous_sync = integration.last_sync_at
    calls = 0

    async def stats(counter, start, end, **kwargs):
        nonlocal calls
        calls += 1
        # Old data must still exist even during the *second* provider batch.
        assert db.query(models.MetrikaGoals.conversion_count).scalar() == 34
        if failure == "late_batch" and calls == 2:
            raise TimeoutError("synthetic timeout")
        metrics = [2] * len(kwargs["metrics"].split(","))
        if failure == "bad_metrics":
            metrics = []
        row = {"dimensions": [{"name": "bad" if failure == "bad_date" else DAYS[0].isoformat()}], "metrics": metrics}
        return [row, row] if failure == "duplicate_date" else [row]

    api = SimpleNamespace(get_counter_goals=AsyncMock(return_value=None if failure == "metadata" else [
        {"id": i, "name": str(i)} for i in range(1, 22)]), get_goals_stats=stats)
    monkeypatch.setattr(sync, "YandexMetricaAPI", lambda *args, **kwargs: api)
    with pytest.raises((ValueError, TimeoutError)):
        await sync.sync_integration(db, integration, DAYS[0].isoformat(), DAYS[-1].isoformat())
    db.commit()
    assert db.query(models.MetrikaGoals.conversion_count).scalar() == 34
    assert integration.last_sync_at == previous_sync
    assert integration.sync_status == models.IntegrationSyncStatus.FAILED
    if failure == "late_batch":
        assert calls == 2


@pytest.mark.asyncio
@pytest.mark.parametrize("select_all,empty", [(False, False), (True, False), (False, True)])
async def test_standalone_replaces_complete_window_without_doubling(standalone, monkeypatch, select_all, empty):
    from automation import sync
    db, integration = standalone
    integration.selected_goals = None if select_all else '["1"]'
    api = SimpleNamespace(get_counter_goals=AsyncMock(return_value=[{"id": 1, "name": "Заявка"}]),
        get_goals_stats=AsyncMock(return_value=[] if empty else [
            {"dimensions": [{"name": DAYS[0].isoformat()}], "metrics": [7]}]))
    monkeypatch.setattr(sync, "YandexMetricaAPI", lambda *args, **kwargs: api)
    for _ in range(2):
        await sync.sync_integration(db, integration, DAYS[0].isoformat(), DAYS[-1].isoformat())
        db.commit()
        rows = db.query(models.MetrikaGoals).filter(models.MetrikaGoals.date == DAYS[0]).all()
        assert len(rows) == 2
        assert {row.goal_id: row.conversion_count for row in rows} == {"all": 0 if empty else 7, "1": 0 if empty else 7}
        assert next(row.goal_name for row in rows if row.goal_id == "all") == ("All Goals" if select_all else "Selected Goals")
        assert integration.sync_status == models.IntegrationSyncStatus.SUCCESS
