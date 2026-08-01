"""Граница тарифа: докупленные слоты и состояние превышения (§8 экономики).

subscriptions.purchased_project_slots — докупленные слоты проектов; эффективный
лимит = лимит тарифа + слоты. overflow_since / overflow_periods_count — состояние
превышения (сам факт не хранится, вычисляется от эффективного лимита).

Продублировано в init_db_with_retry() и core/models.py (правило проекта).

Revision ID: y6z7a8b9c0d1
Revises: x5y6z7a8b9c0
Create Date: 2026-08-01
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "y6z7a8b9c0d1"
down_revision: Union[str, Sequence[str], None] = "x5y6z7a8b9c0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_column(table: str, column: str) -> bool:
    inspector = sa.inspect(op.get_bind())
    return column in {col["name"] for col in inspector.get_columns(table)}


def upgrade() -> None:
    if not _has_column("subscriptions", "purchased_project_slots"):
        op.add_column(
            "subscriptions",
            sa.Column("purchased_project_slots", sa.Integer(), nullable=False, server_default="0"),
        )
    if not _has_column("subscriptions", "overflow_since"):
        op.add_column(
            "subscriptions",
            sa.Column("overflow_since", sa.DateTime(timezone=True), nullable=True),
        )
    if not _has_column("subscriptions", "overflow_periods_count"):
        op.add_column(
            "subscriptions",
            sa.Column("overflow_periods_count", sa.Integer(), nullable=False, server_default="0"),
        )


def downgrade() -> None:
    for col in ("overflow_periods_count", "overflow_since", "purchased_project_slots"):
        if _has_column("subscriptions", col):
            op.drop_column("subscriptions", col)
