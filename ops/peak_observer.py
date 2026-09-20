#!/usr/bin/env python3
"""Bounded host/container observer for an approved provider peak run.

The observer executes only fixed Docker read commands, never reads container
environment or logs, and stores aggregate resource measurements without
customer identifiers or response bodies. It does not start workload itself.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import math
import os
import re
import signal
import subprocess
import tempfile
import time
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any

if __package__:
    from .provider_peak_scope import load_and_assess
else:
    from provider_peak_scope import load_and_assess


NAME_RE = re.compile(r"[a-zA-Z0-9][a-zA-Z0-9_.-]{0,127}\Z")
BYTE_UNITS = {
    "b": 1,
    "kb": 1000,
    "kib": 1024,
    "mb": 1000**2,
    "mib": 1024**2,
    "gb": 1000**3,
    "gib": 1024**3,
}
MAX_OUTPUT = 1024 * 1024


def validate_names(values: Sequence[str]) -> tuple[str, ...]:
    names = tuple(values)
    if not 1 <= len(names) <= 16 or len(names) != len(set(names)):
        raise ValueError("one to sixteen unique container names are required")
    if any(NAME_RE.fullmatch(name) is None for name in names):
        raise ValueError("invalid container name")
    return names


def parse_bytes(value: str) -> int:
    match = re.fullmatch(r"\s*(\d+(?:\.\d+)?)\s*([kmgt]?i?b)\s*", value, re.IGNORECASE)
    if match is None or match.group(2).lower() not in BYTE_UNITS:
        raise ValueError("invalid Docker byte value")
    return round(float(match.group(1)) * BYTE_UNITS[match.group(2).lower()])


def parse_percent(value: str) -> float:
    if not isinstance(value, str) or not value.endswith("%"):
        raise ValueError("invalid Docker percentage")
    parsed = float(value[:-1])
    if not 0 <= parsed <= 10000:
        raise ValueError("Docker percentage is outside bounds")
    return round(parsed, 3)


def run_command(command: list[str]) -> str:
    result = subprocess.run(command, capture_output=True, text=True, timeout=15, check=True)
    if len(result.stdout.encode("utf-8")) > MAX_OUTPUT:
        raise RuntimeError("observer command output exceeded limit")
    return result.stdout


def docker_states(names: tuple[str, ...], *, runner: Callable[[list[str]], str] = run_command) -> dict[str, dict]:
    template = '{{json .Name}}|{{.RestartCount}}|{{.State.OOMKilled}}|{{json .State.Status}}'
    output = runner(["docker", "inspect", "--format", template, *names])
    states: dict[str, dict] = {}
    for line in output.splitlines():
        parts = line.split("|", 3)
        if len(parts) != 4:
            raise RuntimeError("unexpected Docker inspect output")
        name = json.loads(parts[0]).lstrip("/")
        states[name] = {
            "restart_count": int(parts[1]),
            "oom_killed": parts[2].lower() == "true",
            "status": json.loads(parts[3]),
        }
    if set(states) != set(names):
        raise RuntimeError("Docker inspect container set differs")
    return states


def docker_sample(names: tuple[str, ...], *, runner: Callable[[list[str]], str] = run_command) -> dict[str, dict]:
    output = runner(["docker", "stats", "--no-stream", "--format", "{{json .}}", *names])
    samples: dict[str, dict] = {}
    for line in output.splitlines():
        raw = json.loads(line)
        name = str(raw.get("Name", ""))
        usage = str(raw.get("MemUsage", "")).split("/", 1)[0]
        samples[name] = {
            "cpu_pct": parse_percent(raw.get("CPUPerc")),
            "memory_bytes": parse_bytes(usage),
            "memory_pct": parse_percent(raw.get("MemPerc")),
            "pids": int(raw.get("PIDs")),
        }
    if set(samples) != set(names):
        raise RuntimeError("Docker stats container set differs")
    if any(item["pids"] < 0 for item in samples.values()):
        raise RuntimeError("negative Docker PID count")
    return samples


def read_process_memory(pid: int) -> tuple[int, int]:
    rss_kib = pss_kib = None
    for line in Path(f"/proc/{pid}/smaps_rollup").read_text(encoding="ascii").splitlines():
        key, separator, value = line.partition(":")
        if separator and key in {"Rss", "Pss"}:
            amount, unit = value.strip().split()
            if unit != "kB":
                raise RuntimeError("unexpected smaps unit")
            if key == "Rss":
                rss_kib = int(amount)
            else:
                pss_kib = int(amount)
    if rss_kib is None or pss_kib is None:
        raise RuntimeError("required smaps fields are missing")
    return rss_kib * 1024, pss_kib * 1024


def docker_process_memory(
    names: tuple[str, ...],
    *,
    runner: Callable[[list[str]], str] = run_command,
    reader: Callable[[int], tuple[int, int]] = read_process_memory,
) -> dict[str, dict[str, int]]:
    result = {}
    for name in names:
        lines = runner(["docker", "top", name, "-eo", "pid"]).splitlines()
        if not lines or lines[0].strip().upper() != "PID" or not 1 <= len(lines) - 1 <= 512:
            raise RuntimeError("unexpected Docker process inventory")
        pids = [int(line.strip()) for line in lines[1:]]
        if any(pid <= 0 for pid in pids) or len(pids) != len(set(pids)):
            raise RuntimeError("invalid Docker process inventory")
        total_rss = total_pss = observed = 0
        for pid in pids:
            try:
                rss, pss = reader(pid)
            except FileNotFoundError:
                continue
            total_rss += rss
            total_pss += pss
            observed += 1
        if observed == 0:
            raise RuntimeError("Docker processes disappeared during memory sample")
        result[name] = {"rss_bytes": total_rss, "pss_bytes": total_pss, "processes_observed": observed}
    return result


def host_sample(
    *,
    meminfo: Path = Path("/proc/meminfo"),
    loadavg: Path = Path("/proc/loadavg"),
) -> dict[str, float | int]:
    memory = {}
    for line in meminfo.read_text(encoding="ascii").splitlines():
        key, separator, value = line.partition(":")
        if separator and key in {"MemTotal", "MemAvailable"}:
            amount, unit = value.strip().split()
            if unit != "kB":
                raise RuntimeError("unexpected meminfo unit")
            memory[key] = int(amount) * 1024
    if set(memory) != {"MemTotal", "MemAvailable"}:
        raise RuntimeError("required meminfo fields are missing")
    load_parts = loadavg.read_text(encoding="ascii").split()
    if len(load_parts) < 3:
        raise RuntimeError("loadavg is incomplete")
    return {
        "memory_total_bytes": memory["MemTotal"],
        "memory_available_bytes": memory["MemAvailable"],
        "load_1": float(load_parts[0]),
        "load_5": float(load_parts[1]),
        "load_15": float(load_parts[2]),
    }


def observe(
    names: Sequence[str],
    *,
    samples: int,
    interval: float,
    runner: Callable[[list[str]], str] = run_command,
    process_reader: Callable[[int], tuple[int, int]] = read_process_memory,
    host_reader: Callable[[], dict[str, float | int]] = host_sample,
    sleep: Callable[[float], None] = time.sleep,
    now: Callable[[], dt.datetime] = lambda: dt.datetime.now(dt.timezone.utc),
    scope_digest: str | None = None,
    max_duration_seconds: float = 1800,
    monotonic: Callable[[], float] = time.monotonic,
) -> dict[str, Any]:
    names = validate_names(names)
    if (type(samples) is not int or not 2 <= samples <= 1800
            or not math.isfinite(interval) or not 0.25 <= interval <= 60
            or not math.isfinite(max_duration_seconds) or not 0 < max_duration_seconds <= 1800
            or samples * interval > max_duration_seconds):
        raise ValueError("observer duration is outside bounds")
    deadline = monotonic() + max_duration_seconds
    started_at = now()
    before = docker_states(names, runner=runner)
    aggregates = {
        name: {
            "max_cpu_pct": 0.0,
            "max_memory_bytes": 0,
            "max_memory_pct": 0.0,
            "max_pids": 0,
            "max_rss_bytes": 0,
            "max_pss_bytes": 0,
        }
        for name in names
    }
    host = {"min_memory_available_bytes": None, "max_load_1": 0.0, "max_load_5": 0.0}
    for index in range(samples):
        if monotonic() >= deadline:
            raise TimeoutError("observer exceeded approved duration")
        for name, item in docker_sample(names, runner=runner).items():
            row = aggregates[name]
            row["max_cpu_pct"] = max(row["max_cpu_pct"], item["cpu_pct"])
            row["max_memory_bytes"] = max(row["max_memory_bytes"], item["memory_bytes"])
            row["max_memory_pct"] = max(row["max_memory_pct"], item["memory_pct"])
            row["max_pids"] = max(row["max_pids"], item["pids"])
        for name, item in docker_process_memory(names, runner=runner, reader=process_reader).items():
            row = aggregates[name]
            row["max_rss_bytes"] = max(row["max_rss_bytes"], item["rss_bytes"])
            row["max_pss_bytes"] = max(row["max_pss_bytes"], item["pss_bytes"])
        host_item = host_reader()
        available = int(host_item["memory_available_bytes"])
        host["min_memory_available_bytes"] = (
            available if host["min_memory_available_bytes"] is None
            else min(host["min_memory_available_bytes"], available)
        )
        host["max_load_1"] = max(host["max_load_1"], float(host_item["load_1"]))
        host["max_load_5"] = max(host["max_load_5"], float(host_item["load_5"]))
        if index + 1 < samples:
            sleep(interval)
    after = docker_states(names, runner=runner)
    for name in names:
        aggregates[name]["restart_delta"] = after[name]["restart_count"] - before[name]["restart_count"]
        aggregates[name]["oom_killed"] = after[name]["oom_killed"]
        aggregates[name]["final_status"] = after[name]["status"]
    completed_at = now()
    if monotonic() >= deadline:
        raise TimeoutError("observer exceeded approved duration")
    passed = all(
        row["restart_delta"] == 0 and row["oom_killed"] is False and row["final_status"] == "running"
        and row["max_memory_pct"] < 100
        and before[name]["status"] == "running" and before[name]["oom_killed"] is False
        for name, row in aggregates.items()
    ) and host["min_memory_available_bytes"] >= 1536 * 1024**2
    return {
        "format": "admirra-provider-peak-observer-v1",
        "started_at": started_at.isoformat().replace("+00:00", "Z"),
        "completed_at": completed_at.isoformat().replace("+00:00", "Z"),
        "status": "pass" if passed else "failed",
        "provider_peak_accepted": False,
        "sample_count": samples,
        "interval_seconds": interval,
        "scope_digest": scope_digest,
        "containers": aggregates,
        "host": host,
    }


def atomic_write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix="." + path.name + ".", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary, 0o600)
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--container", action="append", required=True)
    parser.add_argument("--samples", type=int, default=150)
    parser.add_argument("--interval", type=float, default=2.0)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--scope-file", type=Path, required=True)
    parser.add_argument("--expected-image", required=True)
    parser.add_argument("--expected-schema", required=True)
    args = parser.parse_args()
    try:
        scope_digest, scope_errors = load_and_assess(
            args.scope_file,
            now=dt.datetime.now(dt.timezone.utc),
            expected_image=args.expected_image,
            expected_schema=args.expected_schema,
        )
        if scope_errors:
            raise ValueError("approved peak scope is invalid")
        scope_bytes = args.scope_file.read_bytes()
        scope = json.loads(scope_bytes)
        # Bind duration to the same bytes that were validated, not a replaced file.
        import hashlib
        if "sha256:" + hashlib.sha256(scope_bytes).hexdigest() != scope_digest:
            raise ValueError("scope changed during validation")
        expires = dt.datetime.fromisoformat(scope["expires_at"].replace("Z", "+00:00"))
        maximum = min(scope["limits"]["max_duration_minutes"] * 60,
                      (expires - dt.datetime.now(dt.timezone.utc)).total_seconds())
        if maximum <= 0 or args.samples * args.interval > maximum:
            raise ValueError("observer exceeds approved scope window")
        def expired(*_):
            raise TimeoutError("observer exceeded approved scope window")
        signal.signal(signal.SIGALRM, expired)
        signal.setitimer(signal.ITIMER_REAL, maximum)
        result = observe(
            args.container,
            samples=args.samples,
            interval=args.interval,
            scope_digest=scope_digest,
            max_duration_seconds=maximum,
        )
        atomic_write(args.output, result)
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError, json.JSONDecodeError):
        print(json.dumps({"status": "blocked", "error": "peak observer failed; inspect host diagnostics privately"}))
        return 2
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
    print(json.dumps({"status": result["status"], "output": str(args.output), "samples": result["sample_count"]}))
    return 0 if result["status"] == "pass" else 2


if __name__ == "__main__":
    raise SystemExit(main())
