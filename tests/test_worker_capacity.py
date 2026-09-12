from copy import deepcopy
import json
from pathlib import Path

import pytest

from ops.check_worker_capacity import assess, worker_concurrency, memory_bytes


def prepared():
    budget = json.loads((Path(__file__).parents[1] / "ops/worker_capacity.json").read_text())
    services = {}
    for name, memory, role, children in (("broker", 512, None, 0), ("cache", 256, None, 0),
        ("sync-manual", 1536, "worker", 2), ("sync-nightly", 1536, "worker", 2),
        ("reports", 768, "worker", 1), ("maintenance", 768, "worker", 1),
        ("ai-prewarm", 768, "worker", 1), ("scheduler", 256, "scheduler", 0)):
        services[name] = {"mem_limit": memory * 1024**2, "cpus": 1,
            "command": ["python", "-m", "automation.work_worker", f"--concurrency={children}"],
            "environment": {"APP_PROCESS_ROLE": role, "DB_POOL_SIZE": "2", "DB_MAX_OVERFLOW": "0"}}
    return {"services": services}, budget


def test_worker_child_parent_heartbeat_budget():
    compose, budget = prepared()
    result = assess(compose, budget)
    assert result["capacity_pass"] and result["load_accepted"] is False
    assert result["worker_db_pool_max"] == 16  # 7 children * 2 + scheduler * 2
    assert sum(row["parent_processes"] for row in result["services"]) == 5
    assert result["memory_caps_mib"] == 6400 and result["os_headroom_mib"] == 1540


def test_api2_cannot_be_added_over_the_original_worker_caps():
    compose, budget = prepared()
    result = assess(compose, budget, with_api2=True)
    assert result["capacity_pass"] is False
    assert result["os_headroom_mib"] == 516
    assert result["errors"] == ["Host memory caps plus OS reserve exceed physical RAM"]


def test_replica_change_recomputes_connections_not_just_containers():
    compose, budget = prepared()
    compose["services"]["sync-manual"]["deploy"] = {"replicas": 2}
    result = assess(compose, budget)
    assert result["worker_db_pool_max"] == 20
    assert "Worker database role connection budget exceeded" in result["errors"]


@pytest.mark.parametrize("command", ["python -m automation.work_worker", "python -m automation.work_worker --concurrency=2 --autoscale=10,2",
    "python -m automation.work_worker --concurrency=2 --pool=threads", "python -m automation.work_worker --concurrency=0"])
def test_unbounded_or_different_pool_is_refused(command):
    with pytest.raises((ValueError, TypeError)):
        worker_concurrency(command)


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
