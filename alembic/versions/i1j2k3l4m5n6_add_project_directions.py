"""Add project directions

Revision ID: i1j2k3l4m5n6
Revises: h2a3b4c5d6e7
Create Date: 2026-06-01

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


revision: str = "i1j2k3l4m5n6"
down_revision: Union[str, Sequence[str], None] = "h2a3b4c5d6e7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "clients",
        sa.Column("direction_label", sa.String(length=32), nullable=False, server_default="directions"),
    )
    op.create_table(
        "project_directions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("client_id", UUID(as_uuid=True), sa.ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_table(
        "project_direction_masks",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("direction_id", UUID(as_uuid=True), sa.ForeignKey("project_directions.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("mask", sa.String(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
    )
    op.create_index("ix_project_directions_client_position", "project_directions", ["client_id", "position"])


def downgrade() -> None:
    op.drop_index("ix_project_directions_client_position", table_name="project_directions")
    op.drop_table("project_direction_masks")
    op.drop_table("project_directions")
    op.drop_column("clients", "direction_label")
