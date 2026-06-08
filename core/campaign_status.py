from datetime import datetime, timezone


ACTIVE_STATUSES = {"ACTIVE", "ACCEPTED"}
ACTIVE_STATES = {"ON", "ACTIVE"}
PAUSED_STATUSES = {
    "BLOCKED",
    "DRAFT",
    "MODERATION",
    "PREACCEPTED",
    "SUSPENDED",
    "STOPPED",
    "PAUSED",
    "OFF",
}
PAUSED_STATES = {"OFF", "SUSPENDED", "ENDED", "STOPPED", "PAUSED", "BLOCKED"}
ARCHIVED_STATUSES = {"ARCHIVED", "DELETED", "CONVERTED"}
ARCHIVED_STATES = {"ARCHIVED", "DELETED", "CONVERTED"}

STATUS_LABELS = {
    "active": "Активна",
    "paused": "Приостановлена",
    "archived": "Архив",
    "unknown": "Неизвестно",
}


def normalize_platform_status(raw_status: str | None = None, raw_state: str | None = None) -> str:
    status = str(raw_status or "").strip().upper()
    state = str(raw_state or "").strip().upper()

    if state in ARCHIVED_STATES or status in ARCHIVED_STATUSES:
        return "archived"
    if state in PAUSED_STATES or status in PAUSED_STATUSES:
        return "paused"
    if state in ACTIVE_STATES or status in ACTIVE_STATUSES:
        return "active"
    return "unknown"


def status_label(display_status: str | None) -> str:
    return STATUS_LABELS.get(str(display_status or "").strip().lower(), STATUS_LABELS["unknown"])


def apply_platform_status(campaign, data: dict | None) -> str:
    data = data or {}
    raw_status = data.get("status")
    raw_state = data.get("state")
    display_status = normalize_platform_status(raw_status, raw_state)

    campaign.platform_status = str(raw_status) if raw_status not in (None, "") else None
    campaign.platform_state = str(raw_state) if raw_state not in (None, "") else None
    campaign.display_status = display_status
    campaign.status_synced_at = datetime.now(timezone.utc)
    return display_status
