"""Outbox transport never holds a SQL connection; every crash gap is replayable."""
from concurrent.futures import ThreadPoolExecutor
import multiprocessing
import os

import pytest
import sqlalchemy as sa

from automation import work_ledger as ledger
from automation.work_tables import outbox
from tests.test_durable_work import pg, submit, claim


def due(factory, id=None):
    with factory.begin() as db:
        query = outbox.update()
        if id is not None:
            query = query.where(outbox.c.job_id == id)
        db.execute(query.values(next_publish_at=sa.func.clock_timestamp() - sa.text("interval '1 second'")))


def test_transport_has_no_checked_out_sql_or_row_lock(pg):
    factory, engine = pg
    id = submit(factory)
    sent = []
    def send(job_id, queue):
        assert engine.pool.checkedout() == 0
        with factory.begin() as db:
            row = db.execute(sa.select(outbox).where(outbox.c.job_id == id)
                .with_for_update(nowait=True)).mappings().one()
            assert row["publish_count"] == 1
            assert row["next_publish_at"] > db.scalar(sa.select(sa.func.clock_timestamp()))
        sent.append((job_id, queue))
    assert ledger.publish_pending(factory, send) == 1
    assert sent == [(str(id), "sync.manual")]
    assert engine.pool.checkedout() == 0
    assert ledger.publish_pending(factory, send) == 0


def test_crash_after_reservation_before_send_loses_no_job(pg):
    factory, _ = pg
    id = submit(factory)
    with factory.begin() as db:
        first = ledger.reserve_publications(db)[0]
    assert ledger.publish_pending(factory, lambda *args: pytest.fail("lease active")) == 0
    due(factory)
    sent = []
    assert ledger.publish_pending(factory, lambda *args: sent.append(args)) == 1
    assert sent == [(str(id), "sync.manual")]
    with factory() as db:
        assert db.scalar(sa.select(outbox.c.publish_count)) == first["generation"] + 1


def test_reservation_rollback_releases_work_without_publish(pg):
    factory, _ = pg
    submit(factory)
    with factory() as db:
        assert len(ledger.reserve_publications(db)) == 1
        db.rollback()
    assert ledger.publish_pending(factory, lambda *args: None) == 1


def test_concurrent_publishers_reserve_disjoint_batches(pg):
    factory, _ = pg
    ids = {submit(factory, str(i)) for i in range(10)}
    def reserve(_):
        with factory.begin() as db:
            return ledger.reserve_publications(db, batch_size=5)
    with ThreadPoolExecutor(2) as pool:
        batches = list(pool.map(reserve, range(2)))
    first, second = ({row["job_id"] for row in batch} for batch in batches)
    assert len(first) == len(second) == 5
    assert not first & second and first | second == ids


def test_stale_publisher_cannot_confirm_successor_or_recovery_deadline(pg):
    factory, _ = pg
    submit(factory)
    with factory.begin() as db:
        old = ledger.reserve_publications(db)[0]
    due(factory)
    with factory.begin() as db:
        assert not ledger.confirm_publication(db, old)
        current = ledger.reserve_publications(db)[0]
        assert not ledger.confirm_publication(db, old)
        assert db.scalar(sa.select(outbox.c.next_publish_at)) == current["deadline"]
        assert ledger.confirm_publication(db, current)
        assert not ledger.confirm_publication(db, current)  # confirmation is fenced/idempotent


def test_job_finished_while_broker_returns_does_not_resurrect_outbox(pg):
    factory, _ = pg
    id = submit(factory)
    def send(*args):
        execution = claim(factory, id)
        with factory.begin() as db:
            assert ledger.finish(db, id, execution["lease_token"])
    assert ledger.publish_pending(factory, send) == 1
    with factory() as db:
        assert db.scalar(sa.select(sa.func.count()).select_from(outbox)) == 0
    assert claim(factory, id) is None


def test_partial_batch_unknown_result_keeps_all_remaining_records(pg):
    factory, _ = pg
    for i in range(3):
        submit(factory, str(i))
    sent = []
    def send(*args):
        sent.append(args)
        if len(sent) == 2:
            raise RuntimeError("Synthetic broker response lost")
    with pytest.raises(RuntimeError):
        ledger.publish_pending(factory, send)
    with factory() as db:
        assert db.scalar(sa.select(sa.func.count()).select_from(outbox)) == 3
    due(factory)
    retry = []
    assert ledger.publish_pending(factory, lambda *args: retry.append(args)) == 3
    assert set(sent) <= set(retry)  # transport duplicates allowed, business duplicates fenced


def test_sql_confirmation_failure_after_broker_acceptance_is_replayable(pg, monkeypatch):
    factory, engine = pg
    submit(factory)
    sent = []
    def fail(*args):
        raise RuntimeError("Synthetic SQL commit failure")
    with monkeypatch.context() as context:
        context.setattr(ledger, "confirm_publication", fail)
        with pytest.raises(RuntimeError):
            ledger.publish_pending(factory, lambda *args: sent.append(args))
    assert engine.pool.checkedout() == 0
    due(factory)
    assert ledger.publish_pending(factory, lambda *args: sent.append(args)) == 1
    assert len(sent) == 2 and sent[0] == sent[1]


@pytest.mark.parametrize("after_send", [False, True])
def test_abrupt_publisher_process_death_does_not_lose_committed_outbox(pg, after_send):
    factory, engine = pg
    id = submit(factory)
    context = multiprocessing.get_context("fork")
    receive, send = context.Pipe(duplex=False)
    def crashed_process():
        receive.close()
        engine.dispose(close=False)
        if after_send:
            def accepted(job_id, queue):
                assert engine.pool.checkedout() == 0
                send.send(job_id)  # observable transport acceptance before death
                os._exit(17)
            ledger.publish_pending(factory, accepted)
        else:
            with factory.begin() as db:
                ledger.reserve_publications(db)
            os._exit(17)
    process = context.Process(target=crashed_process)
    process.start()
    send.close()
    try:
        process.join(timeout=5)
        assert process.exitcode == 17
        if after_send:
            assert receive.poll(1) and receive.recv() == str(id)
        with factory() as db:
            assert db.scalar(sa.select(sa.func.count()).select_from(outbox)) == 1
        due(factory)
        sent = []
        assert ledger.publish_pending(factory, lambda *args: sent.append(args)) == 1
        assert sent == [(str(id), "sync.manual")]
    finally:
        if process.is_alive():
            process.kill()
            process.join(timeout=5)
        receive.close()


@pytest.mark.parametrize("size", [0, 11, True, "2"])
def test_unbounded_publication_batches_are_refused(pg, size):
    factory, _ = pg
    with factory.begin() as db, pytest.raises(ValueError):
        ledger.reserve_publications(db, batch_size=size)
