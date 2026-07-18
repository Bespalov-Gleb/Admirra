"""Reports July delta: addressable recipients and durable preview state.

Revision ID: t1u2v3w4x5y6
Revises: s0t1u2v3w4x5
Create Date: 2026-07-18
"""
from __future__ import annotations

import uuid
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "t1u2v3w4x5y6"
down_revision: Union[str, Sequence[str], None] = "s0t1u2v3w4x5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "report_deliveries",
        sa.Column("comment_status", sa.String(length=16), server_default="none", nullable=False),
    )
    op.execute(
        "UPDATE report_deliveries SET comment_status = 'draft' "
        "WHERE COALESCE(comment, '') <> ''"
    )

    for name, column in (
        ("status", sa.Column("status", sa.String(length=24), server_default="active", nullable=False)),
        ("last_error", sa.Column("last_error", sa.Text(), nullable=True)),
        ("last_delivery_at", sa.Column("last_delivery_at", sa.DateTime(timezone=True), nullable=True)),
    ):
        op.add_column("report_chat_targets", column)

    op.create_table(
        "report_email_recipients",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("client_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("folder_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=True),
        sa.Column("status", sa.String(length=24), server_default="active", nullable=False),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("last_delivery_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["folder_id"], ["folders.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("user_id", "client_id", "folder_id", "email", name="uq_report_email_recipient_scope"),
    )
    op.create_index("ix_report_email_recipients_user_id", "report_email_recipients", ["user_id"])
    op.create_index("ix_report_email_recipients_client_id", "report_email_recipients", ["client_id"])
    op.create_index("ix_report_email_recipients_folder_id", "report_email_recipients", ["folder_id"])

    # Preserve existing project email selections.  One schedule per scope is
    # already guaranteed by the preceding migration, so this backfill has an
    # unambiguous owner and scope.
    bind = op.get_bind()
    rows = bind.execute(
        sa.text(
            """
            SELECT user_id, scope_client_id, scope_folder_id,
                   jsonb_array_elements_text(COALESCE(email_recipients, '[]')::jsonb) AS email
            FROM report_schedules
            WHERE scope_client_id IS NOT NULL OR scope_folder_id IS NOT NULL
            """
        )
    ).mappings().all()
    seen: set[tuple] = set()
    for row in rows:
        email = str(row["email"] or "").strip().lower()
        if not email:
            continue
        key = (row["user_id"], row["scope_client_id"], row["scope_folder_id"], email)
        if key in seen:
            continue
        seen.add(key)
        bind.execute(
            sa.text(
                """
                INSERT INTO report_email_recipients
                    (id, user_id, client_id, folder_id, email, status)
                VALUES (:id, :user_id, :client_id, :folder_id, :email, 'active')
                """
            ),
            {
                "id": uuid.uuid4(),
                "user_id": row["user_id"],
                "client_id": row["scope_client_id"],
                "folder_id": row["scope_folder_id"],
                "email": email,
            },
        )


def downgrade() -> None:
    op.drop_index("ix_report_email_recipients_folder_id", table_name="report_email_recipients")
    op.drop_index("ix_report_email_recipients_client_id", table_name="report_email_recipients")
    op.drop_index("ix_report_email_recipients_user_id", table_name="report_email_recipients")
    op.drop_table("report_email_recipients")
    op.drop_column("report_chat_targets", "last_delivery_at")
    op.drop_column("report_chat_targets", "last_error")
    op.drop_column("report_chat_targets", "status")
    op.drop_column("report_deliveries", "comment_status")
