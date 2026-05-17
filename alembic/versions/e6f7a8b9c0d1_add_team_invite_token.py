"""add team invite token columns

Revision ID: e6f7a8b9c0d1
Revises: c3d4e5f6a7b8
Create Date: 2026-05-15
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e6f7a8b9c0d1"
down_revision: Union[str, Sequence[str], None] = "c3d4e5f6a7b8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("team_members", sa.Column("invite_token", sa.UUID(), nullable=True))
    op.add_column("team_members", sa.Column("invite_token_expires_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index(
        "ix_team_members_invite_token",
        "team_members",
        ["invite_token"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ix_team_members_invite_token", table_name="team_members")
    op.drop_column("team_members", "invite_token_expires_at")
    op.drop_column("team_members", "invite_token")
