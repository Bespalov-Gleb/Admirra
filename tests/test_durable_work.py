"""Failure-path tests on real, isolated PostgreSQL (not SQLite approximations)."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
import importlib
import os
import uuid
from urllib.parse import urlsplit

import pytest
import sqlalchemy as sa
from sqlalchemy.orm import sessionmaker

from automation import work_ledger as ledger
from automation.work_tables import metadata, jobs, outbox, schedule_cursor
from core.job_fence import LeaseLost, fenced_job


@pytest.fixture
def pg():
    url = os.getenv("ISOLATED_POSTGRES_URL")
    if not url:
        pytest.skip("requires ops/compose.isolated.yml")
    assert os.getenv("WW_TEST") == "1" and urlsplit(url).hostname == "test-db"
    schema = "work_" + uuid.uuid4().hex
    admin = sa.create_engine(url)
    with admin.begin() as db:
        db.execute(sa.text(f'CREATE SCHEMA "{schema}"'))
    engine = sa.create_engine(url, connect_args={"options": f"-csearch_path={schema} -cstatement_timeout=5000"})
    metadata.create_all(engine)
    with engine.begin() as db:
        db.execute(sa.text("CREATE TABLE effects (id integer PRIMARY KEY)"))
    try:
        yield sessionmaker(bind=engine), engine
    finally:
        engine.dispose()
        with admin.begin() as db:
            db.execute(sa.text(f'DROP SCHEMA "{schema}" CASCADE'))
        admin.dispose()


def submit(factory, key="one", resource=None, tenant="client", safe=True, queue="sync.manual", attempts=3):
    with factory.begin() as db:
        return ledger.submit(db, kind="goals", queue=queue, key=key, resource=resource or key,
                             tenant=tenant, payload={}, replay_safe=safe, max_attempts=attempts)


def claim(factory, job):
    with factory.begin() as db:
        return ledger.claim(db, job)


def expire(factory, job):
    with factory.begin() as db:
        db.execute(jobs.update().where(jobs.c.id == job).values(lease_until=sa.func.now() - sa.text("interval '1 second'")))


def ready(factory, job):
    with factory.begin() as db:
        db.execute(jobs.update().where(jobs.c.id == job).values(available_at=sa.func.now()))


def test_atomic_outbox_rollback(pg):
    factory, _ = pg
    with factory() as db:
        ledger.submit(db, kind="goals", queue="sync.manual", key="one", resource="cabinet", tenant="client", payload={})
        db.rollback()
    with factory() as db:
        assert db.scalar(sa.select(sa.func.count()).select_from(jobs)) == 0
        assert db.scalar(sa.select(sa.func.count()).select_from(outbox)) == 0


def test_concurrent_submission_and_claim_are_unique(pg):
    factory, _ = pg
    with ThreadPoolExecutor(6) as pool:
        ids = list(pool.map(lambda _: submit(factory), range(6)))
        claims = list(pool.map(lambda _: claim(factory, ids[0]), range(6)))
    assert len(set(ids)) == 1
    assert sum(item is not None for item in claims) == 1


def test_resource_and_client_caps_global_across_workers(pg, monkeypatch):
    factory, _ = pg
    monkeypatch.setenv("SYNC_GLOBAL_CONCURRENCY", "3")
    monkeypatch.setenv("SYNC_TENANT_CONCURRENCY", "2")
    first = submit(factory, "first", resource="cabinet")
    same = submit(factory, "goals", resource="cabinet")
    second = submit(factory, "second")
    third = submit(factory, "third")
    other = submit(factory, "other", tenant="other")
    fourth = submit(factory, "fourth", tenant="third")
    assert claim(factory, first)
    assert claim(factory, same) is None
    assert claim(factory, second)
    assert claim(factory, third) is None
    assert claim(factory, other)
    assert claim(factory, fourth) is None


def test_publisher_crash_after_send_then_redis_loss(pg):
    factory, _ = pg
    job = submit(factory)
    sent = []
    def accepted_then_lost(*args):
        sent.append(args)
        raise RuntimeError("Synthetic lost broker response")
    with pytest.raises(RuntimeError):
        ledger.publish_pending(factory, accepted_then_lost)
    assert ledger.publish_pending(factory, lambda *args: sent.append(args)) == 0
    # Committed reservation expires after a publisher crash; outbox survives.
    with factory.begin() as db:
        db.execute(outbox.update().values(next_publish_at=sa.func.now()))
    assert ledger.publish_pending(factory, lambda *args: sent.append(args)) == 1
    assert sent == [(str(job), "sync.manual")] * 2
    # Even if Redis loses both messages, the committed job will be republished.
    with factory.begin() as db:
        db.execute(outbox.update().values(next_publish_at=sa.func.now()))
    assert ledger.publish_pending(factory, lambda *args: sent.append(args)) == 1
    execution = claim(factory, job)
    assert claim(factory, job) is None
    with factory.begin() as db:
        assert ledger.finish(db, job, execution["lease_token"])
    assert claim(factory, job) is None
    with factory() as db:
        assert db.scalar(sa.select(sa.func.count()).select_from(outbox)) == 0


@pytest.mark.parametrize("safe,attempts,expected", [(True, 3, "queued"), (True, 1, "failed"), (False, 3, "uncertain")])
def test_crash_recovery_policy(pg, safe, attempts, expected):
    factory, _ = pg
    job = submit(factory, safe=safe, attempts=attempts)
    old = claim(factory, job)
    expire(factory, job)
    with factory.begin() as db:
        assert not ledger.heartbeat(db, job, old["lease_token"])
        assert ledger.recover_expired(db) == 1
        assert db.scalar(sa.select(jobs.c.state)) == expected
        assert not ledger.finish(db, job, old["lease_token"])


def test_fencing_rejects_old_worker_even_after_context_exit(pg):
    factory, _ = pg
    job = submit(factory)
    old = claim(factory, job)
    with factory() as stale:
        with fenced_job(job, old["lease_token"]):
            stale.execute(sa.text("INSERT INTO effects VALUES (1)"))
        expire(factory, job)
        with factory.begin() as db:
            ledger.recover_expired(db)
        ready(factory, job)
        fresh = claim(factory, job)
        assert fresh["lease_token"] != old["lease_token"]
        with pytest.raises(LeaseLost):
            stale.commit()
        stale.rollback()
    with fenced_job(job, fresh["lease_token"]):
        with factory.begin() as db:
            db.execute(sa.text("INSERT INTO effects VALUES (2)"))
    with factory.begin() as db:
        db.execute(sa.text("INSERT INTO effects VALUES (3)"))  # ordinary API not fenced
        assert db.execute(sa.text("SELECT id FROM effects ORDER BY id")).scalars().all() == [2, 3]


@pytest.mark.parametrize("failure", ["timeout", "lost_worker"])
def test_uncertain_resource_blocks_new_occurrence_but_not_other_tenant(pg, failure):
    factory, _ = pg
    previous = submit(factory, "yesterday", resource="delivery:one", safe=False, queue="reports")
    execution = claim(factory, previous)
    if failure == "lost_worker":
        expire(factory, previous)
        with factory.begin() as db:
            ledger.recover_expired(db)
    else:
        with factory.begin() as db:
            ledger.finish(db, previous, execution["lease_token"], error=TimeoutError("unknown outcome"))
    next_job = submit(factory, "today", resource="delivery:one", safe=False, queue="reports")
    unrelated = submit(factory, "other", resource="delivery:two", tenant="other", safe=False, queue="reports")
    assert claim(factory, next_job) is None
    assert claim(factory, unrelated)
    with factory() as db:
        assert db.scalar(sa.select(jobs.c.state).where(jobs.c.id == previous)) == "uncertain"
        assert db.scalar(sa.select(jobs.c.attempt).where(jobs.c.id == next_job)) == 0
    # Simulate an operator-confirmed terminal outcome, not an automatic retry.
    with factory.begin() as db:
        db.execute(jobs.update().where(jobs.c.id == previous).values(state="succeeded"))
    assert claim(factory, next_job)


def test_live_heartbeat_and_wrong_token(pg):
    factory, _ = pg
    job = submit(factory)
    execution = claim(factory, job)
    with factory.begin() as db:
        assert ledger.heartbeat(db, job, execution["lease_token"])
        assert not ledger.heartbeat(db, job, uuid.uuid4())
        assert ledger.recover_expired(db) == 0


def test_savepoint_release_does_not_block_heartbeat_but_outer_commit_is_fenced(pg):
    factory, _ = pg
    job = submit(factory)
    execution = claim(factory, job)
    with factory() as session:
        with fenced_job(job, execution["lease_token"]):
            session.execute(sa.text("INSERT INTO effects VALUES (1)"))
            with session.begin_nested():
                session.execute(sa.text("INSERT INTO effects VALUES (2)"))
            # Another thread/process must be able to renew while the outer
            # transaction performs slow I/O after finishing its savepoint.
            with ThreadPoolExecutor(1) as pool:
                def renew():
                    with factory.begin() as other:
                        return ledger.heartbeat(other, job, execution["lease_token"])
                assert pool.submit(renew).result(timeout=3)
                pool.submit(expire, factory, job).result(timeout=3)
            with pytest.raises(LeaseLost):
                session.commit()
            session.rollback()
    with factory() as db:
        assert db.scalar(sa.text("SELECT count(*) FROM effects")) == 0


def test_scheduler_deduplicates_and_bounds_catchup(pg):
    from automation.work_control import schedule_due
    factory, _ = pg
    now = datetime(2026, 9, 11, 0, 0, tzinfo=timezone.utc)  # 03:00 MSK
    with factory.begin() as db:
        assert schedule_due(db, now=now) == 3
        assert schedule_due(db, now=now) == 0
        assert schedule_due(db, now=now - timedelta(minutes=1)) == 0
    with factory.begin() as db:
        schedule_due(db, now=now + timedelta(days=3))
        nightly = db.execute(sa.select(jobs).where(jobs.c.kind == "nightly.enqueue")).all()
        assert len(nightly) == 2  # old days are not replayed in bulk
        recent_reports = db.execute(sa.select(jobs).where(jobs.c.kind == "reports.rules")).all()
        assert len(recent_reports) == 17  # original minute + last 15 minutes inclusive


def test_ai_prewarm_requires_explicit_capacity_flag(monkeypatch):
    from automation.work_control import occurrences

    now = datetime(2026, 9, 11, 2, 0, tzinfo=timezone.utc)  # 05:00 MSK
    monkeypatch.delenv("AI_PREWARM_ENABLED", raising=False)
    kinds = [kind for kind, *_ in occurrences(now, now)]
    assert "reports.export" in kinds and "billing.maintenance" in kinds
    assert "ai.prewarm" not in kinds

    monkeypatch.setenv("AI_PREWARM_ENABLED", "true")
    assert "ai.prewarm" in [kind for kind, *_ in occurrences(now, now)]


def test_executor_duplicate_and_external_failure(pg, monkeypatch):
    from automation import work_executor
    factory, engine = pg
    monkeypatch.setattr(work_executor, "engine", engine)
    job = submit(factory, safe=False)
    calls = []
    def failing(kind, payload):
        calls.append(kind)
        raise TimeoutError("unknown external outcome")
    assert work_executor.execute_job(job, handler=failing) == "finished"
    assert work_executor.execute_job(job, handler=failing) == "not_claimed"
    assert calls == ["goals"]
    with factory() as db:
        assert db.scalar(sa.select(jobs.c.state)) == "uncertain"


def test_migration_ddl_and_safe_downgrade(pg):
    from alembic.migration import MigrationContext
    from alembic.operations import Operations
    factory, engine = pg
    metadata.drop_all(engine)
    from pathlib import Path
    spec = importlib.util.spec_from_file_location("durable_migration", Path(__file__).resolve().parents[1] / "alembic/versions/dd4e5f6a7b8c_durable_background_jobs.py")
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    with engine.begin() as connection:
        with Operations.context(MigrationContext.configure(connection)):
            migration.upgrade()
    job = submit(factory)
    with engine.begin() as connection:
        with Operations.context(MigrationContext.configure(connection)):
            with pytest.raises(RuntimeError):
                migration.downgrade()
    with factory.begin() as db:
        db.execute(jobs.update().values(state="succeeded"))
    with engine.begin() as connection:
        with Operations.context(MigrationContext.configure(connection)):
            migration.downgrade()
        assert not sa.inspect(connection).has_table("background_jobs")


def test_retention_never_deletes_uncertain_or_active_work(pg):
    factory, _ = pg
    for state in ("queued", "running", "uncertain", "failed", "succeeded"):
        job = submit(factory, state)
        with factory.begin() as db:
            db.execute(jobs.update().where(jobs.c.id == job).values(state=state,
                       finished_at=sa.func.now() - sa.text("interval '31 days'")))
    with factory.begin() as db:
        assert ledger.prune_completed(db) == 2
        assert set(db.execute(sa.select(jobs.c.state)).scalars()) == {"queued", "running", "uncertain"}


def test_worker_preflight_rejects_wrong_schema_and_orphaned_legacy_queue(pg, monkeypatch):
    from automation.work_preflight import check
    from core import database
    factory, engine = pg
    monkeypatch.setattr(database, "engine", engine)
    monkeypatch.setenv("WW_TEST", "0")  # Exercise production validation on synthetic DB.
    monkeypatch.setenv("APP_RELEASE", "test-release")
    monkeypatch.setenv("EXPECTED_SCHEMA_REVISION", "expected")
    with engine.begin() as db:
        db.execute(sa.text("CREATE TABLE alembic_version (version_num varchar PRIMARY KEY)"))
        db.execute(sa.text("INSERT INTO alembic_version VALUES ('old')"))
        db.execute(sa.text("CREATE TABLE sync_jobs (id uuid PRIMARY KEY, status varchar)"))
    with pytest.raises(RuntimeError, match="schema"):
        check()
    legacy_id = uuid.uuid4()
    with engine.begin() as db:
        db.execute(sa.text("UPDATE alembic_version SET version_num = 'expected'"))
        db.execute(sa.text("INSERT INTO sync_jobs VALUES (:id, 'QUEUED')"), {"id": legacy_id})
    with pytest.raises(RuntimeError, match="Legacy"):
        check()
    with factory.begin() as db:
        ledger.submit(db, kind="sync", queue="sync.manual", key="new", resource="new", tenant="client",
                      payload={"sync_job_id": str(legacy_id)}, replay_safe=True)
    check()
