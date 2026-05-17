"""add max oauth login attempts

Revision ID: a1b2c3d4e5f8
Revises: c4d5e6f7a8b9
Create Date: 2026-05-15
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a1b2c3d4e5f8"
down_revision: Union[str, Sequence[str], None] = "c4d5e6f7a8b9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "max_oauth_login_attempts",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("state_hash", sa.String(length=128), nullable=False),
        sa.Column("payload_hash", sa.String(length=128), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=True),
        sa.Column("max_user_id", sa.String(length=128), nullable=True),
        sa.Column("max_username", sa.String(length=255), nullable=True),
        sa.Column("max_name", sa.String(length=255), nullable=True),
        sa.Column("max_chat_id", sa.String(length=128), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("authorized_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_max_oauth_login_attempts_state_hash"), "max_oauth_login_attempts", ["state_hash"], unique=True)
    op.create_index(op.f("ix_max_oauth_login_attempts_payload_hash"), "max_oauth_login_attempts", ["payload_hash"], unique=True)
    op.create_index(op.f("ix_max_oauth_login_attempts_user_id"), "max_oauth_login_attempts", ["user_id"], unique=False)
    op.create_index(op.f("ix_max_oauth_login_attempts_max_user_id"), "max_oauth_login_attempts", ["max_user_id"], unique=False)
    op.create_index(op.f("ix_max_oauth_login_attempts_expires_at"), "max_oauth_login_attempts", ["expires_at"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_max_oauth_login_attempts_expires_at"), table_name="max_oauth_login_attempts")
    op.drop_index(op.f("ix_max_oauth_login_attempts_max_user_id"), table_name="max_oauth_login_attempts")
    op.drop_index(op.f("ix_max_oauth_login_attempts_user_id"), table_name="max_oauth_login_attempts")
    op.drop_index(op.f("ix_max_oauth_login_attempts_payload_hash"), table_name="max_oauth_login_attempts")
    op.drop_index(op.f("ix_max_oauth_login_attempts_state_hash"), table_name="max_oauth_login_attempts")
    op.drop_table("max_oauth_login_attempts")
