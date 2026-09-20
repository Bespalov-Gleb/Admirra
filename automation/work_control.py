"""Durable calendar and outbox publisher; never runs external business work."""
from datetime import timedelta
import logging
import os
import signal
import threading
from zoneinfo import ZoneInfo

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import insert

from automation.work_ledger import publish_pending, recover_expired, submit, prune_completed
from automation.work_tables import schedule_cursor
from core.runtime import env_bool, env_int, get_runtime

log = logging.getLogger(__name__)
MSK = ZoneInfo("Europe/Moscow")


def occurrences(tick, now):
    """Bound catch-up: no late customer reports, at most one day of housekeeping."""
    local = tick.astimezone(MSK)
    stamp = tick.isoformat()
    if now - tick <= timedelta(minutes=15):
        # Planning only: external sends belong to non-replayable rule children.
        yield "reports.rules", "maintenance", True, stamp
    if local.hour == env_int("AUTO_SYNC_HOUR_MSK", 3, 0, 23) and local.minute == 0:
        yield "nightly.enqueue", "maintenance", True, stamp
    if local.hour == env_int("AUTO_REPORTS_HOUR_MSK", 5, 0, 23) and local.minute == 0:
        yield "reports.export", "maintenance", True, stamp
        if env_bool("AI_PREWARM_ENABLED", False):
            yield "ai.prewarm", "ai.prewarm", False, stamp
        yield "billing.maintenance", "maintenance", False, stamp
    if local.minute == 0:
        yield "vk.maintenance", "maintenance", True, stamp
    # Preserve the legacy container timezone explicitly at cutover.
    alerts = tick.astimezone(ZoneInfo(os.getenv("LEAD_ALERT_TIMEZONE", "UTC")))
    if alerts.hour == 9 and alerts.minute == 0:
        yield "lead.daily", "reports", False, stamp
    if alerts.weekday() == 0 and alerts.hour == 9 and alerts.minute == 30:
        yield "lead.weekly", "reports", False, stamp


def schedule_due(db, *, now=None):
    now = now or db.execute(sa.select(sa.func.clock_timestamp())).scalar_one()
    minute = now.replace(second=0, microsecond=0)
    db.execute(insert(schedule_cursor).values(name="calendar-v1", last_tick=minute - timedelta(minutes=1))
               .on_conflict_do_nothing())
    last = db.execute(sa.select(schedule_cursor.c.last_tick).where(schedule_cursor.c.name == "calendar-v1")
                      .with_for_update()).scalar_one()
    tick = max(last + timedelta(minutes=1), minute - timedelta(hours=24) + timedelta(minutes=1))
    count = 0
    while tick <= minute:
        for kind, queue, safe, stamp in occurrences(tick, now):
            submit(db, kind=kind, queue=queue, key=f"calendar:{kind}:{stamp}", resource=f"calendar:{kind}",
                   tenant="system", payload={"scheduled_at": stamp}, replay_safe=safe)
            count += 1
        tick += timedelta(minutes=1)
    if minute > last:
        db.execute(schedule_cursor.update().where(schedule_cursor.c.name == "calendar-v1").values(last_tick=minute))
    return count


def main():
    if get_runtime().role != "scheduler" or not env_bool("DURABLE_TASKS", False):
        raise SystemExit("Requires scheduler role and DURABLE_TASKS=true")
    from automation.work_preflight import check
    check()
    from core.database import SessionLocal
    from automation.celery_app import app
    stopped = threading.Event()
    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, lambda *_: stopped.set())
    logging.basicConfig(level=logging.INFO)
    while not stopped.is_set():
        try:
            with SessionLocal.begin() as db:
                recover_expired(db)
                schedule_due(db)
                from automation.backfill_work import reconcile
                reconcile(db, min_age_seconds=15)
                prune_completed(db)
            published = publish_pending(SessionLocal, lambda job_id, queue: app.send_task(
                "admirra.execute", args=[job_id], queue=queue, retry=False), batch_size=10)
            if published:
                log.info("Published %d durable jobs", published)
        except Exception as exc:
            log.error("Control iteration failed: %s", type(exc).__name__)
        stopped.wait(2)


if __name__ == "__main__":
    main()
