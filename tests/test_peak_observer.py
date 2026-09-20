import datetime as dt
import json

import pytest

from ops.peak_observer import (
    atomic_write,
    docker_process_memory,
    docker_sample,
    docker_states,
    observe,
    parse_bytes,
    validate_names,
)


NAMES = ("admirra-sync-manual-1", "admirra-reports-1")


def runner_factory(*, restart_after=0, oom_after=False, status_after="running"):
    calls = {"inspect": 0, "stats": 0}

    def runner(command):
        if command[1] == "inspect":
            calls["inspect"] += 1
            final = calls["inspect"] > 1
            restart = restart_after if final else 0
            oom = "true" if final and oom_after else "false"
            status = status_after if final else "running"
            return "\n".join(
                json.dumps("/" + name) + f"|{restart}|{oom}|" + json.dumps(status)
                for name in NAMES
            )
        if command[1] == "top":
            return "PID\n101\n102\n"
        calls["stats"] += 1
        memory = "100MiB" if calls["stats"] == 1 else "125MiB"
        return "\n".join(
            json.dumps({
                "Name": name,
                "CPUPerc": "12.5%",
                "MemUsage": f"{memory} / 768MiB",
                "MemPerc": "16.28%",
                "PIDs": "4",
            })
            for name in NAMES
        )

    return runner


def host_reader():
    return {"memory_available_bytes": 2_000_000_000, "load_1": 1.25, "load_5": 0.75}


def process_reader(pid):
    assert pid in {101, 102}
    return 1000 * pid, 800 * pid


def clock():
    return dt.datetime(2026, 9, 20, 18, 0, tzinfo=dt.timezone.utc)


@pytest.mark.parametrize(
    "value,expected",
    [("1B", 1), ("1.5KiB", 1536), ("2MiB", 2 * 1024**2), ("0.5GB", 500_000_000)],
)
def test_parse_docker_bytes(value, expected):
    assert parse_bytes(value) == expected


@pytest.mark.parametrize("names", [[], ["a", "a"], ["bad/name"], ["a"] * 17])
def test_container_inventory_is_bounded(names):
    with pytest.raises(ValueError):
        validate_names(names)


def test_docker_parsers_keep_only_resource_and_state_fields():
    runner = runner_factory()
    states = docker_states(NAMES, runner=runner)
    stats = docker_sample(NAMES, runner=runner)
    assert states[NAMES[0]] == {"restart_count": 0, "oom_killed": False, "status": "running"}
    assert stats[NAMES[0]]["memory_bytes"] == 100 * 1024**2
    assert set(stats[NAMES[0]]) == {"cpu_pct", "memory_bytes", "memory_pct", "pids"}


def test_process_memory_sums_only_rss_and_pss():
    memory = docker_process_memory(NAMES, runner=runner_factory(), reader=process_reader)
    assert memory[NAMES[0]] == {
        "rss_bytes": 203000,
        "pss_bytes": 162400,
        "processes_observed": 2,
    }


def test_observer_aggregates_without_logs_or_environment():
    sleeps = []
    result = observe(
        NAMES,
        samples=2,
        interval=1,
        runner=runner_factory(),
        process_reader=process_reader,
        host_reader=host_reader,
        sleep=sleeps.append,
        now=clock,
    )
    assert result["status"] == "pass"
    assert result["containers"][NAMES[0]]["max_memory_bytes"] == 125 * 1024**2
    assert result["containers"][NAMES[0]]["restart_delta"] == 0
    assert result["containers"][NAMES[0]]["max_rss_bytes"] == 203000
    assert result["containers"][NAMES[0]]["max_pss_bytes"] == 162400
    assert result["host"]["min_memory_available_bytes"] == 2_000_000_000
    assert result["scope_digest"] is None
    assert sleeps == [1]
    assert "secret" not in json.dumps(result)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"restart_after": 1},
        {"oom_after": True},
        {"status_after": "exited"},
    ],
)
def test_observer_fails_on_container_health_regression(kwargs):
    result = observe(
        NAMES,
        samples=2,
        interval=0.25,
        runner=runner_factory(**kwargs),
        process_reader=process_reader,
        host_reader=host_reader,
        sleep=lambda _: None,
        now=clock,
    )
    assert result["status"] == "failed"


def test_observer_rejects_unbounded_runtime():
    with pytest.raises(ValueError):
        observe(NAMES, samples=1800, interval=2, runner=runner_factory(), host_reader=host_reader)


def test_evidence_file_is_private_and_atomic(tmp_path):
    path = tmp_path / "peak.json"
    atomic_write(path, {"status": "pass"})
    assert path.stat().st_mode & 0o777 == 0o600
    assert json.loads(path.read_text()) == {"status": "pass"}


def test_low_host_reserve_is_not_reported_as_pass():
    result = observe(NAMES, samples=2, interval=1, runner=runner_factory(),
        process_reader=process_reader, host_reader=lambda: {
            "memory_available_bytes": 512 * 1024**2, "load_1": 1, "load_5": 1},
        sleep=lambda _: None, now=clock)
    assert result["status"] == "failed"
    assert result["provider_peak_accepted"] is False


def test_measurement_time_counts_towards_deadline():
    times = iter([0, 0, 60])
    with pytest.raises(TimeoutError):
        observe(NAMES, samples=2, interval=1, max_duration_seconds=30,
            monotonic=lambda: next(times), runner=runner_factory(),
            process_reader=process_reader, host_reader=host_reader,
            sleep=lambda _: None, now=clock)
