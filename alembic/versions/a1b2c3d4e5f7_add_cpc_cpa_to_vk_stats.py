"""add_cpc_cpa_to_vk_stats

Revision ID: a1b2c3d4e5f7
Revises: 2f3a4b5c6d78
Create Date: 2026-01-31 15:40:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f7"
down_revision: Union[str, Sequence[str], None] = "2f3a4b5c6d78"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add cpc and cpa columns to vk_stats table."""
    op.add_column("vk_stats", sa.Column("cpc", sa.Numeric(20, 2), nullable=True))
    op.add_column("vk_stats", sa.Column("cpa", sa.Numeric(20, 2), nullable=True))


def downgrade() -> None:
    """Remove cpc and cpa columns from vk_stats table."""
    op.drop_column("vk_stats", "cpa")
    op.drop_column("vk_stats", "cpc")

