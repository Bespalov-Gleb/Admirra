"""Add project settings fields and tables (budgets, target CPA)

Revision ID: g1a2b3c4d5e6
Revises: d0e1f2a3b4c5
Create Date: 2026-05-17

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


revision: str = "g1a2b3c4d5e6"
down_revision: Union[str, Sequence[str], None] = "d0e1f2a3b4c5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # New columns on clients
    op.add_column("clients", sa.Column("site_url", sa.String(), nullable=True))
    op.add_column("clients", sa.Column("status", sa.Enum("ACTIVE", "PAUSED", name="clientstatus"), nullable=False, server_default="ACTIVE"))
    op.add_column("clients", sa.Column("detector_enabled", sa.Boolean(), nullable=False, server_default="false"))
    op.add_column("clients", sa.Column("actual_start_date", sa.Date(), nullable=True))

    # project_budgets table
    op.create_table(
        "project_budgets",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("client_id", UUID(as_uuid=True), sa.ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("channel", sa.Enum("YANDEX_DIRECT", "VK_ADS", "YANDEX_METRIKA", "MYTARGET", name="integrationplatform", create_type=False), nullable=False),
        sa.Column("amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("period_start", sa.Date(), nullable=False),
        sa.Column("period_end", sa.Date(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # project_target_cpa table
    op.create_table(
        "project_target_cpa",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("client_id", UUID(as_uuid=True), sa.ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("channel", sa.Enum("YANDEX_DIRECT", "VK_ADS", "YANDEX_METRIKA", "MYTARGET", name="integrationplatform", create_type=False), nullable=True),
        sa.Column("goal_id", sa.String(), nullable=True),
        sa.Column("goal_name", sa.String(), nullable=True),
        sa.Column("is_summary", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("target_cpa", sa.Numeric(14, 2), nullable=True),
        sa.Column("control_enabled", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("period_start", sa.Date(), nullable=False),
        sa.Column("period_end", sa.Date(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("project_target_cpa")
    op.drop_table("project_budgets")
    op.drop_column("clients", "actual_start_date")
    op.drop_column("clients", "detector_enabled")
    op.drop_column("clients", "status")
    op.drop_column("clients", "site_url")
    sa.Enum("ACTIVE", "PAUSED", name="clientstatus").drop(op.get_bind(), checkfirst=True)
