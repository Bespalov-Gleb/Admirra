#!/usr/bin/env python3
"""Fail-closed validator for an AdMirra production cutover evidence bundle.

The bundle is deliberately data-only: collectors may run on different hosts,
while this validator never needs production credentials and never prints the
bundle (which may contain internal identifiers). It is the final admission
gate, not a substitute for collecting fresh evidence.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo


FORMAT = "admirra-cutover-evidence-v1"
SHA_RE = re.compile(r"[0-9a-f]{40}\Z")
IMAGE_RE = re.compile(r"sha256:[0-9a-f]{64}\Z")
SCHEMA_RE = re.compile(r"[0-9a-f]{12}\Z")
BACKUP_RE = re.compile(r"[0-9]{8}T[0-9]{6}Z-[0-9a-f]{8}\Z")
MOSCOW = ZoneInfo("Europe/Moscow")


@dataclass
class Verdict:
    checks: dict[str, bool] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)

    def check(self, name: str, condition: bool, message: str) -> None:
        passed = condition is True
        self.checks[name] = passed
        if not passed:
            self.errors.append(message)

    @property
    def passed(self) -> bool:
        return not self.errors


def _mapping(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


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
    if parsed.tzinfo is None:
        return None
    return parsed.astimezone(dt.timezone.utc)


def _fresh(
    verdict: Verdict,
    name: str,
    value: Any,
    now: dt.datetime,
    maximum_age: dt.timedelta,
) -> dt.datetime | None:
    parsed = _timestamp(value)
    verdict.check(f"{name}_timestamp", parsed is not None, f"{name} timestamp is missing or invalid")
    if parsed is None:
        return None
    age = now - parsed
    verdict.check(
        f"{name}_fresh",
        -dt.timedelta(minutes=5) <= age <= maximum_age,
        f"{name} evidence is stale or dated in the future",
    )
    return parsed


def _zero(verdict: Verdict, section: dict[str, Any], key: str, message: str) -> None:
    value = section.get(key)
    verdict.check(key, type(value) is int and value == 0, message)


def assess(
    evidence: dict[str, Any],
    *,
    now: dt.datetime,
    expected_production_commit: str,
    expected_candidate_commit: str,
    expected_candidate_image: str,
    expected_rollback_image: str,
    expected_schema: str,
) -> Verdict:
    """Evaluate a complete evidence bundle without performing side effects."""
    verdict = Verdict()
    now = now.astimezone(dt.timezone.utc)
    verdict.check("format", evidence.get("format") == FORMAT, "unknown evidence format")
    _fresh(verdict, "observed_at", evidence.get("observed_at"), now, dt.timedelta(minutes=5))

    window = _mapping(evidence.get("window"))
    starts = _timestamp(window.get("starts_at"))
    ends = _timestamp(window.get("ends_at"))
    verdict.check("window_timestamps", starts is not None and ends is not None, "cutover window is invalid")
    if starts is not None and ends is not None:
        verdict.check("window_order", starts < ends, "cutover window start must precede its end")
        verdict.check("window_duration", ends - starts <= dt.timedelta(hours=4), "cutover window exceeds four hours")
        verdict.check("window_active", starts <= now <= ends, "current time is outside the approved cutover window")
    forbidden_hours = window.get("forbidden_hours_msk")
    verdict.check(
        "forbidden_hours_declared",
        forbidden_hours == [3, 5],
        "03:00 and 05:00 MSK must be explicitly excluded",
    )
    verdict.check(
        "forbidden_hour",
        now.astimezone(MOSCOW).hour not in {3, 5},
        "cutover is forbidden during the 03:00/05:00 MSK scheduler windows",
    )
    verdict.check("operator", _provided(window.get("operator")), "cutover operator is not assigned")

    release = _mapping(evidence.get("release"))
    verdict.check(
        "production_commit",
        SHA_RE.fullmatch(str(release.get("production_commit", ""))) is not None
        and release.get("production_commit") == expected_production_commit,
        "production commit differs from the approved baseline",
    )
    verdict.check(
        "candidate_commit",
        SHA_RE.fullmatch(str(release.get("candidate_commit", ""))) is not None
        and release.get("candidate_commit") == expected_candidate_commit,
        "candidate commit differs from the tested release",
    )
    verdict.check(
        "candidate_image",
        IMAGE_RE.fullmatch(str(release.get("candidate_image", ""))) is not None
        and release.get("candidate_image") == expected_candidate_image,
        "candidate image digest differs from the tested artifact",
    )
    verdict.check(
        "rollback_image",
        IMAGE_RE.fullmatch(str(release.get("rollback_image", ""))) is not None
        and release.get("rollback_image") == expected_rollback_image
        and release.get("rollback_image") != release.get("candidate_image"),
        "rollback image differs from the preserved production artifact",
    )
    verdict.check(
        "expected_schema",
        SCHEMA_RE.fullmatch(str(release.get("expected_schema", ""))) is not None
        and release.get("expected_schema") == expected_schema,
        "candidate schema differs from the tested migration head",
    )
    for key, message in (
        ("tracked_tree_clean", "production tracked tree is dirty"),
        ("tests_passed", "candidate regression evidence is missing"),
        ("restore_passed", "candidate restore evidence is missing"),
        ("config_validated", "candidate configuration was not validated"),
    ):
        verdict.check(key, release.get(key) is True, message)

    recovery = _mapping(evidence.get("recovery"))
    verdict.check(
        "backup_id",
        BACKUP_RE.fullmatch(str(recovery.get("backup_id", ""))) is not None,
        "external recovery point identifier is invalid",
    )
    _fresh(verdict, "backup_created_at", recovery.get("created_at"), now, dt.timedelta(hours=2))
    _fresh(verdict, "restore_drill_at", recovery.get("restore_drill_at"), now, dt.timedelta(days=7))
    verdict.check(
        "manifest_verified",
        recovery.get("manifest_verified") is True,
        "backup release manifest was not verified",
    )
    external_ready = all(
        recovery.get(key) is True
        for key in (
            "external_to_runtime_hosts",
            "versioned_or_immutable",
            "key_escrow_confirmed",
            "pitr_chain_healthy",
        )
    )
    exception = _mapping(recovery.get("temporary_launch_exception"))
    exception_expires = _timestamp(exception.get("expires_at"))
    exception_ready = (
        exception.get("owner_accepted") is True
        and exception.get("server2_backup_verified") is True
        and exception.get("offline_key_copy_confirmed") is True
        and _provided(exception.get("owner"))
        and exception_expires is not None
        and now < exception_expires <= now + dt.timedelta(days=30)
    )
    verdict.check(
        "recovery_policy",
        external_ready or exception_ready,
        "external recovery or a bounded owner-accepted launch exception is required",
    )
    verdict.check(
        "temporary_exception_bounded",
        external_ready or exception_expires is not None and now < exception_expires <= now + dt.timedelta(days=30),
        "temporary recovery exception is expired or exceeds 30 days",
    )

    alerts = _mapping(evidence.get("alerts"))
    _fresh(verdict, "receiver_tested_at", alerts.get("receiver_tested_at"), now, dt.timedelta(hours=24))
    _fresh(
        verdict,
        "external_heartbeat_checked_at",
        alerts.get("external_heartbeat_checked_at"),
        now,
        dt.timedelta(minutes=5),
    )
    for key, message in (
        ("firing_delivered", "firing alert was not delivered to a human"),
        ("resolved_delivered", "resolved alert was not delivered to a human"),
        ("external_heartbeat_healthy", "external heartbeat is not healthy"),
    ):
        verdict.check(key, alerts.get(key) is True, message)

    runtime = _mapping(evidence.get("runtime"))
    for key, message in (
        ("active_deployments", "another deployment is active"),
        ("active_legacy_sync", "legacy sync jobs are active"),
        ("active_reports", "report deliveries are active"),
        ("active_ai_operations", "AI operations are active"),
        ("uncertain_background_jobs", "background jobs require reconciliation"),
        ("expired_leases", "expired job leases exist"),
        ("firing_alerts", "monitoring has firing alerts"),
    ):
        _zero(verdict, runtime, key, message)
    for key, message in (
        ("production_ready", "production API is not ready"),
        ("api2_ready", "private API-2 is not ready"),
        ("capacity_pass", "reviewed capacity gate failed"),
        ("worker_boot_passed", "worker boot smoke failed"),
        ("read_load_passed", "restored read-load smoke failed"),
        ("provider_peak_accepted", "provider/report/AI/billing peak is not accepted"),
    ):
        verdict.check(key, runtime.get(key) is True, message)

    approval = _mapping(evidence.get("approval"))
    verdict.check("owner_approved", approval.get("owner_approved") is True, "owner cutover approval is missing")
    verdict.check(
        "approved_test_scope",
        _provided(approval.get("test_scope")),
        "approved test tenant/scope is missing",
    )
    verdict.check(
        "rollback_operator",
        _provided(approval.get("rollback_operator")),
        "rollback operator is not assigned",
    )
    return verdict


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("evidence", type=Path)
    parser.add_argument("--expected-production-commit", required=True)
    parser.add_argument("--expected-candidate-commit", required=True)
    parser.add_argument("--expected-candidate-image", required=True)
    parser.add_argument("--expected-rollback-image", required=True)
    parser.add_argument("--expected-schema", required=True)
    args = parser.parse_args()
    try:
        raw = args.evidence.read_text(encoding="utf-8")
        if len(raw) > 256 * 1024:
            raise ValueError("evidence file is too large")
        evidence = json.loads(raw)
        if not isinstance(evidence, dict):
            raise ValueError("evidence root must be an object")
        verdict = assess(
            evidence,
            now=dt.datetime.now(dt.timezone.utc),
            expected_production_commit=args.expected_production_commit,
            expected_candidate_commit=args.expected_candidate_commit,
            expected_candidate_image=args.expected_candidate_image,
            expected_rollback_image=args.expected_rollback_image,
            expected_schema=args.expected_schema,
        )
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        print(json.dumps({"status": "blocked", "errors": ["cutover evidence is unreadable or invalid"]}))
        return 2
    print(json.dumps(
        {
            "status": "pass" if verdict.passed else "blocked",
            "checks": verdict.checks,
            "errors": verdict.errors,
        },
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    ))
    return 0 if verdict.passed else 2


if __name__ == "__main__":
    raise SystemExit(main())
