"""Explicit allowlist. No arbitrary import/function name from broker payloads."""
import asyncio
from datetime import datetime
import uuid


async def _goals(payload):
    from core.database import SessionLocal
    from core import models, security
    from automation.sync import (_sync_metrika_goals_for_direct, _selected_yandex_direct_profile,
                                 _metrika_utm_source_filter, _avito_utm_source)
    with SessionLocal() as db:
        integration = db.query(models.Integration).filter(models.Integration.id == uuid.UUID(payload["integration_id"])).first()
        if integration is None:
            return
        from backend_api.services.project_settings import is_project_paused
        if is_project_paused(integration.client):
            return
        filters = None
        if integration.platform == models.IntegrationPlatform.AVITO_ADS:
            from automation.avito_integration_helpers import avito_metrika_access_token, avito_metrika_profile_login
            token, profile = avito_metrika_access_token(integration), avito_metrika_profile_login(integration)
            filters = _metrika_utm_source_filter(_avito_utm_source(integration))
        elif integration.platform == models.IntegrationPlatform.YANDEX_DIRECT:
            token, profile = security.decrypt_token(integration.access_token), _selected_yandex_direct_profile(integration)
        else:
            return
        if not token:
            raise ValueError("Metrika credentials are unavailable")
        await _sync_metrika_goals_for_direct(db, integration, payload["date_from"], payload["date_to"], token, profile, filters=filters)
        db.commit()


async def _async_run(kind, payload):
    if kind == "goals":
        return await _goals(payload)
    if kind == "nightly.enqueue":
        from core.database import SessionLocal
        from core import models
        from automation.durable_sync import enqueue
        from automation.main import AUTO_SYNC_DAYS
        with SessionLocal() as db:
            ids = db.query(models.Integration.id).join(models.Client).filter(
                models.Client.status == models.ClientStatus.ACTIVE,
                models.Integration.connection_status == "active",
            ).all()
        for (integration_id,) in ids:
            enqueue(integration_id, days=AUTO_SYNC_DAYS, force_full=False, trigger="auto",
                    occurrence=payload["scheduled_at"])
        return
    if kind == "reports.rules":
        from backend_api.reports.scheduler import run_scheduled_report_rules
        from datetime import timezone, timedelta
        scheduled = datetime.fromisoformat(payload["scheduled_at"])
        if datetime.now(timezone.utc) - scheduled > timedelta(minutes=15):
            return  # Never deliver an obsolete minute after a long queue outage.
        return await run_scheduled_report_rules(scheduled_at=scheduled)
    if kind == "ai.prewarm":
        from ai.comment_prewarm import prewarm_warm_project_comments
        return await prewarm_warm_project_comments()
    if kind == "billing.maintenance":
        from backend_api.services.billing_notifications import send_overflow_renewal_warnings, reconcile_recurring_totals
        await send_overflow_renewal_warnings()
        return await reconcile_recurring_totals()
    if kind == "lead.daily":
        from lead_validator.tasks.alert_scheduler import run_daily_alerts
        return await run_daily_alerts()
    if kind == "lead.weekly":
        from lead_validator.tasks.alert_scheduler import run_weekly_report
        return await run_weekly_report()
    raise ValueError("Unsupported background job kind")


def run(kind, payload):
    if kind == "sync":
        from automation.durable_sync import execute
        return execute(payload)
    if kind == "reports.export":
        from automation.sync import run_post_sync_reports
        return run_post_sync_reports(datetime.fromisoformat(payload["scheduled_at"]).date())
    if kind == "vk.maintenance":
        from backend_api.integrations import maintain_vk_client_links
        return maintain_vk_client_links()
    # Request queues belong to the loop and must be closed before asyncio.run
    # closes it; otherwise each task leaves loop/worker references behind.
    async def wrapped():
        try:
            return await _async_run(kind, payload)
        finally:
            from automation.request_queue import shutdown_request_queue
            await shutdown_request_queue()
    return asyncio.run(wrapped())
