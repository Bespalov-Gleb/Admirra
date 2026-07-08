"""add report deliveries

Revision ID: l3m4n5o6p7q8
Revises: k2l3m4n5o6p7
Create Date: 2026-07-08 22:30:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "l3m4n5o6p7q8"
down_revision = "k2l3m4n5o6p7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "report_schedules",
        sa.Column("approval_required", sa.Boolean(), server_default="true", nullable=False),
    )
    op.add_column(
        "report_schedules",
        sa.Column("include_ai_comment", sa.Boolean(), server_default="true", nullable=False),
    )
    op.add_column("telegram_link_tokens", sa.Column("client_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("telegram_link_tokens", sa.Column("folder_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("max_report_link_tokens", sa.Column("client_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("max_report_link_tokens", sa.Column("folder_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_index("ix_telegram_link_tokens_client_id", "telegram_link_tokens", ["client_id"])
    op.create_index("ix_telegram_link_tokens_folder_id", "telegram_link_tokens", ["folder_id"])
    op.create_index("ix_max_report_link_tokens_client_id", "max_report_link_tokens", ["client_id"])
    op.create_index("ix_max_report_link_tokens_folder_id", "max_report_link_tokens", ["folder_id"])
    op.create_foreign_key("fk_telegram_link_tokens_client_id_clients", "telegram_link_tokens", "clients", ["client_id"], ["id"], ondelete="SET NULL")
    op.create_foreign_key("fk_telegram_link_tokens_folder_id_folders", "telegram_link_tokens", "folders", ["folder_id"], ["id"], ondelete="SET NULL")
    op.create_foreign_key("fk_max_report_link_tokens_client_id_clients", "max_report_link_tokens", "clients", ["client_id"], ["id"], ondelete="SET NULL")
    op.create_foreign_key("fk_max_report_link_tokens_folder_id_folders", "max_report_link_tokens", "folders", ["folder_id"], ["id"], ondelete="SET NULL")

    op.create_table(
        "report_deliveries",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("schedule_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("client_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("folder_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("status", sa.String(length=24), server_default="pending", nullable=False),
        sa.Column("source", sa.String(length=24), server_default="manual", nullable=False),
        sa.Column("platform", sa.String(), server_default="all", nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("channels", sa.String(), server_default="[]", nullable=False),
        sa.Column("chat_targets", sa.String(), nullable=True),
        sa.Column("report_format", sa.String(), server_default="desktop", nullable=False),
        sa.Column("include_dynamics", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("include_ai_comment", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("sections", sa.String(), nullable=True),
        sa.Column("chart_metrics", sa.String(), nullable=True),
        sa.Column("dynamics_metrics", sa.String(), nullable=True),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("anomaly_reason", sa.Text(), nullable=True),
        sa.Column("delivery_results", sa.JSON(), nullable=True),
        sa.Column("approved_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["approved_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["folder_id"], ["folders.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["schedule_id"], ["report_schedules.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_report_deliveries_client_id", "report_deliveries", ["client_id"])
    op.create_index("ix_report_deliveries_folder_id", "report_deliveries", ["folder_id"])
    op.create_index("ix_report_deliveries_schedule_id", "report_deliveries", ["schedule_id"])
    op.create_index("ix_report_deliveries_status", "report_deliveries", ["status"])
    op.create_index("ix_report_deliveries_user_id", "report_deliveries", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_report_deliveries_user_id", table_name="report_deliveries")
    op.drop_index("ix_report_deliveries_status", table_name="report_deliveries")
    op.drop_index("ix_report_deliveries_schedule_id", table_name="report_deliveries")
    op.drop_index("ix_report_deliveries_folder_id", table_name="report_deliveries")
    op.drop_index("ix_report_deliveries_client_id", table_name="report_deliveries")
    op.drop_table("report_deliveries")
    op.drop_constraint("fk_max_report_link_tokens_folder_id_folders", "max_report_link_tokens", type_="foreignkey")
    op.drop_constraint("fk_max_report_link_tokens_client_id_clients", "max_report_link_tokens", type_="foreignkey")
    op.drop_constraint("fk_telegram_link_tokens_folder_id_folders", "telegram_link_tokens", type_="foreignkey")
    op.drop_constraint("fk_telegram_link_tokens_client_id_clients", "telegram_link_tokens", type_="foreignkey")
    op.drop_index("ix_max_report_link_tokens_folder_id", table_name="max_report_link_tokens")
    op.drop_index("ix_max_report_link_tokens_client_id", table_name="max_report_link_tokens")
    op.drop_index("ix_telegram_link_tokens_folder_id", table_name="telegram_link_tokens")
    op.drop_index("ix_telegram_link_tokens_client_id", table_name="telegram_link_tokens")
    op.drop_column("max_report_link_tokens", "folder_id")
    op.drop_column("max_report_link_tokens", "client_id")
    op.drop_column("telegram_link_tokens", "folder_id")
    op.drop_column("telegram_link_tokens", "client_id")
    op.drop_column("report_schedules", "include_ai_comment")
    op.drop_column("report_schedules", "approval_required")
