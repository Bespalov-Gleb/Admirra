"""Artifact metadata, leases, references and capabilities (caller-owned tx).

Filesystem/network operations never belong inside these transactions. Reserve
metadata -> upload outside SQL -> finalize with a fencing generation -> attach.
"""
from datetime import timedelta
import hashlib
import re
import secrets
import uuid

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

from backend_api.reports.public_links import authorize, LinkUnavailable
from core.artifact_storage import MAX_BYTES, ObjectInfo
from core.runtime import env_int

metadata = sa.MetaData()
artifacts = sa.Table("stored_artifacts", metadata,
    sa.Column("id", UUID(as_uuid=True), primary_key=True),
    sa.Column("creator_id", UUID(as_uuid=True)), sa.Column("account_id", UUID(as_uuid=True)),
    sa.Column("scope_ids", JSONB, nullable=False), sa.Column("kind", sa.String(32), nullable=False),
    sa.Column("size_bytes", sa.BigInteger, nullable=False), sa.Column("sha256", sa.String(64), nullable=False),
    sa.Column("request_hash", sa.String(64), nullable=False), sa.Column("state", sa.String(16), nullable=False),
    sa.Column("generation", sa.BigInteger, nullable=False), sa.Column("lease_until", sa.DateTime(timezone=True)),
    sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    sa.Column("ready_at", sa.DateTime(timezone=True)), sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
    sa.Column("deleted_at", sa.DateTime(timezone=True)))
references = sa.Table("report_artifact_refs", metadata,
    sa.Column("delivery_id", UUID(as_uuid=True), primary_key=True),
    sa.Column("format", sa.String(8), primary_key=True),
    sa.Column("artifact_id", UUID(as_uuid=True), nullable=False),
    sa.Column("source_hash", sa.String(64), nullable=False))
file_links = sa.Table("artifact_public_links", metadata,
    sa.Column("id", UUID(as_uuid=True), primary_key=True),
    sa.Column("creator_id", UUID(as_uuid=True), nullable=False),
    sa.Column("artifact_id", UUID(as_uuid=True), nullable=False),
    sa.Column("token_hash", sa.String(64), nullable=False),
    sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
    sa.Column("revoked_at", sa.DateTime(timezone=True)))

MIME = {"report_pdf": "application/pdf", "report_png": "image/png",
        "report_docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document"}


class ArtifactConflict(Exception):
    pass


class ArtifactLimit(Exception):
    pass


def _digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def _scope(ids):
    result = sorted({str(uuid.UUID(str(value))) for value in ids})
    if not 1 <= len(result) <= 1000:
        raise ValueError("Invalid artifact scope")
    return result


def descriptor(row):
    return ObjectInfo(str(row["id"]), row["size_bytes"], row["sha256"])


def reserve(db, creator_id, scope_ids, kind, size, digest, request_key):
    if kind not in MIME or not isinstance(request_key, str) or not 1 <= len(request_key) <= 200:
        raise ValueError("Invalid artifact metadata")
    id = uuid.uuid4()
    ObjectInfo(str(id), size, digest)
    scope = _scope(scope_ids)
    account_id = authorize(db, creator_id, scope)
    lock_id = int.from_bytes(hashlib.sha256(b"artifact-quota:" + str(account_id).encode()).digest()[:8], "big", signed=True)
    db.execute(sa.select(sa.func.pg_advisory_xact_lock(lock_id)))
    request_hash = _digest(str(creator_id) + ":" + request_key)
    existing = db.execute(sa.select(artifacts).where(artifacts.c.account_id == account_id,
        artifacts.c.request_hash == request_hash).with_for_update()).mappings().first()
    now = db.scalar(sa.select(sa.func.clock_timestamp()))
    if existing:
        if (existing["creator_id"], existing["scope_ids"], existing["kind"], existing["size_bytes"], existing["sha256"]) != (creator_id, scope, kind, size, digest):
            raise ArtifactConflict()
        if existing["state"] not in {"ready", "uploading"}:
            raise ArtifactConflict()
        if existing["state"] == "uploading" and existing["lease_until"] <= now:
            return db.execute(artifacts.update().where(artifacts.c.id == existing["id"])
                .values(generation=artifacts.c.generation + 1, lease_until=now + timedelta(minutes=15))
                .returning(artifacts)).mappings().one()
        return existing
    used, pending = db.execute(sa.select(
        sa.func.coalesce(sa.func.sum(artifacts.c.size_bytes), 0),
        sa.func.count().filter(artifacts.c.state == "uploading"),
    ).where(artifacts.c.account_id == account_id, artifacts.c.state != "deleted")).one()
    max_bytes = env_int("ARTIFACT_ACCOUNT_MAX_BYTES", 2 * 1024**3, MAX_BYTES, 1024**4)
    if used + size > max_bytes or pending >= 8:
        raise ArtifactLimit()
    return db.execute(artifacts.insert().values(id=id, creator_id=creator_id, account_id=account_id,
        scope_ids=scope, kind=kind, size_bytes=size, sha256=digest, request_hash=request_hash,
        state="uploading", generation=1, lease_until=now + timedelta(minutes=15), created_at=now,
        expires_at=now + timedelta(days=2)).returning(artifacts)).mappings().one()


def owned(db, id, creator_id, *, lock=False, ready=True):
    query = sa.select(artifacts).where(artifacts.c.id == id, artifacts.c.creator_id == creator_id)
    if lock:
        query = query.with_for_update()
    row = db.execute(query).mappings().first()
    if not row or row["account_id"] is None or row["creator_id"] is None or (ready and row["state"] != "ready"):
        raise LinkUnavailable()
    authorize(db, creator_id, row["scope_ids"], row["account_id"])
    return row


def finalize(db, id, creator_id, generation, actual):
    row = owned(db, id, creator_id, lock=True, ready=False)
    if descriptor(row) != actual or row["generation"] != generation:
        raise ArtifactConflict()
    if row["state"] == "ready":
        return row
    now = db.scalar(sa.select(sa.func.clock_timestamp()))
    if row["state"] != "uploading" or row["lease_until"] <= now:
        raise ArtifactConflict()
    return db.execute(artifacts.update().where(artifacts.c.id == id).values(state="ready", ready_at=now,
        lease_until=None).returning(artifacts)).mappings().one()


def attach_report(db, delivery_id, creator_id, format, artifact_id, source_hash):
    """Caller locks/checks report revision before attaching. GC shares row lock."""
    from core.models import ReportDelivery
    from sqlalchemy.dialects.postgresql import insert
    if format not in {"pdf", "png", "docx"} or not re.fullmatch(r"[0-9a-f]{64}", source_hash):
        raise ValueError("Invalid report artifact binding")
    if not db.query(ReportDelivery.id).filter(ReportDelivery.id == delivery_id, ReportDelivery.user_id == creator_id).first():
        raise LinkUnavailable()
    row = owned(db, artifact_id, creator_id, lock=True)
    if row["kind"] != "report_" + format:
        raise ArtifactConflict()
    query = insert(references).values(delivery_id=delivery_id, format=format, artifact_id=artifact_id, source_hash=source_hash)
    db.execute(query.on_conflict_do_update(index_elements=[references.c.delivery_id, references.c.format],
        set_={"artifact_id": artifact_id, "source_hash": source_hash}))


def linked_report(db, delivery_id, creator_id, format, source_hash):
    from core.models import ReportDelivery
    if not db.query(ReportDelivery.id).filter(ReportDelivery.id == delivery_id, ReportDelivery.user_id == creator_id).first():
        raise LinkUnavailable()
    ref = db.execute(sa.select(references).where(references.c.delivery_id == delivery_id,
        references.c.format == format, references.c.source_hash == source_hash)).mappings().first()
    return owned(db, ref["artifact_id"], creator_id) if ref else None


def create_link(db, artifact_id, creator_id, ttl_seconds=86400):
    if isinstance(ttl_seconds, bool) or not isinstance(ttl_seconds, int) or not 1 <= ttl_seconds <= 86400:
        raise ValueError("Invalid file link TTL")
    # One creator-level lock serializes quota checks across all their artifacts.
    lock_id = int.from_bytes(hashlib.sha256(b"artifact-link-quota:" + str(creator_id).encode()).digest()[:8], "big", signed=True)
    db.execute(sa.select(sa.func.pg_advisory_xact_lock(lock_id)))
    owned(db, artifact_id, creator_id, lock=True)
    now = db.scalar(sa.select(sa.func.clock_timestamp()))
    count = db.scalar(sa.select(sa.func.count()).select_from(file_links).where(file_links.c.creator_id == creator_id,
        file_links.c.created_at > now - timedelta(days=1)))
    if count >= 200:
        raise ArtifactLimit()
    token, id = "f1_" + secrets.token_urlsafe(32), uuid.uuid4()
    expires = now + timedelta(seconds=ttl_seconds)
    db.execute(file_links.insert().values(id=id, creator_id=creator_id, artifact_id=artifact_id,
        token_hash=_digest(token), created_at=now, expires_at=expires))
    return {"token": token, "link_id": str(id), "expires_at": expires.isoformat(), "url": "/api/reports/file/" + token}


def resolve_link(db, token):
    if not re.fullmatch(r"f1_[A-Za-z0-9_-]{43}", token):
        raise LinkUnavailable()
    link = db.execute(sa.select(file_links).where(file_links.c.token_hash == _digest(token),
        file_links.c.revoked_at.is_(None), file_links.c.expires_at > sa.func.clock_timestamp())).mappings().first()
    if not link:
        raise LinkUnavailable()
    return owned(db, link["artifact_id"], link["creator_id"])


def revoke_link(db, id, creator_id):
    value = db.scalar(file_links.update().where(file_links.c.id == id, file_links.c.creator_id == creator_id)
        .values(revoked_at=sa.func.coalesce(file_links.c.revoked_at, sa.func.clock_timestamp())).returning(file_links.c.id))
    if value is None:
        raise LinkUnavailable()


def claim_cleanup(db, limit=50):
    if not 1 <= limit <= 100:
        raise ValueError("Invalid cleanup batch size")
    now = db.scalar(sa.select(sa.func.clock_timestamp()))
    rows = db.execute(sa.select(artifacts).where(sa.or_(
        sa.and_(artifacts.c.state.in_(["uploading", "deleting"]), artifacts.c.lease_until < now),
        sa.and_(artifacts.c.state == "ready", artifacts.c.expires_at < now)))
        .order_by(artifacts.c.created_at, artifacts.c.id).limit(limit).with_for_update(skip_locked=True)).mappings().all()
    result = []
    for row in rows:
        # Fresh READ COMMITTED statement after acquiring the artifact lock:
        # a reference committed just before the lock must be observed here.
        bound = db.scalar(sa.select(sa.exists().where(references.c.artifact_id == row["id"])))
        shared = db.scalar(sa.select(sa.exists().where(file_links.c.artifact_id == row["id"],
            file_links.c.revoked_at.is_(None), file_links.c.expires_at > now)))
        if bound or shared:
            continue
        result.append(db.execute(artifacts.update().where(artifacts.c.id == row["id"])
            .values(state="deleting", generation=artifacts.c.generation + 1, lease_until=now + timedelta(minutes=5))
            .returning(artifacts)).mappings().one())
    return result


def finish_cleanup(db, id, generation):
    changed = db.scalar(artifacts.update().where(artifacts.c.id == id, artifacts.c.state == "deleting",
        artifacts.c.generation == generation, artifacts.c.lease_until > sa.func.clock_timestamp())
        .values(state="deleted", deleted_at=sa.func.clock_timestamp(), lease_until=None)
        .returning(artifacts.c.id))
    if changed is None:
        raise ArtifactConflict()


def check_schema(engine):
    with engine.connect() as db:
        db.execute(sa.text("SET LOCAL statement_timeout = '2000ms'"))
        for table in (artifacts, references, file_links):
            db.execute(sa.select(table).where(sa.false()))
