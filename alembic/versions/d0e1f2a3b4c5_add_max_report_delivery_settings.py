"""add_max_report_delivery_settings

Revision ID: d0e1f2a3b4c5
Revises: c9d0e1f2a3b4
Create Date: 2026-05-17

Добавляет настройки доставки отчётов в MAX и список включённых каналов.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d0e1f2a3b4c5"
down_revision: Union[str, Sequence[str], None] = "c9d0e1f2a3b4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(sa.text("ALTER TABLE users ADD COLUMN IF NOT EXISTS report_max_chat_id VARCHAR"))
    op.execute(sa.text("ALTER TABLE users ADD COLUMN IF NOT EXISTS report_max_user_id VARCHAR"))
    op.execute(sa.text("ALTER TABLE users ADD COLUMN IF NOT EXISTS report_max_username VARCHAR"))
    op.execute(sa.text("ALTER TABLE users ADD COLUMN IF NOT EXISTS report_delivery_channels VARCHAR"))

    op.execute(sa.text("""
        CREATE TABLE IF NOT EXISTS max_report_link_tokens (
            id UUID PRIMARY KEY,
            user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            token VARCHAR(64) NOT NULL UNIQUE,
            expires_at TIMESTAMPTZ NOT NULL,
            consumed_at TIMESTAMPTZ,
            created_at TIMESTAMPTZ DEFAULT now()
        )
    """))
    op.execute(sa.text(
        "CREATE INDEX IF NOT EXISTS ix_max_report_link_tokens_user_id ON max_report_link_tokens (user_id)"
    ))
    op.execute(sa.text(
        "CREATE UNIQUE INDEX IF NOT EXISTS ix_max_report_link_tokens_token ON max_report_link_tokens (token)"
    ))


def downgrade() -> None:
    op.drop_index("ix_max_report_link_tokens_token", table_name="max_report_link_tokens")
    op.drop_index("ix_max_report_link_tokens_user_id", table_name="max_report_link_tokens")
    op.drop_table("max_report_link_tokens")
    op.drop_column("users", "report_delivery_channels")
    op.drop_column("users", "report_max_username")
    op.drop_column("users", "report_max_user_id")
    op.drop_column("users", "report_max_chat_id")
