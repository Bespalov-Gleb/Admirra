"""add team members tables

Revision ID: c3d4e5f6a7b8
Revises: b1c2d3e4f5a6
Create Date: 2026-04-27
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c3d4e5f6a7b8"
down_revision: Union[str, Sequence[str], None] = "b1c2d3e4f5a6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()

    team_member_role = sa.Enum("member", "client", name="teammemberrole")
    team_member_status = sa.Enum("pending", "active", name="teammemberstatus")
    team_member_role.create(bind, checkfirst=True)
    team_member_status.create(bind, checkfirst=True)

    op.create_table(
        "team_members",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("account_id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=True),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("role", team_member_role, nullable=False),
        sa.Column("status", team_member_status, nullable=False),
        sa.Column("invited_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["account_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("account_id", "email", name="uq_team_member_account_email"),
    )
    op.create_index(op.f("ix_team_members_account_id"), "team_members", ["account_id"], unique=False)
    op.create_index(op.f("ix_team_members_user_id"), "team_members", ["user_id"], unique=False)
    op.create_index(op.f("ix_team_members_email"), "team_members", ["email"], unique=False)

    op.create_table(
        "team_member_projects",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("team_member_id", sa.UUID(), nullable=False),
        sa.Column("project_id", sa.UUID(), nullable=False),
        sa.Column("granted_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("granted_by", sa.UUID(), nullable=True),
        sa.ForeignKeyConstraint(["team_member_id"], ["team_members.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["clients.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["granted_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("team_member_id", "project_id", name="uq_team_member_project"),
    )
    op.create_index(op.f("ix_team_member_projects_team_member_id"), "team_member_projects", ["team_member_id"], unique=False)
    op.create_index(op.f("ix_team_member_projects_project_id"), "team_member_projects", ["project_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_team_member_projects_project_id"), table_name="team_member_projects")
    op.drop_index(op.f("ix_team_member_projects_team_member_id"), table_name="team_member_projects")
    op.drop_table("team_member_projects")

    op.drop_index(op.f("ix_team_members_email"), table_name="team_members")
    op.drop_index(op.f("ix_team_members_user_id"), table_name="team_members")
    op.drop_index(op.f("ix_team_members_account_id"), table_name="team_members")
    op.drop_table("team_members")

    bind = op.get_bind()
    sa.Enum("pending", "active", name="teammemberstatus").drop(bind, checkfirst=True)
    sa.Enum("member", "client", name="teammemberrole").drop(bind, checkfirst=True)
