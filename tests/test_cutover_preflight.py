import datetime as dt
import json
from copy import deepcopy
from pathlib import Path

import pytest

from ops.cutover_preflight import assess


NOW = dt.datetime(2026, 9, 20, 15, 30, tzinfo=dt.timezone.utc)
PRODUCTION = "cdf0a4d3c9dee66722219d7e7e2924d5475c0044"
CANDIDATE = "acf6ed8d76ea13436152e8ccc9659346169c7040"
IMAGE = "sha256:ad9559725e724789281765526f85839b8b9adf604c114ad25850812b0c544d0a"
ROLLBACK = "sha256:" + "1" * 64
SCHEMA = "bc8d9e0f1a2b"


def evidence():
    return {
        "format": "admirra-cutover-evidence-v1",
        "observed_at": "2026-09-20T15:29:00Z",
        "window": {
            "starts_at": "2026-09-20T15:00:00Z",
            "ends_at": "2026-09-20T17:00:00Z",
            "forbidden_hours_msk": [3, 5],
            "operator": "primary-operator",
        },
        "release": {
            "production_commit": PRODUCTION,
            "candidate_commit": CANDIDATE,
            "candidate_image": IMAGE,
            "rollback_image": ROLLBACK,
            "expected_schema": SCHEMA,
            "tracked_tree_clean": True,
            "tests_passed": True,
            "restore_passed": True,
            "config_validated": True,
        },
        "recovery": {
            "backup_id": "20260920T150000Z-deadbeef",
            "created_at": "2026-09-20T15:00:00Z",
            "restore_drill_at": "2026-09-20T14:00:00Z",
            "external_to_runtime_hosts": True,
            "versioned_or_immutable": True,
            "manifest_verified": True,
            "key_escrow_confirmed": True,
            "pitr_chain_healthy": True,
        },
        "alerts": {
            "receiver_tested_at": "2026-09-20T15:00:00Z",
            "external_heartbeat_checked_at": "2026-09-20T15:29:30Z",
            "firing_delivered": True,
            "resolved_delivered": True,
            "external_heartbeat_healthy": True,
        },
        "runtime": {
            "active_deployments": 0,
            "active_legacy_sync": 0,
            "active_reports": 0,
            "active_ai_operations": 0,
            "uncertain_background_jobs": 0,
            "expired_leases": 0,
            "firing_alerts": 0,
            "production_ready": True,
            "api2_ready": True,
            "capacity_pass": True,
            "worker_boot_passed": True,
            "read_load_passed": True,
            "provider_peak_accepted": True,
        },
        "approval": {
            "owner_approved": True,
            "test_scope": "approved-test-tenant",
            "rollback_operator": "secondary-operator",
        },
    }


def run(bundle, *, now=NOW, candidate=CANDIDATE):
    return assess(
        bundle,
        now=now,
        expected_production_commit=PRODUCTION,
        expected_candidate_commit=candidate,
        expected_candidate_image=IMAGE,
        expected_rollback_image=ROLLBACK,
        expected_schema=SCHEMA,
    )


def test_complete_fresh_evidence_passes():
    verdict = run(evidence())
    assert verdict.passed
    assert verdict.errors == []
    assert all(verdict.checks.values())


@pytest.mark.parametrize(
    "section,key",
    [
        ("alerts", "firing_delivered"),
        ("alerts", "external_heartbeat_healthy"),
        ("runtime", "provider_peak_accepted"),
        ("approval", "owner_approved"),
    ],
)
def test_required_boolean_evidence_fails_closed(section, key):
    bundle = evidence()
    bundle[section][key] = False
    verdict = run(bundle)
    assert not verdict.passed
    assert verdict.checks[key] is False


@pytest.mark.parametrize(
    "key",
    [
        "active_deployments",
        "active_legacy_sync",
        "active_reports",
        "active_ai_operations",
        "uncertain_background_jobs",
        "expired_leases",
        "firing_alerts",
    ],
)
def test_active_or_uncertain_runtime_work_blocks_cutover(key):
    bundle = evidence()
    bundle["runtime"][key] = 1
    verdict = run(bundle)
    assert not verdict.passed
    assert verdict.checks[key] is False


def test_stale_snapshot_and_backup_are_rejected():
    bundle = evidence()
    bundle["observed_at"] = "2026-09-20T15:20:00Z"
    bundle["recovery"]["created_at"] = "2026-09-20T12:00:00Z"
    verdict = run(bundle)
    assert not verdict.passed
    assert verdict.checks["observed_at_fresh"] is False
    assert verdict.checks["backup_created_at_fresh"] is False


def test_stale_external_heartbeat_is_rejected():
    bundle = evidence()
    bundle["alerts"]["external_heartbeat_checked_at"] = "2026-09-20T15:20:00Z"
    verdict = run(bundle)
    assert not verdict.passed
    assert verdict.checks["external_heartbeat_checked_at_fresh"] is False


def test_bounded_owner_exception_can_temporarily_replace_external_recovery():
    bundle = evidence()
    bundle["recovery"].update({
        "external_to_runtime_hosts": False,
        "versioned_or_immutable": False,
        "key_escrow_confirmed": False,
        "pitr_chain_healthy": False,
        "temporary_launch_exception": {
            "owner_accepted": True,
            "owner": "product-owner",
            "expires_at": "2026-10-01T00:00:00Z",
            "server2_backup_verified": True,
            "offline_key_copy_confirmed": True,
        },
    })
    verdict = run(bundle)
    assert verdict.passed, verdict.errors
    assert verdict.checks["recovery_policy"] is True


def test_missing_or_unbounded_recovery_exception_is_rejected():
    bundle = evidence()
    bundle["recovery"].update({
        "external_to_runtime_hosts": False,
        "versioned_or_immutable": False,
        "key_escrow_confirmed": False,
        "pitr_chain_healthy": False,
        "temporary_launch_exception": {
            "owner_accepted": True,
            "owner": "product-owner",
            "expires_at": "2026-11-01T00:00:00Z",
            "server2_backup_verified": True,
            "offline_key_copy_confirmed": True,
        },
    })
    verdict = run(bundle)
    assert not verdict.passed
    assert verdict.checks["recovery_policy"] is False
    assert verdict.checks["temporary_exception_bounded"] is False


def test_release_mismatch_and_mutable_rollback_are_rejected():
    bundle = evidence()
    bundle["release"]["candidate_commit"] = "2" * 40
    bundle["release"]["rollback_image"] = IMAGE
    verdict = run(bundle)
    assert not verdict.passed
    assert verdict.checks["candidate_commit"] is False
    assert verdict.checks["rollback_image"] is False


def test_unpreserved_rollback_image_is_rejected():
    bundle = evidence()
    bundle["release"]["rollback_image"] = "sha256:" + "2" * 64
    verdict = run(bundle)
    assert not verdict.passed
    assert verdict.checks["rollback_image"] is False


def test_example_uses_the_preserved_backend_rollback_image():
    root = Path(__file__).parents[1]
    manifest = json.loads((root / "ops" / "rollback_images.json").read_text())
    example = json.loads((root / "ops" / "cutover_evidence.example.json").read_text())
    assert manifest["format"] == "admirra-rollback-images-v1"
    assert example["release"]["rollback_image"] == manifest["images"]["backend"]["image"]
    assert example["release"]["rollback_image"] == "sha256:047c8019bbbeec83c0c8cd11b39c03b31af2931d8e2f0b415196199f8768afe0"


def test_forbidden_scheduler_hour_blocks_even_inside_window():
    bundle = evidence()
    bundle["window"]["starts_at"] = "2026-09-21T00:00:00Z"
    bundle["window"]["ends_at"] = "2026-09-21T02:00:00Z"
    bundle["observed_at"] = "2026-09-21T00:10:00Z"
    now = dt.datetime(2026, 9, 21, 0, 10, tzinfo=dt.timezone.utc)  # 03:10 MSK
    verdict = run(bundle, now=now)
    assert not verdict.passed
    assert verdict.checks["forbidden_hour"] is False


def test_wrong_types_do_not_compare_equal_to_zero_or_true():
    bundle = evidence()
    bundle["runtime"]["active_reports"] = False
    bundle["runtime"]["capacity_pass"] = 1
    verdict = run(bundle)
    assert not verdict.passed
    assert verdict.checks["active_reports"] is False
    assert verdict.checks["capacity_pass"] is False


@pytest.mark.parametrize(
    "section,key",
    [
        ("window", "operator"),
        ("approval", "test_scope"),
        ("approval", "rollback_operator"),
    ],
)
def test_required_placeholders_are_not_accepted_as_approvals(section, key):
    bundle = evidence()
    bundle[section][key] = "REQUIRED"
    verdict = run(bundle)
    assert not verdict.passed
    check = "approved_test_scope" if key == "test_scope" else key
    assert verdict.checks[check] is False


def test_assess_does_not_mutate_evidence():
    bundle = evidence()
    original = deepcopy(bundle)
    run(bundle)
    assert bundle == original
