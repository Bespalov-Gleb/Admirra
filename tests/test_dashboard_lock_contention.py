"""Regression: two browser tabs must not serialize behind detector/sync locks."""
from datetime import timedelta
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace
import sqlalchemy as sa
import pytest

from core import models, consumer_freshness
from core.data_requirements import DataNotReady
from backend_api.read_snapshot import begin_read_snapshot
from backend_api.dashboard_visit import record_visit
from tests.test_durable_work import pg
from tests.test_metrika_goal_work import goals, DAY
from tests.test_consumer_freshness import consumer, cover


def test_ui_evidence_does_not_wait_for_writer_and_pool_resets(consumer):
    g = consumer
    cover(g, DAY - timedelta(days=60))
    with g.factory.begin() as writer, g.factory() as reader:
        writer.execute(sa.select(models.Client).where(models.Client.id == g.client).with_for_update())
        writer.execute(sa.select(models.Integration).where(models.Integration.id == g.id).with_for_update())
        begin_read_snapshot(reader)
        reader.execute(sa.text("SET LOCAL statement_timeout='500ms'"))
        before = consumer_freshness.verify(reader, [g.client], DAY, DAY)
        assert before['status'] == 'ready'
        # An uncommitted setting must not leak into an otherwise old snapshot.
        writer.execute(sa.update(models.Integration).where(models.Integration.id == g.id).values(selected_goals='[999]'))
        assert consumer_freshness.verify(reader, [g.client], DAY, DAY)['revision'] == before['revision']
        reader.rollback()
        assert not reader.connection().get_execution_options().get('admirra_read_snapshot')
        assert reader.scalar(sa.text('SHOW transaction_read_only')) == 'off'
    with g.factory() as reader:
        begin_read_snapshot(reader)
        with pytest.raises(DataNotReady):
            consumer_freshness.verify(reader, [g.client], DAY, DAY)


def test_ui_snapshot_never_locks_out_a_writer(consumer):
    g = consumer
    cover(g)
    with g.factory() as reader:
        begin_read_snapshot(reader)
        first = consumer_freshness.verify(reader, [g.client], DAY, DAY)
        cover(g)  # Real fenced writer takes both row locks and replaces evidence.
        assert consumer_freshness.verify(reader, [g.client], DAY, DAY)['revision'] == first['revision']
        reader.rollback()
        begin_read_snapshot(reader)
        assert consumer_freshness.verify(reader, [g.client], DAY, DAY)['revision'] != first['revision']


def test_durable_consumers_still_lock_sources(consumer):
    g = consumer
    cover(g)
    with g.factory() as reader, g.factory() as writer:
        consumer_freshness.verify(reader, [g.client], DAY, DAY)
        with pytest.raises(sa.exc.OperationalError):
            writer.execute(sa.select(models.Client).where(models.Client.id == g.client).with_for_update(nowait=True))


def test_visit_skips_busy_project_but_preserves_normal_memory(consumer):
    g = consumer
    values = {'expenses': 100, 'leads': 2, 'cpa': 50}
    with g.factory.begin() as writer, g.factory() as visitor:
        writer.execute(sa.select(models.Client).where(models.Client.id == g.client).with_for_update())
        visitor.execute(sa.text("SET LOCAL statement_timeout='500ms'"))
        assert record_visit(visitor, g.client, DAY, DAY, 'vk', values) is False
    with g.factory() as visitor:
        assert record_visit(visitor, g.client, DAY, DAY, 'vk', values)
        saved = visitor.get(models.Client, g.client).last_dashboard_snapshot
        assert saved['current']['leads'] == 2
        assert saved['previous'] is None
        assert record_visit(visitor, g.client, DAY, DAY, 'vk', dict(values, leads=3))
        saved = visitor.get(models.Client, g.client).last_dashboard_snapshot
        assert saved['current']['leads'] == 3 and saved['previous'] is None


def test_parallel_detector_summary_and_dashboard_visit(consumer, monkeypatch):
    from backend_api import detector
    g = consumer
    cover(g, DAY - timedelta(days=60))
    monkeypatch.setattr(detector, '_assert_detector_access', lambda *a, **k: None)
    # Exercise the real handler with a synthetic owner/project and source locks.
    from datetime import datetime, timezone
    monkeypatch.setattr(detector, '_now', lambda: datetime.combine(DAY, datetime.min.time(), timezone.utc))
    def one(n):
        with g.factory() as db:
            if n % 2:
                return record_visit(db, g.client, DAY, DAY, 'yandex', {'leads': 3})
            result = detector.get_detector_summary(g.client, SimpleNamespace(id=g.owner), db)
            assert 'sync_issues' in result
            return True
    with ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(one, range(12)))
    assert g.engine.pool.checkedout() == 0
