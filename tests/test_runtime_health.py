import importlib

import pytest


class Result:
    def __init__(self, revisions):
        self.revisions = revisions

    def scalars(self):
        return self.revisions


class Connection:
    class dialect:
        name = "postgresql"

    def __init__(self, revisions=("test-revision",)):
        self.revisions = revisions
        self.queries = []

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def execute(self, statement):
        self.queries.append(str(statement))
        return Result(self.revisions)


@pytest.fixture
def health(monkeypatch):
    monkeypatch.setenv("APP_PROCESS_ROLE", "api")
    monkeypatch.setenv("APP_RELEASE", "test-release")
    monkeypatch.setenv("EXPECTED_SCHEMA_REVISION", "test-revision")
    return importlib.import_module("backend_api.runtime_health")


def test_live_does_not_connect_to_database(health, monkeypatch):
    def fail():
        raise AssertionError("Liveness must not connect")
    monkeypatch.setattr(health.engine, "connect", fail)
    assert health.live()["status"] == "ok"


def test_ready_checks_revision_with_local_timeouts(health, monkeypatch):
    conn = Connection()
    monkeypatch.setattr(health.engine, "connect", lambda: conn)
    assert health.ready()["release"] == "test-release"
    assert conn.queries == ["SET LOCAL statement_timeout = '2000ms'",
                            "SET LOCAL lock_timeout = '1000ms'", "SELECT 1",
                            "SELECT version_num FROM alembic_version"]


def test_ready_fails_on_schema_mismatch(health, monkeypatch):
    monkeypatch.setattr(health.engine, "connect", lambda: Connection(("wrong",)))
    assert health.ready().status_code == 503


def test_ready_does_not_leak_database_errors(health, monkeypatch):
    def fail():
        raise RuntimeError("connection string with a secret")
    monkeypatch.setattr(health.engine, "connect", fail)
    response = health.ready()
    assert response.status_code == 503
    assert b"secret" not in response.body


def test_api_requires_expected_schema(health, monkeypatch):
    monkeypatch.delenv("EXPECTED_SCHEMA_REVISION")
    assert health.ready().status_code == 503
