"""add_vk_user_id_to_integrations

Revision ID: e4f5a6b7c8d9
Revises: d1e2f3a4b5c6
Create Date: 2026-02-01 19:41:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e4f5a6b7c8d9'
down_revision: Union[str, Sequence[str], None] = 'd1e2f3a4b5c6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add vk_user_id column to integrations table."""
    op.add_column('integrations', sa.Column('vk_user_id', sa.String(), nullable=True))


def downgrade() -> None:
    """Remove vk_user_id column from integrations table."""
    op.drop_column('integrations', 'vk_user_id')


