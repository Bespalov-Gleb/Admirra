"""Durable evidence for each report recipient, not just the overall batch."""
from alembic import op
import sqlalchemy as sa

revision = "ee5f6a7b8c9d"
down_revision = "dd4e5f6a7b8c"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""CREATE TABLE report_route_attempts (
        delivery_id UUID NOT NULL REFERENCES report_deliveries(id) ON DELETE CASCADE,
        route_key VARCHAR(64) NOT NULL, channel VARCHAR(16) NOT NULL,
        state VARCHAR(16) NOT NULL, token UUID NOT NULL, attempt INTEGER NOT NULL DEFAULT 1,
        updated_at TIMESTAMPTZ NOT NULL DEFAULT now(), resolutions JSONB NOT NULL DEFAULT '[]',
        PRIMARY KEY (delivery_id, route_key),
        CONSTRAINT ck_report_route_state CHECK (state IN ('sending','accepted','rejected','uncertain'))
    )""")
    op.execute("CREATE INDEX ix_report_route_reconciliation ON report_route_attempts (state, updated_at) WHERE state IN ('sending','uncertain')")
    # The old sender had no durable per-recipient evidence. Never guess that
    # a failed/sending legacy batch was not delivered before a lost response.
    op.execute("""UPDATE report_deliveries SET delivery_results =
        (COALESCE(delivery_results::jsonb, '{}'::jsonb) || jsonb_build_object('legacy_untracked_attempts', true))::json
        WHERE status IN ('sending','failed','partial')""")


def downgrade():
    if op.get_bind().scalar(sa.text("SELECT count(*) FROM report_route_attempts WHERE state IN ('sending','uncertain')")):
        raise RuntimeError("Reconcile in-flight/uncertain report recipients before downgrade")
    op.drop_table("report_route_attempts")
