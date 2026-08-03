"""Expand detector alert mode for iteration-3 critical checks.

Revision ID: aa1b2c3d4e5f
Revises: z7a8b9c0d1e2
Create Date: 2026-08-03
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "aa1b2c3d4e5f"
down_revision: Union[str, Sequence[str], None] = "z7a8b9c0d1e2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "detector_alerts",
        "mode",
        existing_type=sa.String(length=16),
        type_=sa.String(length=32),
        existing_nullable=False,
    )


def downgrade() -> None:
    # PostgreSQL refuses to narrow VARCHAR while longer values exist.  A
    # downgraded application cannot represent these newer modes anyway, so
    # preserve the rows and use a deterministic legacy-safe identifier.
    op.execute(
        "UPDATE detector_alerts "
        "SET mode = LEFT(mode, 16) "
        "WHERE char_length(mode) > 16"
    )
    op.alter_column(
        "detector_alerts",
        "mode",
        existing_type=sa.String(length=32),
        type_=sa.String(length=16),
        existing_nullable=False,
    )
