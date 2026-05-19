"""Add detector_alerts table

Revision ID: h2a3b4c5d6e7
Revises: g1a2b3c4d5e6
Create Date: 2026-05-19

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSON


revision: str = "h2a3b4c5d6e7"
down_revision: Union[str, Sequence[str], None] = "g1a2b3c4d5e6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "detector_alerts",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("client_id", UUID(as_uuid=True), sa.ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("owner_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("metric", sa.String(32), nullable=False),
        sa.Column("detection_level", sa.String(32), nullable=False, server_default="project"),
        sa.Column("entity_id", sa.String(128), nullable=True),
        sa.Column("channel", sa.Enum("YANDEX_DIRECT", "VK_ADS", "YANDEX_METRIKA", "MYTARGET", name="integrationplatform", create_type=False), nullable=True),
        sa.Column("mode", sa.String(16), nullable=False, server_default="baseline"),
        sa.Column("severity", sa.String(16), nullable=False, server_default="warning"),
        sa.Column("deviation_pct", sa.Numeric(8, 2), nullable=True),
        sa.Column("baseline_value", sa.Numeric(20, 2), nullable=True),
        sa.Column("actual_value", sa.Numeric(20, 2), nullable=True),
        sa.Column("consecutive_days", sa.Integer, nullable=False, server_default="1"),
        sa.Column("pattern_key", sa.String(64), nullable=True),
        sa.Column("hypothesis_text", sa.String(500), nullable=True),
        sa.Column("status", sa.String(16), nullable=False, server_default="open", index=True),
        sa.Column("opened_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("dismissed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_checked_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("meta", JSON, nullable=True),
        sa.UniqueConstraint(
            "client_id", "metric", "detection_level", "entity_id", "channel", "mode",
            name="uq_detector_alert_open",
        ),
    )
    op.create_index("ix_detector_alerts_client_status", "detector_alerts", ["client_id", "status"])
    op.create_index("ix_detector_alerts_owner_status", "detector_alerts", ["owner_id", "status"])


def downgrade() -> None:
    op.drop_index("ix_detector_alerts_owner_status", table_name="detector_alerts")
    op.drop_index("ix_detector_alerts_client_status", table_name="detector_alerts")
    op.drop_table("detector_alerts")
