from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock
import uuid

import httpx
import pytest
import sqlalchemy as sa

from automation import lead_alert_work as work, work_ledger as ledger
from automation.work_tables import jobs, lead_deliveries
from automation.work_errors import RejectedBeforeExternalIO
from core import models, delivery_outcome
from core.job_fence import fenced_job, LeaseLost
from tests.test_durable_work import pg, claim, expire


@pytest.fixture
def scope(pg, monkeypatch):
    factory, engine = pg
    models.Base.metadata.create_all(engine)
    now = datetime.now(timezone.utc).replace(second=0, microsecond=0)
    monkeypatch.setattr(work.settings, "ALERT_MIN_LEADS", 5)
    monkeypatch.setattr(work.settings, "ALERT_THRESHOLD_PERCENT", 50)
    monkeypatch.setattr(work.settings, "ALERT_LOOKBACK_DAYS", 7)
    with factory.begin() as db:
        owner = models.User(email="lead-alert@example.test", password_hash="synthetic")
        db.add(owner)
        db.flush()
        project = models.PhoneProject(owner_id=owner.id, name="Synthetic", telegram_chat_id="synthetic-chat")
        db.add(project)
        db.flush()
        result = SimpleNamespace(factory=factory, engine=engine, now=now, project=project.id, owner=owner.id)
    return result


def add_leads(s, count=6, **overrides):
    with s.factory.begin() as db:
        for i in range(count):
            data = dict(project_id=s.project, phone="never-export-this", status=models.LeadStatus.INVALID,
                created_at=s.now - timedelta(days=1), utm_source="source", utm_campaign="campaign", utm_content="placement")
            data.update(overrides)
            db.add(models.Lead(**data))


def plan(s, kind="lead.daily"):
    work.plan_page(s.factory, kind, {"scheduled_at": s.now.isoformat()})
    with s.factory() as db:
        row = db.execute(sa.select(jobs).where(jobs.c.kind == kind + ".project")).mappings().one()
    execution = claim(s.factory, row["id"])
    s.job, s.token, s.payload, s.kind = row["id"], execution["lease_token"], row["payload"], row["kind"]


def sender(s, behavior=None):
    async def send(text, *, parse_mode, chat_id):
        assert s.engine.pool.checkedout() == 0
        assert parse_mode is None and chat_id == "synthetic-chat"
        assert "never-export-this" not in text and len(text.encode("utf-16-le")) // 2 <= 3900
        if behavior:
            return behavior()
        return True
    return SimpleNamespace(enabled=True, token="synthetic-token", send_message=AsyncMock(side_effect=send))


async def run(s, notifier):
    with fenced_job(s.job, s.token):
        return await work.execute(s.factory, s.kind, s.payload, notifier=notifier)


def receipt(s):
    with s.factory() as db:
        return db.execute(sa.select(lead_deliveries).where(lead_deliveries.c.job_id == s.job)).mappings().first()


def test_bounded_planning_dedupe_and_recipient_binding(scope):
    s = scope
    with s.factory.begin() as db:
        db.delete(db.get(models.PhoneProject, s.project))
        for i in range(205):
            db.add(models.PhoneProject(id=uuid.UUID(int=i + 1), owner_id=s.owner,
                name="Synthetic", telegram_chat_id="synthetic-chat"))
        db.add(models.PhoneProject(owner_id=s.owner, name="No recipient"))
        db.add(models.PhoneProject(owner_id=s.owner, name="Paused", is_active=False, telegram_chat_id="synthetic-chat"))
    payload = {"scheduled_at": s.now.isoformat(), "owner_id": str(s.owner)}
    for cursor in (None, 100, 200):
        page = dict(payload)
        if cursor:
            page.update(cursor=str(uuid.UUID(int=cursor)), upper_id=str(uuid.UUID(int=205)))
        expected = {"planned": 100 if cursor != 200 else 5, "has_next": cursor != 200}
        assert work.plan_page(s.factory, "lead.daily", page) == expected
        assert work.plan_page(s.factory, "lead.daily", page) == expected
    with s.factory() as db:
        children = db.execute(sa.select(jobs).where(jobs.c.kind == "lead.daily.project")).mappings().all()
        assert len(children) == 205 and all(not r["replay_safe"] for r in children)
        assert all(r["tenant"] == str(s.owner) for r in children)
        assert all("synthetic-chat" not in str(r["payload"]) for r in children)


@pytest.mark.asyncio
@pytest.mark.parametrize("kind", ["lead.daily", "lead.weekly"])
async def test_db_window_owner_isolation_no_sql_during_send_and_receipt_replay(scope, kind):
    s = scope
    add_leads(s)
    add_leads(s, 2, status=models.LeadStatus.VALID)
    add_leads(s, 40, status=models.LeadStatus.PENDING)
    add_leads(s, 50, created_at=s.now - timedelta(days=8))
    add_leads(s, 30, created_at=s.now)  # Half-open interval.
    with s.factory.begin() as db:
        other = models.User(email="other-lead@example.test", password_hash="synthetic")
        db.add(other)
        db.flush()
        other_project = models.PhoneProject(owner_id=other.id, name="Other", telegram_chat_id="other-chat")
        db.add(other_project)
        db.flush()
        other_id = other_project.id
    add_leads(s, 60, project_id=other_id)
    # Scope the planner, otherwise this fixture would include two children.
    work.plan_page(s.factory, kind, {"scheduled_at": s.now.isoformat(), "owner_id": str(s.owner)})
    with s.factory() as db:
        row = db.execute(sa.select(jobs).where(jobs.c.tenant == str(s.owner))).mappings().one()
    execution = claim(s.factory, row["id"])
    s.job, s.token, s.payload, s.kind = row["id"], execution["lease_token"], row["payload"], row["kind"]
    notifier = sender(s)
    assert await run(s, notifier) == {"accepted": True}
    assert await run(s, notifier) == {"accepted": True, "replayed": True}
    notifier.send_message.assert_awaited_once()
    text = notifier.send_message.call_args.args[0]
    assert "Проверено: 8. Отклонено: 6 (75.0%)" in text and "6 из 8" in text
    assert receipt(s)["state"] == "sent"


@pytest.mark.asyncio
@pytest.mark.parametrize("change", ["recipient", "paused", "owner", "payload", "lease", "no_fence", "disabled"])
async def test_reject_before_send(scope, change):
    s = scope
    add_leads(s)
    plan(s)
    notifier = sender(s)
    with s.factory.begin() as db:
        project = db.get(models.PhoneProject, s.project)
        if change == "recipient":
            project.telegram_chat_id = "changed"
        elif change == "paused":
            project.is_active = False
        elif change == "owner":
            owner = models.User(email="moved@example.test", password_hash="synthetic")
            db.add(owner)
            db.flush()
            project.owner_id = owner.id
    if change == "payload":
        s.payload = {**s.payload, "days": 20}
    if change == "lease":
        expire(s.factory, s.job)
    if change == "disabled":
        notifier.enabled = False
    with pytest.raises((RejectedBeforeExternalIO, LeaseLost)):
        if change == "no_fence":
            await work.execute(s.factory, s.kind, s.payload, notifier=notifier)
        else:
            await run(s, notifier)
    notifier.send_message.assert_not_awaited()
    assert receipt(s) is None


@pytest.mark.asyncio
@pytest.mark.parametrize("result", ["uncertain", "rejected", "crash", "scope_changed", "lease_lost"])
async def test_failed_send_evidence_blocks_blind_retry(scope, result):
    s = scope
    add_leads(s)
    plan(s)
    def behavior():
        if result == "crash":
            raise RuntimeError("synthetic timeout")
        if result == "scope_changed":
            with s.factory.begin() as db:
                db.get(models.PhoneProject, s.project).telegram_chat_id = "changed"
            return True
        if result == "lease_lost":
            with s.engine.begin() as db:
                db.execute(jobs.update().where(jobs.c.id == s.job).values(
                    lease_until=sa.func.clock_timestamp() - sa.text("interval '1 second'")))
            return True
        if result == "rejected":
            delivery_outcome.rejected()
        return False
    notifier = sender(s, behavior)
    with pytest.raises(RuntimeError) as error:
        await run(s, notifier)
    assert isinstance(error.value, RejectedBeforeExternalIO) == (result == "rejected")
    assert receipt(s)["state"] == ("rejected" if result == "rejected" else "sending")
    with pytest.raises(RuntimeError):
        await run(s, notifier)
    assert notifier.send_message.await_count == 1
    if result != "lease_lost":
        with s.factory.begin() as db:
            ledger.finish(db, s.job, s.token, error=error.value)
        with s.factory() as db:
            assert db.scalar(sa.select(jobs.c.state).where(jobs.c.id == s.job)) == (
                "failed" if result == "rejected" else "uncertain")


@pytest.mark.asyncio
async def test_empty_and_good_daily_do_not_send(scope):
    s = scope
    plan(s)
    notifier = sender(s)
    assert await run(s, notifier) == {"skipped": "empty_or_expired"}
    add_leads(s, status=models.LeadStatus.VALID)
    assert await run(s, notifier) == {"skipped": "empty_or_expired"}
    notifier.send_message.assert_not_awaited()
    assert receipt(s) is None


@pytest.mark.asyncio
async def test_weekly_good_period_sends_db_totals(scope):
    s = scope
    add_leads(s, status=models.LeadStatus.VALID)
    plan(s, "lead.weekly")
    notifier = sender(s)
    await run(s, notifier)
    text = notifier.send_message.call_args.args[0]
    assert "Проверено: 6. Отклонено: 0" in text
    assert "Источников, превышающих заданный порог, нет." in text


@pytest.mark.asyncio
async def test_top_sources_bounded_plain_text(scope):
    s = scope
    for i in range(12):
        add_leads(s, utm_campaign=f"{i} " + "😀" * 200, utm_content="[_*\n" * 200)
    plan(s)
    notifier = sender(s)
    await run(s, notifier)
    text = notifier.send_message.call_args.args[0]
    assert text.count("• ") == 10


@pytest.mark.asyncio
async def test_missing_and_empty_utm_share_one_source_threshold(scope):
    s = scope
    add_leads(s, 3, utm_source=None, utm_campaign=None, utm_content=None)
    add_leads(s, 3, utm_source="", utm_campaign="", utm_content="")
    plan(s)
    notifier = sender(s)
    await run(s, notifier)
    text = notifier.send_message.call_args.args[0]
    assert "direct / none / none: 6 из 6" in text


@pytest.mark.asyncio
@pytest.mark.parametrize("field", ["tenant", "resource", "kind"])
async def test_authoritative_job_binding(scope, field):
    s = scope
    add_leads(s)
    plan(s)
    with s.factory.begin() as db:
        db.execute(jobs.update().where(jobs.c.id == s.job).values(**{field: "other"}))
    notifier = sender(s)
    with pytest.raises(RejectedBeforeExternalIO):
        await run(s, notifier)
    notifier.send_message.assert_not_awaited()


@pytest.mark.asyncio
async def test_linked_paused_client_is_not_notified(scope):
    s = scope
    with s.factory.begin() as db:
        client = models.Client(owner_id=s.owner, name="Paused", status=models.ClientStatus.PAUSED)
        db.add(client)
        db.flush()
        db.get(models.PhoneProject, s.project).client_id = client.id
    add_leads(s)
    plan(s)
    notifier = sender(s)
    with pytest.raises(RejectedBeforeExternalIO):
        await run(s, notifier)
    notifier.send_message.assert_not_awaited()


@pytest.mark.parametrize("hours", [-25, 1])
def test_expired_or_future_occurrence_not_planned(scope, hours):
    assert work.plan_page(scope.factory, "lead.daily", {"scheduled_at": (
        scope.now + timedelta(hours=hours)).isoformat()}) == {"planned": 0, "skipped": "expired_occurrence"}


def test_page_rollback_keeps_no_partial_children(scope, monkeypatch):
    s = scope
    with s.factory.begin() as db:
        db.add(models.PhoneProject(owner_id=s.owner, name="Second", telegram_chat_id="synthetic-chat"))
    original = work.submit
    calls = 0
    def fail(*args, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise RuntimeError("synthetic interruption")
        return original(*args, **kwargs)
    monkeypatch.setattr(work, "submit", fail)
    with pytest.raises(RuntimeError):
        work.plan_page(s.factory, "lead.daily", {"scheduled_at": s.now.isoformat()})
    with s.factory() as db:
        assert db.scalar(sa.select(sa.func.count()).select_from(jobs)) == 0


def test_startup_rejects_unreconciled_global_sends(scope):
    from automation.work_preflight import check_lead_alert_bindings
    s = scope
    with s.factory.begin() as db:
        check_lead_alert_bindings(db)
        ledger.submit(db, kind="lead.daily", queue="reports", key="old-global", resource="calendar:lead.daily",
                      tenant="system", payload={}, replay_safe=False)
    with s.factory() as db:
        with pytest.raises(RuntimeError, match="Legacy global lead sends"):
            check_lead_alert_bindings(db)


def test_calendar_only_plans_replay_safe_lead_parents(monkeypatch):
    from automation.work_control import occurrences
    monkeypatch.setenv("LEAD_ALERT_TIMEZONE", "UTC")
    for minute, kind in [(0, "lead.daily"), (30, "lead.weekly")]:
        now = datetime(2026, 9, 21, 9, minute, tzinfo=timezone.utc)
        assert (kind, "maintenance", True, now.isoformat()) in list(occurrences(now, now))


@pytest.mark.asyncio
async def test_expired_lease_before_intent_commit_rolls_back_and_never_sends(scope, monkeypatch):
    s = scope
    add_leads(s)
    plan(s)
    original = work.prepare
    def expiring(*args):
        snapshot = original(*args)
        with s.engine.begin() as db:
            db.execute(jobs.update().where(jobs.c.id == s.job).values(
                lease_until=sa.func.clock_timestamp() - sa.text("interval '1 second'")))
        return snapshot
    monkeypatch.setattr(work, "prepare", expiring)
    notifier = sender(s)
    with pytest.raises(LeaseLost):
        await run(s, notifier)
    assert receipt(s) is None
    notifier.send_message.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("response,outcome", [(400, "rejected"), (500, "unknown"), ("connect", "rejected"),
    ("read", "unknown"), ("malformed", "unknown"), (200, "unknown")])
async def test_telegram_message_transport_evidence_and_safe_logging(monkeypatch, caplog, response, outcome):
    from lead_validator.services.telegram import TelegramNotifier
    notifier = TelegramNotifier()
    notifier.enabled, notifier.token = True, "secret-token"
    class Client:
        async def __aenter__(self): return self
        async def __aexit__(self, *args): pass
        async def post(self, *args, **kwargs):
            if response == "connect": raise httpx.ConnectError("secret-token")
            if response == "read": raise httpx.ReadTimeout("secret-token")
            if response == "malformed": return httpx.Response(200, text="secret-token")
            return httpx.Response(response, json={"ok": response == 200, "description": "secret-token"})
    monkeypatch.setattr(httpx, "AsyncClient", lambda **kwargs: Client())
    assert await notifier.send_message("private body", chat_id="private-recipient") == (response == 200)
    assert delivery_outcome.outcome.get() == outcome
    assert all(value not in caplog.text for value in ("secret-token", "private body", "private-recipient"))
