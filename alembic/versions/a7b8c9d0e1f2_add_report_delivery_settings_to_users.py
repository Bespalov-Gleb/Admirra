"""add_report_delivery_settings_to_users

Revision ID: a7b8c9d0e1f2
Revises: add_captcha_fields
Create Date: 2026-02-18

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a7b8c9d0e1f2"
down_revision: Union[str, Sequence[str], None] = "add_captcha_fields"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("report_telegram_chat_id", sa.String(), nullable=True))
    op.add_column("users", sa.Column("report_email_recipients", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "report_email_recipients")
    op.drop_column("users", "report_telegram_chat_id")
