"""Persist report freshness requirements; disabled until explicit rollout."""
from alembic import op
import sqlalchemy as sa

revision = "f13c4d5e6f70"
down_revision = "f02b3c4d5e6f"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("report_deliveries", sa.Column("data_readiness", sa.JSON(), nullable=True))


def downgrade():
    op.drop_column("report_deliveries", "data_readiness")
