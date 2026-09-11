"""Reject commits from workers whose durable execution lease is no longer valid.

The row lock is held through COMMIT, so a competing claim cannot cross the
validation/commit boundary. Ordinary API sessions have no fence and are unchanged.
"""
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
import uuid

from sqlalchemy import event, text
from sqlalchemy.orm import Session


class LeaseLost(RuntimeError):
    pass


@dataclass(frozen=True)
class Fence:
    job_id: uuid.UUID
    token: uuid.UUID


current_fence = ContextVar("admirra_job_fence", default=None)


@contextmanager
def fenced_job(job_id, token):
    reset = current_fence.set(Fence(job_id, token))
    try:
        yield
    finally:
        current_fence.reset(reset)


@event.listens_for(Session, "after_begin")
def remember_fence(session, transaction, connection):
    fence = current_fence.get()
    if fence is not None:
        # Remember it even if a caller later exits the context before committing.
        session.info.setdefault("job_fence", fence)


@event.listens_for(Session, "before_commit")
def validate_fenced_commit(session):
    # Releasing a SAVEPOINT does not persist data. Locking the lease there would
    # hold it during later HTTP/LLM calls in the outer transaction and block the
    # heartbeat. Fence only the actual outer COMMIT.
    if session.in_nested_transaction():
        return
    fence = session.info.get("job_fence") or current_fence.get()
    if fence is None:
        return
    connection = session.connection()
    if connection.dialect.name != "postgresql":
        raise LeaseLost("Durable execution requires PostgreSQL fencing")
    row = connection.execute(text("""
        SELECT id FROM background_jobs
        WHERE id = :job_id AND lease_token = :token AND state = 'running'
          AND lease_until > clock_timestamp()
        FOR UPDATE
    """), {"job_id": fence.job_id, "token": fence.token}).first()
    if row is None:
        raise LeaseLost("Execution lease expired or was superseded; refusing commit")
