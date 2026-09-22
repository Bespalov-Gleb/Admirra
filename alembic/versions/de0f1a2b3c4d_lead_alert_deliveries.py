"""Durable recipient-scoped lead alert dispatch evidence."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "de0f1a2b3c4d"
down_revision = "cd9e0f1a2b3c"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("lead_alert_deliveries",
        sa.Column("job_id", UUID(as_uuid=True), sa.ForeignKey("background_jobs.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("scope_digest", sa.String(64), nullable=False),
        sa.Column("body_digest", sa.String(64), nullable=False),
        sa.Column("state", sa.String(16), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("confirmed_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint("state IN ('sending','sent','rejected')", name="ck_lead_alert_delivery_state"))


def downgrade():
    raise RuntimeError("Retain lead delivery evidence on application rollback")
