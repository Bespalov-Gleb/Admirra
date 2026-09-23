"""Bounded offline concurrency rehearsal, NOT a production capacity estimate.

Real PostgreSQL, production dashboard routes, durable sync apply and automatic
report receipts run together. Auth is fixture-scoped; vendor/LLM/render are
controlled slow stubs. HTTP uses ASGI TestClient, not two deployed API replicas.
No Celery/broker/cache/real provider acceptance is claimed by this test.
"""
import asyncio
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
import json
import math
import threading
import time

from fastapi import FastAPI, Header, HTTPException
from fastapi.testclient import TestClient
import sqlalchemy as sa
from sqlalchemy.orm import sessionmaker

from automation import ads_sync_work as ads, metrika_sync_work as sync, work_ledger as ledger
from automation.sync_request import request_params
from automation.work_tables import jobs
from backend_api import stats
from backend_api.reports import automatic_comment, scheduler
from core import models, security
from core.database import get_db
from core.job_fence import fenced_job
from tests.test_durable_work import pg

DAY = date(2026, 9, 10)


def test_dashboard_reads_during_sync_and_report_generation(pg, monkeypatch):
    factory, engine = pg
    models.Base.metadata.create_all(engine)
    with engine.connect() as db:
        schema = db.scalar(sa.text('SELECT current_schema()'))
    # Separate bounded pools for foreground, sync and report traffic.
    engines = [sa.create_engine(engine.url, pool_size=n, max_overflow=0, pool_timeout=5,
        connect_args={'options': f'-csearch_path={schema} -cstatement_timeout=5000 -clock_timeout=2000'})
        for n in (5, 2, 2)]
    read_factory, sync_factory, report_factory = [sessionmaker(bind=e) for e in engines]
    checked_out, peak = Counter(), Counter()
    lock = threading.Lock()
    for index, e in enumerate(engines):
        def checkout(connection, record, proxy, index=index):
            thread = threading.get_ident()
            record.info['load_thread'] = thread
            with lock:
                checked_out[(index, thread)] += 1
                peak[index] = max(peak[index], sum(v for (i, _), v in checked_out.items() if i == index))
        def checkin(connection, record, index=index):
            with lock:
                checked_out[(index, record.info.pop('load_thread'))] -= 1
        sa.event.listen(e, 'checkout', checkout)
        sa.event.listen(e, 'checkin', checkin)

    def no_io_transaction():
        with lock:
            assert all(v == 0 for (_, thread), v in checked_out.items() if thread == threading.get_ident())

    owners, projects, pending, deliveries = [], {}, [], []
    with factory.begin() as db:
        for tenant in range(2):
            user = models.User(email=f'mixed-{tenant}@example.test', password_hash='synthetic', email_verified=True)
            db.add(user); db.flush()
            owners.append(user.id)
            projects[user.id] = []
            for number in range(6):
                client = models.Client(owner_id=user.id, name=f'Synthetic {tenant}-{number}')
                db.add(client); db.flush()
                projects[user.id].append(client.id)
                integration = models.Integration(client_id=client.id, platform=models.IntegrationPlatform.VK_ADS,
                    access_token='synthetic', account_id='100', lead_action_types='["leadads"]',
                    sync_status=models.IntegrationSyncStatus.SUCCESS)
                db.add(integration); db.flush()
                campaign = models.Campaign(integration_id=integration.id, external_id='42', name='Synthetic',
                    is_active=True, vk_goal_action_id='leadads', vk_goal_action_name='Lead')
                db.add(campaign); db.flush()
                for day, multiplier in ((DAY, 1), (DAY - timedelta(days=1), 2)):
                    db.add(models.VKStats(client_id=client.id, campaign_id=campaign.id, campaign_name='Synthetic',
                        date=day, cost=100 * multiplier, conversions=4 * multiplier,
                        impressions=1000 * multiplier, clicks=100 * multiplier))
                params = request_params(integration, client, days=1, force_full=False,
                    trigger='auto' if number % 2 else 'manual', date_from=str(DAY), date_to=str(DAY))
                business = models.SyncJob(integration_id=integration.id, status=models.SyncJobStatus.QUEUED,
                    params=json.dumps(params))
                db.add(business); db.flush()
                payload = dict(sync_job_id=str(business.id), client_id=str(client.id), owner_id=str(user.id))
                job_id = ledger.submit(db, kind='sync', queue='sync.nightly' if number % 2 else 'sync.manual',
                    key=f'mixed:{client.id}', resource=f'integration:{integration.id}', tenant=str(user.id),
                    payload=payload, replay_safe=True)
                pending.append((job_id, payload))
                delivery = models.ReportDelivery(user_id=user.id, client_id=client.id, start_date=DAY,
                    end_date=DAY, source='auto', include_ai_comment=True, channels='[]',
                    snapshot_data={'summary': {'leads': 4}, 'top_campaigns': [],
                        '_scope_client_ids': [str(client.id)], 'start_date': str(DAY), 'end_date': str(DAY)},
                    data_readiness={'status': 'ready'})
                db.add(delivery); db.flush()
                deliveries.append((delivery.id, user.id))
    monkeypatch.setattr(security, 'decrypt_token', lambda value: value)
    monkeypatch.setattr('automation.sync._run_detector_after_sync', lambda *args: False)
    active, overlap, calls = Counter(), Counter(), Counter()
    io_started = threading.Event()
    async def slow(value, kind):
        no_io_transaction()
        with lock:
            active[kind] += 1
            calls[kind] += 1
        io_started.set()
        try:
            await asyncio.sleep(.1)
            return value
        finally:
            with lock:
                active[kind] -= 1
    class Vendor:
        async def get_campaigns(self, *args):
            return await slow([{'id': '42', 'name': 'Synthetic', 'goal_action_id': 'leadads'}], 'sync')
        async def get_statistics(self, *args, **kwargs):
            return await slow([dict(campaign_id='42', campaign_name='Synthetic', date=str(DAY),
                impressions=1500, clicks=150, cost=150, conversions=5)], 'sync')
        async def get_goal_actions_from_statistics(self, *args, **kwargs):
            return {'42': ('leadads', 'Lead')}
        async def get_balance(self, *args):
            return await slow({'balance': 1000, 'currency': 'RUB'}, 'sync')
    monkeypatch.setattr(ads, 'make_api', lambda plan: Vendor())
    async def model(snapshot):
        assert snapshot['summary']['leads'] == 4  # immutable before-sync report
        return await slow('Synthetic fixed snapshot', 'report')
    def render(snapshot):
        no_io_transaction()
        time.sleep(.05)
        snapshot.pdf_snapshot = b'synthetic-pdf'
        snapshot.png_snapshot = b'synthetic-png'
    monkeypatch.setattr('ai.report_generator.generate_delivery_comment', model)
    monkeypatch.setattr(scheduler, 'refresh_delivery_snapshot_files', render)

    app = FastAPI()
    app.include_router(stats.router, prefix='/api')
    def db_dependency():
        with read_factory() as db:
            yield db
    def user_dependency(x_test_owner: str = Header(...)):
        if x_test_owner not in {str(owner) for owner in owners}:
            raise HTTPException(401)
        with read_factory() as db:
            return db.get(models.User, next(owner for owner in owners if str(owner) == x_test_owner))
    app.dependency_overrides[get_db] = db_dependency
    app.dependency_overrides[security.get_current_user] = user_dependency

    def synchronise():
        for job_id, payload in pending:
            with sync_factory.begin() as db:
                execution = ledger.claim(db, job_id)
            assert execution is not None
            with fenced_job(job_id, execution['lease_token']):
                assert asyncio.run(sync.execute(sync_factory, payload)) == 'updated'
            with sync_factory.begin() as db:
                assert ledger.finish(db, job_id, execution['lease_token'])
    def reports():
        for identifier, owner in deliveries:
            async def generate():
                with report_factory() as db:
                    await automatic_comment.generate(db, db.get(models.ReportDelivery, identifier), owner)
            asyncio.run(generate())
            asyncio.run(generate())  # replay must not buy/generate twice

    def read_lane(lane):
        assert io_started.wait(10)
        owner = owners[lane % 2]
        with TestClient(app) as browser:
            headers = {'X-Test-Owner': str(owner)}
            records = []
            for iteration in range(30):
                previous = iteration % 3 == 0
                day = DAY - timedelta(days=1) if previous else DAY
                params = [('start_date', str(day)), ('end_date', str(day))]
                batch = iteration % 2 == 0
                if batch:
                    path = '/api/dashboard/project-summaries'
                    params += [('client_ids', str(client)) for client in projects[owner]]
                else:
                    path = '/api/dashboard/summary'
                    params += [('platform', 'vk')]
                with lock:
                    for kind in ('sync', 'report'):
                        if active[kind]: overlap[kind] += 1
                start = time.perf_counter()
                response = browser.get(path, params=params, headers=headers)
                records.append((time.perf_counter() - start) * 1000)
                assert response.status_code == 200, response.text[:200]
                data = response.json()
                if batch:
                    assert set(data) == {str(client) for client in projects[owner]}
                    for channels in data.values():
                        row = channels['vk']
                        assert (row['expenses'], row['leads']) in (
                            {(200, 8)} if previous else {(100, 4), (150, 5)})
                else:
                    # Six accessible projects, each atomically old or new. A
                    # different owner must never enter the aggregate.
                    cost, leads = data['expenses'], data['leads']
                    if previous:
                        assert (cost, leads) == (1200, 48)
                    else:
                        assert 600 <= cost <= 900 and leads == 24 + (cost - 600) / 50
            foreign = browser.get('/api/dashboard/project-summaries', headers=headers,
                params={'client_ids': str(projects[owners[1 - lane % 2]][0])})
            assert foreign.status_code == 403
            return records
    started = time.perf_counter()
    try:
        with ThreadPoolExecutor(max_workers=6) as pool:
            writers = [pool.submit(synchronise), pool.submit(reports)]
            readers = [pool.submit(read_lane, n) for n in range(4)]
            timings = [value for reader in readers for value in reader.result(timeout=120)]
            for writer in writers: writer.result(timeout=120)
        assert overlap['sync'] > 0 and overlap['report'] > 0
        assert calls['report'] == 12  # One model call per delivery despite replay.
        with factory() as db:
            assert db.scalar(sa.select(sa.func.count()).select_from(jobs).where(jobs.c.state == 'succeeded')) == 12
            assert db.scalar(sa.select(sa.func.count()).select_from(models.SyncJob)
                .where(models.SyncJob.status == models.SyncJobStatus.SUCCESS)) == 12
            for row in db.scalars(sa.select(models.ReportDelivery)):
                assert row.delivery_results['automatic_ai_attempt']['status'] == 'confirmed'
                assert row.comment == 'Synthetic fixed snapshot' and row.pdf_snapshot == b'synthetic-pdf'
        assert all(e.pool.checkedout() == 0 for e in engines)
        print('MIXED_READ_EVIDENCE ' + json.dumps(dict(requests=len(timings), readers=4, sync_jobs=12,
            reports=12, auth_denials=4, duration_seconds=round(time.perf_counter() - started, 3),
            p95_ms=round(sorted(timings)[math.ceil(len(timings) * .95) - 1], 2),
            max_ms=round(max(timings), 2), overlap_reads=dict(overlap), pool_peaks=dict(peak))))
    finally:
        for e in engines: e.dispose()
