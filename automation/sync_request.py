"""Immutable request windows; no raw credentials are persisted in job payloads."""
from datetime import datetime, timedelta, timezone
import hashlib
import json

from core import models


def settings_digest(integration, client):
    names = (
        "client_id", "platform", "connection_status", "selected_goals", "primary_goal_id",
        "selected_counters", "lead_action_types", "access_token", "refresh_token",
        "metrika_access_token", "platform_client_id", "platform_client_secret", "account_id",
        "metrika_account_id", "is_agency", "agency_client_login", "utm_source", "oauth_app",
    )
    values = [getattr(integration, name, None) for name in names]
    values += [client.owner_id, client.status]
    return hashlib.sha256(json.dumps(values, default=str).encode()).hexdigest()


def request_params(integration, client, *, days, force_full, trigger, date_from=None, date_to=None, now=None):
    if type(days) is not int or days < 1 or type(force_full) is not bool:
        raise ValueError("Invalid sync request")
    if bool(date_from) != bool(date_to):
        raise ValueError("Both sync dates are required")
    now = now or datetime.now(timezone.utc)
    if date_from:
        start, end = (datetime.strptime(str(v), "%Y-%m-%d").date() for v in (date_from, date_to))
        if start > end:
            raise ValueError("Invalid sync date range")
    else:
        # Preserve the existing incremental-window policy, but freeze it when
        # accepted. A queue delay or midnight must not silently move the window.
        last = integration.last_sync_at
        first = last is None or integration.sync_status == models.IntegrationSyncStatus.NEVER
        if not force_full and not first:
            if last.tzinfo is None:
                last = last.replace(tzinfo=timezone.utc)
            elapsed = max(0, (now - last).days)
            if elapsed < 1:
                days = 3
            elif elapsed < days:
                days = min(elapsed + 3, days)
        end = now.date()
        start = end - timedelta(days=days)
    return {"date_from": start.isoformat(), "date_to": end.isoformat(),
            "days": (end - start).days + 1, "force_full": force_full,
            "trigger": trigger, "settings_digest": settings_digest(integration, client)}


def read_params(job):
    try:
        value = json.loads(job.params or "{}")
        return value if isinstance(value, dict) else {}
    except (TypeError, ValueError):
        return {}


def covers(existing, wanted):
    return (existing.get("settings_digest") == wanted["settings_digest"]
        and bool(existing.get("date_from")) and bool(existing.get("date_to"))
        and existing["date_from"] <= wanted["date_from"]
        and existing["date_to"] >= wanted["date_to"]
        and (not wanted["force_full"] or existing.get("force_full") is True))


def merged(existing, wanted):
    result = dict(wanted)
    # The nightly planner can widen a pending manual request, but must not
    # relabel the user's request as automatic while its queue stays manual.
    if wanted.get("trigger") == "auto" and existing.get("trigger") not in (None, "auto"):
        result["trigger"] = existing["trigger"]
    for field, operation in (("date_from", min), ("date_to", max)):
        if existing.get(field):
            result[field] = operation(existing[field], wanted[field])
    result["force_full"] = bool(existing.get("force_full") or wanted["force_full"])
    result["days"] = (datetime.fromisoformat(result["date_to"]) - datetime.fromisoformat(result["date_from"])).days + 1
    if existing.get("after_sync_job_id"):
        result["after_sync_job_id"] = existing["after_sync_job_id"]
    return result


def public_request(job):
    params = read_params(job)
    return {name: params.get(name) for name in ("date_from", "date_to", "after_sync_job_id")}
