import datetime as dt
import json
import uuid

import pytest

from ops.provider_peak_scope import assess, load_and_assess


NOW = dt.datetime(2026, 9, 20, 18, 0, tzinfo=dt.timezone.utc)
IMAGE = "sha256:" + "a" * 64
SCHEMA = "bc8d9e0f1a2b"


def scope():
    return {
        "format": "admirra-provider-peak-scope-v1",
        "approved_at": "2026-09-20T17:30:00Z",
        "expires_at": "2026-09-20T20:00:00Z",
        "owner": "product-owner",
        "operator": "release-operator",
        "release": {"candidate_image": IMAGE, "expected_schema": SCHEMA},
        "target": {
            "tenant_ids": [str(uuid.UUID(int=1))],
            "client_ids": [str(uuid.UUID(int=2))],
            "integration_ids": [str(uuid.UUID(int=3))],
            "provider_calls_approved": True,
        },
        "limits": {
            "max_concurrency": 4,
            "max_duration_minutes": 20,
            "operations": {
                "manual_sync": 2,
                "nightly_sync": 2,
                "report_render": 1,
                "report_delivery": 0,
                "assistant": 2,
                "billing_replay": 1,
            },
        },
        "safety": {
            "recipient_policy": "disabled",
            "sandbox_recipient_configured": False,
            "billing_sandbox_only": True,
            "production_messages_allowed": False,
            "production_charges_allowed": False,
            "all_projects_force_sync_allowed": False,
        },
    }


def verdict(value):
    return assess(value, now=NOW, expected_image=IMAGE, expected_schema=SCHEMA)


def test_complete_bounded_scope_passes():
    assert verdict(scope()) == []


@pytest.mark.parametrize("key", ["owner", "operator"])
def test_required_people_placeholders_fail(key):
    value = scope()
    value[key] = "REQUIRED"
    assert verdict(value)


@pytest.mark.parametrize("key", ["tenant_ids", "client_ids", "integration_ids"])
def test_target_ids_must_be_canonical_uuid_lists(key):
    value = scope()
    value["target"][key] = ["not-a-uuid"]
    assert verdict(value)


@pytest.mark.parametrize(
    "field,value",
    [("max_concurrency", 5), ("max_concurrency", True), ("max_duration_minutes", 31)],
)
def test_runtime_limits_are_bounded(field, value):
    item = scope()
    item["limits"][field] = value
    assert verdict(item)


@pytest.mark.parametrize("operation", ["manual_sync", "nightly_sync", "report_render", "assistant", "billing_replay"])
def test_required_operation_paths_cannot_be_skipped(operation):
    value = scope()
    value["limits"]["operations"][operation] = 0
    assert verdict(value)


def test_delivery_requires_configured_sandbox_recipient():
    value = scope()
    value["limits"]["operations"]["report_delivery"] = 1
    assert verdict(value)
    value["safety"]["recipient_policy"] = "sandbox"
    value["safety"]["sandbox_recipient_configured"] = True
    assert verdict(value) == []


@pytest.mark.parametrize(
    "key",
    ["production_messages_allowed", "production_charges_allowed", "all_projects_force_sync_allowed"],
)
def test_production_side_effects_are_forbidden(key):
    value = scope()
    value["safety"][key] = True
    assert verdict(value)


def test_scope_is_fresh_and_expires_within_one_day():
    stale = scope()
    stale["approved_at"] = "2026-09-19T16:00:00Z"
    stale["expires_at"] = "2026-09-21T19:00:00Z"
    assert len(verdict(stale)) >= 2


def test_scope_digest_binds_evidence_to_exact_bytes(tmp_path):
    path = tmp_path / "scope.json"
    path.write_text(json.dumps(scope(), sort_keys=True))
    digest, errors = load_and_assess(path, now=NOW, expected_image=IMAGE, expected_schema=SCHEMA)
    assert errors == []
    assert digest.startswith("sha256:") and len(digest) == 71


@pytest.mark.parametrize("bad", [[{}], [["nested"]], [True], [None]])
def test_malformed_uuid_lists_fail_without_crashing(bad):
    value = scope()
    value["target"]["client_ids"] = bad
    assert verdict(value)


@pytest.mark.parametrize("bad", [None, "one", {}, [], True])
def test_malformed_sandbox_counts_fail_without_crashing(bad):
    value = scope()
    value["safety"]["recipient_policy"] = "sandbox"
    value["limits"]["operations"]["report_delivery"] = bad
    assert verdict(value)


def test_non_text_approval_is_rejected():
    value = scope()
    value["owner"] = {"approved": True}
    assert verdict(value)
