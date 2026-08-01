"""Модель тёплых проектов: last_dashboard_viewed_at / last_comment_generated_at (§9.2).

last_dashboard_viewed_at пишется при открытии дашборда любым пользователем аккаунта
(проект «тёплый» в окне warm_window_days, и от этой точки берётся дельта §9.5).
last_comment_generated_at — троттлинг ночной генерации.

Продублировано в init_db_with_retry() и core/models.py.

Revision ID: z7a8b9c0d1e2
Revises: y6z7a8b9c0d1
Create Date: 2026-08-01
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "z7a8b9c0d1e2"
down_revision: Union[str, Sequence[str], None] = "y6z7a8b9c0d1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_column(table: str, column: str) -> bool:
    inspector = sa.inspect(op.get_bind())
    return column in {col["name"] for col in inspector.get_columns(table)}


def upgrade() -> None:
    if not _has_column("clients", "last_dashboard_viewed_at"):
        op.add_column("clients", sa.Column("last_dashboard_viewed_at", sa.DateTime(timezone=True), nullable=True))
    if not _has_column("clients", "last_comment_generated_at"):
        op.add_column("clients", sa.Column("last_comment_generated_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    for col in ("last_comment_generated_at", "last_dashboard_viewed_at"):
        if _has_column("clients", col):
            op.drop_column("clients", col)
