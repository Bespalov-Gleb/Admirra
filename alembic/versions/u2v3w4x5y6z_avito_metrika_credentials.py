"""Keep the Avito Metrika OAuth grant on the Avito integration itself.

Revision ID: u2v3w4x5y6z
Revises: t1u2v3w4x5y6
Create Date: 2026-07-21
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "u2v3w4x5y6z"
down_revision: Union[str, Sequence[str], None] = "t1u2v3w4x5y6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("integrations", sa.Column("metrika_access_token", sa.String(), nullable=True))
    op.add_column("integrations", sa.Column("metrika_refresh_token", sa.String(), nullable=True))
    op.add_column("integrations", sa.Column("metrika_account_id", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("integrations", "metrika_account_id")
    op.drop_column("integrations", "metrika_refresh_token")
    op.drop_column("integrations", "metrika_access_token")
