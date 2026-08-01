"""price_book_version в подписке + переименование кодов тарифов на новую линейку.

§7.2 экономики: price_book_version фиксирует за аккаунтом версию прайса на момент
подписки — при выпуске новой линейки аккаунт платит по своей, пока сам не сменит
тариф. §7.3: коды basic/standard приводятся к новым agency/pro. Резолвер понимает
старые коды через алиасы, но в БД держать оба навсегда незачем.

Как и прочие объекты схемы, продублировано в init_db_with_retry() и core/models.py —
иначе на пересозданной через create_all() базе поля не окажется.

Revision ID: x5y6z7a8b9c0
Revises: w4x5y6z7a8b9
Create Date: 2026-08-01
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "x5y6z7a8b9c0"
down_revision: Union[str, Sequence[str], None] = "w4x5y6z7a8b9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_column(table: str, column: str) -> bool:
    inspector = sa.inspect(op.get_bind())
    return column in {col["name"] for col in inspector.get_columns(table)}


def upgrade() -> None:
    # Колонку параллельно создаёт init_db_with_retry, поэтому add_column оборачиваем
    # проверкой, иначе повторный прогон падает с DuplicateColumn.
    if not _has_column("subscriptions", "price_book_version"):
        op.add_column(
            "subscriptions",
            sa.Column("price_book_version", sa.Integer(), nullable=True),
        )
    bind = op.get_bind()
    bind.execute(sa.text("UPDATE subscriptions SET plan_code='agency' WHERE plan_code='basic'"))
    bind.execute(sa.text("UPDATE subscriptions SET plan_code='pro' WHERE plan_code='standard'"))
    bind.execute(sa.text("UPDATE subscriptions SET pending_plan_code='agency' WHERE pending_plan_code='basic'"))
    bind.execute(sa.text("UPDATE subscriptions SET pending_plan_code='pro' WHERE pending_plan_code='standard'"))


def downgrade() -> None:
    bind = op.get_bind()
    bind.execute(sa.text("UPDATE subscriptions SET plan_code='basic' WHERE plan_code='agency'"))
    bind.execute(sa.text("UPDATE subscriptions SET plan_code='standard' WHERE plan_code='pro'"))
    bind.execute(sa.text("UPDATE subscriptions SET pending_plan_code='basic' WHERE pending_plan_code='agency'"))
    bind.execute(sa.text("UPDATE subscriptions SET pending_plan_code='standard' WHERE pending_plan_code='pro'"))
    if _has_column("subscriptions", "price_book_version"):
        op.drop_column("subscriptions", "price_book_version")
