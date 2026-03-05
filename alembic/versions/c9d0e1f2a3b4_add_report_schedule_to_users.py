"""add_report_schedule_to_users

Revision ID: c9d0e1f2a3b4
Revises: b8c9d0e1f2a3
Create Date: 2026-03-05

Добавляет report_schedule в users для автоматической отправки отчётов.
Формат: mon_10, tue_10, wed_10, thu_10, fri_10, daily_10
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c9d0e1f2a3b4"
down_revision: Union[str, Sequence[str], None] = "b8c9d0e1f2a3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(sa.text("ALTER TABLE users ADD COLUMN IF NOT EXISTS report_schedule VARCHAR"))


def downgrade() -> None:
    op.drop_column("users", "report_schedule")
