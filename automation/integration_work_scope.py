"""Validate queued integration work against its authoritative execution row.

Queue payloads never grant access by themselves. Old tasks without the explicit
owner/project binding fail closed and must be resubmitted, not rehomed silently.
"""
import uuid

import sqlalchemy as sa

from automation.work_tables import jobs
from automation.work_errors import RejectedBeforeExternalIO
from core import models
from core.job_fence import current_fence, LeaseLost


class IntegrationScopeChanged(RejectedBeforeExternalIO):
    pass


def require_execution(db, payload, *, kind, integration_id):
    fence = current_fence.get()
    if fence is None:
        raise LeaseLost("Integration work requires the durable executor")
    execution = db.execute(sa.select(jobs.c.kind, jobs.c.resource, jobs.c.tenant, jobs.c.payload).where(
        jobs.c.id == fence.job_id, jobs.c.lease_token == fence.token, jobs.c.state == "running",
        jobs.c.lease_until > sa.func.clock_timestamp(),
    )).mappings().first()
    if execution is None:
        raise LeaseLost("Integration execution lease expired or was superseded")
    integration_id = uuid.UUID(str(integration_id))
    if (execution["kind"] != kind or execution["resource"] != f"integration:{integration_id}"
            or execution["payload"] != payload):
        raise IntegrationScopeChanged("Queued integration work does not match its execution scope")
    return execution


def require_scope(db, payload, *, kind, integration_id):
    execution = require_execution(db, payload, kind=kind, integration_id=integration_id)
    integration_id = uuid.UUID(str(integration_id))
    integration = db.get(models.Integration, integration_id)
    client = db.get(models.Client, integration.client_id) if integration else None
    if (not client or client.status != models.ClientStatus.ACTIVE or integration.connection_status != "active"
            or payload.get("client_id") != str(client.id)
            or payload.get("owner_id") != str(client.owner_id)
            or execution["tenant"] != str(client.owner_id)):
        raise IntegrationScopeChanged("Queued integration source was removed, paused or changed owner/project")
    if payload.get("report_refresh") is not None:
        from automation.report_refresh import require_report
        require_report(db, payload, integration, client)
    if payload.get("consumer_refresh") is not None:
        from automation.consumer_refresh import require_request
        require_request(db, payload, integration, client)
    return integration, client
