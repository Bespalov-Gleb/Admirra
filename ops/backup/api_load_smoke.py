"""Bounded authenticated read load, executed only inside an isolated restore API."""
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
import json
import math
import os
import time
import urllib.error
import urllib.request

import sqlalchemy as sa

from core import models, security
from core.database import SessionLocal


def selected_user_email() -> str:
    email = os.environ.get("ADMIRRA_TEST_ACCOUNT_EMAIL", "").strip()
    if not email:
        raise RuntimeError("ADMIRRA_TEST_ACCOUNT_EMAIL must identify the approved test account")
    with SessionLocal() as db:
        row = db.execute(
            sa.select(models.User.email, sa.func.count(models.Client.id).label("projects"))
            .join(models.Client, models.Client.owner_id == models.User.id)
            .where(models.User.is_active.is_(True), models.User.email_verified.is_(True),
                   sa.func.lower(models.User.email) == email.lower())
            .group_by(models.User.id, models.User.email)
            .order_by(sa.desc("projects"), models.User.id)
            .limit(1)
        ).first()
    if not row:
        raise RuntimeError("Approved restore account has no active verified user with projects")
    return row.email


def percentile(values: list[float], fraction: float) -> float:
    return sorted(values)[max(0, math.ceil(len(values) * fraction) - 1)]


def main() -> None:
    token = security.create_access_token({"sub": selected_user_email()})
    end = date.today()
    start = end - timedelta(days=13)
    paths = {
        "auth": "/api/auth/me",
        "clients": "/api/clients",
        "folders": "/api/folders",
        "notifications": "/api/notifications",
        "summary": f"/api/dashboard/summary?start_date={start.isoformat()}&end_date={end.isoformat()}&platform=all",
    }
    requests = list(paths.values()) * 8

    def fetch(path: str) -> tuple[int, float]:
        request = urllib.request.Request(
            "http://127.0.0.1:8001" + path,
            headers={"Authorization": "Bearer " + token},
        )
        started = time.perf_counter()
        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                body = response.read(10 * 1024 * 1024 + 1)
                status = response.status
        except urllib.error.HTTPError as error:
            error.read(1024)
            status = error.code
            body = b""
        except OSError:
            status = 0
            body = b""
        elapsed = time.perf_counter() - started
        if len(body) > 10 * 1024 * 1024:
            raise RuntimeError("Restore API response exceeded load-smoke limit")
        return status, elapsed

    for label, path in paths.items():
        status, _ = fetch(path)
        if status != 200:
            raise RuntimeError(f"Restore API warm-up failed: route={label} status={status}")

    started = time.perf_counter()
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(fetch, requests))
    duration = time.perf_counter() - started
    statuses: dict[int, int] = {}
    latencies = []
    for status, elapsed in results:
        statuses[status] = statuses.get(status, 0) + 1
        latencies.append(elapsed)
    evidence = {
        "requests": len(results),
        "concurrency": 4,
        "statuses": statuses,
        "duration_seconds": round(duration, 3),
        "requests_per_second": round(len(results) / duration, 2),
        "p50_ms": round(percentile(latencies, 0.50) * 1000, 2),
        "p95_ms": round(percentile(latencies, 0.95) * 1000, 2),
        "max_ms": round(max(latencies) * 1000, 2),
    }
    print(json.dumps(evidence, sort_keys=True))
    if statuses != {200: len(results)}:
        raise SystemExit("Restore API load smoke returned non-200 responses")


if __name__ == "__main__":
    main()
