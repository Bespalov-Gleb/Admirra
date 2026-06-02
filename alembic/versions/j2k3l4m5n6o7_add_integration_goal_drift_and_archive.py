"""Add integration goal drift tracking and archive flags.

Revision ID: j2k3l4m5n6o7
Revises: None
Create Date: 2026-06-02
"""
from alembic import op
import sqlalchemy as sa


revision = "j2k3l4m5n6o7"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.execute(sa.text("ALTER TABLE integrations ADD COLUMN IF NOT EXISTS known_goal_ids VARCHAR"))
    op.execute(sa.text("ALTER TABLE integrations ADD COLUMN IF NOT EXISTS goals_snapshot VARCHAR"))
    op.execute(sa.text("ALTER TABLE integrations ADD COLUMN IF NOT EXISTS goals_snapshot_at TIMESTAMP"))
    op.execute(sa.text("ALTER TABLE integrations ADD COLUMN IF NOT EXISTS is_archived BOOLEAN NOT NULL DEFAULT FALSE"))
    op.execute(sa.text("ALTER TABLE integrations ADD COLUMN IF NOT EXISTS archived_at TIMESTAMP"))


def downgrade():
    op.drop_column("integrations", "archived_at")
    op.drop_column("integrations", "is_archived")
    op.drop_column("integrations", "goals_snapshot_at")
    op.drop_column("integrations", "goals_snapshot")
    op.drop_column("integrations", "known_goal_ids")
