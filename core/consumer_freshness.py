"""Opt-in, SQL-only evidence for derived consumers; no provider IO or commits."""
from datetime import date, timedelta
import hashlib
import json
import uuid

import sqlalchemy as sa
from core import models, sync_coverage
from core.data_requirements import requirements, DataNotReady
from core.runtime import env_bool, env_int

FLAGS = {"ai": "AI_FRESHNESS_GUARDS", "sheets": "SHEETS_FRESHNESS_GUARDS", "detector": "DETECTOR_FRESHNESS_GUARDS"}


def enabled(consumer):
    if not env_bool(FLAGS[consumer], False):
        return False
    if not (env_bool("REPORT_FRESHNESS_GUARDS", False) and env_bool("DURABLE_TASKS", False)
            and env_bool("REPORT_DELIVERY_GUARDS", True)):
        raise RuntimeError("Consumer freshness requires durable report freshness")
    return True


def verify(db, ids, start, end):
    if type(start) is not date or type(end) is not date or not 0 <= (end - start).days < 7320:
        raise DataNotReady("invalid_period")
    required = requirements(db, ids, start, end)
    now = db.scalar(sa.select(sa.func.clock_timestamp()))
    threshold = now - timedelta(minutes=env_int("REPORT_DATA_MAX_AGE_MINUTES", 1440, 1, 1440))
    evidence = []
    for req in required:
        result = sync_coverage.assess(db, integration_id=uuid.UUID(req["integration_id"]),
            client_id=uuid.UUID(req["client_id"]), owner_id=uuid.UUID(req["owner_id"]),
            stages=req["stages"], start=start, end=end, not_before=threshold)
        if not result.ready:
            raise DataNotReady(result.reason)
        rows = db.execute(sa.select(models.SyncCoverage.id, models.SyncCoverage.execution_id,
            models.SyncCoverage.stage, models.SyncCoverage.date_from, models.SyncCoverage.date_to,
            models.SyncCoverage.observed_at).where(
                models.SyncCoverage.integration_id == uuid.UUID(req["integration_id"]),
                models.SyncCoverage.settings_digest == req["settings"],
                models.SyncCoverage.stage.in_(req["stages"]), models.SyncCoverage.observed_at >= threshold,
                models.SyncCoverage.date_from <= end, models.SyncCoverage.date_to >= start,
            ).order_by(models.SyncCoverage.id).limit(sync_coverage.MAX_WINDOWS + 1)).all()
        if len(rows) > sync_coverage.MAX_WINDOWS:
            raise DataNotReady("fragmentation_limit")
        evidence.append((req, [tuple(row) for row in rows]))
    revision = hashlib.sha256(json.dumps(evidence, default=str, sort_keys=True).encode()).hexdigest()
    return {"status": "ready", "revision": revision, "date_from": str(start), "date_to": str(end),
            "checked_at": now.isoformat()}
