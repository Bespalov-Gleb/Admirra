"""VK Ads personal-client authorization links and selected lead actions.

Revision ID: o6p7q8r9s0t
Revises: n5o6p7q8r9s0
Create Date: 2026-07-11
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "o6p7q8r9s0t"
down_revision: Union[str, Sequence[str], None] = "n5o6p7q8r9s0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # A draft is deliberately created before the client authorizes VK Ads.
    op.alter_column("integrations", "access_token", existing_type=sa.String(), nullable=True)
    op.add_column("integrations", sa.Column("lead_action_types", sa.String(), nullable=True))
    op.add_column("integrations", sa.Column("vk_known_lead_action_types", sa.String(), nullable=True))
    op.add_column(
        "integrations",
        sa.Column("vk_new_lead_actions_pending", sa.Boolean(), server_default=sa.false(), nullable=False),
    )
    op.add_column(
        "integrations",
        sa.Column("connection_status", sa.String(length=24), server_default="active", nullable=False),
    )
    op.add_column("integrations", sa.Column("link_token", sa.String(), nullable=True))
    op.add_column("integrations", sa.Column("link_token_hash", sa.String(length=64), nullable=True))
    op.add_column("integrations", sa.Column("link_expires_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("integrations", sa.Column("link_created_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("integrations", sa.Column("link_authorized_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_integrations_connection_status", "integrations", ["connection_status"])
    op.create_index("ix_integrations_link_token_hash", "integrations", ["link_token_hash"])


def downgrade() -> None:
    op.drop_index("ix_integrations_link_token_hash", table_name="integrations")
    op.drop_index("ix_integrations_connection_status", table_name="integrations")
    for column in (
        "link_authorized_at",
        "link_created_at",
        "link_expires_at",
        "link_token_hash",
        "link_token",
        "connection_status",
        "lead_action_types",
        "vk_new_lead_actions_pending",
        "vk_known_lead_action_types",
    ):
        op.drop_column("integrations", column)
    # Pending links cannot be represented by the old non-nullable schema.
    op.execute("DELETE FROM integrations WHERE access_token IS NULL")
    op.alter_column("integrations", "access_token", existing_type=sa.String(), nullable=False)
