"""add_account_name_to_integrations

Revision ID: a2b3c4d5e6f8
Revises: c9d0e1f2a3b4
Create Date: 2026-03-08

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'a2b3c4d5e6f8'
down_revision: Union[str, Sequence[str], None] = 'c9d0e1f2a3b4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('integrations', sa.Column('account_name', sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column('integrations', 'account_name')
