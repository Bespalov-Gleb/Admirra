"""Журнал денежных событий и отложенное понижение тарифа.

billing_events — неизменяемая история платежей. До неё денежная история
сводилась к перезаписываемым полям в subscriptions, поэтому нельзя было ни
разобрать спор с клиентом, ни отличить повторную доставку вебхука от нового
платежа. Уникальный transaction_id и есть механизм идемпотентности.

subscriptions.pending_plan_code — тариф, вступающий в силу после конца
оплаченного периода: понижение больше не отбирает уже оплаченный уровень.

Как и остальные объекты схемы в этом проекте, всё продублировано в
init_db_with_retry() и в core/models.py — иначе на пересозданной через
create_all() базе объекта не окажется.

Revision ID: w4x5y6z7a8b9
Revises: v3w4x5y6z7a8
Create Date: 2026-07-26
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "w4x5y6z7a8b9"
down_revision: Union[str, Sequence[str], None] = "v3w4x5y6z7a8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_column(table: str, column: str) -> bool:
    inspector = sa.inspect(op.get_bind())
    return column in {col["name"] for col in inspector.get_columns(table)}


def _has_table(table: str) -> bool:
    return sa.inspect(op.get_bind()).has_table(table)


def upgrade() -> None:
    if not _has_table("billing_events"):
        op.create_table(
            "billing_events",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                      server_default=sa.text("gen_random_uuid()")),
            sa.Column("user_id", postgresql.UUID(as_uuid=True),
                      sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
            sa.Column("subscription_id", postgresql.UUID(as_uuid=True),
                      sa.ForeignKey("subscriptions.id", ondelete="SET NULL"), nullable=True),
            sa.Column("event_type", sa.String(16), nullable=False),
            sa.Column("invoice_id", sa.String(64), nullable=True),
            sa.Column("transaction_id", sa.String(64), nullable=True),
            sa.Column("cp_subscription_id", sa.String(64), nullable=True),
            sa.Column("amount", sa.Numeric(14, 2), nullable=True),
            sa.Column("currency", sa.String(8), nullable=True),
            sa.Column("plan_code", sa.String(32), nullable=True),
            sa.Column("billing_period", sa.String(8), nullable=True),
            sa.Column("payload", sa.JSON(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True),
                      server_default=sa.text("now()"), nullable=False),
        )

    op.execute("CREATE INDEX IF NOT EXISTS ix_billing_events_user_id ON billing_events (user_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_billing_events_subscription_id ON billing_events (subscription_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_billing_events_event_type ON billing_events (event_type)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_billing_events_invoice_id ON billing_events (invoice_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_billing_events_cp_subscription_id ON billing_events (cp_subscription_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_billing_events_created_at ON billing_events (created_at)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_billing_events_user_created ON billing_events (user_id, created_at)")
    # Ключ идемпотентности. Частичный — у recurrent-уведомлений TransactionId нет.
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_billing_events_transaction "
        "ON billing_events (transaction_id) WHERE transaction_id IS NOT NULL"
    )

    if not _has_column("subscriptions", "pending_plan_code"):
        op.add_column("subscriptions", sa.Column("pending_plan_code", sa.String(), nullable=True))


def downgrade() -> None:
    if _has_column("subscriptions", "pending_plan_code"):
        op.drop_column("subscriptions", "pending_plan_code")
    if _has_table("billing_events"):
        op.drop_table("billing_events")
