"""Add campaign platform status fields

Revision ID: j1k2l3m4n5o6
Revises: i1j2k3l4m5n6
Create Date: 2026-06-08

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "j1k2l3m4n5o6"
down_revision: Union[str, Sequence[str], None] = "i1j2k3l4m5n6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("campaigns", sa.Column("platform_status", sa.String(), nullable=True))
    op.add_column("campaigns", sa.Column("platform_state", sa.String(), nullable=True))
    op.add_column("campaigns", sa.Column("display_status", sa.String(), nullable=True))
    op.add_column("campaigns", sa.Column("status_synced_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("campaigns", "status_synced_at")
    op.drop_column("campaigns", "display_status")
    op.drop_column("campaigns", "platform_state")
    op.drop_column("campaigns", "platform_status")
