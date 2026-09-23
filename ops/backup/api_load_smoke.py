"""Bounded authenticated read load, executed only inside an isolated restore API."""
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
import hashlib
import json
import math
import os
import time
import urllib.error
import urllib.request
from urllib.parse import urlsplit

import sqlalchemy as sa

from core import models, security
from core.database import SessionLocal


def assert_isolated_restore() -> None:
    url = urlsplit(os.environ.get("DATABASE_URL", ""))
    if (os.environ.get("WW_TEST") != "1"
            or not os.environ.get("WW_TEST_ID", "").startswith("restore-")
            or url.hostname != "127.0.0.1" or url.path != "/restore"):
        raise RuntimeError("Read load is restricted to the isolated restore instance")


def selected_user_email() -> str:
    assert_isolated_restore()
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


def response_profile(label: str, body: bytes) -> dict:
    """Aggregate size only; never output names, identifiers or field values."""
    if label not in {'clients', 'project_cards', 'project_tree'}:
        return {}
    data = json.loads(body)
    if label == 'project_tree':
        rows = data.get('root_projects', []) + [p for f in data.get('folders', []) for p in f.get('projects', [])]
    else:
        rows = data
    integrations = [item for row in rows for item in row.get('integrations', [])]
    campaigns = [item for row in integrations for item in row.get('campaigns', [])]
    return dict(projects=len(rows), integrations=len(integrations), campaigns=len(campaigns),
        campaign_json_bytes=len(json.dumps(campaigns, ensure_ascii=False, separators=(',', ':')).encode()))


def main() -> None:
    assert_isolated_restore()
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
    if os.getenv("ADMIRRA_DASHBOARD_BENCHMARK") == "1":
        period = f"start_date={start.isoformat()}&end_date={end.isoformat()}"
        paths.update({
            "project_cards": f"/api/clients/stats?{period}",
            "project_tree": f"/api/folders/tree?{period}&with_stats=true",
            "top_projects": f"/api/folders/top-projects?{period}&limit=5",
        })
    requests = list(paths.items()) * 8

    def fetch(item):
        label, path = item
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
        digest = hashlib.sha256(body).hexdigest() if status == 200 else None
        return label, status, elapsed, len(body), digest, response_profile(label, body) if status == 200 else {}

    cold = {}
    for label, path in paths.items():
        _, status, elapsed, size, digest, profile = fetch((label, path))
        if status != 200:
            raise RuntimeError(f"Restore API warm-up failed: route={label} status={status}")
        cold[label] = {"first_ms": round(elapsed * 1000, 2), "bytes": size, "sha256": digest, **profile}

    started = time.perf_counter()
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(fetch, requests))
    duration = time.perf_counter() - started
    statuses: dict[int, int] = {}
    latencies = []
    for _, status, elapsed, _, _, _ in results:
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
        "routes": {
            label: {**cold[label],
                "p50_ms": round(percentile([r[2] for r in results if r[0] == label], .5) * 1000, 2),
                "p95_ms": round(percentile([r[2] for r in results if r[0] == label], .95) * 1000, 2),
                "statuses": [r[1] for r in results if r[0] == label],
            } for label in paths
        },
    }
    print(json.dumps(evidence, sort_keys=True))
    if statuses != {200: len(results)}:
        raise SystemExit("Restore API load smoke returned non-200 responses")


if __name__ == "__main__":
    main()
