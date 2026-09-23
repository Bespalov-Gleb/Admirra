from copy import deepcopy
import json
from pathlib import Path

import pytest

from ops.check_worker_capacity import assess, worker_concurrency, worker_queues, memory_bytes


def prepared():
    budget = json.loads((Path(__file__).parents[1] / "ops/worker_capacity.json").read_text())
    services = {}
    for name, memory, role, children, queues in (("broker", 512, None, 0, ""), ("cache", 256, None, 0, ""),
        ("sync-manual", 1280, "worker", 2, "sync.manual"),
        ("sync-nightly", 1280, "worker", 2, "sync.nightly,sync.backfill"),
        ("reports", 768, "worker", 1, "reports"), ("maintenance", 768, "worker", 1, "maintenance"),
        ("scheduler", 256, "scheduler", 0, "")):
        services[name] = {"mem_limit": memory * 1024**2, "cpus": 1,
            "command": ["python", "-m", "automation.work_worker", f"--concurrency={children}", f"--queues={queues}"],
            "environment": {"APP_PROCESS_ROLE": role, "DB_POOL_SIZE": "2", "DB_MAX_OVERFLOW": "0"}}
    return {"services": services}, budget


def test_worker_schema_expectation_requires_release_input():
    text = (Path(__file__).parents[1] / 'ops/compose.workers.yml').read_text()
    values = [line.strip() for line in text.splitlines() if 'EXPECTED_SCHEMA_REVISION:' in line]
    assert values == ['EXPECTED_SCHEMA_REVISION: ${ADMIRRA_SCHEMA_REVISION:?Set the tested migration head}']
    # One runtime anchor inherited by workers and scheduler; no old fixed head.
    assert 'environment: &runtime' in text and '<<: *runtime' in text


def test_worker_child_parent_heartbeat_budget():
    compose, budget = prepared()
    result = assess(compose, budget)
    assert result["capacity_pass"] and result["load_accepted"] is False
    assert result["worker_db_pool_max"] == 14  # 6 children * 2 + scheduler * 2
    assert sum(row["parent_processes"] for row in result["services"]) == 4
    assert result["memory_caps_mib"] == 5120 and result["os_headroom_mib"] == 2820


def test_api2_fits_launch_profile_with_os_reserve():
    compose, budget = prepared()
    result = assess(compose, budget, with_api2=True)
    assert result["capacity_pass"] is True
    assert result["os_headroom_mib"] == 1796
    assert result["errors"] == []


def test_replica_change_recomputes_connections_not_just_containers():
    compose, budget = prepared()
    compose["services"]["sync-manual"]["deploy"] = {"replicas": 2}
    result = assess(compose, budget)
    assert result["worker_db_pool_max"] == 18
    assert "Worker database role connection budget exceeded" in result["errors"]


@pytest.mark.parametrize("command", ["python -m automation.work_worker", "python -m automation.work_worker --concurrency=2 --autoscale=10,2",
    "python -m automation.work_worker --concurrency=2 --pool=threads", "python -m automation.work_worker --concurrency=0"])
def test_unbounded_or_different_pool_is_refused(command):
    with pytest.raises((ValueError, TypeError)):
        worker_concurrency(command)


def test_queue_inventory_is_explicit_and_exclusive():
    assert worker_queues(["python", "-m", "automation.work_worker", "--queues=sync.nightly,sync.backfill"]) == [
        "sync.nightly", "sync.backfill"]
    compose, budget = prepared()
    compose["services"]["maintenance"]["command"][-1] = "--queues=maintenance,ai.prewarm"
    with pytest.raises(ValueError, match="queue inventory"):
        assess(compose, budget)


def test_missing_inventory_or_limits_do_not_false_pass():
    compose, budget = prepared()
    for service in ({"cpus": 1}, {"mem_limit": 1024}, {"mem_limit": 1024, "cpus": float("nan")}):
        changed = deepcopy(compose)
        changed["services"]["broker"] = service
        with pytest.raises(ValueError):
            assess(changed, budget)
    compose["services"]["unknown"] = compose["services"]["broker"]
    with pytest.raises(ValueError, match="inventory"):
        assess(compose, budget)


@pytest.mark.parametrize("raw,expected", [("768m", 768 * 1024**2), ("1.5g", 1536 * 1024**2),
    ("1048576", 1024**2), (1048576, 1024**2), ("256MiB", 256 * 1024**2)])
def test_compose_memory_strings_and_numeric_normalization(raw, expected):
    assert memory_bytes(raw) == expected


@pytest.mark.parametrize("raw", ["unlimited", "-1g", 0, True, "1.1b", "512pct"])
def test_unknown_memory_caps_fail_closed(raw):
    with pytest.raises(ValueError):
        memory_bytes(raw)
