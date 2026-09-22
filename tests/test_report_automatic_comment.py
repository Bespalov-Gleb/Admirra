"""Immutable report -> detached AI/render -> conditional publication; offline."""
from datetime import date
from types import SimpleNamespace
from unittest.mock import AsyncMock
import uuid
import pytest
import sqlalchemy as sa
from core import models
from backend_api.reports import automatic_comment as work, scheduler
from ai import report_generator as ai
from tests.test_durable_work import pg


@pytest.fixture
def delivery(pg, monkeypatch):
    factory, engine = pg
    models.Base.metadata.create_all(engine)
    with factory.begin() as db:
        owner = models.User(email='report@example.test', password_hash='synthetic')
        db.add(owner); db.flush()
        client = models.Client(owner_id=owner.id, name='Synthetic')
        db.add(client); db.flush()
        row = models.ReportDelivery(user_id=owner.id, client_id=client.id, start_date=date(2026, 9, 1),
            end_date=date(2026, 9, 7), source='auto', include_ai_comment=True, channels='[]',
            snapshot_data={'summary': {'leads': 34}, 'top_campaigns': [], '_scope_client_ids': [str(client.id)],
                'start_date': '2026-09-01', 'end_date': '2026-09-07'}, data_readiness={'status': 'ready'})
        db.add(row); db.flush()
        s = SimpleNamespace(factory=factory, engine=engine, id=row.id, owner=owner.id)
    async def generate(snapshot):
        assert engine.pool.checkedout() == 0
        assert snapshot['summary']['leads'] == 34
        return 'Synthetic fixed-snapshot comment'
    def render(snapshot):
        assert engine.pool.checkedout() == 0
        snapshot.pdf_snapshot = b'synthetic pdf'
        snapshot.png_snapshot = b'synthetic png'
        snapshot.snapshot_data = {**snapshot.snapshot_data, 'ai_comment': snapshot.comment}
    s.generate = AsyncMock(side_effect=generate)
    monkeypatch.setattr(ai, 'generate_delivery_comment', s.generate)
    monkeypatch.setattr(scheduler, 'refresh_delivery_snapshot_files', render)
    return s


async def run(s):
    with s.factory() as db:
        await work.generate(db, db.get(models.ReportDelivery, s.id), s.owner)


@pytest.mark.asyncio
async def test_ai_and_renderer_hold_no_sql_and_confirm_once(delivery):
    s = delivery
    await run(s)
    await run(s)
    s.generate.assert_awaited_once()
    with s.factory() as db:
        row = db.get(models.ReportDelivery, s.id)
        assert row.comment == 'Synthetic fixed-snapshot comment'
        assert row.pdf_snapshot == b'synthetic pdf'
        assert row.delivery_results['automatic_ai_attempt']['status'] == 'confirmed'


@pytest.mark.asyncio
async def test_unknown_ai_outcome_is_not_automatically_paid_again(delivery):
    s = delivery
    s.generate.side_effect = TimeoutError('synthetic')
    await run(s)
    await run(s)
    s.generate.assert_awaited_once()
    with s.factory() as db:
        row = db.get(models.ReportDelivery, s.id)
        assert row.comment is None
        assert row.delivery_results['automatic_ai_attempt']['status'] == 'uncertain'


@pytest.mark.asyncio
async def test_human_edit_in_flight_wins(delivery):
    s = delivery
    async def changed(snapshot):
        with s.factory.begin() as db:
            row = db.get(models.ReportDelivery, s.id)
            row.comment = 'Human reviewed text'
        return 'Old model output'
    s.generate.side_effect = changed
    await run(s)
    with s.factory() as db:
        row = db.get(models.ReportDelivery, s.id)
        assert row.comment == 'Human reviewed text'
        assert row.delivery_results['automatic_ai_attempt']['status'] == 'superseded'
        assert row.pdf_snapshot is None


@pytest.mark.asyncio
@pytest.mark.parametrize('attribute,value', [('source', 'manual'), ('include_ai_comment', False),
    ('comment', 'Already approved'), ('comment_status', 'approved'), ('comment_status', 'edited')])
async def test_manual_and_approved_reports_never_call_ai(delivery, attribute, value):
    s = delivery
    with s.factory.begin() as db:
        setattr(db.get(models.ReportDelivery, s.id), attribute, value)
    await run(s)
    s.generate.assert_not_called()


@pytest.mark.asyncio
async def test_missing_coverage_fails_before_provider(delivery):
    s = delivery
    with s.factory.begin() as db:
        db.get(models.ReportDelivery, s.id).data_readiness = {'status': 'waiting'}
    with pytest.raises(ValueError, match='ready immutable'):
        await run(s)
    s.generate.assert_not_called()


@pytest.mark.asyncio
async def test_concurrent_request_cannot_send_before_generation_finishes(delivery):
    s = delivery
    async def generating(snapshot):
        with pytest.raises(work.AutomaticCommentPending):
            await run(s)
        return 'Only one generation'
    s.generate.side_effect = generating
    await run(s)
    s.generate.assert_awaited_once()


@pytest.mark.asyncio
async def test_expired_attempt_allows_report_without_ai_and_blocks_late_publication(delivery):
    from datetime import datetime, timezone, timedelta
    s = delivery
    async def expired(snapshot):
        with s.factory.begin() as db:
            row = db.get(models.ReportDelivery, s.id)
            attempt = row.delivery_results['automatic_ai_attempt']
            row.delivery_results = {**row.delivery_results, 'automatic_ai_attempt': {**attempt,
                'deadline': (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat()}}
        await run(s)
        return 'Late output must not change delivered file'
    s.generate.side_effect = expired
    await run(s)
    s.generate.assert_awaited_once()
    with s.factory() as db:
        row = db.get(models.ReportDelivery, s.id)
        assert row.comment is None
        assert row.delivery_results['automatic_ai_attempt']['status'] == 'uncertain'


@pytest.mark.asyncio
async def test_delivery_context_never_uses_db_or_live_statistics(monkeypatch):
    generator = AsyncMock(return_value='text')
    monkeypatch.setattr(ai, '_generate_report', generator)
    snapshot = {'_scope_client_ids': [str(uuid.uuid4())], 'summary': {'leads': 34}, 'top_campaigns': [],
                'start_date': '2026-09-01', 'end_date': '2026-09-07'}
    assert await ai.generate_delivery_comment(snapshot) == 'text'
    assert generator.call_args.kwargs['db'] is None
    assert generator.call_args.kwargs['_prepared'][0]['leads'] == 34
    assert snapshot['summary'] == {'leads': 34}
    with pytest.raises(ValueError):
        await ai.generate_delivery_comment({**snapshot, 'top_campaigns': [{}] * 11})
    with pytest.raises(ValueError):
        await ai.generate_delivery_comment({**snapshot, 'summary': {'large': 'a' * 65536}})
    generator.assert_awaited_once()


@pytest.mark.asyncio
async def test_comment_money_matches_displayed_vat_and_lead_cost_basis(monkeypatch):
    generator = AsyncMock(return_value='text')
    monkeypatch.setattr(ai, '_generate_report', generator)
    snapshot = {'_scope_client_ids': [str(uuid.uuid4())], 'platform': 'all',
        'summary': {'expenses': 300, 'clicks': 10, 'leads': 2,
            'cost_by_platform': {'yandex': 100, 'vk': 100, 'avito': 100},
            'lead_cost_by_platform': {'yandex': 100, 'vk': 0, 'avito': 100}},
        'top_campaigns': [{'platform': 'avito', 'cost': 100}, {'platform': 'yandex', 'cost': 100}],
        'start_date': '2026-09-01', 'end_date': '2026-09-07'}
    await ai.generate_delivery_comment(snapshot)
    summary, campaigns = generator.call_args.kwargs['_prepared']
    assert summary['expenses'] == 344
    assert summary['cpc'] == 34.4
    assert summary['cpa'] == 111
    assert [c['cost'] for c in campaigns] == [100, 122]
    assert snapshot['summary']['expenses'] == 300


@pytest.mark.asyncio
async def test_attempt_receipt_survives_delivery_checkpoint(delivery, monkeypatch):
    s = delivery
    from backend_api.reports import freshness
    monkeypatch.setattr(freshness, 'enabled', lambda: True)
    monkeypatch.setattr(scheduler.route_ledger, 'enabled', lambda: False)
    monkeypatch.setattr(scheduler, 'build_delivery_snapshot', AsyncMock())
    with s.factory() as db:
        row = db.get(models.ReportDelivery, s.id)
        row.channels = '["telegram"]'  # Missing chat: no external transport.
        db.commit()
        result = await scheduler._send_report_delivery(db, row, db.get(models.User, s.owner))
        assert result['automatic_ai_attempt']['status'] == 'confirmed'
        assert result['telegram'] is False
        db.expire_all()
        assert db.get(models.ReportDelivery, s.id).delivery_results['automatic_ai_attempt']['status'] == 'confirmed'


@pytest.mark.asyncio
async def test_real_generation_pipeline_does_not_read_live_stats(pg, monkeypatch):
    def no_stats(*args, **kwargs):
        raise AssertionError('Immutable comment must not read live data')
    monkeypatch.setattr(ai.StatsService, 'aggregate_summary', no_stats)
    monkeypatch.setattr(ai.StatsService, 'get_campaign_stats', no_stats)
    monkeypatch.setattr(ai.settings, 'OPENAI_API_KEY', 'synthetic-not-real')
    async def transport(**kwargs):
        assert pg[1].pool.checkedout() == 0
        assert '34' in kwargs['messages'][0]['content']
        return SimpleNamespace(content=[SimpleNamespace(text='Период ровный. Стоимость заявки остаётся у цели. Настройки стоит сохранить.')])
    create = AsyncMock(side_effect=transport)
    monkeypatch.setattr(ai, '_create_anthropic_client', lambda: SimpleNamespace(messages=SimpleNamespace(create=create)))
    text = await ai.generate_delivery_comment({'_scope_client_ids': [str(uuid.uuid4())],
        'summary': {'leads': 34}, 'top_campaigns': [], 'start_date': '2026-09-01', 'end_date': '2026-09-07'})
    assert 'Период ровный' in text
    create.assert_awaited_once()


@pytest.mark.asyncio
async def test_lost_lease_does_not_publish_files_or_comment(delivery):
    from automation import work_ledger as ledger
    from core.job_fence import current_fence, fenced_job, LeaseLost
    from tests.test_durable_work import claim, expire
    s = delivery
    with s.factory.begin() as db:
        job = ledger.submit(db, kind='reports.rule', queue='reports', key='synthetic-comment',
            resource='synthetic-report', tenant=str(s.owner), payload={})
    execution = claim(s.factory, job)
    async def lose(snapshot):
        token = current_fence.set(None)
        try:
            expire(s.factory, job)
        finally:
            current_fence.reset(token)
        return 'Late old worker output'
    s.generate.side_effect = lose
    with fenced_job(job, execution['lease_token']), pytest.raises(LeaseLost):
        await run(s)
    with s.factory() as db:
        row = db.get(models.ReportDelivery, s.id)
        assert row.comment is None and row.pdf_snapshot is None
        assert row.delivery_results['automatic_ai_attempt']['status'] == 'sending'
