"""Per-recipient send guards. Unknown external outcomes are NEVER replayed."""
from contextvars import ContextVar
from functools import wraps
import hashlib
import uuid

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID, insert

from core.delivery_outcome import outcome
from core.runtime import env_bool

metadata = sa.MetaData()
routes = sa.Table("report_route_attempts", metadata,
    sa.Column("delivery_id", UUID(as_uuid=True), primary_key=True),
    sa.Column("route_key", sa.String(64), primary_key=True),
    sa.Column("channel", sa.String(16), nullable=False),
    sa.Column("state", sa.String(16), nullable=False),
    sa.Column("token", UUID(as_uuid=True), nullable=False),
    sa.Column("attempt", sa.Integer, nullable=False, server_default="1"),
    sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    sa.Column("resolutions", JSONB, nullable=False, server_default="[]"),
    sa.CheckConstraint("state IN ('sending','accepted','rejected','uncertain')", name="ck_report_route_state"),
)
context = ContextVar("report_delivery_context", default=None)
UNCERTAIN = "Результат отправки неизвестен. Проверьте получение у клиента перед разрешением повтора."


def enabled():
    return env_bool("REPORT_DELIVERY_GUARDS", env_bool("DURABLE_TASKS", False))


def route_key(channel, recipient):
    return hashlib.sha256(f"{channel}:{str(recipient).strip()}".encode()).hexdigest()


def acquire(db, delivery_id, key, channel, *, untracked_history=False):
    token = uuid.uuid4()
    where = (routes.c.delivery_id == delivery_id, routes.c.route_key == key)
    inserted = db.execute(insert(routes).values(delivery_id=delivery_id, route_key=key, channel=channel,
        state="uncertain" if untracked_history else "sending", token=token).on_conflict_do_nothing().returning(routes.c.token)).scalar()
    if inserted:
        db.commit()  # The attempt must be durable BEFORE the first network byte.
        return (None, "uncertain") if untracked_history else (token, "sending")
    row = db.execute(sa.select(routes).where(*where).with_for_update()).mappings().one()
    if row["state"] == "rejected":
        db.execute(routes.update().where(*where).values(state="sending", token=token,
            attempt=routes.c.attempt + 1, updated_at=sa.func.now()))
        db.commit()
        return token, "sending"
    state = row["state"]
    db.commit()
    return None, state


def settle(db, delivery_id, key, token, state):
    changed = db.execute(routes.update().where(routes.c.delivery_id == delivery_id,
        routes.c.route_key == key, routes.c.token == token, routes.c.state == "sending"
    ).values(state=state, updated_at=sa.func.now())).rowcount
    if changed != 1:
        db.rollback()
        raise RuntimeError("Report send ownership changed; outcome requires reconciliation")
    db.commit()


def add_evidence(db, delivery_id, results):
    results = dict(results or {})
    rows = db.execute(sa.select(routes.c.route_key, routes.c.channel, routes.c.state)
        .where(routes.c.delivery_id == delivery_id)).mappings().all()
    results["route_states"] = [dict(row) for row in rows]
    results["requires_reconciliation"] = any(row["state"] in {"sending", "uncertain"} for row in rows)
    return results


def resolve(db, delivery_id, key, actor_id, decision, reason):
    if decision not in {"accepted", "retry"} or len(reason.strip()) < 10:
        raise ValueError("Specify accepted/retry and a meaningful reconciliation note")
    row = db.execute(sa.select(routes).where(routes.c.delivery_id == delivery_id,
        routes.c.route_key == key).with_for_update()).mappings().first()
    if not row:
        raise LookupError("Recipient attempt not found")
    now = db.scalar(sa.select(sa.func.clock_timestamp()))
    if row["state"] == "sending" and (now - row["updated_at"]).total_seconds() < 900:
        raise ValueError("Sending is still in progress; retry is not allowed")
    if row["state"] not in {"sending", "uncertain"}:
        raise ValueError("Only an unknown outcome can be reconciled")
    audit = [*row["resolutions"], {"actor_id": str(actor_id), "decision": decision, "reason": reason.strip(), "at": now.isoformat()}]
    db.execute(routes.update().where(routes.c.delivery_id == delivery_id, routes.c.route_key == key).values(
        state="accepted" if decision == "accepted" else "rejected", token=uuid.uuid4(), resolutions=audit, updated_at=now))
    # Caller authorizes ownership and commits atomically with any delivery changes.


def guarded(channel, recipient):
    def decorate(fn):
        @wraps(fn)
        async def wrapped(*args, **kwargs):
            active = context.get()
            if not active or not enabled():
                return await fn(*args, **kwargs)
            db, delivery = active
            key = route_key(channel, recipient(kwargs))
            token, state = acquire(db, delivery.id, key, channel,
                untracked_history=bool((delivery.delivery_results or {}).get("legacy_untracked_attempts")))
            if token is None:
                return (True, None) if state == "accepted" else (False, UNCERTAIN)
            reset = outcome.set("unknown")
            try:
                ok, error = await fn(*args, **kwargs)
                state = "accepted" if ok else "rejected" if outcome.get() == "rejected" else "uncertain"
                settle(db, delivery.id, key, token, state)
                return ok, UNCERTAIN if state == "uncertain" else error
            except Exception:
                # A failed DB commit after an accepted send leaves 'sending'
                # behind; a retry will be blocked, not silently resend.
                db.rollback()
                settle(db, delivery.id, key, token, "uncertain")
                return False, UNCERTAIN
            finally:
                outcome.reset(reset)
        return wrapped
    return decorate
