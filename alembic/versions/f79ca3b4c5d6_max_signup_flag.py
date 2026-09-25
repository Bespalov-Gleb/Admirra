"""Explicit new-account marker for the one-time MAX login response."""
from alembic import op
import sqlalchemy as sa

revision = 'f79ca3b4c5d6'
down_revision = 'f68b92a3b4c5'
branch_labels = None
depends_on = None

def upgrade():
    # Online expand may precede the coordinated worker/schema-version rollout.
    columns = {c['name']: c for c in sa.inspect(op.get_bind()).get_columns('max_oauth_login_attempts')}
    if 'is_new_user' not in columns:
        op.add_column('max_oauth_login_attempts', sa.Column('is_new_user', sa.Boolean(), nullable=False, server_default=sa.false()))
    else:
        assert isinstance(columns['is_new_user']['type'], sa.Boolean) and not columns['is_new_user']['nullable']

def downgrade():
    op.drop_column('max_oauth_login_attempts', 'is_new_user')
