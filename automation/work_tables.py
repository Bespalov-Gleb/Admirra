"""Durable control plane; schema is installed only by an explicit migration."""
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

metadata = sa.MetaData()
jobs = sa.Table(
    "background_jobs", metadata,
    sa.Column("id", UUID(as_uuid=True), primary_key=True),
    sa.Column("kind", sa.String(64), nullable=False),
    sa.Column("queue", sa.String(64), nullable=False),
    sa.Column("dedupe_key", sa.String(255), nullable=False, unique=True),
    sa.Column("resource", sa.String(255), nullable=False),
    sa.Column("tenant", sa.String(64), nullable=False),
    sa.Column("payload", JSONB, nullable=False),
    sa.Column("state", sa.String(16), nullable=False, server_default="queued"),
    sa.Column("attempt", sa.Integer, nullable=False, server_default="0"),
    sa.Column("max_attempts", sa.Integer, nullable=False, server_default="3"),
    sa.Column("replay_safe", sa.Boolean, nullable=False, server_default=sa.false()),
    sa.Column("lease_token", UUID(as_uuid=True)),
    sa.Column("lease_until", sa.DateTime(timezone=True)),
    sa.Column("heartbeat_at", sa.DateTime(timezone=True)),
    sa.Column("available_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    sa.Column("finished_at", sa.DateTime(timezone=True)),
    sa.Column("error_type", sa.String(128)),
    sa.CheckConstraint("state IN ('queued','running','succeeded','failed','uncertain')", name="ck_background_state"),
    sa.CheckConstraint("attempt >= 0 AND max_attempts > 0", name="ck_background_attempts"),
)
sa.Index("ix_background_ready", jobs.c.state, jobs.c.available_at)
sa.Index("ix_background_resource", jobs.c.resource, jobs.c.state)
sa.Index("ix_background_sync_job", jobs.c.payload["sync_job_id"].astext, postgresql_where=jobs.c.kind == "sync")
sa.Index("ix_background_retention", jobs.c.finished_at, postgresql_where=jobs.c.state.in_(["succeeded", "failed"]))
sa.Index("uq_background_running_resource", jobs.c.resource, unique=True,
         postgresql_where=jobs.c.state == "running")
outbox = sa.Table(
    "background_outbox", metadata,
    sa.Column("job_id", UUID(as_uuid=True), sa.ForeignKey("background_jobs.id", ondelete="CASCADE"), primary_key=True),
    sa.Column("next_publish_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    sa.Column("publish_count", sa.Integer, nullable=False, server_default="0"),
)
sa.Index("ix_background_outbox_due", outbox.c.next_publish_at)
schedule_cursor = sa.Table(
    "background_schedule_cursor", metadata,
    sa.Column("name", sa.String(64), primary_key=True),
    sa.Column("last_tick", sa.DateTime(timezone=True), nullable=False),
)

# One immutable authorization/receipt per recipient-scoped calendar child.
# No raw chat IDs, message bodies, tokens or lead personal data are stored here.
lead_deliveries = sa.Table(
    "lead_alert_deliveries", metadata,
    sa.Column("job_id", UUID(as_uuid=True), sa.ForeignKey("background_jobs.id", ondelete="CASCADE"), primary_key=True),
    sa.Column("scope_digest", sa.String(64), nullable=False),
    sa.Column("body_digest", sa.String(64), nullable=False),
    sa.Column("state", sa.String(16), nullable=False),
    sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    sa.Column("confirmed_at", sa.DateTime(timezone=True)),
    sa.CheckConstraint("state IN ('sending','sent','rejected')", name="ck_lead_alert_delivery_state"),
)

lead_exports = sa.Table(
    "lead_export_receipts", metadata,
    sa.Column("job_id", UUID(as_uuid=True), sa.ForeignKey("background_jobs.id", ondelete="CASCADE"), primary_key=True),
    sa.Column("scope_digest", sa.String(64), nullable=False),
    sa.Column("body_digest", sa.String(64), nullable=False),
    sa.Column("state", sa.String(16), nullable=False),
    sa.Column("provider_ref", sa.String(128)),
    sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    sa.Column("confirmed_at", sa.DateTime(timezone=True)),
    sa.CheckConstraint("state IN ('sending','sent','rejected')", name="ck_lead_export_receipt_state"),
)
