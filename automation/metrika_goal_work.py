"""Durable Metrika collection: snapshot -> external IO -> guarded short write.

Not a replacement for the full legacy sync transaction. Resource exclusion and
execution fencing are supplied by the durable job executor, not process globals.
"""
from dataclasses import dataclass, field
from datetime import date
import uuid

from sqlalchemy import select

from core import models, security
from core.job_fence import current_fence, LeaseLost
from automation.metrika_goal_batch import latest_goal_names, collect_goal_rows, replace_goal_window
from automation.metrika_goal_window import goal_window


class GoalSettingsChanged(RuntimeError):
    """Retryable: discard the old response and collect using current settings."""


# Compare encrypted credentials in memory only. Never serialize/log this tuple.
SETTING_FIELDS = ("id", "client_id", "platform", "connection_status", "selected_goals",
    "primary_goal_id", "selected_counters", "access_token", "metrika_access_token",
    "account_id", "metrika_account_id", "is_agency", "agency_client_login", "utm_source")


def signature(integration, client):
    return tuple(getattr(integration, name) for name in SETTING_FIELDS) + (client.owner_id, client.status)


@dataclass(frozen=True)
class GoalPlan:
    integration_id: uuid.UUID
    client_id: uuid.UUID
    owner_id: uuid.UUID
    platform: models.IntegrationPlatform
    settings: tuple = field(repr=False)
    token: str = field(repr=False)
    profile: str | None = field(repr=False)
    filters: str | None = field(repr=False)
    goals: tuple[str, ...] | None
    counters: tuple[str, ...]
    days: tuple[date, ...]
    known_names: dict = field(repr=False)


def prepare(db, integration_id, date_from, date_to):
    from automation.sync import (_json_list, _selected_yandex_direct_profile,
        _metrika_utm_source_filter, _avito_utm_source)
    integration = db.get(models.Integration, integration_id)
    if integration is None:
        return None
    client = db.get(models.Client, integration.client_id)
    if client is None or client.status != models.ClientStatus.ACTIVE or integration.connection_status != "active":
        return None
    filters = None
    if integration.platform == models.IntegrationPlatform.YANDEX_DIRECT:
        token = security.decrypt_token(integration.access_token) if integration.access_token else None
        profile = _selected_yandex_direct_profile(integration)
    elif integration.platform == models.IntegrationPlatform.AVITO_ADS:
        from automation.avito_integration_helpers import avito_metrika_access_token, avito_metrika_profile_login
        token, profile = avito_metrika_access_token(integration), avito_metrika_profile_login(integration)
        filters = _metrika_utm_source_filter(_avito_utm_source(integration))
    elif integration.platform == models.IntegrationPlatform.YANDEX_METRIKA:
        # A login here represents an authorization link, not a counter. Its
        # linked advertising integration collects the actual statistics.
        if not str(integration.account_id).strip().isdigit():
            return None
        token = security.decrypt_token(integration.access_token) if integration.access_token else None
        profile = integration.agency_client_login
        if profile and profile.lower() == "unknown":
            profile = None
    else:
        return None
    if not token:
        raise ValueError("Metrika credentials are unavailable")
    goals = _json_list(integration.selected_goals)
    if integration.primary_goal_id:
        goals.append(str(integration.primary_goal_id))
    goals = tuple(dict.fromkeys(goals))
    counters = tuple(dict.fromkeys(_json_list(integration.selected_counters)))
    standalone = integration.platform == models.IntegrationPlatform.YANDEX_METRIKA
    if standalone:
        counters = (str(integration.account_id),)
    if (not goals and not standalone) or not counters:
        return None
    exists = db.scalar(select(models.MetrikaGoals.id).where(
        models.MetrikaGoals.integration_id == integration_id).limit(1)) is not None
    days = goal_window(date_from, date_to,
        first_sync=not exists or integration.sync_status == models.IntegrationSyncStatus.NEVER)
    return GoalPlan(integration.id, integration.client_id, client.owner_id, integration.platform, signature(integration, client), token,
        profile, filters, goals or None, counters, tuple(days),
        latest_goal_names(db, integration.id, goals) if goals else {})


def apply(db, plan, rows, missing):
    from automation.sync import _notify_missing_metrika_goals
    # Client first, then integration: both settings/ownership and pause/delete are
    # stable through the write COMMIT. No network work below these locks.
    client = db.scalar(select(models.Client).where(models.Client.id == plan.client_id).with_for_update())
    integration = db.scalar(select(models.Integration).where(
        models.Integration.id == plan.integration_id).with_for_update())
    if client is None or integration is None or signature(integration, client) != plan.settings:
        raise GoalSettingsChanged("Metrika settings changed during collection")
    replace_goal_window(db, integration, plan.days, rows, missing, plan.known_names, _notify_missing_metrika_goals)


async def execute(factory, payload, *, kind="goals"):
    if kind not in {"goals", "history.backfill"}:
        raise ValueError("Unsupported Metrika execution kind")
    if current_fence.get() is None:
        raise LeaseLost("Goals-only work requires the durable executor")
    with factory.begin() as db:
        from automation.integration_work_scope import require_scope, IntegrationScopeChanged
        integration, _ = require_scope(db, payload, kind=kind, integration_id=payload["integration_id"])
        if kind == "history.backfill" and integration.platform != models.IntegrationPlatform.YANDEX_METRIKA:
            raise IntegrationScopeChanged("Detached history collection requires standalone Metrika")
        plan = prepare(db, uuid.UUID(payload["integration_id"]), payload["date_from"], payload["date_to"])
        # READ COMMITTED may observe an ownership/project change between the
        # guard and preparation. Never adopt that new scope into this old job.
        if plan is not None and (str(plan.integration_id) != payload["integration_id"]
                or str(plan.client_id) != payload["client_id"] or str(plan.owner_id) != payload["owner_id"]
                or (kind == "history.backfill" and plan.platform != models.IntegrationPlatform.YANDEX_METRIKA)):
            raise IntegrationScopeChanged("Integration scope changed during goals preparation")
    if plan is None:
        return "skipped"
    from automation.yandex_metrica import YandexMetricaAPI
    from automation.request_queue import get_request_queue
    from automation.sync import METRIKA_STATS_METRICS_LIMIT
    api = YandexMetricaAPI(plan.token, client_login=plan.profile)
    queue = await get_request_queue()
    rows, missing = await collect_goal_rows(api, queue, plan.counters, plan.goals, plan.days,
        plan.known_names, filters=plan.filters, batch_size=METRIKA_STATS_METRICS_LIMIT)
    with factory.begin() as db:
        apply(db, plan, rows, missing)
        if kind == "history.backfill":
            from backend_api.services.project_settings import update_actual_start_date
            update_actual_start_date(db, plan.client_id)
    if kind == "history.backfill":
        # Invalidate only after committed statistics are visible to readers.
        # Historical collection must not advance the current sync watermark.
        from backend_api.cache_service import CacheService
        CacheService.invalidate_client(str(plan.client_id))
    return "updated"
