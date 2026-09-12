"""Real prefork process + Redis + PostgreSQL: kill a child during an open write."""
import os
import signal
import subprocess
import sys
import time
import uuid

import pytest
import sqlalchemy as sa
from redis import Redis

from tests.test_durable_work import pg
from tests.test_private_services import secured_redis
from automation import work_ledger as ledger
from automation.work_tables import jobs


def until(fn, seconds=30):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        value = fn()
        if value:
            return value
        time.sleep(.1)
    raise AssertionError("Isolated worker did not reach expected state")


@pytest.mark.parametrize("restricted", [False, True])
def test_real_child_crash_recovery_and_duplicate_delivery(pg, tmp_path, monkeypatch, secured_redis, restricted):
    factory, engine = pg
    admin_url = os.environ["ISOLATED_REDIS_URL"]
    redis_url = admin_url
    client = Redis.from_url(admin_url)
    marker = uuid.uuid4().hex
    prefix = "test-worker:" + marker + ":"
    if restricted:
        restricted_client, _ = secured_redis
        password = restricted_client("broker_worker").connection_pool.connection_kwargs["password"]
        redis_url = "redis://broker_worker:" + password + "@test-redis:6379/15"
        prefix = "admirra:task:"
    monkeypatch.setenv("CELERY_BROKER_URL", redis_url)
    monkeypatch.setenv("TASK_BROKER_PREFIX", prefix)
    from automation.celery_app import make_app
    app = make_app()
    with engine.connect() as db:
        schema = db.scalar(sa.text("SELECT current_schema()"))
    from sqlalchemy.engine import make_url
    url = make_url(os.environ["ISOLATED_POSTGRES_URL"]).update_query_dict({"options": f"-csearch_path={schema}"})
    env = {**os.environ, "APP_PROCESS_ROLE": "worker", "DURABLE_TASKS": "true",
           "DATABASE_URL": url.render_as_string(hide_password=False), "RATE_LIMIT_REDIS_URL": admin_url}
    log_path = tmp_path / "worker.log"
    with log_path.open("w") as log:
        args = [sys.executable, "-m", "automation.work_worker", "--concurrency=1",
                "--queues=maintenance", "--include=ops.celery_fixture", "--hostname=" + marker]
        if not restricted:
            args.extend(["--without-gossip", "--without-mingle"])
        proc = subprocess.Popen(args, env=env, stdout=log, stderr=log)
    try:
        def started():
            assert proc.poll() is None, log_path.read_text()
            return "ready." in log_path.read_text()
        until(started)
        with factory.begin() as db:
            job = ledger.submit(db, kind="test.probe", queue="maintenance", key=marker,
                                resource=marker, tenant="test", payload={"value": 7, "marker": marker, "delay": 20},
                                replay_safe=True)
        ledger.publish_pending(factory, lambda job_id, queue: app.send_task(
            "admirra.test_execute", args=[job_id], queue=queue, retry=False))
        def child_started():
            assert proc.poll() is None, log_path.read_text()
            return client.get(f"probe:{marker}")
        child_pid = int(until(child_started))
        os.kill(child_pid, signal.SIGKILL)
        # Broker redelivery sees the still-owned job and cannot duplicate it.
        def no_effect():
            with factory() as db:
                return db.scalar(sa.text("SELECT count(*) FROM effects")) == 0
        assert no_effect()
        with factory.begin() as db:
            db.execute(jobs.update().where(jobs.c.id == job).values(lease_until=sa.func.now() - sa.text("interval '1 second'")))
            assert ledger.recover_expired(db) == 1
            db.execute(jobs.update().where(jobs.c.id == job).values(available_at=sa.func.now(),
                       payload={"value": 7, "marker": marker, "delay": 0}))
        for _ in range(3):
            app.send_task("admirra.test_execute", args=[str(job)], queue="maintenance")
        def completed():
            with factory() as db:
                return db.scalar(sa.select(jobs.c.state).where(jobs.c.id == job)) == "succeeded"
        until(completed)
        with factory() as db:
            assert db.execute(sa.text("SELECT id FROM effects")).scalars().all() == [7]
            assert db.scalar(sa.select(jobs.c.attempt)) == 2
        assert "noperm" not in log_path.read_text().lower()
    except BaseException:
        print(log_path.read_text())  # Synthetic fixture: no production credentials.
        raise
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=5)
        app.close()
        client.delete(f"probe:{marker}")
        keys = list(client.scan_iter(prefix + "*"))
        if keys:
            client.delete(*keys)
        client.close()
