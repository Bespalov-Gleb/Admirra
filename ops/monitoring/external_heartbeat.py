#!/usr/bin/env python3
"""Independent public AdMirra heartbeat; no credentials or customer data."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable
from pathlib import Path


MAX_BODY = 256 * 1024


def validate_base_url(value: str) -> str:
    parsed = urllib.parse.urlsplit(value)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("base URL must be a credential-free HTTPS origin")
    if parsed.path not in ("", "/") or parsed.query or parsed.fragment:
        raise ValueError("base URL must not contain path, query or fragment")
    return value.rstrip("/")


def request_status(
    request: urllib.request.Request,
    *,
    timeout: float,
    open_url: Callable = urllib.request.urlopen,
) -> tuple[int, bytes]:
    try:
        with open_url(request, timeout=timeout) as response:
            return response.status, response.read(MAX_BODY + 1)
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read(MAX_BODY + 1)


def probe_once(base_url: str, *, timeout: float = 8.0, open_url: Callable = urllib.request.urlopen) -> dict:
    started = time.monotonic()
    root_status, root_body = request_status(
        urllib.request.Request(base_url + "/", headers={"User-Agent": "AdMirra-External-Heartbeat/1"}),
        timeout=timeout,
        open_url=open_url,
    )
    auth_status, auth_body = request_status(
        urllib.request.Request(base_url + "/api/auth/me", headers={"User-Agent": "AdMirra-External-Heartbeat/1"}),
        timeout=timeout,
        open_url=open_url,
    )
    if len(root_body) > MAX_BODY or len(auth_body) > MAX_BODY:
        raise RuntimeError("heartbeat response exceeded the body limit")
    if root_status != 200 or not root_body:
        raise RuntimeError("public frontend probe failed")
    if auth_status != 401:
        raise RuntimeError("auth guard probe returned an unexpected status")
    return {
        "ok": True,
        "root_status": root_status,
        "auth_status": auth_status,
        "duration_ms": round((time.monotonic() - started) * 1000, 2),
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
        os.chmod(temporary, 0o644)
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def run(
    base_url: str,
    *,
    attempts: int,
    delay: float,
    timeout: float,
    probe: Callable[..., dict] = probe_once,
    sleep: Callable[[float], None] = time.sleep,
) -> dict:
    if not 1 <= attempts <= 5 or not 0 <= delay <= 30 or not 1 <= timeout <= 30:
        raise ValueError("heartbeat bounds are invalid")
    observations = []
    for index in range(attempts):
        try:
            observations.append(probe(base_url, timeout=timeout))
        except (OSError, RuntimeError, ValueError, urllib.error.URLError) as exc:
            observations.append({"ok": False, "error_type": type(exc).__name__})
        if observations[-1]["ok"]:
            break
        if index + 1 < attempts:
            sleep(delay)
    now = dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z")
    return {
        "format": "admirra-external-heartbeat-v1",
        "checked_at": now,
        "status": "ok" if observations[-1]["ok"] else "critical",
        "attempts": observations,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="https://admirra.ru")
    parser.add_argument("--state-file", type=Path, default=Path("/var/lib/admirra-public-heartbeat/status.json"))
    parser.add_argument("--attempts", type=int, default=3)
    parser.add_argument("--delay", type=float, default=2.0)
    parser.add_argument("--timeout", type=float, default=8.0)
    args = parser.parse_args()
    try:
        result = run(
            validate_base_url(args.base_url),
            attempts=args.attempts,
            delay=args.delay,
            timeout=args.timeout,
        )
        atomic_write(args.state_file, result)
    except (OSError, RuntimeError, ValueError):
        raise SystemExit("external heartbeat configuration or state write failed") from None
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0 if result["status"] == "ok" else 2


if __name__ == "__main__":
    raise SystemExit(main())
