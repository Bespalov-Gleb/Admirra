"""Durable, revocable HTML report snapshots. No process-local public capabilities.

Callers own transaction boundaries. Tokens are returned once and never stored;
the public read path checks the creator's current account/project access.
"""
from datetime import date, datetime, timedelta
from decimal import Decimal
import hashlib
import json
import re
import secrets
import uuid

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

from core.runtime import env_bool

metadata = sa.MetaData()
links = sa.Table(
    "public_report_links", metadata,
    sa.Column("id", UUID(as_uuid=True), primary_key=True),
    sa.Column("creator_id", UUID(as_uuid=True), nullable=False),
    sa.Column("account_id", UUID(as_uuid=True), nullable=False),
    sa.Column("token_hash", sa.String(64), nullable=False),
    sa.Column("scope_ids", JSONB, nullable=False),
    # Preserve exact JSON number spelling (JSONB rewrites -0.0/exponents and
    # would invalidate a byte hash despite the same logical value).
    sa.Column("snapshot", sa.Text, nullable=False),
    sa.Column("snapshot_hash", sa.String(64), nullable=False),
    sa.Column("snapshot_bytes", sa.Integer, nullable=False),
    sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
    sa.Column("revoked_at", sa.DateTime(timezone=True)),
)
TOKEN_PATTERN = re.compile(r"r1_[A-Za-z0-9_-]{43}\Z")
MAX_SNAPSHOT_BYTES = 1024 * 1024
MAX_SCOPE_IDS = 1000
MAX_ACTIVE_LINKS = 100
MAX_DAILY_LINKS = 200
MAX_TTL_SECONDS = 86400
PRIVATE_HEADERS = {
    "Cache-Control": "no-store, private",
    "Referrer-Policy": "no-referrer",
    "X-Robots-Tag": "noindex, nofollow, noarchive",
    "X-Content-Type-Options": "nosniff",
    "Content-Security-Policy": "default-src 'none'; style-src 'unsafe-inline'; img-src data:; base-uri 'none'; form-action 'none'; frame-ancestors 'none'",
}


class LinkUnavailable(Exception):
    """Opaque public 404 (invalid, revoked, expired, deleted or inaccessible)."""


class LinkLimitReached(Exception):
    pass


class SnapshotCorrupt(Exception):
    pass


def enabled():
    return env_bool("DURABLE_REPORT_LINKS", False)


def is_durable_token(token):
    # Do not fall back to local dictionaries for malformed/unknown versioned tokens.
    return isinstance(token, str) and token.startswith("r1_")


def token_hash(token):
    if not isinstance(token, str) or TOKEN_PATTERN.fullmatch(token) is None:
        raise LinkUnavailable()
    return hashlib.sha256(token.encode("ascii")).hexdigest()


def _json_default(value):
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, uuid.UUID):
        return str(value)
    raise ValueError("Unsupported report snapshot value")


def _encode(snapshot):
    if not isinstance(snapshot, dict):
        raise ValueError("Report snapshot must be an object")
    raw = json.dumps(snapshot, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
                     allow_nan=False, default=_json_default).encode("utf-8")
    if len(raw) > MAX_SNAPSHOT_BYTES:
        raise ValueError("Report snapshot is too large")
    return raw


def _scope(ids):
    result = sorted({str(uuid.UUID(str(value))) for value in ids})
    if not 1 <= len(result) <= MAX_SCOPE_IDS:
        raise ValueError("Invalid report scope size")
    return result


def authorize(db, creator_id, scope_ids, account_id=None):
    """Authoritative access, never a cached JWT/tenant list. No secret in errors."""
    from core import models
    from backend_api.access_control import get_team_context, get_accessible_client_ids
    user = db.query(models.User).filter(models.User.id == creator_id, models.User.is_active.is_(True)).first()
    if user is None:
        raise LinkUnavailable()
    account = get_team_context(db, user).account_id
    if account_id is not None and account != account_id:
        raise LinkUnavailable()
    if not db.query(models.User.id).filter(models.User.id == account, models.User.is_active.is_(True)).first():
        raise LinkUnavailable()
    allowed = {str(value) for value in get_accessible_client_ids(db, user)}
    if not scope_ids or not set(scope_ids).issubset(allowed):
        raise LinkUnavailable()
    return account


def create(db, creator_id, scope_ids, snapshot, ttl_seconds=MAX_TTL_SECONDS):
    if isinstance(ttl_seconds, bool) or not isinstance(ttl_seconds, int) or not 1 <= ttl_seconds <= MAX_TTL_SECONDS:
        raise ValueError("Report link TTL must be between 1 and 86400 seconds")
    scope = _scope(scope_ids)
    raw = _encode(snapshot)
    # Serialize quota checks across processes, not a read-then-insert race.
    # Namespace does not overlap with durable work coordination.
    lock_id = int.from_bytes(hashlib.sha256(b"report-links:" + str(creator_id).encode()).digest()[:8], "big", signed=True)
    db.execute(sa.select(sa.func.pg_advisory_xact_lock(lock_id)))
    account_id = authorize(db, creator_id, scope)
    now = db.scalar(sa.select(sa.func.clock_timestamp()))
    active, recent = db.execute(sa.select(
        sa.func.count().filter(sa.and_(links.c.revoked_at.is_(None), links.c.expires_at > now)),
        sa.func.count().filter(links.c.created_at > now - timedelta(days=1)),
    ).where(links.c.creator_id == creator_id)).one()
    if active >= MAX_ACTIVE_LINKS or recent >= MAX_DAILY_LINKS:
        raise LinkLimitReached()
    token, id = "r1_" + secrets.token_urlsafe(32), uuid.uuid4()
    expires = now + timedelta(seconds=ttl_seconds)
    db.execute(links.insert().values(id=id, creator_id=creator_id, account_id=account_id,
        token_hash=token_hash(token), scope_ids=scope, snapshot=raw.decode("utf-8"),
        snapshot_hash=hashlib.sha256(raw).hexdigest(), snapshot_bytes=len(raw), created_at=now, expires_at=expires))
    return {"token": token, "link_id": str(id), "expires_at": expires.isoformat(),
            "url": f"/api/reports/view/{token}"}


def read(db, token):
    digest = token_hash(token)
    row = db.execute(sa.select(links).where(links.c.token_hash == digest,
        links.c.revoked_at.is_(None), links.c.expires_at > sa.func.clock_timestamp())).mappings().first()
    if row is None:
        raise LinkUnavailable()
    authorize(db, row["creator_id"], row["scope_ids"], row["account_id"])
    try:
        raw = row["snapshot"].encode("utf-8")
        if len(raw) > MAX_SNAPSHOT_BYTES:
            raise ValueError("Oversized stored snapshot")
        snapshot = json.loads(raw)
        if not isinstance(snapshot, dict):
            raise ValueError("Invalid stored snapshot")
    except (ValueError, TypeError, OverflowError):
        raise SnapshotCorrupt() from None
    if len(raw) != row["snapshot_bytes"] or hashlib.sha256(raw).hexdigest() != row["snapshot_hash"]:
        raise SnapshotCorrupt()
    return snapshot


def revoke(db, link_id, creator_id):
    # Link management never accepts a bearer token instead of authenticated owner.
    id = db.scalar(links.update().where(links.c.id == link_id, links.c.creator_id == creator_id)
        .values(revoked_at=sa.func.coalesce(links.c.revoked_at, sa.func.clock_timestamp()))
        .returning(links.c.id))
    if id is None:
        raise LinkUnavailable()


def list_owned(db, creator_id, limit=50, before=None):
    if not 1 <= limit <= 100:
        raise ValueError("Invalid page size")
    # No bearer/hash/snapshot/scope names in the management listing.
    columns = [links.c.id.label("link_id"), links.c.created_at, links.c.expires_at, links.c.revoked_at]
    query = sa.select(*columns).where(links.c.creator_id == creator_id)
    if before is not None:
        cursor = db.execute(sa.select(links.c.created_at, links.c.id).where(
            links.c.id == before, links.c.creator_id == creator_id)).first()
        if cursor is None:
            raise LinkUnavailable()
        query = query.where(sa.tuple_(links.c.created_at, links.c.id) < sa.tuple_(*cursor))
    return [dict(row) for row in db.execute(query.order_by(links.c.created_at.desc(), links.c.id.desc()).limit(limit)).mappings()]


def check_schema(engine):
    """Called on opt-in startup before traffic; never creates/changes a table."""
    with engine.connect() as db:
        db.execute(sa.text("SET LOCAL statement_timeout = '2000ms'"))
        db.execute(sa.select(links).where(sa.false()))


def prune(db, limit=100):
    """Bounded maintenance: expired/revoked snapshots only; live ones survive.

    Keep seven days after expiry/revocation for operational evidence. This table
    is not the delivery/payment ledger; those are never touched here.
    """
    if not 1 <= limit <= 1000:
        raise ValueError("Invalid cleanup batch size")
    cutoff = sa.func.clock_timestamp() - sa.text("interval '7 days'")
    batch = sa.select(links.c.id).where(sa.or_(links.c.expires_at < cutoff, links.c.revoked_at < cutoff))\
        .order_by(links.c.expires_at, links.c.id).limit(limit).with_for_update(skip_locked=True)
    return db.execute(links.delete().where(links.c.id.in_(batch))).rowcount
