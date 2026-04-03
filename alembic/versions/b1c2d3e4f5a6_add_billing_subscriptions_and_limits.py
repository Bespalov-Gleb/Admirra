"""add billing subscriptions and limits

Revision ID: b1c2d3e4f5a6
Revises: a7b8c9d0e1f2
Create Date: 2026-04-01
"""

from alembic import op
import sqlalchemy as sa
from typing import Sequence, Union


revision: str = "b1c2d3e4f5a6"
down_revision: Union[str, Sequence[str], None] = "a7b8c9d0e1f2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("is_subscribed", sa.Boolean(), nullable=False, server_default=sa.text("false")))
    op.add_column("users", sa.Column("subscription_expires_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("users", sa.Column("ai_requests_used", sa.Integer(), nullable=False, server_default=sa.text("0")))
    op.add_column("users", sa.Column("ai_requests_period_started_at", sa.DateTime(timezone=True), nullable=True))

    op.create_table(
        "tariff_plans",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("code", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("price_rub", sa.Integer(), nullable=False),
        sa.Column("max_projects", sa.Integer(), nullable=False),
        sa.Column("max_ai_requests_per_period", sa.Integer(), nullable=False),
        sa.Column("period_days", sa.Integer(), nullable=False),
        sa.Column("trial_days", sa.Integer(), nullable=False),
        sa.Column("is_default", sa.Boolean(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_tariff_plans_code"), "tariff_plans", ["code"], unique=True)

    subscription_status = sa.Enum("TRIAL", "ACTIVE", "PAST_DUE", "CANCELED", "EXPIRED", name="subscriptionstatus")
    subscription_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "subscriptions",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("plan_id", sa.UUID(), nullable=True),
        sa.Column("plan_code", sa.String(), nullable=False),
        sa.Column("status", subscription_status, nullable=False),
        sa.Column("cloudpayments_subscription_id", sa.String(), nullable=True),
        sa.Column("cloudpayments_transaction_id", sa.String(), nullable=True),
        sa.Column("current_period_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("current_period_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancel_at_period_end", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["plan_id"], ["tariff_plans.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_subscriptions_user_id"), "subscriptions", ["user_id"], unique=False)
    op.create_index(op.f("ix_subscriptions_plan_id"), "subscriptions", ["plan_id"], unique=False)
    op.create_index(op.f("ix_subscriptions_plan_code"), "subscriptions", ["plan_code"], unique=False)
    op.create_index(op.f("ix_subscriptions_status"), "subscriptions", ["status"], unique=False)
    op.create_index(op.f("ix_subscriptions_cloudpayments_subscription_id"), "subscriptions", ["cloudpayments_subscription_id"], unique=False)
    op.create_index(op.f("ix_subscriptions_cloudpayments_transaction_id"), "subscriptions", ["cloudpayments_transaction_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_subscriptions_cloudpayments_transaction_id"), table_name="subscriptions")
    op.drop_index(op.f("ix_subscriptions_cloudpayments_subscription_id"), table_name="subscriptions")
    op.drop_index(op.f("ix_subscriptions_status"), table_name="subscriptions")
    op.drop_index(op.f("ix_subscriptions_plan_code"), table_name="subscriptions")
    op.drop_index(op.f("ix_subscriptions_plan_id"), table_name="subscriptions")
    op.drop_index(op.f("ix_subscriptions_user_id"), table_name="subscriptions")
    op.drop_table("subscriptions")

    op.drop_index(op.f("ix_tariff_plans_code"), table_name="tariff_plans")
    op.drop_table("tariff_plans")

    op.drop_column("users", "ai_requests_period_started_at")
    op.drop_column("users", "ai_requests_used")
    op.drop_column("users", "subscription_expires_at")
    op.drop_column("users", "is_subscribed")

    subscription_status = sa.Enum("TRIAL", "ACTIVE", "PAST_DUE", "CANCELED", "EXPIRED", name="subscriptionstatus")
    subscription_status.drop(op.get_bind(), checkfirst=True)

