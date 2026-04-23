"""add sync settings to integration

Revision ID: a99fe91b1079
Revises: 1753da2599ca
Create Date: 2026-01-12 21:10:27.447231

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a99fe91b1079'
down_revision: Union[str, Sequence[str], None] = '1753da2599ca'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('integrations', sa.Column('auto_sync', sa.Boolean(), nullable=True, server_default='true'))
    op.add_column('integrations', sa.Column('sync_interval', sa.Integer(), nullable=True, server_default='1440'))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('integrations', 'sync_interval')
    op.drop_column('integrations', 'auto_sync')
