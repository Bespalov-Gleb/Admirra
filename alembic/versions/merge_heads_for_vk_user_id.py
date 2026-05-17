"""merge_heads_for_vk_user_id

Revision ID: d1e2f3a4b5c6
Revises: a1b2c3d4e5f7, a1b2c3d4e5f8, b2c3d4e5f6a7, cfab8b343364
Create Date: 2026-02-01 19:40:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd1e2f3a4b5c6'
down_revision: Union[str, Sequence[str], None] = ('a1b2c3d4e5f7', 'a1b2c3d4e5f8', 'b2c3d4e5f6a7', 'cfab8b343364')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Merge heads."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass


