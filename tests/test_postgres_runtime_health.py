"""Real PostgreSQL probes, never against a production database."""
import os
from urllib.parse import urlsplit

import pytest
from sqlalchemy import create_engine, text


@pytest.fixture
def pg_health(monkeypatch):
    url = os.getenv("ISOLATED_POSTGRES_URL")
    if not url:
        pytest.skip("requires ops/compose.isolated.yml")
    assert os.getenv("WW_TEST") == "1" and urlsplit(url).hostname == "test-db"
    from backend_api import runtime_health
    engine = create_engine(url, pool_size=1, max_overflow=0)
    with engine.begin() as conn:
        conn.execute(text("CREATE TEMP TABLE alembic_version (version_num VARCHAR PRIMARY KEY)"))
        conn.execute(text("INSERT INTO alembic_version VALUES ('isolated-revision')"))
    monkeypatch.setattr(runtime_health, "engine", engine)
    monkeypatch.setenv("APP_PROCESS_ROLE", "api")
    monkeypatch.setenv("EXPECTED_SCHEMA_REVISION", "isolated-revision")
    try:
        yield runtime_health, engine
    finally:
        engine.dispose()


def test_postgres_readiness_leaves_no_open_transaction_or_session_settings(pg_health):
    health, engine = pg_health
    for _ in range(3):
        assert health.ready()["status"] == "ok"
        assert engine.pool.checkedout() == 0
    with engine.connect() as conn:
        assert conn.execute(text("SHOW statement_timeout")).scalar() == "0"
        assert conn.execute(text("SHOW lock_timeout")).scalar() == "0"


def test_postgres_schema_mismatch_and_recovery(pg_health, monkeypatch):
    health, engine = pg_health
    monkeypatch.setenv("EXPECTED_SCHEMA_REVISION", "future-revision")
    assert health.ready().status_code == 503
    assert engine.pool.checkedout() == 0
    monkeypatch.setenv("EXPECTED_SCHEMA_REVISION", "isolated-revision")
    assert health.ready()["status"] == "ok"
