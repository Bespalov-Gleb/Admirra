"""Read-only queue diagnostics: no customer payloads, tokens or exception text."""
import json
import sys

import sqlalchemy as sa
from automation.work_tables import jobs, outbox
from core.database import engine


def snapshot(connection):
    counts = connection.execute(sa.select(jobs.c.queue, jobs.c.state, sa.func.count()).group_by(jobs.c.queue, jobs.c.state)).all()
    age = connection.scalar(sa.select(sa.func.extract("epoch", sa.func.now() - sa.func.min(jobs.c.created_at)))
                            .where(jobs.c.state == "queued"))
    expired = connection.scalar(sa.select(sa.func.count()).select_from(jobs).where(
        jobs.c.state == "running", jobs.c.lease_until < sa.func.now()))
    uncertain = sum(count for _, state, count in counts if state == "uncertain")
    return {"queues": [{"queue": queue, "state": state, "count": count} for queue, state, count in counts],
            "oldest_queued_seconds": float(age or 0), "expired_leases": expired, "uncertain_jobs": uncertain,
            "pending_outbox": connection.scalar(sa.select(sa.func.count()).select_from(outbox))}


def main():
    with engine.begin() as connection:
        connection.execute(sa.text("SET TRANSACTION READ ONLY"))
        connection.execute(sa.text("SET LOCAL statement_timeout = '5s'"))
        state = snapshot(connection)
    print(json.dumps(state, ensure_ascii=False))
    return 2 if state["expired_leases"] or state["uncertain_jobs"] or state["oldest_queued_seconds"] > 3600 else 0


if __name__ == "__main__":
    sys.exit(main())
