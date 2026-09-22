"""First advertising account signup discount.

Revision ID: ef1a2b3c4d5e
Revises: de0f1a2b3c4d
"""
from alembic import op
import sqlalchemy as sa

revision = 'ef1a2b3c4d5e'
down_revision = 'de0f1a2b3c4d'
branch_labels = None
depends_on = None

DATES = ('granted', 'expires', 'used', 'modal_seen', 'toast_seen', 'reminder_claimed', 'reminder_sent')


def upgrade():
    # Production may receive this additive schema independently of the pending
    # DevOps chain. Later normal Alembic upgrade verifies and adopts it.
    columns = {c['name']: c for c in sa.inspect(op.get_bind()).get_columns('users')}
    for name in DATES:
        key = f'signup_discount_{name}_at'
        if key in columns:
            col = columns[key]
            if not (isinstance(col['type'], sa.DateTime) and col['type'].timezone and col['nullable']):
                raise RuntimeError('Unexpected existing signup discount column: ' + key)
        else:
            op.add_column('users', sa.Column(key, sa.DateTime(timezone=True), nullable=True))
    key = 'signup_discount_invoice_id'
    if key in columns:
        col = columns[key]
        if not (isinstance(col['type'], sa.String) and col['type'].length == 64 and col['nullable']):
            raise RuntimeError('Unexpected existing signup discount invoice column')
    else:
        op.add_column('users', sa.Column(key, sa.String(64), nullable=True))
    indexes = {i['name']: i for i in sa.inspect(op.get_bind()).get_indexes('users')}
    if 'ix_users_signup_discount_reminder' not in indexes:
        op.create_index('ix_users_signup_discount_reminder', 'users', ['signup_discount_expires_at'],
            postgresql_where=sa.text('signup_discount_used_at IS NULL AND signup_discount_reminder_claimed_at IS NULL'))
    elif indexes['ix_users_signup_discount_reminder']['column_names'] != ['signup_discount_expires_at']:
        raise RuntimeError('Unexpected signup discount reminder index')


def downgrade():
    op.drop_index('ix_users_signup_discount_reminder', table_name='users')
    op.drop_column('users', 'signup_discount_invoice_id')
    for name in reversed(DATES):
        op.drop_column('users', f'signup_discount_{name}_at')
