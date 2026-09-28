"""Persist attribution across MAX browser / bot handoff."""
from alembic import op
import sqlalchemy as sa

revision = 'f8ad4b5c6d7e'
down_revision = 'f79ca3b4c5d6'
branch_labels = None
depends_on = None


def upgrade():
    columns = {c['name']: c for c in sa.inspect(op.get_bind()).get_columns('max_oauth_login_attempts')}
    if 'registration_attribution' not in columns:
        op.add_column('max_oauth_login_attempts', sa.Column('registration_attribution', sa.JSON(), nullable=True))
    else:
        assert isinstance(columns['registration_attribution']['type'], sa.JSON) and columns['registration_attribution']['nullable']


def downgrade():
    op.drop_column('max_oauth_login_attempts', 'registration_attribution')
