"""TZ admin v1: staff manager role and user fields

Revision ID: f8a9b0c1d2e3
Revises: f7a8b9c0d1e2
Create Date: 2026-05-24
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f8a9b0c1d2e3"
down_revision: Union[str, Sequence[str], None] = "f7a8b9c0d1e2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE userrole ADD VALUE IF NOT EXISTS 'STAFF_MANAGER'")

    op.add_column("users", sa.Column("block_reason", sa.String(), nullable=True))
    op.add_column("users", sa.Column("ai_quota_resets_at", sa.DateTime(timezone=True), nullable=True))

    staff_status = sa.Enum("pending", "active", "inactive", name="staffstatus")
    staff_status.create(op.get_bind(), checkfirst=True)
    op.add_column("users", sa.Column("staff_status", staff_status, nullable=True))


def downgrade() -> None:
    op.drop_column("users", "staff_status")
    op.drop_column("users", "ai_quota_resets_at")
    op.drop_column("users", "block_reason")
    op.execute("DROP TYPE IF EXISTS staffstatus")
