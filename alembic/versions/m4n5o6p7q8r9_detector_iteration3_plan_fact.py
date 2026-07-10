"""Detector iteration 3: versioned plan inputs and efficient detector reads.

Revision ID: m4n5o6p7q8r9
Revises: l3m4n5o6p7q8
Create Date: 2026-07-11
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "m4n5o6p7q8r9"
down_revision: Union[str, Sequence[str], None] = "l3m4n5o6p7q8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # NULL channel represents an optional project-wide budget.  Existing
    # per-channel rows remain unchanged and continue to take precedence.
    op.alter_column("project_budgets", "channel", existing_type=sa.Enum(name="integrationplatform"), nullable=True)
    op.add_column("project_budgets", sa.Column("manual_leads", sa.Integer(), nullable=True))
    op.add_column("clients", sa.Column("detector_onboarding_dismissed_until", sa.DateTime(timezone=True), nullable=True))
    op.create_index(
        "ix_project_budgets_detector_lookup",
        "project_budgets",
        ["client_id", "channel", "period_start", "period_end", "created_at"],
    )
    op.create_index(
        "ix_project_target_cpa_detector_lookup",
        "project_target_cpa",
        ["client_id", "channel", "goal_id", "is_summary", "period_start", "period_end", "created_at"],
    )
    # Historical deviations are intentionally not "recovered": iteration 3
    # replaced their model, so keeping them open would leak old noise at
    # release time before the next synchronization.
    op.execute(
        """
        UPDATE detector_alerts
        SET status = 'closed', closed_at = NOW(),
            meta = (COALESCE(meta::jsonb, '{}'::jsonb) || '{"close_reason":"closed_by_iteration3_migration"}'::jsonb)::json
        WHERE status IN ('open', 'dismissed')
          AND mode IN ('baseline', 'plan_spend', 'plan_cpa', 'plan_leads')
        """
    )


def downgrade() -> None:
    op.drop_index("ix_project_target_cpa_detector_lookup", table_name="project_target_cpa")
    op.drop_index("ix_project_budgets_detector_lookup", table_name="project_budgets")
    op.drop_column("project_budgets", "manual_leads")
    op.drop_column("clients", "detector_onboarding_dismissed_until")
    op.alter_column("project_budgets", "channel", existing_type=sa.Enum(name="integrationplatform"), nullable=False)
