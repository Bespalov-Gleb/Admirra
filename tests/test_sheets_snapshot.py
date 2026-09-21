from datetime import date, datetime, timezone
from decimal import Decimal
import json
from unittest.mock import Mock

import pytest
import sqlalchemy as sa

from automation import sheets_snapshot as snapshot, calendar_work, reports
from automation.google_sheets import GoogleSheetsService
from core import models
from tests.test_durable_work import pg
from tests.test_calendar_work import scopes


def seed(scopes, count=1):
    factory, owners, project = scopes
    with factory.begin() as db:
        foreign = models.Client(owner_id=owners[1], name="Other", status=models.ClientStatus.ACTIVE)
        db.add(foreign)
        db.flush()
        for model in (models.YandexStats, models.VKStats, models.AvitoStats):
            db.add(model(client_id=foreign.id, date=date(2026, 9, 1), campaign_name="MUST NOT EXPORT", cost=999))
            db.add_all([model(client_id=project, date=date(2026, 9, 1), campaign_name=f"Кампания {i:04}",
                              impressions=100 + i, clicks=10, cost=Decimal("123.45"), conversions=2)
                        for i in range(count)])
        db.add(models.WeeklyReport(client_id=project, week_start=date(2026, 8, 31), week_end=date(2026, 9, 6),
                                    total_cost=42, total_clicks=7, total_conversions=1, avg_cpc=6, avg_cpa=42))
        db.add(models.MonthlyReport(client_id=project, year=2026, month=9, total_cost=42))
        db.add(models.MetrikaGoals(client_id=project, date=date(2026, 9, 1), goal_id="goal-1", goal_name="Заявка",
                                   conversion_count=3))
    return project


def test_streamed_snapshot_preserves_full_legacy_output_and_tenant_scope(scopes):
    factory, _, _ = scopes
    project = seed(scopes, count=300)
    with factory() as db:
        legacy = {"Raw Data": GoogleSheetsService.raw_rows(project, db),
                  "Weekly Reports": GoogleSheetsService.weekly_rows(project, db),
                  "Monthly Report": GoogleSheetsService.monthly_rows(project, db),
                  "Goals": GoogleSheetsService.goal_rows(project, db)}
    observed = []
    def before_cursor(conn, cursor, statement, parameters, context, many):
        if statement.lstrip().upper().startswith("SELECT"):
            observed.append(context.execution_options.get("yield_per"))
    engine = factory.kw["bind"]
    sa.event.listen(engine, "before_cursor_execute", before_cursor)
    try:
        with factory() as db:
            actual = snapshot.prepare_snapshot(project, db)
            assert len(db.identity_map) == 0  # Only scalar columns, no full ORM history.
        assert actual == legacy
        assert len(actual["Raw Data"]) == 901
        assert observed == [snapshot.FETCH_ROWS] * 6
        assert "MUST NOT EXPORT" not in json.dumps(actual)
    finally:
        sa.event.remove(engine, "before_cursor_execute", before_cursor)
    assert engine.pool.checkedout() == 0


def test_row_limit_is_shared_across_channels_reports_and_goals(scopes):
    factory, _, _ = scopes
    project = seed(scopes)
    with factory() as db:
        complete = snapshot.prepare_snapshot(project, db, limits=snapshot.SnapshotLimits(max_rows=6))
        assert sum(len(rows) - 1 for rows in complete.values()) == 6
        with pytest.raises(snapshot.ExportSnapshotLimitExceeded):
            snapshot.prepare_snapshot(project, db, limits=snapshot.SnapshotLimits(max_rows=5))
        assert db.scalar(sa.select(sa.func.count()).select_from(models.YandexStats)) == 2


def test_byte_budget_counts_escaped_text_and_never_returns_a_prefix(scopes):
    factory, _, _ = scopes
    project = seed(scopes)
    with factory() as db:
        complete = snapshot.prepare_snapshot(project, db)
        actual_bytes = len(json.dumps(complete).encode())
        assert snapshot.prepare_snapshot(project, db, limits=snapshot.SnapshotLimits(max_bytes=actual_bytes + 100)) == complete
        with pytest.raises(snapshot.ExportSnapshotLimitExceeded):
            snapshot.prepare_snapshot(project, db, limits=snapshot.SnapshotLimits(max_bytes=actual_bytes - 1))


@pytest.mark.parametrize("table,field", [
    (models.YandexStats, "campaign_name"), (models.VKStats, "campaign_name"),
    (models.AvitoStats, "campaign_name"), (models.MetrikaGoals, "goal_name"),
    (models.MetrikaGoals, "goal_id"),
])
def test_oversized_cell_is_rejected_instead_of_truncated(scopes, table, field):
    factory, _, _ = scopes
    project = seed(scopes)
    with factory.begin() as db:
        record = db.query(table).filter_by(client_id=project).first()
        setattr(record, field, "x" * (snapshot.MAX_CELL_CHARS + 1))
    with factory() as db:
        with pytest.raises(snapshot.ExportSnapshotLimitExceeded):
            snapshot.prepare_snapshot(project, db)


@pytest.mark.parametrize("row_limit", [1, 2])
def test_cursor_closes_even_when_consumer_exceeds_budget(row_limit):
    class Result:
        closed = False
        def __iter__(self):
            yield (date(2026, 9, 1), "a", 1, 1, 1, 1, False)
            yield (date(2026, 9, 1), "b", 1, 1, 1, 1, False)
        def close(self):
            self.closed = True
    db = Mock()
    result = Result()
    db.execute.return_value = result
    with pytest.raises(snapshot.ExportSnapshotLimitExceeded):
        snapshot.prepare_snapshot("synthetic", db, limits=snapshot.SnapshotLimits(max_rows=row_limit))
    assert result.closed


def test_limit_failure_happens_before_sdk_construction_or_sheet_clear(scopes, monkeypatch):
    factory, owners, project = scopes
    seed(scopes)
    with factory.begin() as db:
        db.get(models.Client, project).spreadsheet_id = "s" * 24
    monkeypatch.setenv("SHEETS_SNAPSHOT_MAX_ROWS", "2")
    monkeypatch.setattr(reports, "generate_weekly_report", lambda *_: None)
    monkeypatch.setattr(reports, "generate_monthly_report", lambda *_: None)
    sdk = Mock(side_effect=AssertionError("No Google IO before snapshot is complete"))
    with pytest.raises(snapshot.ExportSnapshotLimitExceeded):
        calendar_work.export_project(factory, {"client_id": str(project), "owner_id": str(owners[0]),
                                     "scheduled_at": datetime.now(timezone.utc).isoformat()}, service_factory=sdk)
    sdk.assert_not_called()
    assert factory.kw["bind"].pool.checkedout() == 0


def test_empty_history_keeps_all_headers(scopes):
    factory, _, project = scopes
    with factory() as db:
        prepared = snapshot.prepare_snapshot(project, db)
        assert len(prepared) == 4 and all(len(rows) == 1 for rows in prepared.values())
        with pytest.raises(snapshot.ExportSnapshotLimitExceeded):
            snapshot.prepare_snapshot(project, db, limits=snapshot.SnapshotLimits(max_bytes=1))


@pytest.mark.parametrize("key,value", [("max_rows", 0), ("max_rows", 200001), ("max_rows", True),
                                       ("max_bytes", 0), ("max_bytes", 32 * 1024 * 1024 + 1)])
def test_invalid_limits_fail_closed(key, value):
    with pytest.raises(ValueError):
        snapshot.SnapshotLimits(**{key: value})


def test_configured_limits_cannot_disable_bound(monkeypatch):
    monkeypatch.setenv("SHEETS_SNAPSHOT_MAX_ROWS", "-1")
    with pytest.raises(ValueError):
        snapshot.SnapshotLimits.configured()


def test_budget_stops_consuming_a_large_source_and_closes_it(monkeypatch):
    seen = {"rows": 0, "closed": False}
    def history(*_):
        try:
            for i in range(1_000_000):
                seen["rows"] += 1
                yield ["2026-09-01", "Yandex Direct", str(i), 0, 0, 0, 0]
        finally:
            seen["closed"] = True
    monkeypatch.setattr(snapshot, "_raw", history)
    with pytest.raises(snapshot.ExportSnapshotLimitExceeded):
        snapshot.prepare_snapshot("synthetic", Mock(), limits=snapshot.SnapshotLimits(max_rows=1000))
    assert seen == {"rows": 1001, "closed": True}


def test_huge_text_does_not_reach_python_from_stream_query(scopes):
    factory, _, project = scopes
    with factory.begin() as db:
        db.add(models.YandexStats(client_id=project, date=date(2026, 9, 1), campaign_name="x" * 100_000))
    with factory() as db:
        value, marker = snapshot._text(models.YandexStats.campaign_name)
        assert db.execute(sa.select(value, marker).where(models.YandexStats.client_id == project)).one() == (None, True)
        assert db.scalar(sa.select(sa.func.length(models.YandexStats.campaign_name))) == 100_000


def test_limit_rejection_is_failed_not_success_or_unknown_external_delivery(scopes, monkeypatch):
    from automation import work_executor, work_ledger
    from automation.work_tables import jobs
    factory, owners, project = scopes
    seed(scopes)
    with factory.begin() as db:
        db.get(models.Client, project).spreadsheet_id = "s" * 24
        job_id = work_ledger.submit(db, kind="reports.project", queue="reports", key="over-limit",
                                   resource=f"export:{project}", tenant=owners[0], replay_safe=False,
                                   payload={"client_id": str(project), "owner_id": str(owners[0]),
                                            "scheduled_at": datetime.now(timezone.utc).isoformat()})
    monkeypatch.setenv("SHEETS_SNAPSHOT_MAX_ROWS", "2")
    monkeypatch.setattr(work_executor, "engine", factory.kw["bind"])
    monkeypatch.setattr(reports, "generate_weekly_report", lambda *_: None)
    monkeypatch.setattr(reports, "generate_monthly_report", lambda *_: None)
    sdk = Mock(side_effect=AssertionError("No Google IO permitted"))
    def handler(kind, payload):
        return calendar_work.export_project(factory, payload, service_factory=sdk)
    assert work_executor.execute_job(job_id, handler=handler) == "finished"
    with factory() as db:
        assert db.scalar(sa.select(jobs.c.state).where(jobs.c.id == job_id)) == "failed"
        assert db.scalar(sa.select(jobs.c.error_type).where(jobs.c.id == job_id)) == "ExportSnapshotLimitExceeded"
    assert work_executor.execute_job(job_id, handler=handler) == "not_claimed"
    sdk.assert_not_called()


def test_sheet_timeout_after_first_external_write_stays_uncertain(scopes, monkeypatch):
    from automation import work_executor, work_ledger
    from automation.work_tables import jobs
    factory, owners, project = scopes
    seed(scopes)
    with factory.begin() as db:
        db.get(models.Client, project).spreadsheet_id = "s" * 24
        job_id = work_ledger.submit(db, kind="reports.project", queue="reports", key="partial-write",
                                   resource=f"export:{project}", tenant=owners[0], replay_safe=False,
                                   payload={"client_id": str(project), "owner_id": str(owners[0]),
                                            "scheduled_at": datetime.now(timezone.utc).isoformat()})
    monkeypatch.setattr(work_executor, "engine", factory.kw["bind"])
    monkeypatch.setattr(reports, "generate_weekly_report", lambda *_: None)
    monkeypatch.setattr(reports, "generate_monthly_report", lambda *_: None)
    writes = []
    class Service:
        configured = True
        def write_snapshot(self, spreadsheet, prepared):
            assert factory.kw["bind"].pool.checkedout() == 0
            writes.append("first sheet accepted")
            raise TimeoutError("synthetic unknown second sheet acceptance")
    def handler(kind, payload):
        return calendar_work.export_project(factory, payload, service_factory=Service)
    assert work_executor.execute_job(job_id, handler=handler) == "finished"
    with factory() as db:
        assert db.scalar(sa.select(jobs.c.state).where(jobs.c.id == job_id)) == "uncertain"
    assert work_executor.execute_job(job_id, handler=handler) == "not_claimed"
    assert writes == ["first sheet accepted"]
