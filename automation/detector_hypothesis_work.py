"""Optional durable-sync enrichment: short reads -> LLM -> guarded short write.

The caller must commit completed sync/detector data before entering this module.
This is not a durable paid-request ledger; unknown provider outcomes are never
retried here. Model, prompt, token limit and cache policy match the legacy path.
"""
from copy import deepcopy
from dataclasses import dataclass, field
from datetime import datetime, timezone
import logging
import uuid

from sqlalchemy import select

from core import models
from core.config import get_config
from core.job_fence import current_fence, LeaseLost
from backend_api.services.detector_llm import _build_prompt, _SYSTEM_PROMPT

logger = logging.getLogger(__name__)
DETERMINISTIC_MODES = ("plan", "critical_balance", "critical_stopped", "critical_tracking")


@dataclass(frozen=True)
class Hypothesis:
    id: uuid.UUID
    client_id: uuid.UUID
    owner_id: uuid.UUID
    prompt: str = field(repr=False)
    signature: tuple = field(repr=False)


def signature(alert):
    # Include lifecycle, detector values and all metadata: a stale response
    # must not overwrite a dismissal, newer run, or another enrichment.
    return tuple(deepcopy(getattr(alert, col.name)) for col in models.DetectorAlert.__table__.columns)


def fresh(alert, now):
    try:
        last = datetime.fromisoformat((alert.meta or {}).get("llm_hypothesis_at", ""))
        return (now - last).total_seconds() < 23 * 3600
    except (TypeError, ValueError):
        return False


def enabled(client, owner):
    return (client is not None and owner is not None
        and client.status == models.ClientStatus.ACTIVE and client.detector_enabled
        and owner.global_detector_enabled)


def prepare(db, client_id, now):
    client = db.get(models.Client, client_id)
    owner = db.get(models.User, client.owner_id) if client else None
    if not enabled(client, owner):
        return []
    from backend_api.services.detector_freshness import status
    proof = status(db, client_id, now.date())
    if proof is not None and proof["status"] != "ready":
        return []
    alerts = db.scalars(select(models.DetectorAlert).where(
        models.DetectorAlert.client_id == client_id,
        models.DetectorAlert.status == "open",
        ~models.DetectorAlert.mode.in_(DETERMINISTIC_MODES),
    ).order_by(models.DetectorAlert.id)).all()
    return [Hypothesis(a.id, client.id, owner.id, _build_prompt(a), signature(a))
        for a in alerts if not fresh(a, now) and (proof is None or (a.meta or {}).get("data_revision") == proof["revision"])]


def apply(db, plan, text, now):
    client = db.scalar(select(models.Client).where(models.Client.id == plan.client_id).with_for_update())
    if client is None or client.owner_id != plan.owner_id:
        return False
    owner = db.scalar(select(models.User).where(models.User.id == plan.owner_id).with_for_update())
    if not enabled(client, owner):
        return False
    from backend_api.services.detector_freshness import status
    proof = status(db, plan.client_id, now.date())
    if proof is not None and proof["status"] != "ready":
        return False
    alert = db.scalar(select(models.DetectorAlert).where(
        models.DetectorAlert.id == plan.id, models.DetectorAlert.client_id == plan.client_id).with_for_update())
    if alert is None or signature(alert) != plan.signature:
        return False
    if proof is not None and (alert.meta or {}).get("data_revision") != proof["revision"]:
        return False
    alert.hypothesis_text = text
    alert.meta = {**(alert.meta or {}), "llm_hypothesis_at": now.isoformat()}
    return True


async def execute(factory, client_id, *, expected_owner_id=None):
    if current_fence.get() is None:
        raise LeaseLost("Detached hypothesis work requires the durable executor")
    cfg = get_config()
    if not cfg.openai.api_key:
        return 0
    with factory() as db:
        plans = prepare(db, client_id, datetime.now(timezone.utc))
    if expected_owner_id is not None:
        plans = [plan for plan in plans if plan.owner_id == expected_owner_id]
    if not plans:
        return 0

    from anthropic import AsyncAnthropic
    kwargs = {"api_key": cfg.openai.api_key, "max_retries": 0}
    base_url = (cfg.openai.base_url or "").strip().rstrip("/")
    if base_url:
        kwargs["base_url"] = base_url
    updated = 0
    async with AsyncAnthropic(**kwargs) as api:
        for plan in plans:
            try:
                response = await api.messages.create(model=cfg.openai.model, max_tokens=150,
                    system=_SYSTEM_PROMPT, messages=[{"role": "user", "content": plan.prompt}], temperature=1.0)
                text = (response.content[0].text if response.content else "").strip()
            except Exception as exc:
                # No exception payloads/keys and no automatic paid replay.
                logger.warning("Hypothesis provider failed for alert %s (%s)", plan.id, type(exc).__name__)
                continue
            if text:
                with factory.begin() as db:
                    applied = apply(db, plan, text, datetime.now(timezone.utc))
                updated += int(applied)
                if applied:
                    from backend_api.cache_service import CacheService
                    CacheService.invalidate_client(str(client_id))
    return updated
