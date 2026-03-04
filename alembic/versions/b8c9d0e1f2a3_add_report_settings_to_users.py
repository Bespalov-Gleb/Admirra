"""add_report_settings_to_users (standalone)

Revision ID: b8c9d0e1f2a3
Revises: 3f9c7a1b2d34
Create Date: 2026-03-04

Добавляет report_telegram_chat_id и report_email_recipients в users.
Используйте если add_captcha_fields не применяется из-за overlaps.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b8c9d0e1f2a3"
down_revision: Union[str, Sequence[str], None] = "3f9c7a1b2d34"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # PostgreSQL: IF NOT EXISTS — безопасно при повторном запуске
    op.execute(sa.text("ALTER TABLE users ADD COLUMN IF NOT EXISTS report_telegram_chat_id VARCHAR"))
    op.execute(sa.text("ALTER TABLE users ADD COLUMN IF NOT EXISTS report_email_recipients VARCHAR"))


def downgrade() -> None:
    op.drop_column("users", "report_email_recipients")
    op.drop_column("users", "report_telegram_chat_id")
