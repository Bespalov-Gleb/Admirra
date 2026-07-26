"""Keep the Avito Metrika OAuth grant on the Avito integration itself.

Revision ID: u2v3w4x5y6z
Revises: t1u2v3w4x5y6
Create Date: 2026-07-21
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "u2v3w4x5y6z"
down_revision: Union[str, Sequence[str], None] = "t1u2v3w4x5y6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


COLUMNS = ("metrika_access_token", "metrika_refresh_token", "metrika_account_id")


def _existing_columns() -> set:
    inspector = sa.inspect(op.get_bind())
    return {col["name"] for col in inspector.get_columns("integrations")}


def upgrade() -> None:
    # Идемпотентно: те же колонки параллельно создаёт init_db_with_retry() в
    # backend_api/main.py, поэтому на проде они уже есть, и обычный add_column
    # падал бы с DuplicateColumn. В проекте схема ведётся двумя механизмами
    # сразу, значит миграции обязаны переживать «колонка уже создана».
    present = _existing_columns()
    for name in COLUMNS:
        if name not in present:
            op.add_column("integrations", sa.Column(name, sa.String(), nullable=True))


def downgrade() -> None:
    present = _existing_columns()
    for name in reversed(COLUMNS):
        if name in present:
            op.drop_column("integrations", name)
