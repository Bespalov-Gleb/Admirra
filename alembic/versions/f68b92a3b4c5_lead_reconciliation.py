"""Preserve operator resolutions without replaying customer deliveries."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = 'f68b92a3b4c5'
down_revision = 'f57a8192a3b4'
branch_labels = None
depends_on = None


def upgrade():
    op.drop_constraint('ck_lead_intake_state', 'lead_intakes', type_='check')
    op.create_check_constraint('ck_lead_intake_state', 'lead_intakes', "state IN ('processing','done','held','closed')")
    op.drop_constraint('ck_lead_export_receipt_state', 'lead_export_receipts', type_='check')
    op.create_check_constraint('ck_lead_export_receipt_state', 'lead_export_receipts', "state IN ('sending','sent','rejected','closed')")
    op.create_table('lead_operation_resolutions',
        sa.Column('subject_type', sa.String(16), primary_key=True),
        sa.Column('subject_id', UUID(as_uuid=True), primary_key=True),
        sa.Column('owner_id', UUID(as_uuid=True), nullable=False),
        sa.Column('project_id', UUID(as_uuid=True), nullable=False),
        sa.Column('version', sa.String(64), nullable=False),
        sa.Column('decision', sa.String(32), nullable=False),
        sa.Column('actor', sa.String(128), nullable=False),
        sa.Column('reason', sa.String(1000), nullable=False),
        sa.Column('evidence_ref', sa.String(255), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("subject_type IN ('intake','export')", name='ck_lead_resolution_subject'),
        sa.CheckConstraint("decision IN ('close_unverified','confirm_delivered','close_without_resend')", name='ck_lead_resolution_decision'))


def downgrade():
    # Do not destroy evidence or invalidate terminal states on app rollback.
    pass
