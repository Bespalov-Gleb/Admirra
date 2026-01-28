"""add phone projects and leads

Revision ID: b2c3d4e5f6a7
Revises: 1753da2599ca
Create Date: 2026-01-26 18:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'b2c3d4e5f6a7'
down_revision: Union[str, Sequence[str], None] = '1753da2599ca'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create phone_projects table
    op.create_table(
        'phone_projects',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('owner_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('client_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('description', sa.String(), nullable=True),
        sa.Column('webhook_url', sa.String(), nullable=True),
        sa.Column('webhook_secret', sa.String(), nullable=True),
        sa.Column('crm_webhook_url', sa.String(), nullable=True),
        sa.Column('email_recipients', sa.String(), nullable=True),
        sa.Column('telegram_chat_id', sa.String(), nullable=True),
        sa.Column('enable_social_check', sa.Boolean(), server_default='false'),
        sa.Column('enable_gosuslugi_check', sa.Boolean(), server_default='false'),
        sa.Column('enable_metrica_export', sa.Boolean(), server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default='true'),
        sa.ForeignKeyConstraint(['owner_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['client_id'], ['clients.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_phone_projects_owner_id'), 'phone_projects', ['owner_id'], unique=False)
    op.create_index(op.f('ix_phone_projects_client_id'), 'phone_projects', ['client_id'], unique=False)

    # Create lead_status enum
    leadstatus_enum = postgresql.ENUM('PENDING', 'VALID', 'SPAM', 'INVALID', name='leadstatus', create_type=True)
    leadstatus_enum.create(op.get_bind(), checkfirst=True)

    # Create leads table
    op.create_table(
        'leads',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('project_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('phone', sa.String(), nullable=False),
        sa.Column('email', sa.String(), nullable=True),
        sa.Column('name', sa.String(), nullable=True),
        sa.Column('surname', sa.String(), nullable=True),
        sa.Column('form_data', sa.String(), nullable=True),
        sa.Column('utm_source', sa.String(), nullable=True),
        sa.Column('utm_medium', sa.String(), nullable=True),
        sa.Column('utm_campaign', sa.String(), nullable=True),
        sa.Column('utm_content', sa.String(), nullable=True),
        sa.Column('utm_term', sa.String(), nullable=True),
        sa.Column('client_ip', sa.String(), nullable=True),
        sa.Column('user_agent', sa.String(), nullable=True),
        sa.Column('referer', sa.String(), nullable=True),
        sa.Column('geo_country', sa.String(), nullable=True),
        sa.Column('browser_timezone', sa.String(), nullable=True),
        sa.Column('ym_uid', sa.String(), nullable=True),
        sa.Column('fingerprint', sa.String(), nullable=True),
        sa.Column('is_valid', sa.Boolean(), server_default='false'),
        sa.Column('validation_reason', sa.String(), nullable=True),
        sa.Column('phone_type', sa.String(), nullable=True),
        sa.Column('phone_provider', sa.String(), nullable=True),
        sa.Column('phone_region', sa.String(), nullable=True),
        sa.Column('phone_city', sa.String(), nullable=True),
        sa.Column('dadata_qc', sa.Integer(), nullable=True),
        sa.Column('main_operator', sa.String(), nullable=True),
        sa.Column('registrant_info', sa.String(), nullable=True),
        sa.Column('has_telegram', sa.Boolean(), nullable=True),
        sa.Column('has_whatsapp', sa.Boolean(), nullable=True),
        sa.Column('has_tiktok', sa.Boolean(), nullable=True),
        sa.Column('has_vk', sa.Boolean(), nullable=True),
        sa.Column('social_accounts_data', sa.String(), nullable=True),
        sa.Column('has_gosuslugi', sa.Boolean(), nullable=True),
        sa.Column('gosuslugi_name', sa.String(), nullable=True),
        sa.Column('gosuslugi_surname', sa.String(), nullable=True),
        sa.Column('status', postgresql.ENUM('PENDING', 'VALID', 'SPAM', 'INVALID', name='leadstatus', create_type=False), nullable=True, server_default='PENDING'),
        sa.Column('is_spam', sa.Boolean(), server_default='false'),
        sa.Column('is_verified', sa.Boolean(), server_default='false'),
        sa.Column('exported_to_crm', sa.Boolean(), server_default='false'),
        sa.Column('exported_to_email', sa.Boolean(), server_default='false'),
        sa.Column('exported_to_telegram', sa.Boolean(), server_default='false'),
        sa.Column('exported_to_metrica', sa.Boolean(), server_default='false'),
        sa.Column('export_timestamp', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['project_id'], ['phone_projects.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_leads_project_id'), 'leads', ['project_id'], unique=False)
    op.create_index(op.f('ix_leads_phone'), 'leads', ['phone'], unique=False)
    op.create_index(op.f('ix_leads_email'), 'leads', ['email'], unique=False)
    op.create_index(op.f('ix_leads_status'), 'leads', ['status'], unique=False)
    op.create_index(op.f('ix_leads_is_spam'), 'leads', ['is_spam'], unique=False)
    op.create_index(op.f('ix_leads_created_at'), 'leads', ['created_at'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_leads_created_at'), table_name='leads')
    op.drop_index(op.f('ix_leads_is_spam'), table_name='leads')
    op.drop_index(op.f('ix_leads_status'), table_name='leads')
    op.drop_index(op.f('ix_leads_email'), table_name='leads')
    op.drop_index(op.f('ix_leads_phone'), table_name='leads')
    op.drop_index(op.f('ix_leads_project_id'), table_name='leads')
    op.drop_table('leads')
    op.execute("DROP TYPE IF EXISTS leadstatus")
    op.drop_index(op.f('ix_phone_projects_client_id'), table_name='phone_projects')
    op.drop_index(op.f('ix_phone_projects_owner_id'), table_name='phone_projects')
    op.drop_table('phone_projects')

