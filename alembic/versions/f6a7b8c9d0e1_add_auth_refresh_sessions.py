"""add auth refresh sessions

Revision ID: f6a7b8c9d0e1
Revises: d5e6f7a8b9c0
Create Date: 2026-05-14
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f6a7b8c9d0e1"
down_revision: Union[str, Sequence[str], None] = "d5e6f7a8b9c0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "auth_refresh_sessions",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("token_hash", sa.String(length=128), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("remember_me", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("user_agent", sa.String(length=512), nullable=True),
        sa.Column("ip_address", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_auth_refresh_sessions_user_id"), "auth_refresh_sessions", ["user_id"], unique=False)
    op.create_index(op.f("ix_auth_refresh_sessions_token_hash"), "auth_refresh_sessions", ["token_hash"], unique=True)
    op.create_index(op.f("ix_auth_refresh_sessions_expires_at"), "auth_refresh_sessions", ["expires_at"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_auth_refresh_sessions_expires_at"), table_name="auth_refresh_sessions")
    op.drop_index(op.f("ix_auth_refresh_sessions_token_hash"), table_name="auth_refresh_sessions")
    op.drop_index(op.f("ix_auth_refresh_sessions_user_id"), table_name="auth_refresh_sessions")
    op.drop_table("auth_refresh_sessions")
