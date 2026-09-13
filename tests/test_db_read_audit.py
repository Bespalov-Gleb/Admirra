import json
from unittest.mock import Mock

import pytest
import sqlalchemy as sa

from ops import db_read_audit as audit
from tests.test_durable_work import pg


def test_catalog_audit_is_read_only_bounded_and_contains_no_business_rows(pg):
    _, engine = pg
    with engine.begin() as db:
        schema = db.scalar(sa.text("SELECT current_schema()"))
        db.execute(sa.text("CREATE TABLE metrika_goals (id integer PRIMARY KEY, private_payload text)"))
        db.execute(sa.text("INSERT INTO metrika_goals VALUES (1, 'must-never-appear-in-diagnostics')"))
    result = audit.collect(engine, schema=schema)
    serialized = json.dumps(result, default=str)
    assert "must-never-appear-in-diagnostics" not in serialized
    assert "private_payload" not in serialized
    assert result["database"][0]["transaction_read_only"] == "on"
    assert result["database"][0]["statement_timeout"] == "3s"
    assert result["database"][0]["lock_timeout"] == "1s"
    assert result["load_accepted"] is False
    assert any(row["table_name"] == "metrika_goals" for row in result["tables"])
    assert any(row["unique_index"] for row in result["indexes"])
    assert len(result["tables"]) <= 32 and len(result["indexes"]) <= 256
    assert engine.pool.checkedout() == 0
    with engine.begin() as db:
        assert db.scalar(sa.text("SHOW transaction_read_only")) == "off"
        assert db.scalar(sa.text("SELECT private_payload FROM metrika_goals")) == "must-never-appear-in-diagnostics"


def test_accidental_write_query_is_refused_by_postgres(pg, monkeypatch):
    _, engine = pg
    monkeypatch.setattr(audit, "QUERIES", {"forbidden": "CREATE TABLE unsafe_audit_write (id integer)"})
    with pytest.raises(sa.exc.DBAPIError):
        audit.collect(engine)
    assert engine.pool.checkedout() == 0
    with engine.connect() as db:
        assert db.scalar(sa.text("SELECT to_regclass('unsafe_audit_write')")) is None


def test_schema_is_a_bound_value_not_sql(pg):
    _, engine = pg
    result = audit.collect(engine, schema="'; DROP TABLE background_jobs; --")
    assert not result["tables"] and not result["indexes"]
    with engine.connect() as db:
        assert db.scalar(sa.text("SELECT to_regclass('background_jobs')")) is not None


def test_cli_never_prints_driver_secrets(monkeypatch, capsys):
    engine = Mock()
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:secret-placeholder@db/test")
    monkeypatch.setattr(audit.sa, "create_engine", Mock(return_value=engine))
    monkeypatch.setattr(audit, "collect", Mock(side_effect=RuntimeError("secret-placeholder")))
    with pytest.raises(SystemExit) as error:
        audit.main()
    assert "secret-placeholder" not in str(error.value)
    assert "secret-placeholder" not in capsys.readouterr().out
    engine.dispose.assert_called_once()
