"""add_report_settings_to_users

Revision ID: b8c9d0e1f2a3
Revises: add_captcha_fields
Create Date: 2026-03-04

Добавляет report_telegram_chat_id и report_email_recipients в users.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b8c9d0e1f2a3"
down_revision: Union[str, Sequence[str], None] = "add_captcha_fields"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # PostgreSQL: IF NOT EXISTS — безопасно при повторном запуске
    op.execute(sa.text("ALTER TABLE users ADD COLUMN IF NOT EXISTS report_telegram_chat_id VARCHAR"))
    op.execute(sa.text("ALTER TABLE users ADD COLUMN IF NOT EXISTS report_email_recipients VARCHAR"))


def downgrade() -> None:
    op.drop_column("users", "report_email_recipients")
    op.drop_column("users", "report_telegram_chat_id")
