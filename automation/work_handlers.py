"""Explicit allowlist. No arbitrary import/function name from broker payloads."""
import asyncio
from datetime import datetime


async def _goals(payload):
    from core.database import SessionLocal
    from automation.metrika_goal_work import execute
    return await execute(SessionLocal, payload)


async def _async_run(kind, payload):
    if kind == "history.backfill":
        from automation.backfill_work import execute
        return await execute(payload)
    if kind == "goals":
        return await _goals(payload)
    if kind == "reports.rule":
        from automation.calendar_work import run_report
        return await run_report(payload)
    if kind == "ai.prewarm":
        from ai.comment_prewarm import prewarm_warm_project_comments
        return await prewarm_warm_project_comments()
    if kind in {"billing.warning", "billing.recurring"}:
        from automation.billing_work import execute
        return await execute(kind, payload)
    if kind == "lead.daily":
        from lead_validator.tasks.alert_scheduler import run_daily_alerts
        return await run_daily_alerts()
    if kind == "lead.weekly":
        from lead_validator.tasks.alert_scheduler import run_weekly_report
        return await run_weekly_report()
    raise ValueError("Unsupported background job kind")


def run(kind, payload):
    if kind == "billing.maintenance":
        from core.database import SessionLocal
        from automation.billing_work import plan_page
        return plan_page(SessionLocal, payload)
    if kind == "sync.alias":
        # Durable receipt only: the referenced SyncJob owns execution/status.
        return {"joined_sync_job_id": payload["sync_job_id"]}
    if kind in {"nightly.enqueue", "reports.rules", "reports.export"}:
        from core.database import SessionLocal
        from automation.calendar_work import plan_page
        return plan_page(SessionLocal, kind, payload)
    if kind == "nightly.integration":
        from automation.calendar_work import enqueue_nightly
        return enqueue_nightly(payload)
    if kind == "sync":
        from automation.durable_sync import execute
        return execute(payload)
    if kind == "reports.project":
        from core.database import SessionLocal
        from automation.calendar_work import export_project
        return export_project(SessionLocal, payload)
    if kind == "vk.maintenance":
        from core.database import SessionLocal
        from automation.vk_maintenance import run_page
        return run_page(SessionLocal, payload)
    # Request queues belong to the loop and must be closed before asyncio.run
    # closes it; otherwise each task leaves loop/worker references behind.
    async def wrapped():
        try:
            return await _async_run(kind, payload)
        finally:
            from automation.request_queue import shutdown_request_queue
            await shutdown_request_queue()
    return asyncio.run(wrapped())
