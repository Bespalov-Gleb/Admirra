"""Durable synchronization effective date/stage coverage (no historical backfill).

Revision ID: f02b3c4d5e6f
Revises: ef1a2b3c4d5e
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "f02b3c4d5e6f"
down_revision = "ef1a2b3c4d5e"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("sync_coverage",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("integration_id", UUID(as_uuid=True), sa.ForeignKey("integrations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("client_id", UUID(as_uuid=True), sa.ForeignKey("clients.id", ondelete="CASCADE"), nullable=False),
        sa.Column("owner_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("stage", sa.String(32), nullable=False),
        sa.Column("settings_digest", sa.String(64), nullable=False),
        sa.Column("date_from", sa.Date(), nullable=False),
        sa.Column("date_to", sa.Date(), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("execution_id", UUID(as_uuid=True), nullable=False),
        sa.CheckConstraint("date_from <= date_to", name="ck_sync_coverage_dates"))
    op.create_index("ix_sync_coverage_window", "sync_coverage", ["integration_id", "stage", "date_from", "date_to"])


def downgrade():
    op.drop_table("sync_coverage")
