"""Track which Yandex OAuth application issued an integration token.

Revision ID: r9s0t1u2v3w4
Revises: q8r9s0t1u2v3
Create Date: 2026-07-14
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "r9s0t1u2v3w4"
down_revision: Union[str, Sequence[str], None] = "q8r9s0t1u2v3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # NULL — основное приложение, 'org' — «AdMirra — для организаций».
    op.add_column("integrations", sa.Column("oauth_app", sa.String(length=16), nullable=True))


def downgrade() -> None:
    op.drop_column("integrations", "oauth_app")
