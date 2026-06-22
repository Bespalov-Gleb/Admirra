"""Make users.username a non-unique display-name index.

Revision ID: k2l3m4n5o6p7
Revises: j1k2l3m4n5o6
Create Date: 2026-06-22
"""
from typing import Sequence, Union

from alembic import op


revision: str = "k2l3m4n5o6p7"
down_revision: Union[str, Sequence[str], None] = "j1k2l3m4n5o6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_users_username")
    op.execute("CREATE INDEX IF NOT EXISTS ix_users_username ON users (username)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_users_username")
    op.create_index(op.f("ix_users_username"), "users", ["username"], unique=True)
