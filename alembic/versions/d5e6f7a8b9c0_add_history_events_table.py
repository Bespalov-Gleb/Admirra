"""add history events table

Revision ID: d5e6f7a8b9c0
Revises: c3d4e5f6a7b8
Create Date: 2026-04-29
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d5e6f7a8b9c0"
down_revision: Union[str, Sequence[str], None] = "c3d4e5f6a7b8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "history_events",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("account_id", sa.UUID(), nullable=False),
        sa.Column("actor_user_id", sa.UUID(), nullable=True),
        sa.Column("actor_email", sa.String(length=255), nullable=True),
        sa.Column("actor_role", sa.String(length=32), nullable=True),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("action", sa.String(length=128), nullable=False),
        sa.Column("description", sa.String(length=1000), nullable=True),
        sa.Column("client_id", sa.UUID(), nullable=True),
        sa.Column("target_type", sa.String(length=64), nullable=True),
        sa.Column("target_id", sa.String(length=128), nullable=True),
        sa.Column("meta", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["account_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_history_events_account_id"), "history_events", ["account_id"], unique=False)
    op.create_index(op.f("ix_history_events_actor_user_id"), "history_events", ["actor_user_id"], unique=False)
    op.create_index(op.f("ix_history_events_event_type"), "history_events", ["event_type"], unique=False)
    op.create_index(op.f("ix_history_events_client_id"), "history_events", ["client_id"], unique=False)
    op.create_index(op.f("ix_history_events_created_at"), "history_events", ["created_at"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_history_events_created_at"), table_name="history_events")
    op.drop_index(op.f("ix_history_events_client_id"), table_name="history_events")
    op.drop_index(op.f("ix_history_events_event_type"), table_name="history_events")
    op.drop_index(op.f("ix_history_events_actor_user_id"), table_name="history_events")
    op.drop_index(op.f("ix_history_events_account_id"), table_name="history_events")
    op.drop_table("history_events")
