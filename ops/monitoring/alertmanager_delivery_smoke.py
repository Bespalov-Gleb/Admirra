#!/usr/bin/env python3
"""Send a bounded synthetic firing/resolved pair to local Alertmanager."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import time
import urllib.error
import urllib.request
from collections.abc import Callable


def post(url: str, payload: list[dict], timeout: float) -> None:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        if response.status not in (200, 202):
            raise RuntimeError("Alertmanager rejected the synthetic alert")


def deliver(
    url: str,
    hold_seconds: int,
    timeout: float,
    *,
    send: Callable[[str, list[dict], float], None] = post,
    sleep: Callable[[float], None] = time.sleep,
    clock: Callable[[], dt.datetime] = lambda: dt.datetime.now(dt.timezone.utc),
) -> None:
    if not 30 <= hold_seconds <= 300:
        raise ValueError("hold-seconds must be between 30 and 300")
    now = clock()
    if now.tzinfo is None:
        raise ValueError("clock must return a timezone-aware timestamp")
    base = {
        "labels": {
            "alertname": "AdMirraDeliveryTest",
            "severity": "warning",
            "environment": "production-test",
        },
        "annotations": {
            "summary": "AdMirra alert delivery test; no customer impact",
            "runbook": "docs/devops-observability-2026-09-20.md",
        },
        "startsAt": now.isoformat(),
        "generatorURL": "https://admirra.ru/health/live",
    }
    firing = dict(base, endsAt=(now + dt.timedelta(minutes=10)).isoformat())
    send(url, [firing], timeout)
    sleep(hold_seconds)
    resolved = dict(base, endsAt=clock().isoformat())
    send(url, [resolved], timeout)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:9093/api/v2/alerts")
    parser.add_argument("--hold-seconds", type=int, default=45)
    parser.add_argument("--timeout", type=float, default=5.0)
    args = parser.parse_args()
    try:
        deliver(args.url, args.hold_seconds, args.timeout)
    except (OSError, RuntimeError, ValueError, urllib.error.URLError):
        raise SystemExit("synthetic firing/resolved delivery failed") from None
    print(json.dumps({"status": "submitted", "firing": True, "resolved": True}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
