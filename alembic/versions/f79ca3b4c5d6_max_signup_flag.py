"""Explicit new-account marker for the one-time MAX login response."""
from alembic import op
import sqlalchemy as sa

revision = 'f79ca3b4c5d6'
down_revision = 'f68b92a3b4c5'
branch_labels = None
depends_on = None

def upgrade():
    op.add_column('max_oauth_login_attempts', sa.Column('is_new_user', sa.Boolean(), nullable=False, server_default=sa.false()))

def downgrade():
    op.drop_column('max_oauth_login_attempts', 'is_new_user')
