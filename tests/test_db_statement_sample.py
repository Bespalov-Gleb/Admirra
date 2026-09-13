from copy import deepcopy
import json
from unittest.mock import Mock

import pytest
import sqlalchemy as sa

from ops import db_statement_sample as sampler
from tests.test_durable_work import pg


def row(queryid=1, calls=100, ms=1000, *, role=10, top=True):
    return {"queryid": queryid, "db_role_oid": role, "toplevel": top,
        **dict.fromkeys(sampler.COUNTERS, 0), "calls": calls, "total_exec_time": ms}


def snap(rows, at=1):
    return dict(identity="same-cluster-db", server_start="start", server_version="150018",
        extension_version="1.10", reset="reset", dealloc=0, observed_at=str(at),
        monotonic_at=at, collection_seconds=0.01, rows=rows)


def test_interval_delta_not_lifetime_mean_or_nested_double_count():
    first = snap([row(), row(2, top=False), row(role=11)])
    last = snap([row(calls=104, ms=1200), row(2, calls=104, ms=1100, top=False),
        row(role=11, calls=101, ms=1300), row(3, calls=2, ms=40)], at=11)
    delta = sampler.difference(first, last)
    assert delta["completed_top_level_calls"] == 7
    assert delta["completed_sql_calls_per_second"] == 0.7
    assert delta["top_level_exec_ms"] == 540
    assert delta["nested_entries"] == 1
    assert [r["mean_exec_ms"] for r in delta["top"]] == [300, 50, 20]
    assert delta["top"][-1]["new_entry"]


@pytest.mark.parametrize("field,value", [("identity", "other"), ("server_start", "new-start"),
    ("server_version", "160000"), ("extension_version", "1.11"), ("reset", "new-reset"), ("dealloc", 1)])
def test_incompatible_snapshots_refused(field, value):
    first = snap([row()])
    last = snap([row(calls=102)], at=11)
    last[field] = value
    with pytest.raises(sampler.SampleUnavailable):
        sampler.difference(first, last)


@pytest.mark.parametrize("rows", [[], [row(calls=1)], [row(ms=1)], [row(queryid=None)],
    [row(), row()], [row(calls=100, ms=1100)]])
def test_missing_decreasing_hidden_or_inconsistent_entries_refused(rows):
    with pytest.raises(sampler.SampleUnavailable):
        sampler.difference(snap([row()]), snap(rows, at=11))


@pytest.mark.parametrize("value", [True, float("nan"), float("inf"), -1, "100", None])
def test_invalid_counter_refused(value):
    invalid = row()
    invalid["calls"] = value
    with pytest.raises(sampler.SampleUnavailable):
        sampler.difference(snap([row()]), snap([invalid], at=11))


@pytest.mark.parametrize("value", [0, -1, True, 31, "15"])
def test_unbounded_or_invalid_wait_refused(value):
    with pytest.raises(sampler.SampleUnavailable):
        sampler.sample(None, value)


def test_top_is_bounded_but_totals_cover_all_entries():
    delta = sampler.difference(snap([]), snap([row(i, calls=1, ms=1) for i in range(50)], at=11))
    assert len(delta["top"]) == 20
    assert delta["completed_top_level_calls"] == 50
    assert delta["changed_statement_entries"] == 50


def test_snapshot_size_guard(monkeypatch):
    monkeypatch.setattr(sampler, "MAX_ENTRIES", 1)
    with pytest.raises(sampler.SampleUnavailable):
        sampler.difference(snap([]), snap([row(1), row(2)], at=11))


def test_zero_activity_is_valid_not_fabricated_workload():
    first = snap([row()])
    last = snap(deepcopy(first["rows"]), at=11)
    assert sampler.difference(first, last)["completed_top_level_calls"] == 0


@pytest.fixture
def statistics(pg):
    _, engine = pg
    with engine.begin() as db:
        schema = db.scalar(sa.text("SELECT current_schema()"))
        quoted = engine.dialect.identifier_preparer.quote_schema(schema)
        db.execute(sa.text(f"CREATE EXTENSION pg_stat_statements WITH SCHEMA {quoted}"))
    return engine


def test_real_extension_no_sql_held_while_waiting_or_business_text_exposed(statistics):
    engine = statistics
    def wait(_):
        assert engine.pool.checkedout() == 0
        with engine.connect() as db:
            db.execute(sa.text("SELECT 'private-diagnostic-test-value'::text, generate_series(1, 2)"))
    result = sampler.sample(engine, sleep=wait)
    assert result["sample_valid"] and result["completed_top_level_calls"] > 0
    assert not result["query_text_included"] and not result["load_accepted"]
    assert "private-diagnostic-test-value" not in json.dumps(result)
    assert engine.pool.checkedout() == 0
    with engine.connect() as db:
        assert db.scalar(sa.text("SHOW transaction_read_only")) == "off"


def test_real_reset_is_detected_without_sampler_mutation(statistics):
    engine = statistics
    def test_reset(_):
        assert engine.pool.checkedout() == 0
        with engine.begin() as db:
            schema = db.scalar(sa.text("SELECT current_schema()"))
            db.execute(sa.text(f"SELECT {engine.dialect.identifier_preparer.quote_schema(schema)}.pg_stat_statements_reset()"))
    with pytest.raises(sampler.SampleUnavailable):
        sampler.sample(engine, sleep=test_reset)


def test_missing_extension_returns_no_partial_success(pg):
    _, engine = pg
    with pytest.raises(sampler.SampleUnavailable):
        sampler.capture(engine)
    assert engine.pool.checkedout() == 0


def test_cli_driver_errors_do_not_leak_secrets(monkeypatch, capsys):
    monkeypatch.setattr("sys.argv", ["sampler"])
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:secret-placeholder@db/test")
    engine = Mock()
    monkeypatch.setattr(sampler.sa, "create_engine", Mock(return_value=engine))
    monkeypatch.setattr(sampler, "sample", Mock(side_effect=RuntimeError("secret-placeholder")))
    with pytest.raises(SystemExit) as error:
        sampler.main()
    assert "secret-placeholder" not in str(error.value)
    assert not capsys.readouterr().out
    engine.dispose.assert_called_once()
