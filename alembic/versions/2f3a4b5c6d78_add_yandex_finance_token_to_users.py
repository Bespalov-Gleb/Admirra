"""add_yandex_finance_token_to_users

Revision ID: 2f3a4b5c6d78
Revises: 113e8aa25ef0
Create Date: 2026-01-28 16:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "2f3a4b5c6d78"
down_revision: Union[str, Sequence[str], None] = "113e8aa25ef0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
  """Add yandex_finance_token column to users."""
  op.add_column("users", sa.Column("yandex_finance_token", sa.String(), nullable=True))


def downgrade() -> None:
  """Remove yandex_finance_token column from users."""
  op.drop_column("users", "yandex_finance_token")


