#!/usr/bin/env python3
"""Fail-closed validator for an approved AdMirra provider peak test scope."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
import uuid
from pathlib import Path
from typing import Any


FORMAT = "admirra-provider-peak-scope-v1"
IMAGE_RE = re.compile(r"sha256:[0-9a-f]{64}\Z")
SCHEMA_RE = re.compile(r"[0-9a-f]{12}\Z")
OPERATION_LIMITS = {
    "manual_sync": (1, 4),
    "nightly_sync": (1, 4),
    "report_render": (1, 3),
    "report_delivery": (0, 2),
    "assistant": (1, 6),
    "billing_replay": (1, 3),
}


def _provided(value: Any) -> bool:
    text = value.strip() if isinstance(value, str) else ""
    return bool(text) and not text.upper().startswith("REQUIRED")


def _timestamp(value: Any) -> dt.datetime | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed.astimezone(dt.timezone.utc) if parsed.tzinfo else None


def _uuid_list(value: Any, *, minimum: int, maximum: int) -> bool:
    if (not isinstance(value, list) or not minimum <= len(value) <= maximum
            or not all(isinstance(item, str) for item in value)
            or len(value) != len(set(value))):
        return False
    try:
        return all(str(uuid.UUID(item)) == item for item in value if isinstance(item, str)) and all(
            isinstance(item, str) for item in value
        )
    except (ValueError, AttributeError):
        return False


def assess(
    scope: dict[str, Any],
    *,
    now: dt.datetime,
    expected_image: str,
    expected_schema: str,
) -> list[str]:
    errors: list[str] = []
    now = now.astimezone(dt.timezone.utc)
    if scope.get("format") != FORMAT:
        errors.append("unknown scope format")
    approved_at = _timestamp(scope.get("approved_at"))
    expires_at = _timestamp(scope.get("expires_at"))
    if approved_at is None or not -dt.timedelta(minutes=5) <= now - approved_at <= dt.timedelta(hours=24):
        errors.append("approval is missing, stale or dated in the future")
    if expires_at is None or not now < expires_at <= now + dt.timedelta(hours=24):
        errors.append("scope expiry is missing or outside 24 hours")
    if approved_at is not None and expires_at is not None and expires_at > approved_at + dt.timedelta(hours=24):
        errors.append("scope lifetime exceeds 24 hours")
    for key in ("owner", "operator"):
        if not _provided(scope.get(key)):
            errors.append(f"{key} is not assigned")

    release = scope.get("release") if isinstance(scope.get("release"), dict) else {}
    image = release.get("candidate_image")
    schema = release.get("expected_schema")
    if IMAGE_RE.fullmatch(str(image or "")) is None or image != expected_image:
        errors.append("candidate image differs from approved artifact")
    if SCHEMA_RE.fullmatch(str(schema or "")) is None or schema != expected_schema:
        errors.append("schema differs from approved migration head")

    target = scope.get("target") if isinstance(scope.get("target"), dict) else {}
    if not _uuid_list(target.get("tenant_ids"), minimum=1, maximum=1):
        errors.append("exactly one canonical tenant UUID is required")
    if not _uuid_list(target.get("client_ids"), minimum=1, maximum=5):
        errors.append("one to five canonical client UUIDs are required")
    if not _uuid_list(target.get("integration_ids"), minimum=1, maximum=10):
        errors.append("one to ten canonical integration UUIDs are required")
    if target.get("provider_calls_approved") is not True:
        errors.append("provider calls are not explicitly approved")

    limits = scope.get("limits") if isinstance(scope.get("limits"), dict) else {}
    concurrency = limits.get("max_concurrency")
    duration = limits.get("max_duration_minutes")
    if type(concurrency) is not int or not 1 <= concurrency <= 4:
        errors.append("max concurrency must be an integer from one to four")
    if type(duration) is not int or not 5 <= duration <= 30:
        errors.append("max duration must be five to thirty minutes")
    operations = limits.get("operations") if isinstance(limits.get("operations"), dict) else {}
    if set(operations) != set(OPERATION_LIMITS):
        errors.append("operation inventory differs from reviewed peak profile")
    else:
        for operation, (minimum, maximum) in OPERATION_LIMITS.items():
            value = operations.get(operation)
            if type(value) is not int or not minimum <= value <= maximum:
                errors.append(f"{operation} count is outside bounds")

    safety = scope.get("safety") if isinstance(scope.get("safety"), dict) else {}
    for key in (
        "production_messages_allowed",
        "production_charges_allowed",
        "all_projects_force_sync_allowed",
    ):
        if safety.get(key) is not False:
            errors.append(f"{key} must be false")
    if safety.get("billing_sandbox_only") is not True:
        errors.append("billing replay must use sandbox fixtures only")
    recipient_policy = safety.get("recipient_policy")
    delivery_count = operations.get("report_delivery", 0) if isinstance(operations, dict) else 0
    if not isinstance(recipient_policy, str) or recipient_policy not in {"disabled", "sandbox"}:
        errors.append("recipient policy must be disabled or sandbox")
    if recipient_policy == "disabled" and delivery_count != 0:
        errors.append("report delivery must be zero when recipients are disabled")
    if recipient_policy == "sandbox" and (
        type(delivery_count) is not int or delivery_count < 1
        or safety.get("sandbox_recipient_configured") is not True
    ):
        errors.append("sandbox delivery requires a configured sandbox recipient")
    return errors


def load_and_assess(
    path: Path,
    *,
    now: dt.datetime,
    expected_image: str,
    expected_schema: str,
) -> tuple[str, list[str]]:
    raw = path.read_bytes()
    if len(raw) > 64 * 1024:
        raise ValueError("scope file is too large")
    scope = json.loads(raw)
    if not isinstance(scope, dict):
        raise ValueError("scope root must be an object")
    digest = "sha256:" + hashlib.sha256(raw).hexdigest()
    return digest, assess(scope, now=now, expected_image=expected_image, expected_schema=expected_schema)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("scope", type=Path)
    parser.add_argument("--expected-image", required=True)
    parser.add_argument("--expected-schema", required=True)
    args = parser.parse_args()
    try:
        digest, errors = load_and_assess(
            args.scope,
            now=dt.datetime.now(dt.timezone.utc),
            expected_image=args.expected_image,
            expected_schema=args.expected_schema,
        )
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        print(json.dumps({"status": "blocked", "errors": ["scope is unreadable or invalid"]}))
        return 2
    print(json.dumps({"status": "pass" if not errors else "blocked", "scope_digest": digest, "errors": errors}))
    return 0 if not errors else 2


if __name__ == "__main__":
    raise SystemExit(main())
