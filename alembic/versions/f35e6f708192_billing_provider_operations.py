"""Ordered, durable CloudPayments commands; existing billing rows unchanged."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "f35e6f708192"
down_revision = "f24d5e6f7081"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("billing_provider_operations",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("ordinal", sa.BigInteger(), sa.Identity(), nullable=False, unique=True),
        sa.Column("user_id", UUID(as_uuid=True), nullable=False),
        sa.Column("subscription_id", UUID(as_uuid=True), nullable=False),
        sa.Column("command", sa.String(16), nullable=False),
        sa.Column("provider_id", sa.String(128)),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("job_id", UUID(as_uuid=True), nullable=False),
        sa.Column("evidence", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("command IN ('update', 'cancel_one', 'cancel_all')", name="ck_billing_provider_command"),
        sa.CheckConstraint("status IN ('queued', 'dispatching', 'confirmed', 'rejected', 'uncertain', 'superseded')", name="ck_billing_provider_status"))
    op.create_index("ix_billing_provider_owner_order", "billing_provider_operations", ["user_id", "ordinal"])
    op.create_index("ix_billing_provider_status", "billing_provider_operations", ["status", "updated_at"])


def downgrade():
    # Financial evidence survives application rollback; never replay via legacy.
    pass
