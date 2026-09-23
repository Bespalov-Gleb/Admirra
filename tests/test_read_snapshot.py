import pytest
import sqlalchemy as sa
import asyncio
from types import SimpleNamespace
import uuid

from backend_api.read_snapshot import begin_read_snapshot
from core import models
from tests.test_durable_work import pg
from tests.test_summary_queries import summary_db, DAY


def test_snapshot_keeps_one_version_without_blocking_writes_and_resets_pool(pg):
    factory, engine = pg
    with factory.begin() as db:
        db.execute(sa.text('INSERT INTO effects VALUES (1)'))
    with factory() as db:
        db.execute(sa.text('SELECT 1'))  # Existing auth read does not prevent use.
        assert begin_read_snapshot(db)
        assert db.scalar(sa.text('SHOW transaction_isolation')) == 'repeatable read'
        assert db.scalar(sa.text('SHOW transaction_read_only')) == 'on'
        assert db.scalar(sa.text('SELECT id FROM effects')) == 1
        with factory.begin() as writer:
            writer.execute(sa.text('UPDATE effects SET id=2'))
        assert db.scalar(sa.text('SELECT id FROM effects')) == 1
        db.rollback()
        assert db.scalar(sa.text('SHOW transaction_isolation')) == 'read committed'
        assert db.scalar(sa.text('SHOW transaction_read_only')) == 'off'
        assert db.scalar(sa.text('SELECT id FROM effects')) == 2
    assert engine.pool.checkedout() == 0


def test_snapshot_rejects_writes_and_releases_on_error(pg):
    factory, engine = pg
    with factory() as db:
        begin_read_snapshot(db)
        with pytest.raises(sa.exc.DBAPIError):
            db.execute(sa.text('INSERT INTO effects VALUES (1)'))
    with factory.begin() as db:
        db.execute(sa.text('INSERT INTO effects VALUES (2)'))
    assert engine.pool.checkedout() == 0


def test_pending_orm_changes_are_never_silently_discarded(pg):
    factory, _ = pg
    with factory() as db:
        user = models.User(email='not-discarded@example.test', password_hash='synthetic')
        db.add(user)
        with pytest.raises(RuntimeError, match='pending changes'):
            begin_read_snapshot(db)
        assert user in db.new


def test_summary_cannot_mix_old_spend_with_new_leads(summary_db, monkeypatch):
    from backend_api import stats
    db, engine, client, _, _, campaigns = summary_db
    monkeypatch.setattr(stats.StatsService, 'get_effective_client_ids', lambda *args: [client])
    changed = False
    def interleave(connection, cursor, statement, params, context, many):
        nonlocal changed
        if changed or 'sum(vk_stats.cost)' not in statement.lower():
            return
        changed = True
        # Precisely between the spend SELECT and the separate lead SELECT.
        # MVCC must keep the old pair; the writer must not be blocked.
        with engine.begin() as writer:
            writer.execute(sa.update(models.VKStats).where(models.VKStats.campaign_id == campaigns['v'],
                models.VKStats.date == DAY).values(cost=4000, conversions=7))
    sa.event.listen(engine, 'after_cursor_execute', interleave)
    async def read():
        return await stats.get_summary(start_date=str(DAY), end_date=str(DAY), client_id=None,
            folder_id=None, campaign_ids=None, goal_action_ids=None, platform='vk', period_preset=None,
            current_user=SimpleNamespace(id=uuid.uuid4()), db=db)
    try:
        result = asyncio.run(read())
        assert changed and (result['expenses'], result['leads']) == (4000, 6)
        fresh = asyncio.run(read())
        assert (fresh['expenses'], fresh['leads']) == (5000, 7)
    finally:
        sa.event.remove(engine, 'after_cursor_execute', interleave)
