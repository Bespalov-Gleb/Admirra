"""Bounded synthetic storage/queue load, not an HTTP or dashboard benchmark."""
import asyncio
from concurrent.futures import ThreadPoolExecutor
import json
import math
import os
from threading import Lock
import time

import pytest
import sqlalchemy as sa

from core import models
from core.job_fence import fenced_job
from automation import work_ledger as ledger, lead_export_work as exports
from automation.work_tables import jobs, lead_exports
from lead_validator.services import project_intake as intake
from lead_validator.schemas import LeadInput, ValidationResult
from tests.test_durable_work import pg


@pytest.mark.parametrize('concurrency', [2, 8])
def test_bounded_storage_queue_load(pg, monkeypatch, concurrency):
    assert os.getenv('WW_TEST') == '1'
    factory, engine = pg
    models.Base.metadata.create_all(engine)
    monkeypatch.setenv('LEAD_DELIVERY_GUARDS', 'true')
    monkeypatch.setenv('DURABLE_TASKS', 'true')
    projects = []
    with factory.begin() as db:
        for i in range(4):
            owner = models.User(email=f'load-{i}@example.test', password_hash='synthetic')
            db.add(owner); db.flush()
            project = models.PhoneProject(owner_id=owner.id, name='Synthetic load', crm_webhook_url='https://crm.example.test/')
            db.add(project); db.flush()
            projects.append(project.id)
    count = 100
    def admit(i):
        timer = time.perf_counter()
        with factory() as db:
            lead = LeadInput(phone=f'+7900{i:07d}')
            ctx = intake.begin(db, projects[i % 4], lead, form_data=None, user_agent=None, referer=None, key=f'event-{i}')
            if isinstance(ctx, ValidationResult): return ctx, time.perf_counter() - timer
            assert not db.in_transaction()
            time.sleep(.025)  # Synthetic validation latency, no provider/network.
            result = ctx.finish(lead, True, 'passed', time.time(), None, {})
            return result, time.perf_counter() - timer
    timer = time.perf_counter()
    with ThreadPoolExecutor(concurrency) as pool:
        admitted = list(pool.map(admit, range(count)))
        replays = list(pool.map(admit, range(count)))
    admission_elapsed = time.perf_counter() - timer
    assert all(result.success for result, _ in admitted)
    assert [r.lead_id for r, _ in admitted] == [r.lead_id for r, _ in replays]
    with factory() as db:
        rows = db.execute(sa.select(jobs)).mappings().all()
        assert len(rows) == count
        assert db.scalar(sa.select(sa.func.count()).select_from(models.Lead)) == count
    calls = {}
    lock = Lock()
    async def send(snapshot):
        with lock:
            key = snapshot.body['lead_id']
            calls[key] = calls.get(key, 0) + 1
        await asyncio.sleep(.025)
        return True, None
    def dispatch(row):
        timer = time.perf_counter()
        with factory.begin() as db: job = ledger.claim(db, row['id'])
        assert job is not None
        with fenced_job(job['id'], job['lease_token']):
            assert asyncio.run(exports.execute(factory, job['payload'], sender=send))['accepted']
        with factory.begin() as db: assert ledger.finish(db, job['id'], job['lease_token'])
        return time.perf_counter() - timer
    timer = time.perf_counter()
    with ThreadPoolExecutor(concurrency) as pool:
        dispatch_times = list(pool.map(dispatch, rows))
    dispatch_elapsed = time.perf_counter() - timer
    assert len(calls) == count and set(calls.values()) == {1}
    with factory() as db:
        assert db.scalar(sa.select(sa.func.count()).select_from(jobs).where(jobs.c.state == 'succeeded')) == count
        assert db.scalar(sa.select(sa.func.count()).select_from(lead_exports).where(lead_exports.c.state == 'sent')) == count
    assert engine.pool.checkedout() == 0
    def percentile(values, q): return round(sorted(values)[math.ceil(len(values) * q) - 1] * 1000, 2)
    print(json.dumps(dict(benchmark='synthetic-lead-storage-queue', concurrency=concurrency,
        new_leads=count, replays=count, sends=count, duplicate_sends=0,
        admission_and_replay_seconds=round(admission_elapsed, 3), dispatch_seconds=round(dispatch_elapsed, 3),
        admission_p95_ms=percentile([elapsed for _, elapsed in admitted], .95),
        replay_p95_ms=percentile([elapsed for _, elapsed in replays], .95),
        dispatch_p95_ms=percentile(dispatch_times, .95)), sort_keys=True))
