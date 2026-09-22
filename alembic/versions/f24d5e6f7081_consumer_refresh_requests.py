"""Bounded, persisted data refresh requests for derived consumers."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "f24d5e6f7081"
down_revision = "f13c4d5e6f70"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("data_refresh_requests",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("consumer", sa.String(16), nullable=False),
        sa.Column("request_key", sa.String(64), nullable=False),
        sa.Column("state", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("next_check_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("user_id", "consumer", "request_key", name="uq_data_refresh_request"))
    op.create_index("ix_data_refresh_due", "data_refresh_requests", ["status", "next_check_at"])


def downgrade():
    op.drop_table("data_refresh_requests")
