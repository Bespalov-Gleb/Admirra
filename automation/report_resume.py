"""Bounded report readiness poll. Same delivery; no busy wait or blind resend."""
import uuid
from datetime import datetime, timezone
import sqlalchemy as sa

from core import models
from core.job_fence import current_fence, LeaseLost
from automation.work_tables import jobs
from backend_api.reports import freshness, scheduler


async def execute(factory, payload):
    if not freshness.enabled():
        return {"held": "freshness_disabled"}
    fence = current_fence.get()
    if fence is None:
        raise LeaseLost("Report resume requires durable execution")
    delivery_id, owner_id = uuid.UUID(payload["delivery_id"]), uuid.UUID(payload["owner_id"])
    with factory() as db:
        job = db.execute(sa.select(jobs).where(jobs.c.id == fence.job_id,
            jobs.c.lease_token == fence.token, jobs.c.state == "running",
            jobs.c.lease_until > sa.func.clock_timestamp())).mappings().first()
        if (not job or job["kind"] != "reports.resume" or job["payload"] != payload
                or job["tenant"] != str(owner_id) or job["resource"] != f"report-delivery:{delivery_id}"):
            raise LeaseLost("Report resume scope changed")
        delivery = db.scalar(sa.select(models.ReportDelivery).where(models.ReportDelivery.id == delivery_id,
            models.ReportDelivery.user_id == owner_id).with_for_update())
        if delivery is None or delivery.status != "pending":
            return {"skipped": "already_processed_or_unavailable"}
        if (delivery.data_readiness or {}).get("status") != "waiting":
            return {"skipped": "not_waiting"}
        user = db.get(models.User, owner_id)
        if user is None or not user.is_active:
            delivery.data_readiness = {**delivery.data_readiness, "status": "held", "reason": "scope_unavailable"}
            db.commit()
            return {"held": "scope_unavailable"}
        try:
            await scheduler.build_delivery_snapshot(db, delivery, user)
        except freshness.ReportDataPending:
            freshness.enqueue_wait(db, delivery)
            state = delivery.data_readiness["status"]
            db.commit()
            return {"data": state}
        # Manual previews never gain automatic-send permission through this job.
        rule = db.get(models.ReportSchedule, delivery.schedule_id) if delivery.schedule_id else None
        db.refresh(user)
        if not user.is_active:
            delivery.data_readiness = {**delivery.data_readiness, "status": "held", "reason": "scope_unavailable"}
            db.commit()
            return {"held": "scope_unavailable"}
        if delivery.schedule_id and (rule is None or freshness.schedule_digest(rule) != delivery.data_readiness.get("schedule_digest")):
            delivery.data_readiness = {**delivery.data_readiness, "status": "held", "reason": "schedule_changed"}
            db.commit()
            return {"held": "schedule_changed"}
        reason = scheduler._rule_blocking_anomaly(db, rule) if rule else None
        if (delivery.source not in {"auto", "detector"} or rule is None or not rule.enabled
                or rule.user_id != owner_id or rule.approval_required or reason):
            delivery.anomaly_reason = reason or delivery.anomaly_reason
            db.commit()
            return {"data": "ready", "delivery": "pending_approval"}
        # claim before irreversible IO. Lost/unknown sends are not replayed by
        # this non-replayable child; existing per-recipient ledger remains used.
        claimed = db.query(models.ReportDelivery).filter(models.ReportDelivery.id == delivery.id,
            models.ReportDelivery.status == "pending").update({"status": "sending"}, synchronize_session=False)
        if claimed != 1:
            db.rollback()
            return {"skipped": "already_claimed"}
        delivery.status = "sending"
        db.commit()
        result = await scheduler.send_report_delivery(db, delivery, user)
        delivery.delivery_results = result
        delivery.status = scheduler.delivery_status_from_results(result,
            scheduler._jlist(delivery.channels), scheduler._jlist(delivery.chat_targets))
        if delivery.status in {"sent", "partial"}:
            delivery.sent_at = datetime.now(timezone.utc)
            rule.last_sent_at = delivery.sent_at
        db.commit()
        if delivery.status == "failed":
            raise RuntimeError("Report delivery failed; inspect recipient outcomes")
        return {"delivery": delivery.status}
