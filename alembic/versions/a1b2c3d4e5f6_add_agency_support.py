"""add_agency_support

Revision ID: a1b2c3d4e5f6
Revises: 314d27135fdd
Create Date: 2026-01-05 20:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = 'e3b4acdd7635'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('integrations', sa.Column('is_agency', sa.Boolean(), server_default='False', nullable=True))
    op.add_column('integrations', sa.Column('agency_client_login', sa.String(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('integrations', 'agency_client_login')
    op.drop_column('integrations', 'is_agency')
