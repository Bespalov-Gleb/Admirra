"""add_selected_counters_to_integration

Revision ID: cfab8b343364
Revises: 7a8b9c0d1e2f
Create Date: 2025-01-20 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'cfab8b343364'
down_revision: Union[str, Sequence[str], None] = '7a8b9c0d1e2f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Add selected_counters column to integrations table.
    This field stores JSON list of Metrika counter IDs selected by user for Direct integrations.
    Allows syncing goals from specific Metrika counters instead of all counters linked to campaigns.
    """
    op.add_column('integrations', sa.Column('selected_counters', sa.String(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('integrations', 'selected_counters')

