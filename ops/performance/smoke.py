"""Bounded authenticated read smoke for the explicitly approved account.

Run inside backend. No passwords, tokens, project names or response contents in
output. The ordinary individual summary route records visits for that account.
Does not call goals/provider APIs, AI, reports, payments or sync endpoints.
"""
import argparse
from datetime import date, timedelta
import json
import time
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from urllib.error import HTTPError
import uuid

from core import models, security
from core.database import SessionLocal


def smoke(email):
    with SessionLocal() as db:
        user = db.query(models.User).filter(models.User.email == email, models.User.is_active.is_(True)).one()
        token = security.create_access_token({"sub": user.email}, expires_delta=timedelta(minutes=5))
        ids = [str(row[0]) for row in db.query(models.Client.id).filter(models.Client.owner_id == user.id)
               .order_by(models.Client.id).limit(64).all()]
    if not ids:
        raise RuntimeError("Approved account has no projects")
    end = date.today()
    period = {"start_date": str(end - timedelta(days=13)), "end_date": str(end)}

    def get(path, params, authenticated=True):
        request = Request("http://127.0.0.1:8001/api/" + path + "?" + urlencode(params, doseq=True),
                          headers={"Authorization": "Bearer " + token} if authenticated else {})
        with urlopen(request, timeout=30) as response:
            body = response.read(10 * 1024 * 1024 + 1)
            if len(body) > 10 * 1024 * 1024:
                raise RuntimeError("Oversized smoke response")
            return json.loads(body)

    started = time.perf_counter()
    result = get("dashboard/project-summaries", {**period, "client_ids": ids})
    elapsed = time.perf_counter() - started
    assert set(result) == set(ids)
    for cid in ids[:3]:
        for channel in ("all", "yandex", "vk", "avito"):
            individual = get("dashboard/summary", {**period, "client_id": cid, "platform": channel})
            assert result[cid][channel] == individual, "Batch/individual response differs"
    for params, auth, expected in (({**period, "client_ids": ids[:1]}, False, (401, 403)),
                                   ({**period, "client_ids": [str(uuid.uuid4())]}, True, (403,))):
        try:
            get("dashboard/project-summaries", params, auth)
        except HTTPError as error:
            assert error.code in expected
        else:
            raise AssertionError("Access guard failed")
    print(json.dumps({"projects": len(ids), "channels": 4, "batch_ms": round(elapsed * 1000, 2),
                      "compared_individual_reads": min(3, len(ids)) * 4, "access_guards": "passed"}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--email", required=True)
    args = parser.parse_args()
    try:
        smoke(args.email)
    except Exception as error:
        print("Summary smoke failed:", type(error).__name__)
        raise SystemExit(1)
