"""add_integration_id_to_metrika_goals

Revision ID: 7a8b9c0d1e2f
Revises: 113e8aa25ef0
Create Date: 2026-01-19 18:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '7a8b9c0d1e2f'
down_revision: Union[str, Sequence[str], None] = '113e8aa25ef0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Add integration_id column to metrika_goals table to enable filtering goals by integration/profile.
    This allows differentiation when a client has multiple Yandex Direct integrations.
    """
    # Add integration_id column (nullable initially to handle existing data)
    op.add_column('metrika_goals', sa.Column('integration_id', postgresql.UUID(as_uuid=True), nullable=True))
    
    # Add foreign key constraint
    op.create_foreign_key(
        'fk_metrika_goals_integration_id',
        'metrika_goals',
        'integrations',
        ['integration_id'],
        ['id'],
        ondelete='CASCADE'
    )
    
    # Add index for faster filtering
    op.create_index(
        'ix_metrika_goals_integration_id',
        'metrika_goals',
        ['integration_id'],
        unique=False
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Drop index
    op.drop_index('ix_metrika_goals_integration_id', table_name='metrika_goals')
    
    # Drop foreign key
    op.drop_constraint('fk_metrika_goals_integration_id', 'metrika_goals', type_='foreignkey')
    
    # Drop column
    op.drop_column('metrika_goals', 'integration_id')


