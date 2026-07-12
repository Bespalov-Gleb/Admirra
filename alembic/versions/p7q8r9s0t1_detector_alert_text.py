"""Store full detector composite diagnoses.

Revision ID: p7q8r9s0t1
Revises: o6p7q8r9s0t
Create Date: 2026-07-12
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "p7q8r9s0t1"
down_revision: Union[str, Sequence[str], None] = "o6p7q8r9s0t"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "detector_alerts",
        "hypothesis_text",
        existing_type=sa.String(length=500),
        type_=sa.Text(),
        existing_nullable=True,
    )


def downgrade() -> None:
    # Preserve reversibility even if the newer version has saved a full
    # composite diagnosis.
    op.execute("UPDATE detector_alerts SET hypothesis_text = LEFT(hypothesis_text, 500) WHERE hypothesis_text IS NOT NULL")
    op.alter_column(
        "detector_alerts",
        "hypothesis_text",
        existing_type=sa.Text(),
        type_=sa.String(length=500),
        existing_nullable=True,
    )
