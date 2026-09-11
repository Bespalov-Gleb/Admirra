"""Durable jobs/outbox, installed explicitly before enabling DURABLE_TASKS."""
from alembic import op
import sqlalchemy as sa

revision = "dd4e5f6a7b8c"
down_revision = "cc3d4e5f6a7b"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        CREATE TABLE background_jobs (
            id UUID PRIMARY KEY, kind VARCHAR(64) NOT NULL, queue VARCHAR(64) NOT NULL,
            dedupe_key VARCHAR(255) NOT NULL UNIQUE, resource VARCHAR(255) NOT NULL,
            tenant VARCHAR(64) NOT NULL, payload JSONB NOT NULL,
            state VARCHAR(16) NOT NULL DEFAULT 'queued', attempt INTEGER NOT NULL DEFAULT 0,
            max_attempts INTEGER NOT NULL DEFAULT 3, replay_safe BOOLEAN NOT NULL DEFAULT false,
            lease_token UUID, lease_until TIMESTAMPTZ, heartbeat_at TIMESTAMPTZ,
            available_at TIMESTAMPTZ NOT NULL DEFAULT now(), created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            finished_at TIMESTAMPTZ, error_type VARCHAR(128),
            CONSTRAINT ck_background_state CHECK (state IN ('queued','running','succeeded','failed','uncertain')),
            CONSTRAINT ck_background_attempts CHECK (attempt >= 0 AND max_attempts > 0)
        )
    """)
    op.execute("CREATE INDEX ix_background_ready ON background_jobs (state, available_at)")
    op.execute("CREATE INDEX ix_background_resource ON background_jobs (resource, state)")
    op.execute("CREATE INDEX ix_background_sync_job ON background_jobs ((payload->>'sync_job_id')) WHERE kind = 'sync'")
    op.execute("CREATE INDEX ix_background_retention ON background_jobs (finished_at) WHERE state IN ('succeeded', 'failed')")
    op.execute("CREATE UNIQUE INDEX uq_background_running_resource ON background_jobs (resource) WHERE state = 'running'")
    op.execute("""
        CREATE TABLE background_outbox (
            job_id UUID PRIMARY KEY REFERENCES background_jobs(id) ON DELETE CASCADE,
            next_publish_at TIMESTAMPTZ NOT NULL DEFAULT now(), publish_count INTEGER NOT NULL DEFAULT 0
        )
    """)
    op.execute("CREATE INDEX ix_background_outbox_due ON background_outbox (next_publish_at)")
    op.execute("CREATE TABLE background_schedule_cursor (name VARCHAR(64) PRIMARY KEY, last_tick TIMESTAMPTZ NOT NULL)")


def downgrade():
    if op.get_bind().execute(sa.text("SELECT count(*) FROM background_jobs WHERE state IN ('queued','running','uncertain')")).scalar():
        raise RuntimeError("Drain/reconcile durable jobs before downgrading the control plane")
    op.drop_table("background_schedule_cursor")
    op.drop_table("background_outbox")
    op.drop_table("background_jobs")
