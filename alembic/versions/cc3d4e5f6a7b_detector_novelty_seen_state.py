"""Detector iteration 4: per-user seen state and project visits.

Revision ID: cc3d4e5f6a7b
Revises: bb2c3d4e5f6a
Create Date: 2026-08-04
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


revision: str = "cc3d4e5f6a7b"
down_revision: Union[str, Sequence[str], None] = "bb2c3d4e5f6a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Идемпотентно (раннбук прода): те же таблицы/индексы параллельно создаёт
    # init_db_with_retry и Base.metadata.create_all(), поэтому обычный
    # op.create_table упал бы с DuplicateTable при ином порядке запуска.
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing = set(inspector.get_table_names())

    if "detector_alert_views" not in existing:
        op.create_table(
            "detector_alert_views",
            sa.Column("id", UUID(as_uuid=True), primary_key=True),
            sa.Column("alert_id", UUID(as_uuid=True), sa.ForeignKey("detector_alerts.id", ondelete="CASCADE"), nullable=False),
            sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
            sa.Column("seen_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("seen_severity", sa.String(length=16), nullable=True),
            sa.Column("seen_deviation_pct", sa.Numeric(8, 2), nullable=True),
            sa.Column("seen_actual_value", sa.Numeric(20, 2), nullable=True),
            sa.Column("seen_baseline_value", sa.Numeric(20, 2), nullable=True),
            sa.Column("acknowledged", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.UniqueConstraint("alert_id", "user_id", name="uq_detector_alert_view"),
        )
        op.create_index("ix_detector_alert_views_alert_id", "detector_alert_views", ["alert_id"])
        op.create_index("ix_detector_alert_views_user_id", "detector_alert_views", ["user_id"])

    if "detector_project_visits" not in existing:
        op.create_table(
            "detector_project_visits",
            sa.Column("id", UUID(as_uuid=True), primary_key=True),
            sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
            sa.Column("client_id", UUID(as_uuid=True), sa.ForeignKey("clients.id", ondelete="CASCADE"), nullable=False),
            sa.Column("last_viewed_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("previous_viewed_at", sa.DateTime(timezone=True), nullable=True),
            sa.UniqueConstraint("user_id", "client_id", name="uq_detector_project_visit"),
        )
        op.create_index("ix_detector_project_visits_user_id", "detector_project_visits", ["user_id"])
        op.create_index("ix_detector_project_visits_client_id", "detector_project_visits", ["client_id"])


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing = set(inspector.get_table_names())
    if "detector_project_visits" in existing:
        op.drop_table("detector_project_visits")
    if "detector_alert_views" in existing:
        op.drop_table("detector_alert_views")
