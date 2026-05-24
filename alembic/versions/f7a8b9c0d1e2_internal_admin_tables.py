"""internal admin tables and user fields

Revision ID: f7a8b9c0d1e2
Revises: e6f7a8b9c0d1
Create Date: 2026-05-24
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "f7a8b9c0d1e2"
down_revision: Union[str, Sequence[str], None] = "e6f7a8b9c0d1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

seo_status = postgresql.ENUM(
    "draft", "review", "published", "archived",
    name="seoblogpoststatus",
    create_type=False,
)


def upgrade() -> None:
    op.execute("ALTER TYPE userrole ADD VALUE IF NOT EXISTS 'SUPERADMIN'")
    op.execute("ALTER TYPE userrole ADD VALUE IF NOT EXISTS 'SUPPORT'")
    op.execute("ALTER TYPE userrole ADD VALUE IF NOT EXISTS 'SEO'")
    op.execute("ALTER TYPE userrole ADD VALUE IF NOT EXISTS 'DEVELOPER'")

    op.add_column("users", sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("users", sa.Column("registration_utm_source", sa.String(), nullable=True))
    op.add_column("users", sa.Column("registration_utm_medium", sa.String(), nullable=True))
    op.add_column("users", sa.Column("registration_utm_campaign", sa.String(), nullable=True))

    seo_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "ia_support_user_assignments",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("staff_user_id", sa.UUID(), nullable=False),
        sa.Column("client_user_id", sa.UUID(), nullable=False),
        sa.Column("assigned_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("assigned_by", sa.UUID(), nullable=True),
        sa.ForeignKeyConstraint(["assigned_by"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["client_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["staff_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("staff_user_id", "client_user_id", name="uq_ia_support_assignment"),
    )
    op.create_index("ix_ia_support_user_assignments_staff_user_id", "ia_support_user_assignments", ["staff_user_id"])
    op.create_index("ix_ia_support_user_assignments_client_user_id", "ia_support_user_assignments", ["client_user_id"])

    op.create_table(
        "ia_support_notes",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("client_user_id", sa.UUID(), nullable=False),
        sa.Column("author_user_id", sa.UUID(), nullable=True),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["author_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["client_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ia_support_notes_client_user_id", "ia_support_notes", ["client_user_id"])

    op.create_table(
        "ia_admin_audit_logs",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("staff_user_id", sa.UUID(), nullable=True),
        sa.Column("staff_email", sa.String(), nullable=True),
        sa.Column("action", sa.String(), nullable=False),
        sa.Column("target_type", sa.String(), nullable=True),
        sa.Column("target_id", sa.String(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("meta", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("ip_address", sa.String(), nullable=True),
        sa.Column("user_agent", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["staff_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ia_admin_audit_logs_staff_user_id", "ia_admin_audit_logs", ["staff_user_id"])
    op.create_index("ix_ia_admin_audit_logs_action", "ia_admin_audit_logs", ["action"])
    op.create_index("ix_ia_admin_audit_logs_created_at", "ia_admin_audit_logs", ["created_at"])

    op.create_table(
        "ia_admin_staff_sessions",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("staff_user_id", sa.UUID(), nullable=False),
        sa.Column("session_token_hash", sa.String(), nullable=False),
        sa.Column("ip_address", sa.String(), nullable=True),
        sa.Column("user_agent", sa.String(), nullable=True),
        sa.Column("city", sa.String(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["staff_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("session_token_hash"),
    )
    op.create_index("ix_ia_admin_staff_sessions_staff_user_id", "ia_admin_staff_sessions", ["staff_user_id"])
    op.create_index("ix_ia_admin_staff_sessions_session_token_hash", "ia_admin_staff_sessions", ["session_token_hash"])

    op.create_table(
        "ia_admin_settings",
        sa.Column("key", sa.String(), nullable=False),
        sa.Column("value", postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_by", sa.UUID(), nullable=True),
        sa.ForeignKeyConstraint(["updated_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("key"),
    )

    op.create_table(
        "ia_ai_usage_logs",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=True),
        sa.Column("action", sa.String(), nullable=False, server_default="ai_request"),
        sa.Column("tokens_input", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("tokens_output", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("tokens_total", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("cost_usd", sa.String(), nullable=True),
        sa.Column("meta", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ia_ai_usage_logs_user_id", "ia_ai_usage_logs", ["user_id"])
    op.create_index("ix_ia_ai_usage_logs_created_at", "ia_ai_usage_logs", ["created_at"])

    op.create_table(
        "ia_seo_blog_posts",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("slug", sa.String(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("content_html", sa.Text(), nullable=False, server_default=""),
        sa.Column("category", sa.String(), nullable=True),
        sa.Column("status", seo_status, nullable=False, server_default="draft"),
        sa.Column("meta_title", sa.String(), nullable=True),
        sa.Column("meta_description", sa.Text(), nullable=True),
        sa.Column("keywords", sa.String(), nullable=True),
        sa.Column("cover_url", sa.String(), nullable=True),
        sa.Column("traffic_monthly", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("author_user_id", sa.UUID(), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["author_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
    )
    op.create_index("ix_ia_seo_blog_posts_slug", "ia_seo_blog_posts", ["slug"])

    op.create_table(
        "ia_seo_site_pages",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("path", sa.String(), nullable=False),
        sa.Column("title", sa.String(), nullable=True),
        sa.Column("meta_title", sa.String(), nullable=True),
        sa.Column("meta_description", sa.Text(), nullable=True),
        sa.Column("traffic_monthly", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_by", sa.UUID(), nullable=True),
        sa.ForeignKeyConstraint(["updated_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("path"),
    )
    op.create_index("ix_ia_seo_site_pages_path", "ia_seo_site_pages", ["path"])


def downgrade() -> None:
    op.drop_table("ia_seo_site_pages")
    op.drop_table("ia_seo_blog_posts")
    op.drop_table("ia_ai_usage_logs")
    op.drop_table("ia_admin_settings")
    op.drop_table("ia_admin_staff_sessions")
    op.drop_table("ia_admin_audit_logs")
    op.drop_table("ia_support_notes")
    op.drop_table("ia_support_user_assignments")
    op.drop_column("users", "registration_utm_campaign")
    op.drop_column("users", "registration_utm_medium")
    op.drop_column("users", "registration_utm_source")
    op.drop_column("users", "last_login_at")
    op.execute("DROP TYPE IF EXISTS seoblogpoststatus")
