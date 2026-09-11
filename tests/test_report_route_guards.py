"""Real-PG recipient fencing; transports are synthetic, never contact clients."""
import asyncio
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timezone
import importlib
from pathlib import Path
import smtplib
from types import SimpleNamespace
from unittest.mock import AsyncMock
import uuid

from alembic.migration import MigrationContext
from alembic.operations import Operations
import httpx
import pytest
import sqlalchemy as sa

from backend_api.reports import route_ledger as ledger, scheduler
from core import delivery_outcome as evidence
from core.models import ReportDelivery
from tests.test_durable_work import pg


def migration_module():
    spec = importlib.util.spec_from_file_location("route_guard_migration", Path(__file__).resolve().parents[1] /
        "alembic/versions/ee5f6a7b8c9d_report_route_guards.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def recipients(pg, monkeypatch):
    factory, engine = pg
    # Complete ORM projection, but no unrelated application foreign tables.
    table = sa.Table("report_deliveries", sa.MetaData(), *[
        sa.Column(c.name, c.type, primary_key=c.primary_key) for c in ReportDelivery.__table__.columns
    ])
    table.create(engine)
    with engine.begin() as db:
        with Operations.context(MigrationContext.configure(db)):
            migration_module().upgrade()
    monkeypatch.setenv("REPORT_DELIVERY_GUARDS", "true")
    return factory, table


def delivery_row(recipients, results=None, owner=None, status="failed"):
    factory, table = recipients
    item = SimpleNamespace(id=uuid.uuid4(), delivery_results=results or {})
    with factory.begin() as db:
        db.execute(table.insert().values(id=item.id, user_id=owner or uuid.uuid4(),
            status=status, delivery_results=item.delivery_results))
    return item


def test_one_recipient_across_concurrent_senders(recipients):
    factory, _ = recipients
    item = delivery_row(recipients)
    def acquire(_):
        with factory() as db:
            return ledger.acquire(db, item.id, "same", "telegram")
    with ThreadPoolExecutor(6) as pool:
        claims = list(pool.map(acquire, range(6)))
    assert sum(token is not None for token, _ in claims) == 1


@pytest.mark.asyncio
async def test_success_is_not_replayed_despite_missing_batch_checkpoint(recipients):
    factory, _ = recipients
    item = delivery_row(recipients)
    sender = AsyncMock(return_value=(True, None))
    wrapped = ledger.guarded("email", lambda kw: kw["email"])(sender)
    with factory() as db:
        reset = ledger.context.set((db, item))
        try:
            assert await wrapped(email="one@example.test") == (True, None)
            db.rollback()  # Batch status was never saved; recipient evidence was.
            assert await wrapped(email="one@example.test") == (True, None)
            assert await wrapped(email="two@example.test") == (True, None)
            assert sender.await_count == 2
        finally:
            ledger.context.reset(reset)


@pytest.mark.asyncio
@pytest.mark.parametrize("crash", [False, True])
async def test_unknown_result_or_crash_blocks_replay(recipients, crash):
    factory, _ = recipients
    item = delivery_row(recipients)
    class ProcessDied(BaseException):
        pass
    async def send(**kwargs):
        if crash:
            raise ProcessDied()
        raise httpx.ReadTimeout("provider may already have accepted")
    wrapped = ledger.guarded("telegram", lambda kw: kw["chat_id"])(send)
    with factory() as db:
        reset = ledger.context.set((db, item))
        try:
            if crash:
                with pytest.raises(ProcessDied):
                    await wrapped(chat_id="123")
            else:
                assert await wrapped(chat_id="123") == (False, ledger.UNCERTAIN)
            assert await wrapped(chat_id="123") == (False, ledger.UNCERTAIN)
            row = db.execute(sa.select(ledger.routes)).mappings().one()
            assert row["attempt"] == 1
            assert row["state"] == ("sending" if crash else "uncertain")
        finally:
            ledger.context.reset(reset)


@pytest.mark.asyncio
async def test_rejected_recipient_is_retryable_without_resending_accepted_one(recipients):
    factory, _ = recipients
    item = delivery_row(recipients)
    calls = []
    async def send(*, email):
        calls.append(email)
        evidence.rejected()
        return (email == "ok" or calls.count(email) > 1), "known rejection"
    wrapped = ledger.guarded("email", lambda kw: kw["email"])(send)
    with factory() as db:
        reset = ledger.context.set((db, item))
        try:
            await wrapped(email="ok")
            assert not (await wrapped(email="retry"))[0]
            assert (await wrapped(email="ok"))[0]
            assert (await wrapped(email="retry"))[0]
            assert calls == ["ok", "retry", "retry"]
        finally:
            ledger.context.reset(reset)


@pytest.mark.parametrize("decision,expected", [("accepted", "accepted"), ("retry", "rejected")])
def test_explicit_resolution_is_audited_and_old_token_is_fenced(recipients, decision, expected):
    factory, _ = recipients
    item = delivery_row(recipients)
    actor = uuid.uuid4()
    with factory() as db:
        token, _ = ledger.acquire(db, item.id, "route", "max")
        with pytest.raises(ValueError, match="progress"):
            ledger.resolve(db, item.id, "route", actor, decision, "Checked with the recipient")
        db.rollback()
        ledger.settle(db, item.id, "route", token, "uncertain")
        ledger.resolve(db, item.id, "route", actor, decision, "Checked with the recipient")
        db.commit()
        with pytest.raises(RuntimeError):
            ledger.settle(db, item.id, "route", token, "accepted")
        row = db.execute(sa.select(ledger.routes)).mappings().one()
        assert row["state"] == expected
        assert row["resolutions"][0]["actor_id"] == str(actor)


@pytest.mark.asyncio
async def test_legacy_failed_routes_require_verification(recipients):
    factory, _ = recipients
    item = delivery_row(recipients, {"legacy_untracked_attempts": True})
    sender = AsyncMock(return_value=(True, None))
    wrapped = ledger.guarded("max", lambda kw: kw["chat_id"])(sender)
    with factory() as db:
        reset = ledger.context.set((db, item))
        try:
            assert await wrapped(chat_id="legacy") == (False, ledger.UNCERTAIN)
            sender.assert_not_awaited()
            key = ledger.route_key("max", "legacy")
            ledger.resolve(db, item.id, key, uuid.uuid4(), "retry", "Confirmed not received externally")
            db.commit()
            assert (await wrapped(chat_id="legacy"))[0]
            sender.assert_awaited_once()
        finally:
            ledger.context.reset(reset)


@pytest.mark.asyncio
async def test_failure_saving_provider_acceptance_cannot_resend(recipients, monkeypatch):
    factory, _ = recipients
    item = delivery_row(recipients)
    sender = AsyncMock(return_value=(True, None))
    wrapped = ledger.guarded("telegram", lambda kw: kw["chat_id"])(sender)
    original = ledger.settle
    def failed_commit(db, delivery_id, key, token, state):
        if state == "accepted":
            raise ConnectionError("DB lost after provider accepted")
        return original(db, delivery_id, key, token, state)
    monkeypatch.setattr(ledger, "settle", failed_commit)
    with factory() as db:
        reset = ledger.context.set((db, item))
        try:
            assert await wrapped(chat_id="123") == (False, ledger.UNCERTAIN)
            assert await wrapped(chat_id="123") == (False, ledger.UNCERTAIN)
            sender.assert_awaited_once()
        finally:
            ledger.context.reset(reset)


def test_read_only_monitor_reports_recipient_uncertainty(recipients):
    from ops.work_status import snapshot
    factory, _ = recipients
    item = delivery_row(recipients)
    with factory() as db:
        token, _ = ledger.acquire(db, item.id, "one", "telegram")
        ledger.settle(db, item.id, "one", token, "uncertain")
    with factory.begin() as db:
        db.execute(sa.text("SET TRANSACTION READ ONLY"))
        assert snapshot(db)["report_recipients_requiring_reconciliation"] == 1


def test_unknown_old_route_prevents_false_fully_sent_status():
    result = {"telegram": True, "requires_reconciliation": True}
    assert scheduler.delivery_status_from_results(result, ["telegram"], []) == "partial"


@pytest.mark.asyncio
@pytest.mark.parametrize("known_rejection", [False, True])
async def test_png_to_pdf_fallback_requires_proof_of_rejection(monkeypatch, known_rejection):
    from lead_validator.services.telegram import telegram_notifier
    monkeypatch.setenv("REPORT_DELIVERY_GUARDS", "true")
    async def photo(**kwargs):
        evidence.rejected() if known_rejection else evidence.before_send()
        return False
    monkeypatch.setattr(telegram_notifier, "send_photo", photo)
    pdf = AsyncMock(return_value=True)
    monkeypatch.setattr(telegram_notifier, "send_document", pdf)
    ok, _ = await scheduler._send_telegram_report_attachment(chat_id="123", png_snapshot=b"png",
        pdf_snapshot=b"pdf", filename_stem="fixture", caption="test")
    assert ok == known_rejection
    assert pdf.await_count == int(known_rejection)


@pytest.mark.asyncio
@pytest.mark.parametrize("failure,state", [(httpx.ConnectTimeout("test"), "rejected"),
    (httpx.ReadTimeout("test"), "unknown"), (httpx.WriteTimeout("test"), "unknown")])
async def test_transport_failure_evidence(failure, state):
    evidence.before_send()
    evidence.request_failed(failure)
    assert evidence.outcome.get() == state


@pytest.mark.asyncio
async def test_thread_result_preserves_evidence_even_on_exception():
    def operation():
        evidence.rejected()
        raise ValueError("preflight failed")
    evidence.before_send()
    with pytest.raises(ValueError):
        await evidence.in_thread(operation)
    assert evidence.outcome.get() == "rejected"


@pytest.mark.asyncio
@pytest.mark.parametrize("error,expected", [
    (smtplib.SMTPAuthenticationError(535, b"test"), "rejected"),
    (smtplib.SMTPDataError(550, b"test"), "rejected"),
    (TimeoutError("after DATA"), "unknown"),
])
async def test_smtp_evidence_survives_thread(monkeypatch, error, expected):
    from lead_validator.services.email_sender import EmailSender
    sender = EmailSender()
    sender.enabled, sender.from_addr = True, "sender@example.test"
    sender.user, sender.password = "test", "test"
    class SMTP:
        def __init__(self, *args, **kwargs): pass
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def starttls(self): pass
        def login(self, *args):
            if isinstance(error, smtplib.SMTPAuthenticationError): raise error
        def send_message(self, msg): raise error
    monkeypatch.setattr(smtplib, "SMTP", SMTP)
    ok, _ = await sender.send_report_email(["recipient@example.test"], "test", "test")
    assert not ok
    assert evidence.outcome.get() == expected


def test_owner_only_reconciliation(recipients, monkeypatch):
    from backend_api.reports import router
    from core.schemas import ReportRouteReconcile
    from fastapi import HTTPException
    factory, _ = recipients
    owner = uuid.uuid4()
    item = delivery_row(recipients, owner=owner)
    key = "a" * 64
    body = ReportRouteReconcile(route_key=key, decision="retry", reason="Confirmed not received externally")
    with factory() as db:
        token, _ = ledger.acquire(db, item.id, key, "telegram")
        ledger.settle(db, item.id, key, token, "uncertain")
        with pytest.raises(HTTPException) as exc:
            router.reconcile_report_recipient(item.id, body, SimpleNamespace(id=uuid.uuid4()), db)
        assert exc.value.status_code == 404
        db.rollback()
        monkeypatch.setattr(router, "_delivery_to_response", lambda db, d: d.delivery_results)
        result = router.reconcile_report_recipient(item.id, body, SimpleNamespace(id=owner), db)
        assert result["requires_reconciliation"] is False
        assert result["route_states"][0]["state"] == "rejected"


def test_actual_migration_foreign_key_and_legacy_marker(recipients):
    factory, table = recipients
    migration = migration_module()
    legacy = delivery_row(recipients, {"telegram": True}, status="partial")
    with factory() as db:
        with Operations.context(MigrationContext.configure(db.connection())):
            migration.downgrade()
            migration.upgrade()
        db.commit()
        result = db.scalar(sa.select(table.c.delivery_results).where(table.c.id == legacy.id))
        assert result == {"telegram": True, "legacy_untracked_attempts": True}
        with pytest.raises(sa.exc.IntegrityError):
            ledger.acquire(db, uuid.uuid4(), "orphan", "email")
        db.rollback()
        token, _ = ledger.acquire(db, legacy.id, "route", "email")
        with Operations.context(MigrationContext.configure(db.connection())):
            with pytest.raises(RuntimeError, match="Reconcile"):
                migration.downgrade()
        db.rollback()
        ledger.settle(db, legacy.id, "route", token, "accepted")
        db.execute(table.delete().where(table.c.id == legacy.id))
        db.commit()
        assert db.scalar(sa.select(sa.func.count()).select_from(ledger.routes)) == 0
