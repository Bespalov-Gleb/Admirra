"""Project-scoped placement decisions; do not copy unowned Redis history."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = 'f46f708192a3'
down_revision = 'f35e6f708192'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('lead_placement_blocks',
        sa.Column('owner_id', UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('project_id', UUID(as_uuid=True), sa.ForeignKey('phone_projects.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('placement_key', sa.String(64), primary_key=True),
        sa.Column('source', sa.String(200), nullable=False),
        sa.Column('campaign', sa.String(200), nullable=False),
        sa.Column('content', sa.String(200), nullable=False),
        sa.Column('reason', sa.String(200), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False))
    op.create_index('ix_lead_placement_owner_expiry', 'lead_placement_blocks', ['owner_id', 'expires_at'])
    op.create_index('ix_lead_placement_project', 'lead_placement_blocks', ['project_id'])


def downgrade():
    # Keep decisions on an application rollback; never return to global keys.
    pass
