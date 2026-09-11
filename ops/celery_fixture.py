"""Synthetic worker fixture, imported ONLY by explicit isolated-test CLI."""
import os
import time
from urllib.parse import urlsplit

if os.getenv("WW_TEST") != "1" or not os.getenv("WW_TEST_ID") or urlsplit(os.getenv("DATABASE_URL", "")).hostname != "test-db":
    raise RuntimeError("Synthetic probe is forbidden outside the isolated test database")

import sqlalchemy as sa
from core.database import SessionLocal
from automation.celery_app import app
from automation.work_executor import execute_job


def handle(kind, payload):
    if kind != "test.probe":
        raise ValueError("Only synthetic work is allowed")
    with SessionLocal() as db:
        db.execute(sa.text("INSERT INTO effects VALUES (:value)"), {"value": payload["value"]})
        # Marker lets the test kill a real child with an uncommitted write.
        from automation.provider_transport import connection
        connection().set(f"probe:{payload['marker']}", os.getpid(), ex=60)
        time.sleep(payload.get("delay", 0))
        db.commit()


@app.task(name="admirra.test_execute")
def execute(job_id):
    return execute_job(job_id, handler=handle)
