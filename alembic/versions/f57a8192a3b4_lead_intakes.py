"""Persist project intake before validation and bind idempotent results."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = 'f57a8192a3b4'
down_revision = 'f46f708192a3'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('lead_intakes',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('project_id', UUID(as_uuid=True), sa.ForeignKey('phone_projects.id', ondelete='CASCADE'), nullable=False),
        sa.Column('owner_id', UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('lead_id', UUID(as_uuid=True), sa.ForeignKey('leads.id', ondelete='CASCADE'), nullable=False, unique=True),
        sa.Column('key_digest', sa.String(64), nullable=False),
        sa.Column('payload_digest', sa.String(64), nullable=False),
        sa.Column('scope_digest', sa.String(64), nullable=False),
        sa.Column('state', sa.String(16), nullable=False),
        sa.Column('result', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('deadline', sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint('project_id', 'owner_id', 'key_digest', name='uq_lead_intake_key'),
        sa.CheckConstraint("state IN ('processing','done','held')", name='ck_lead_intake_state'))
    op.create_index('ix_lead_intake_pending', 'lead_intakes', ['state', 'deadline'])
    op.create_index('ix_lead_project_phone_date', 'leads', ['project_id', 'phone', 'created_at'])
    op.create_index('ix_lead_project_email_date', 'leads', ['project_id', sa.text('lower(trim(email))'), 'created_at'])
    op.create_table('lead_export_receipts',
        sa.Column('job_id', UUID(as_uuid=True), sa.ForeignKey('background_jobs.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('scope_digest', sa.String(64), nullable=False),
        sa.Column('body_digest', sa.String(64), nullable=False),
        sa.Column('state', sa.String(16), nullable=False),
        sa.Column('provider_ref', sa.String(128)),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('confirmed_at', sa.DateTime(timezone=True)),
        sa.CheckConstraint("state IN ('sending','sent','rejected')", name='ck_lead_export_receipt_state'))


def downgrade():
    # Admission/dispatch evidence must survive an application rollback.
    pass
