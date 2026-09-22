"""Fail-closed freshness evidence for durable sync, not a last_sync_at alias.

Only validated complete responses (including explicit empty results) qualify.
Call replace_window in the SAME fenced transaction as the statistics write.
Legacy writers do not maintain this ledger: consumers MUST NOT enable barriers
until durable writers exclusively own all required sources. Reader row locks
keep source settings stable through the caller's short snapshot transaction.
No IO, commits, credentials, or provider responses are stored here.
"""
from dataclasses import dataclass
from datetime import date, datetime, timedelta
import hashlib
import json

from sqlalchemy import select
from core import models
from core.job_fence import current_fence, LeaseLost

STAGES = frozenset({"campaigns", "groups", "keywords", "creatives", "metrika_goals"})
MAX_WINDOWS = 4096
SEMANTIC_FIELDS = (
    "id", "client_id", "platform", "connection_status", "account_id",
    "metrika_account_id", "selected_goals", "primary_goal_id", "selected_counters",
    "lead_action_types", "is_agency", "agency_client_login", "utm_source", "oauth_app",
)


def settings_digest(integration, client):
    # Token rotation isn't a change of statistical scope. Execution guards still
    # compare the full, credential-sensitive snapshot before applying writes.
    values = {name: getattr(integration, name) for name in SEMANTIC_FIELDS}
    values.update(owner_id=client.owner_id, client_status=client.status)
    return hashlib.sha256(json.dumps(values, sort_keys=True, default=str).encode()).hexdigest()


def _validate(stage, start, end, observed_at):
    if stage not in STAGES or type(start) is not date or type(end) is not date or start > end:
        raise ValueError("Invalid coverage stage/window")
    if not isinstance(observed_at, datetime) or observed_at.utcoffset() is None:
        raise ValueError("Coverage freshness requires a timezone-aware timestamp")


def replace_window(db, integration, client, stage, start, end, observed_at, *, complete=True):
    """Caller holds client -> integration locks and has validated the snapshot.

    Remove overlap across ALL old digests: otherwise A -> B -> A settings could
    resurrect A's evidence for dates whose actual facts were overwritten by B.
    Incomplete data replacement invalidates coverage without marking it fresh.
    """
    _validate(stage, start, end, observed_at)
    fence = current_fence.get()
    if fence is None:
        raise LeaseLost("Coverage writes require a durable execution fence")
    if integration.client_id != client.id:
        raise ValueError("Coverage scope mismatch")
    db.flush()
    old = list(db.scalars(select(models.SyncCoverage).where(
        models.SyncCoverage.integration_id == integration.id,
        models.SyncCoverage.stage == stage,
        models.SyncCoverage.date_from <= end,
        models.SyncCoverage.date_to >= start,
    ).limit(MAX_WINDOWS + 1)))
    if len(old) > MAX_WINDOWS:
        raise ValueError("Coverage window fragmentation limit exceeded")
    for row in old:
        if row.date_from < start and row.date_to > end:
            db.add(models.SyncCoverage(
                integration_id=row.integration_id, client_id=row.client_id, owner_id=row.owner_id,
                stage=row.stage, settings_digest=row.settings_digest,
                date_from=end + timedelta(days=1), date_to=row.date_to,
                observed_at=row.observed_at, recorded_at=row.recorded_at, execution_id=row.execution_id))
            row.date_to = start - timedelta(days=1)
        elif row.date_from < start:
            row.date_to = start - timedelta(days=1)
        elif row.date_to > end:
            row.date_from = end + timedelta(days=1)
        else:
            db.delete(row)
    if complete:
        db.add(models.SyncCoverage(
            integration_id=integration.id, client_id=client.id, owner_id=client.owner_id,
            stage=stage, settings_digest=settings_digest(integration, client),
            date_from=start, date_to=end, observed_at=observed_at, execution_id=fence.job_id))
    db.flush()


@dataclass(frozen=True)
class CoverageResult:
    ready: bool
    reason: str
    missing_stages: tuple[str, ...] = ()


def assess(db, *, integration_id, client_id, owner_id, stages, start, end, not_before):
    """Require ALL requested stages/dates since explicit freshness threshold.

    No external IO while these locks are held. A ready result is evidence only
    for this transaction; persist report requirements separately, not this bool.
    """
    stages = tuple(sorted(set(stages)))
    if not stages:
        raise ValueError("Coverage requires at least one stage")
    for stage in stages:
        _validate(stage, start, end, not_before)
    client = db.scalar(select(models.Client).where(models.Client.id == client_id)
                       .execution_options(populate_existing=True).with_for_update())
    if client is None or client.owner_id != owner_id or client.status != models.ClientStatus.ACTIVE:
        return CoverageResult(False, "scope_unavailable")
    integration = db.scalar(select(models.Integration).where(models.Integration.id == integration_id)
                            .execution_options(populate_existing=True).with_for_update())
    if integration is None or integration.client_id != client.id or integration.connection_status != "active":
        return CoverageResult(False, "scope_unavailable")
    rows = list(db.scalars(select(models.SyncCoverage).where(
        models.SyncCoverage.integration_id == integration.id,
        models.SyncCoverage.client_id == client.id, models.SyncCoverage.owner_id == owner_id,
        models.SyncCoverage.settings_digest == settings_digest(integration, client),
        models.SyncCoverage.stage.in_(stages), models.SyncCoverage.date_from <= end,
        models.SyncCoverage.date_to >= start, models.SyncCoverage.observed_at >= not_before,
    ).order_by(models.SyncCoverage.stage, models.SyncCoverage.date_from).limit(MAX_WINDOWS + 1)))
    if len(rows) > MAX_WINDOWS:
        return CoverageResult(False, "fragmentation_limit", stages)
    missing = []
    for stage in stages:
        cursor, covered = start, False
        for row in rows:
            if row.stage != stage:
                continue
            if row.date_from > cursor:
                break
            if row.date_to >= end:
                covered = True
                break
            cursor = max(cursor, row.date_to + timedelta(days=1))
        if not covered:
            missing.append(stage)
    return CoverageResult(not missing, "ready" if not missing else "missing_or_stale", tuple(missing))
