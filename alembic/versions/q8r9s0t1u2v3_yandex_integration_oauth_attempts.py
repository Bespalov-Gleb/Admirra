"""Create one-time Yandex integration OAuth sessions.

Revision ID: q8r9s0t1u2v3
Revises: p7q8r9s0t1
Create Date: 2026-07-14
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "q8r9s0t1u2v3"
down_revision: Union[str, Sequence[str], None] = "p7q8r9s0t1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "yandex_integration_oauth_attempts",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("state_hash", sa.String(length=128), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("client_id", sa.UUID(), nullable=True),
        sa.Column("client_name", sa.String(length=255), nullable=True),
        sa.Column("platform", sa.String(length=32), nullable=False),
        sa.Column("flow", sa.String(length=32), server_default="yandex_direct", nullable=False),
        sa.Column("resume_integration_id", sa.UUID(), nullable=True),
        sa.Column("redirect_uri", sa.String(length=2048), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_yandex_integration_oauth_attempts_state_hash"),
        "yandex_integration_oauth_attempts",
        ["state_hash"],
        unique=True,
    )
    op.create_index(
        op.f("ix_yandex_integration_oauth_attempts_user_id"),
        "yandex_integration_oauth_attempts",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_yandex_integration_oauth_attempts_client_id"),
        "yandex_integration_oauth_attempts",
        ["client_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_yandex_integration_oauth_attempts_resume_integration_id"),
        "yandex_integration_oauth_attempts",
        ["resume_integration_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_yandex_integration_oauth_attempts_expires_at"),
        "yandex_integration_oauth_attempts",
        ["expires_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_yandex_integration_oauth_attempts_expires_at"), table_name="yandex_integration_oauth_attempts")
    op.drop_index(op.f("ix_yandex_integration_oauth_attempts_resume_integration_id"), table_name="yandex_integration_oauth_attempts")
    op.drop_index(op.f("ix_yandex_integration_oauth_attempts_client_id"), table_name="yandex_integration_oauth_attempts")
    op.drop_index(op.f("ix_yandex_integration_oauth_attempts_user_id"), table_name="yandex_integration_oauth_attempts")
    op.drop_index(op.f("ix_yandex_integration_oauth_attempts_state_hash"), table_name="yandex_integration_oauth_attempts")
    op.drop_table("yandex_integration_oauth_attempts")
