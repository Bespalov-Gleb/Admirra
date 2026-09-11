"""Shared state for history loading across API instances."""
from alembic import op
import sqlalchemy as sa

revision = "ff6a7b8c9d0e"
down_revision = "ee5f6a7b8c9d"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""CREATE TABLE history_backfill_runs (
        client_id UUID PRIMARY KEY REFERENCES clients(id) ON DELETE CASCADE,
        run_id UUID NOT NULL UNIQUE,
        status VARCHAR(16) NOT NULL CHECK (status IN ('running','done','partial')),
        months INTEGER NOT NULL CHECK (months BETWEEN 1 AND 12),
        steps_total INTEGER NOT NULL CHECK (steps_total > 0),
        steps_done INTEGER NOT NULL DEFAULT 0, steps_failed INTEGER NOT NULL DEFAULT 0,
        started_at TIMESTAMPTZ NOT NULL DEFAULT now(), finished_at TIMESTAMPTZ,
        checked_at TIMESTAMPTZ NOT NULL DEFAULT now()
    )""")
    op.execute("CREATE INDEX ix_background_backfill_run ON background_jobs ((payload->>'run_id')) WHERE kind = 'history.backfill'")


def downgrade():
    active = op.get_bind().scalar(sa.text("SELECT count(*) FROM history_backfill_runs WHERE status = 'running'"))
    pending = op.get_bind().scalar(sa.text("SELECT count(*) FROM background_jobs WHERE kind = 'history.backfill' AND state IN ('queued','running','uncertain')"))
    if active or pending:
        raise RuntimeError("Finish history backfills before downgrade")
    op.drop_index("ix_background_backfill_run", table_name="background_jobs")
    op.drop_table("history_backfill_runs")
