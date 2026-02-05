"""add_vk_goal_actions_to_campaigns

Revision ID: 3f9c7a1b2d34
Revises: d1e2f3a4b5c6
Create Date: 2026-02-03 12:15:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "3f9c7a1b2d34"
down_revision: Union[str, Sequence[str], None] = "d1e2f3a4b5c6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add VK goal/action fields to campaigns."""
    op.add_column("campaigns", sa.Column("vk_goal_action_id", sa.String(), nullable=True))
    op.add_column("campaigns", sa.Column("vk_goal_action_name", sa.String(), nullable=True))


def downgrade() -> None:
    """Remove VK goal/action fields from campaigns."""
    op.drop_column("campaigns", "vk_goal_action_name")
    op.drop_column("campaigns", "vk_goal_action_id")
