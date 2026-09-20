#!/usr/bin/env python3
"""Read-only health guard for the API-2 production canary.

The probe deliberately avoids application credentials and customer data.  It
emits a compact JSON result to stdout and atomically writes Prometheus textfile
metrics when ``--metrics-file`` is supplied.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable


CANARY_LINE_RE = re.compile(r"(?P<key>[a-z_]+)=(?P<value>[^ ]*)")
BACKUP_OBJECT_RE = re.compile(
    r"(?P<id>[0-9]{8}T[0-9]{6}Z-[0-9a-f]{8})\.(?P<kind>database|globals|runtime|manifest)\.age\Z"
)


@dataclass
class Result:
    role: str
    checks: dict[str, float] = field(default_factory=dict)
    metrics: dict[str, float] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def check(self, name: str, ok: bool, message: str, *, warning: bool = False) -> None:
        self.checks[name] = 1.0 if ok else 0.0
        if not ok:
            (self.warnings if warning else self.errors).append(message)

    @property
    def status(self) -> str:
        if self.errors:
            return "critical"
        if self.warnings:
            return "warning"
        return "ok"

    @property
    def exit_code(self) -> int:
        return 2 if self.errors else (1 if self.warnings else 0)


def run(command: list[str], timeout: float = 10.0) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        check=False,
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def check_disk(result: Result, path: str, warning_percent: float, critical_percent: float) -> None:
    usage = shutil.disk_usage(path)
    free_percent = usage.free / usage.total * 100.0
    result.metrics["disk_free_percent"] = free_percent
    result.check(
        "disk_critical",
        free_percent >= critical_percent,
        f"disk free below {critical_percent:.0f}%",
    )
    if free_percent >= critical_percent:
        result.check(
            "disk_warning",
            free_percent >= warning_percent,
            f"disk free below {warning_percent:.0f}%",
            warning=True,
        )


def check_wireguard(result: Result, interface: str, maximum_age: int) -> None:
    command = run(["wg", "show", interface, "latest-handshakes"])
    if command.returncode != 0:
        result.check("wireguard", False, "WireGuard status unavailable")
        return
    stamps: list[int] = []
    for line in command.stdout.splitlines():
        columns = line.split()
        if len(columns) >= 2:
            try:
                stamps.append(int(columns[1]))
            except ValueError:
                continue
    newest = max(stamps, default=0)
    age = max(0.0, time.time() - newest) if newest else float("inf")
    result.metrics["wireguard_handshake_age_seconds"] = age if newest else -1.0
    result.check(
        "wireguard",
        bool(newest) and age <= maximum_age,
        "WireGuard handshake is missing or stale",
    )


def check_http_ready(result: Result, url: str, timeout: float) -> None:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            body = response.read(64 * 1024)
            payload = json.loads(body)
            ok = response.status == 200 and payload.get("status") == "ready" and payload.get("database") == "ok"
    except (OSError, ValueError, urllib.error.URLError) as exc:
        result.check("api2_ready", False, f"API-2 readiness failed: {type(exc).__name__}")
        return
    result.check("api2_ready", ok, "API-2 readiness payload is not healthy")


def parse_timestamp(value: str) -> dt.datetime | None:
    try:
        parsed = dt.datetime.fromisoformat(value)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=dt.timezone.utc)
    return parsed


def recent_canary_rows(path: Path, window_seconds: int) -> Iterable[dict[str, str]]:
    cutoff = dt.datetime.now(dt.timezone.utc) - dt.timedelta(seconds=window_seconds)
    if not path.exists():
        raise FileNotFoundError(path)
    # The canary log is intentionally low volume. Read at most the latest 8 MiB
    # so an accidental retention failure cannot exhaust probe memory.
    size = path.stat().st_size
    with path.open("rb") as handle:
        if size > 8 * 1024 * 1024:
            handle.seek(size - 8 * 1024 * 1024)
            handle.readline()
        for raw in handle:
            line = raw.decode("utf-8", errors="replace").strip()
            if not line:
                continue
            timestamp, _, rest = line.partition(" ")
            parsed = parse_timestamp(timestamp)
            if parsed is None or parsed < cutoff:
                continue
            row = {match.group("key"): match.group("value") for match in CANARY_LINE_RE.finditer(rest)}
            if row:
                yield row


def check_ingress(result: Result, args: argparse.Namespace) -> None:
    nginx_active = run(["systemctl", "is-active", "--quiet", "nginx"])
    result.check("nginx_active", nginx_active.returncode == 0, "Nginx is not active")
    nginx_config = run(["nginx", "-t"])
    result.check("nginx_config", nginx_config.returncode == 0, "Nginx configuration test failed")
    check_http_ready(result, args.api2_ready_url, args.http_timeout)

    try:
        rows = list(recent_canary_rows(Path(args.canary_log), args.window_seconds))
    except OSError:
        result.check("canary_log", False, "Canary log is unavailable")
        return

    final_5xx = sum(1 for row in rows if row.get("status", "").startswith("5"))
    api2_attempts = sum(1 for row in rows if row.get("upstream", "").startswith("10.77.0.2:8001"))
    fallbacks = sum(1 for row in rows if "," in row.get("upstream", ""))
    result.metrics.update(
        {
            "canary_requests_window": float(len(rows)),
            "canary_final_5xx_window": float(final_5xx),
            "canary_api2_attempts_window": float(api2_attempts),
            "canary_fallbacks_window": float(fallbacks),
        }
    )
    result.check("canary_log", True, "")
    result.check("canary_final_5xx", final_5xx == 0, "Canary produced final 5xx responses")
    result.check(
        "canary_fallbacks",
        fallbacks <= args.maximum_fallbacks,
        "Canary fallback count exceeded threshold",
        warning=True,
    )


def check_container(result: Result, container: str) -> None:
    command = run(["docker", "inspect", container])
    if command.returncode != 0:
        result.check("api2_container", False, "API-2 container is unavailable")
        return
    try:
        inspected = json.loads(command.stdout)[0]
        state = inspected["State"]
        health = state.get("Health", {}).get("Status", "none")
        restarts = int(inspected.get("RestartCount", 0))
    except (KeyError, TypeError, ValueError, json.JSONDecodeError):
        result.check("api2_container", False, "API-2 container state is invalid")
        return
    result.metrics["api2_container_restarts"] = float(restarts)
    result.check(
        "api2_container",
        state.get("Status") == "running" and health == "healthy",
        "API-2 container is not running and healthy",
    )
    result.check(
        "api2_container_restarts",
        restarts == 0,
        "API-2 container restart count is non-zero",
        warning=True,
    )


def check_api2_host(result: Result, args: argparse.Namespace) -> None:
    check_container(result, args.api2_container)
    check_http_ready(result, args.api2_ready_url, args.http_timeout)
    check_logical_backups(result, Path(args.backup_directory), args.backup_maximum_age)


def logical_backup_inventory(path: Path, now: dt.datetime | None = None) -> tuple[int, float]:
    now = now or dt.datetime.now(dt.timezone.utc)
    objects: dict[str, set[str]] = {}
    for item in path.iterdir():
        if not item.is_file() or item.is_symlink():
            continue
        match = BACKUP_OBJECT_RE.fullmatch(item.name)
        if match:
            objects.setdefault(match.group("id"), set()).add(match.group("kind"))
    legacy = {"database", "globals", "manifest"}
    current = legacy | {"runtime"}
    complete = sorted(backup_id for backup_id, kinds in objects.items() if kinds in (legacy, current))
    if not complete:
        return 0, -1.0
    newest = dt.datetime.strptime(complete[-1][:16], "%Y%m%dT%H%M%SZ").replace(tzinfo=dt.timezone.utc)
    return len(complete), (now - newest).total_seconds()


def check_logical_backups(
    result: Result,
    path: Path,
    maximum_age: int,
    now: dt.datetime | None = None,
) -> None:
    try:
        count, age = logical_backup_inventory(path, now)
    except OSError:
        result.metrics.update({"logical_backup_complete_sets": 0.0, "logical_backup_age_seconds": -1.0})
        result.check("logical_backup", False, "Logical backup repository is unavailable")
        return
    result.metrics.update(
        {"logical_backup_complete_sets": float(count), "logical_backup_age_seconds": age}
    )
    result.check(
        "logical_backup",
        count > 0 and -300 <= age <= maximum_age,
        "Latest logical backup is missing, stale or dated in the future",
    )


def render_metrics(result: Result) -> str:
    lines = [
        "# HELP admirra_api2_monitor_ok Last API-2 monitor has no critical failure (1=healthy or warning).",
        "# TYPE admirra_api2_monitor_ok gauge",
        f'admirra_api2_monitor_ok{{role="{result.role}"}} {1 if not result.errors else 0}',
        "# HELP admirra_api2_monitor_check_ok Individual API-2 monitor check result (1=ok).",
        "# TYPE admirra_api2_monitor_check_ok gauge",
    ]
    for name, value in sorted(result.checks.items()):
        lines.append(f'admirra_api2_monitor_check_ok{{role="{result.role}",check="{name}"}} {value:g}')
    lines.extend(
        [
            "# HELP admirra_api2_monitor_value Numeric values observed by the API-2 monitor.",
            "# TYPE admirra_api2_monitor_value gauge",
        ]
    )
    for name, value in sorted(result.metrics.items()):
        lines.append(f'admirra_api2_monitor_value{{role="{result.role}",name="{name}"}} {value:g}')
    lines.extend(
        [
            "# HELP admirra_api2_monitor_last_check_timestamp_seconds Unix time of the latest probe.",
            "# TYPE admirra_api2_monitor_last_check_timestamp_seconds gauge",
            f'admirra_api2_monitor_last_check_timestamp_seconds{{role="{result.role}"}} {int(time.time())}',
        ]
    )
    return "\n".join(lines) + "\n"


def atomic_write(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(value)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        os.chmod(path, 0o644)
    finally:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("role", choices=("ingress", "api2"))
    result.add_argument("--api2-ready-url", default="http://10.77.0.2:8001/api/health/ready")
    result.add_argument("--api2-container", default="admirra-api2-api-1")
    result.add_argument("--canary-log", default="/var/log/nginx/admirra-api2-canary.log")
    result.add_argument("--metrics-file")
    result.add_argument("--window-seconds", type=int, default=600)
    result.add_argument("--maximum-fallbacks", type=int, default=0)
    result.add_argument("--http-timeout", type=float, default=5.0)
    result.add_argument("--wireguard-interface", default="admirra0")
    result.add_argument("--wireguard-maximum-age", type=int, default=600)
    result.add_argument("--disk-path", default="/")
    result.add_argument("--disk-warning-percent", type=float, default=20.0)
    result.add_argument("--disk-critical-percent", type=float, default=10.0)
    result.add_argument("--backup-directory", default="/var/lib/admirra-backup/postgres")
    result.add_argument("--backup-maximum-age", type=int, default=108000)
    return result


def main() -> int:
    args = parser().parse_args()
    result = Result(role=args.role)
    check_disk(result, args.disk_path, args.disk_warning_percent, args.disk_critical_percent)
    check_wireguard(result, args.wireguard_interface, args.wireguard_maximum_age)
    if args.role == "ingress":
        check_ingress(result, args)
    else:
        check_api2_host(result, args)

    if args.metrics_file:
        atomic_write(Path(args.metrics_file), render_metrics(result))
    print(
        json.dumps(
            {
                "status": result.status,
                "role": result.role,
                "checks": result.checks,
                "metrics": result.metrics,
                "warnings": result.warnings,
                "errors": result.errors,
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return result.exit_code


if __name__ == "__main__":
    sys.exit(main())
