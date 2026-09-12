"""Real PG connections: parent preflight disposal and child pool separation."""
import multiprocessing
import os

import pytest
import sqlalchemy as sa

from automation import work_preflight
from core import database
from tests.test_durable_work import pg


def test_parent_does_not_keep_preflight_database_connections(pg, monkeypatch):
    _, engine = pg
    monkeypatch.setattr(database, "engine", engine)
    def preflight():
        with engine.begin() as db:
            assert db.scalar(sa.text("SELECT 1")) == 1
    monkeypatch.setattr(work_preflight, "check", preflight)
    work_preflight.prepare_worker_parent()
    assert engine.pool.checkedin() == 0 and engine.pool.checkedout() == 0
    with engine.connect() as db:
        assert db.scalar(sa.text("SELECT 2")) == 2  # engine remains usable by children


def test_parent_refuses_fork_with_unfinished_session(pg, monkeypatch):
    _, engine = pg
    monkeypatch.setattr(database, "engine", engine)
    monkeypatch.setattr(work_preflight, "check", lambda: None)
    with engine.connect() as held:
        held.execute(sa.text("SELECT 1"))
        with pytest.raises(RuntimeError, match="checked-out"):
            work_preflight.prepare_worker_parent()


def test_child_reset_does_not_reuse_or_close_parent_connection(pg, monkeypatch):
    from automation.celery_app import reset_connections_after_fork
    _, engine = pg
    monkeypatch.setattr(database, "engine", engine)
    with engine.connect() as db:
        parent_backend = db.scalar(sa.text("SELECT pg_backend_pid()"))
    context = multiprocessing.get_context("fork")
    receive, send = context.Pipe(duplex=False)
    def child():
        receive.close()
        reset_connections_after_fork()
        with engine.connect() as db:
            send.send((db.scalar(sa.text("SELECT pg_backend_pid()")), os.getenv("ADMIRRA_WORKER_CHILD")))
        send.close()
        engine.dispose()
    process = context.Process(target=child)
    process.start()
    send.close()
    try:
        assert receive.poll(5), "Child did not open its isolated SQL connection"
        child_backend, marker = receive.recv()
        process.join(timeout=5)
        assert process.exitcode == 0 and marker == "1"
        assert child_backend != parent_backend
        with engine.connect() as db:
            assert db.scalar(sa.text("SELECT pg_backend_pid()")) == parent_backend
    finally:
        if process.is_alive():
            process.kill()
            process.join(timeout=5)
        receive.close()
