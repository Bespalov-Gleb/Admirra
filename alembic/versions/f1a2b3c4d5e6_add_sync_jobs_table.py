"""add sync_jobs table

Revision ID: f1a2b3c4d5e6
Revises: e7f8a9b0c1d3
Create Date: 2026-03-31
"""

from alembic import op
import sqlalchemy as sa
from typing import Sequence, Union


revision: str = "f1a2b3c4d5e6"
down_revision: Union[str, Sequence[str], None] = "e7f8a9b0c1d3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


sync_job_status = sa.Enum(
    "QUEUED", "RUNNING", "SUCCESS", "FAILED", "CANCELLED",
    name="syncjobstatus",
)


def upgrade() -> None:
    sync_job_status.create(op.get_bind(), checkfirst=True)
    op.create_table(
        "sync_jobs",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("integration_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("integrations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sync_job_status, nullable=False, server_default="QUEUED"),
        sa.Column("stage", sa.String(), nullable=True),
        sa.Column("progress", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("attempt", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error", sa.String(), nullable=True),
        sa.Column("params", sa.String(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_sync_jobs_integration_id", "sync_jobs", ["integration_id"], unique=False)
    op.create_index("ix_sync_jobs_status", "sync_jobs", ["status"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_sync_jobs_status", table_name="sync_jobs")
    op.drop_index("ix_sync_jobs_integration_id", table_name="sync_jobs")
    op.drop_table("sync_jobs")
    sync_job_status.drop(op.get_bind(), checkfirst=True)

