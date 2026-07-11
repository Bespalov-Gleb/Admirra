"""Reports: immutable snapshots, scoped recipients and one schedule per scope.

Revision ID: n5o6p7q8r9s0
Revises: m4n5o6p7q8r9
Create Date: 2026-07-11
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "n5o6p7q8r9s0"
down_revision: Union[str, Sequence[str], None] = "m4n5o6p7q8r9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("telegram_link_tokens", sa.Column("target_type", sa.String(length=24), nullable=True))
    op.add_column("max_report_link_tokens", sa.Column("target_type", sa.String(length=24), nullable=True))

    op.add_column("report_schedules", sa.Column("email_recipients", sa.String(), server_default="[]", nullable=False))
    # Old account-wide rules are intentionally retired, not migrated.
    op.execute("DELETE FROM report_schedules WHERE scope_client_id IS NULL AND scope_folder_id IS NULL")
    # Never reuse account-wide email addresses as recipients of a particular project.
    op.execute("UPDATE report_schedules SET enabled = false WHERE COALESCE(channels, '[]')::jsonb ? 'email'")

    op.add_column("report_chat_targets", sa.Column("client_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("report_chat_targets", sa.Column("folder_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("report_chat_targets", sa.Column("target_type", sa.String(length=24), server_default="group", nullable=False))
    op.create_foreign_key("fk_report_chat_targets_client", "report_chat_targets", "clients", ["client_id"], ["id"], ondelete="CASCADE")
    op.create_foreign_key("fk_report_chat_targets_folder", "report_chat_targets", "folders", ["folder_id"], ["id"], ondelete="CASCADE")
    op.create_index("ix_report_chat_targets_client_id", "report_chat_targets", ["client_id"])
    op.create_index("ix_report_chat_targets_folder_id", "report_chat_targets", ["folder_id"])

    # Existing target ids already live in project schedules. Backfill their scope
    # before enforcing project isolation. A target used by several scopes is cloned
    # by future relinking; existing ambiguous test data stays attached to the newest scope.
    op.execute(
        """
        WITH mapping AS (
            SELECT DISTINCT ON (t.id)
                t.id AS target_id, rs.scope_client_id, rs.scope_folder_id
            FROM report_chat_targets t
            JOIN report_schedules rs
              ON COALESCE(rs.chat_targets, '[]')::jsonb ? t.id::text
            ORDER BY t.id, rs.created_at DESC
        )
        UPDATE report_chat_targets t
        SET client_id = mapping.scope_client_id,
            folder_id = mapping.scope_folder_id
        FROM mapping
        WHERE t.id = mapping.target_id
        """
    )

    op.add_column("report_deliveries", sa.Column("email_recipients", sa.String(), server_default="[]", nullable=False))
    op.add_column("report_deliveries", sa.Column("snapshot_data", sa.JSON(), nullable=True))
    op.add_column("report_deliveries", sa.Column("pdf_snapshot", sa.LargeBinary(), nullable=True))
    op.add_column("report_deliveries", sa.Column("png_snapshot", sa.LargeBinary(), nullable=True))
    op.add_column("report_deliveries", sa.Column("public_token", sa.String(length=64), nullable=True))
    op.add_column("report_deliveries", sa.Column("public_expires_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("report_deliveries", sa.Column("snapshot_created_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_report_deliveries_public_token", "report_deliveries", ["public_token"], unique=True)
    # Remove accidental duplicate scheduled rows before adding idempotency.
    op.execute(
        """
        WITH ranked AS (
            SELECT id,
                   ROW_NUMBER() OVER (
                       PARTITION BY schedule_id, start_date, end_date
                       ORDER BY created_at DESC, id DESC
                   ) AS rn
            FROM report_deliveries
            WHERE schedule_id IS NOT NULL
        )
        DELETE FROM report_deliveries d
        USING ranked
        WHERE d.id = ranked.id AND ranked.rn > 1
        """
    )
    op.create_index(
        "uq_report_deliveries_schedule_period",
        "report_deliveries",
        ["schedule_id", "start_date", "end_date"],
        unique=True,
        postgresql_where=sa.text("schedule_id IS NOT NULL"),
    )

    # Final TZ: one auto-send configuration for each exact scope. Keep the newest
    # row and remove obsolete test/legacy duplicates.
    op.execute(
        """
        WITH ranked AS (
            SELECT id,
                   ROW_NUMBER() OVER (
                       PARTITION BY user_id, scope_client_id, scope_folder_id
                       ORDER BY created_at DESC, id DESC
                   ) AS rn
            FROM report_schedules
        )
        DELETE FROM report_schedules rs
        USING ranked
        WHERE rs.id = ranked.id AND ranked.rn > 1
        """
    )
    op.create_index(
        "uq_report_schedules_project_scope",
        "report_schedules",
        ["user_id", "scope_client_id"],
        unique=True,
        postgresql_where=sa.text("scope_client_id IS NOT NULL AND scope_folder_id IS NULL"),
    )
    op.create_index(
        "uq_report_schedules_folder_scope",
        "report_schedules",
        ["user_id", "scope_folder_id"],
        unique=True,
        postgresql_where=sa.text("scope_folder_id IS NOT NULL AND scope_client_id IS NULL"),
    )
    op.create_index("ix_report_schedules_due_lookup", "report_schedules", ["enabled", "send_time", "day"])


def downgrade() -> None:
    op.drop_index("ix_report_schedules_due_lookup", table_name="report_schedules")
    op.drop_index("uq_report_schedules_folder_scope", table_name="report_schedules")
    op.drop_index("uq_report_schedules_project_scope", table_name="report_schedules")
    op.drop_index("uq_report_deliveries_schedule_period", table_name="report_deliveries")
    op.drop_index("ix_report_deliveries_public_token", table_name="report_deliveries")
    for name in ("snapshot_created_at", "public_expires_at", "public_token", "png_snapshot", "pdf_snapshot", "snapshot_data", "email_recipients"):
        op.drop_column("report_deliveries", name)
    op.drop_index("ix_report_chat_targets_folder_id", table_name="report_chat_targets")
    op.drop_index("ix_report_chat_targets_client_id", table_name="report_chat_targets")
    op.drop_constraint("fk_report_chat_targets_folder", "report_chat_targets", type_="foreignkey")
    op.drop_constraint("fk_report_chat_targets_client", "report_chat_targets", type_="foreignkey")
    op.drop_column("report_chat_targets", "target_type")
    op.drop_column("report_chat_targets", "folder_id")
    op.drop_column("report_chat_targets", "client_id")
    op.drop_column("report_schedules", "email_recipients")
    op.drop_column("max_report_link_tokens", "target_type")
    op.drop_column("telegram_link_tokens", "target_type")
