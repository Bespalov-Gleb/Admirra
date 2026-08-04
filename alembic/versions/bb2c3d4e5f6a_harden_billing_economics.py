"""Harden billing orders, pinned pricing and scheduled slot changes.

Revision ID: bb2c3d4e5f6a
Revises: aa1b2c3d4e5f
Create Date: 2026-08-04
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "bb2c3d4e5f6a"
down_revision: Union[str, Sequence[str], None] = "aa1b2c3d4e5f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_column(table: str, column: str) -> bool:
    inspector = sa.inspect(op.get_bind())
    return column in {col["name"] for col in inspector.get_columns(table)}


def upgrade() -> None:
    columns = (
        sa.Column("pending_billing_period", sa.String(), nullable=True),
        sa.Column("pending_purchased_project_slots", sa.Integer(), nullable=True),
        sa.Column("price_book_snapshot", sa.JSON(), nullable=True),
        sa.Column("pending_price_book_snapshot", sa.JSON(), nullable=True),
        sa.Column("overflow_notice_dismissed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("recurring_sync_required", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("peak_active_projects", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("overflow_warning_period_end", sa.DateTime(timezone=True), nullable=True),
    )
    for column in columns:
        if not _has_column("subscriptions", column.name):
            op.add_column("subscriptions", column)

    client_columns = (
        sa.Column("last_dashboard_snapshot", sa.JSON(), nullable=True),
        sa.Column("ai_comment_memory", sa.JSON(), nullable=True),
    )
    for column in client_columns:
        if not _has_column("clients", column.name):
            op.add_column("clients", column)

    generation_columns = (
        sa.Column("input_tokens", sa.Integer(), nullable=True),
        sa.Column("output_tokens", sa.Integer(), nullable=True),
        sa.Column("cache_creation_input_tokens", sa.Integer(), nullable=True),
        sa.Column("cache_read_input_tokens", sa.Integer(), nullable=True),
        sa.Column("cost_usd", sa.Numeric(14, 6), nullable=True),
        sa.Column("cost_rub", sa.Numeric(14, 6), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("campaign_count", sa.Integer(), nullable=True),
        sa.Column("attempt", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("validation_failed", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("viewed_at", sa.DateTime(timezone=True), nullable=True),
    )
    for column in generation_columns:
        if not _has_column("ai_comment_generations", column.name):
            op.add_column("ai_comment_generations", column)

    # Существующие аккаунты закрепляются за текущей версией при первом чтении;
    # snapshot создаст приложение из фактической env-конфигурации.
    op.execute("UPDATE subscriptions SET price_book_version = 1 WHERE price_book_version IS NULL")


def downgrade() -> None:
    for name in (
        "viewed_at", "validation_failed", "retry_count", "attempt",
        "campaign_count", "duration_ms", "cost_rub", "cost_usd",
        "cache_read_input_tokens", "cache_creation_input_tokens", "output_tokens", "input_tokens",
    ):
        if _has_column("ai_comment_generations", name):
            op.drop_column("ai_comment_generations", name)
    for name in ("ai_comment_memory", "last_dashboard_snapshot"):
        if _has_column("clients", name):
            op.drop_column("clients", name)
    for name in (
        "recurring_sync_required",
        "overflow_warning_period_end",
        "peak_active_projects",
        "overflow_notice_dismissed_at",
        "pending_price_book_snapshot",
        "price_book_snapshot",
        "pending_purchased_project_slots",
        "pending_billing_period",
    ):
        if _has_column("subscriptions", name):
            op.drop_column("subscriptions", name)
