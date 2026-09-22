from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
import importlib.util
from pathlib import Path
import uuid

import pytest
import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations

from core import models
from core.job_fence import fenced_job, LeaseLost
from backend_api.reports import freshness, scheduler
from automation import report_resume
from automation.work_tables import jobs
from tests.test_durable_work import pg, claim
from tests.test_metrika_goal_work import goals, DAY
from tests.test_sync_coverage import write


@pytest.fixture
def report(goals, monkeypatch):
    g = goals
    monkeypatch.setenv("REPORT_FRESHNESS_GUARDS", "true")
    monkeypatch.setenv("DURABLE_TASKS", "true")
    monkeypatch.setenv("REPORT_DELIVERY_GUARDS", "true")
    with g.factory.begin() as db:
        g.owner = db.get(models.Client, g.client).owner_id
        delivery = models.ReportDelivery(user_id=g.owner, client_id=g.client,
            start_date=DAY, end_date=DAY, channels='["telegram"]', include_ai_comment=False)
        db.add(delivery)
        db.flush()
        g.delivery = delivery.id
    g.renders, g.templates, g.sends = [], [], []
    def data(**kwargs):
        assert kwargs["_resolved_client_ids"] == [g.client]
        assert not kwargs["render_pdf"]
        g.templates.append(kwargs["platform"])
        return b"", {"summary": {"leads": 34}}
    def render(delivery):
        assert g.engine.pool.checkedout() == 0
        g.renders.append(delivery.id)
        delivery.pdf_snapshot = b"%PDF synthetic"
    async def send(*args, **kwargs):
        g.sends.append(args[1].id)
        return {"telegram": True}
    monkeypatch.setattr(scheduler, "generate_report_pdf", data)
    monkeypatch.setattr(scheduler, "refresh_delivery_snapshot_files", render)
    monkeypatch.setattr(scheduler, "_delivery_target_details", lambda *a: ([], []))
    monkeypatch.setattr(scheduler, "_delivery_cpl_target", lambda *a: None)
    monkeypatch.setattr(scheduler, "send_report_delivery", send)
    return g


def cover(g, *, comparison=True):
    now = datetime.now(timezone.utc)
    for stage in ("campaigns", "metrika_goals"):
        write(g, DAY - timedelta(days=int(comparison)), DAY, stage=stage, observed=now)


async def build(g, *, wait=False):
    with g.factory() as db:
        d, user = db.get(models.ReportDelivery, g.delivery), db.get(models.User, g.owner)
        if wait:
            with pytest.raises(freshness.ReportDataPending):
                await scheduler.build_delivery_snapshot(db, d, user)
            job = freshness.enqueue_wait(db, d)
            state = dict(d.data_readiness)
            db.commit()
            return state, job
        await scheduler.build_delivery_snapshot(db, d, user)
        db.commit()


async def resume(g, job):
    with g.factory.begin() as db:
        db.execute(jobs.update().where(jobs.c.id == job).values(available_at=sa.func.now()))
        payload = db.scalar(sa.select(jobs.c.payload).where(jobs.c.id == job))
    execution = claim(g.factory, job)
    assert execution
    with fenced_job(job, execution["lease_token"]):
        return await report_resume.execute(g.factory, payload)


@pytest.mark.asyncio
async def test_wait_persisted_deduplicated_without_render_or_send(report):
    g = report
    state, job = await build(g, wait=True)
    again, same_job = await build(g, wait=True)
    assert state["status"] == "waiting" and state["revision"] == 1
    assert same_job == job and again["deadline"] == state["deadline"]
    assert state["required"][0]["date_from"] == str(DAY - timedelta(days=1))
    assert not g.renders and not g.sends and not g.templates
    with g.factory() as db:
        assert db.scalar(sa.select(sa.func.count()).select_from(models.ReportDelivery)) == 1
        row = db.execute(sa.select(jobs).where(jobs.c.id == job)).mappings().one()
        assert row["available_at"] > datetime.now(timezone.utc)
        assert row["replay_safe"] is False


@pytest.mark.asyncio
async def test_current_period_alone_does_not_allow_report(report):
    cover(report, comparison=False)
    state, _ = await build(report, wait=True)
    assert state["status"] == "waiting"
    assert not report.renders


@pytest.mark.asyncio
async def test_ready_render_is_detached_snapshot_reused_after_stats_change(report):
    g = report
    cover(g)
    await build(g)
    assert g.templates == ["all", "yandex", "vk", "avito"]
    with g.factory.begin() as db:
        d = db.get(models.ReportDelivery, g.delivery)
        assert d.data_readiness["status"] == "ready" and d.snapshot_data["coverage_revision"] == 1
        db.get(models.Integration, g.id).selected_goals = '["2"]'
    await build(g)
    assert len(g.renders) == 1 and len(g.templates) == 4


@pytest.mark.asyncio
async def test_settings_revision_does_not_extend_deadline(report):
    g = report
    state, _ = await build(g, wait=True)
    with g.factory.begin() as db:
        db.get(models.Integration, g.id).selected_goals = '["2"]'
    changed, _ = await build(g, wait=True)
    assert changed["revision"] == 2
    assert changed["deadline"] == state["deadline"]


@pytest.mark.asyncio
async def test_switch_template_preserves_verified_snapshot(report):
    g = report
    cover(g)
    await build(g)
    with g.factory() as db:
        d = db.get(models.ReportDelivery, g.delivery)
        db.expunge(d)
    scheduler.switch_delivery_template(d, "vk")
    assert d.snapshot_data["coverage_revision"] == d.data_readiness["revision"]
    with g.factory.begin() as db:
        db.add(d)
    await build(g)
    assert len(g.templates) == 4


@pytest.mark.asyncio
async def test_uncovered_second_channel_blocks_all_templates(report):
    g = report
    cover(g)
    with g.factory.begin() as db:
        db.add(models.Integration(client_id=g.client, platform=models.IntegrationPlatform.VK_ADS, account_id="second"))
    state, _ = await build(g, wait=True)
    assert len(state["required"]) == 2 and len(state["missing"]) == 1
    assert not g.renders


@pytest.mark.asyncio
async def test_render_failure_keeps_frozen_data_for_retry(report, monkeypatch):
    g = report
    cover(g)
    real = scheduler.refresh_delivery_snapshot_files
    def fail(delivery):
        assert g.engine.pool.checkedout() == 0
        raise RuntimeError("synthetic render failure")
    monkeypatch.setattr(scheduler, "refresh_delivery_snapshot_files", fail)
    with pytest.raises(RuntimeError):
        await build(g)
    with g.factory() as db:
        d = db.get(models.ReportDelivery, g.delivery)
        assert d.snapshot_data and not d.pdf_snapshot
    monkeypatch.setattr(scheduler, "refresh_delivery_snapshot_files", real)
    await build(g)
    assert len(g.templates) == 4 and len(g.renders) == 1


@pytest.mark.asyncio
async def test_deadline_holds_without_new_poll(report):
    g = report
    await build(g, wait=True)
    with g.factory.begin() as db:
        d = db.get(models.ReportDelivery, g.delivery)
        d.data_readiness = {**d.data_readiness, "deadline": (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat()}
    cover(g)
    state, job = await build(g, wait=True)
    assert state["reason"] == "deadline_expired" and job is None
    assert not g.renders


@pytest.mark.asyncio
@pytest.mark.parametrize("change", ["owner", "disconnected", "paused"])
async def test_scope_changes_never_produce_report(report, change):
    g = report
    cover(g)
    with g.factory.begin() as db:
        if change == "owner":
            user = models.User(email="other@example.test", password_hash="synthetic")
            db.add(user)
            db.flush()
            db.get(models.Client, g.client).owner_id = user.id
        elif change == "disconnected":
            db.get(models.Integration, g.id).connection_status = "disconnected"
        else:
            db.get(models.Client, g.client).status = models.ClientStatus.PAUSED
    await build(g, wait=True)
    assert not g.renders


@pytest.mark.asyncio
async def test_manual_wait_resumes_preview_but_never_sends(report):
    g = report
    _, job = await build(g, wait=True)
    cover(g)
    result = await resume(g, job)
    assert result["delivery"] == "pending_approval"
    assert len(g.renders) == 1 and not g.sends


@pytest.mark.asyncio
@pytest.mark.parametrize("approval", [False, True])
async def test_auto_wait_preserves_approval_and_sends_at_most_once(report, approval):
    g = report
    with g.factory.begin() as db:
        rule = models.ReportSchedule(user_id=g.owner, scope_client_id=g.client, approval_required=approval)
        db.add(rule)
        db.flush()
        d = db.get(models.ReportDelivery, g.delivery)
        d.source, d.schedule_id = "auto", rule.id
    _, job = await build(g, wait=True)
    cover(g)
    result = await resume(g, job)
    assert result["delivery"] == ("pending_approval" if approval else "sent")
    assert len(g.sends) == int(not approval)
    with g.factory() as db:
        job_row = db.execute(sa.select(jobs).where(jobs.c.id == job)).mappings().one()
    with fenced_job(job, job_row["lease_token"]):
        again = await report_resume.execute(g.factory, job_row["payload"])
    assert "skipped" in again and len(g.sends) == int(not approval)


@pytest.mark.asyncio
async def test_resume_rejects_other_owner_payload(report):
    g = report
    _, job = await build(g, wait=True)
    with g.factory.begin() as db:
        db.execute(jobs.update().where(jobs.c.id == job).values(available_at=sa.func.now()))
    execution = claim(g.factory, job)
    with fenced_job(job, execution["lease_token"]), pytest.raises(LeaseLost):
        await report_resume.execute(g.factory, {"owner_id": str(uuid.uuid4()), "delivery_id": str(g.delivery)})
    assert not g.renders and not g.sends


@pytest.mark.asyncio
async def test_scoped_scheduler_persists_wait_once(report, monkeypatch):
    g = report
    now = datetime.now(scheduler.MSK).replace(second=0, microsecond=0)
    with g.factory.begin() as db:
        rule = models.ReportSchedule(user_id=g.owner, scope_client_id=g.client,
            send_time=now.strftime("%H:%M"), day="daily", approval_required=False)
        db.add(rule)
        db.flush()
        rule_id = rule.id
    monkeypatch.setattr(scheduler, "SessionLocal", g.factory)
    await scheduler.run_scheduled_report_rules(now, rule_id=rule_id, owner_id=g.owner)
    await scheduler.run_scheduled_report_rules(now, rule_id=rule_id, owner_id=g.owner)
    with g.factory() as db:
        rows = list(db.scalars(sa.select(models.ReportDelivery).where(models.ReportDelivery.schedule_id == rule_id)))
        assert len(rows) == 1 and rows[0].data_readiness["status"] == "waiting"
    assert not g.sends


@pytest.mark.asyncio
@pytest.mark.parametrize("during_render", ["manual_sent", "approval_enabled"])
async def test_initial_scheduler_rechecks_after_detached_render(report, monkeypatch, during_render):
    from datetime import time
    g = report
    now = datetime.combine(DAY, time(10), tzinfo=scheduler.MSK)
    with g.factory.begin() as db:
        rule = models.ReportSchedule(user_id=g.owner, scope_client_id=g.client, period_days=1,
            send_time="10:00", day="daily", approval_required=False)
        db.add(rule)
        db.flush()
        rule_id = rule.id
    cover(g)
    original = scheduler.refresh_delivery_snapshot_files
    def concurrent(delivery):
        original(delivery)
        with g.factory.begin() as other:
            if during_render == "manual_sent":
                other.get(models.ReportDelivery, delivery.id).status = "sent"
            else:
                other.get(models.ReportSchedule, rule_id).approval_required = True
    monkeypatch.setattr(scheduler, "refresh_delivery_snapshot_files", concurrent)
    monkeypatch.setattr(scheduler, "SessionLocal", g.factory)
    await scheduler.run_scheduled_report_rules(now, rule_id=rule_id, owner_id=g.owner)
    assert not g.sends
    with g.factory() as db:
        d = db.scalar(sa.select(models.ReportDelivery).where(models.ReportDelivery.schedule_id == rule_id))
        assert d.status == ("sent" if during_render == "manual_sent" else "pending")
        if during_render == "approval_enabled":
            assert d.data_readiness["status"] == "held"


@pytest.mark.asyncio
async def test_approve_wait_returns_409_without_permission_to_send(report):
    from fastapi import HTTPException
    from core import schemas
    from backend_api.reports.router import approve_report_delivery
    g = report
    with g.factory() as db:
        user = db.get(models.User, g.owner)
        with pytest.raises(HTTPException) as error:
            await approve_report_delivery(g.delivery, schemas.ReportDeliveryApprove(), user, db)
        assert error.value.status_code == 409
    with g.factory() as db:
        d = db.get(models.ReportDelivery, g.delivery)
        assert d.status == "pending" and d.approved_at is None
        assert d.data_readiness["status"] == "waiting"
    assert not g.sends


@pytest.mark.asyncio
async def test_rule_edit_holds_waiting_occurrence(report):
    g = report
    with g.factory.begin() as db:
        rule = models.ReportSchedule(user_id=g.owner, scope_client_id=g.client, approval_required=False)
        db.add(rule)
        db.flush()
        db.get(models.ReportDelivery, g.delivery).schedule_id = rule.id
        rule_id = rule.id
    _, job = await build(g, wait=True)
    with g.factory.begin() as db:
        db.get(models.ReportSchedule, rule_id).channels = '["email"]'
    cover(g)
    assert (await resume(g, job))["data"] == "held"
    assert not g.sends


@pytest.mark.asyncio
async def test_legacy_snapshot_is_not_grandfathered(report):
    g = report
    with g.factory.begin() as db:
        d = db.get(models.ReportDelivery, g.delivery)
        d.snapshot_data, d.pdf_snapshot = {"old": True}, b"%PDF old"
    state, job = await build(g, wait=True)
    assert state["reason"] == "unverified_snapshot" and job is None


def test_flag_requires_durable_mode(monkeypatch):
    monkeypatch.setenv("REPORT_FRESHNESS_GUARDS", "true")
    monkeypatch.setenv("DURABLE_TASKS", "false")
    with pytest.raises(RuntimeError):
        freshness.enabled()
    from core.runtime import get_runtime
    with pytest.raises(ValueError, match="Report freshness"):
        get_runtime({"APP_PROCESS_ROLE": "api", "REPORT_FRESHNESS_GUARDS": "true"})


def test_additive_migration(report):
    spec = importlib.util.spec_from_file_location("report_freshness_migration", Path(__file__).resolve().parents[1] /
                                                "alembic/versions/f13c4d5e6f70_report_freshness.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    with report.engine.begin() as connection, Operations.context(MigrationContext.configure(connection)):
        module.downgrade()
        module.upgrade()
        column = next(c for c in sa.inspect(connection).get_columns("report_deliveries") if c["name"] == "data_readiness")
        assert column["nullable"] and isinstance(column["type"], sa.JSON)
