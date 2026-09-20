"""Adopt the additive assistant quota hotfix into the full migration chain."""
from alembic import op
from ops.migrate_assistant_runs import migrate

revision = "cd9e0f1a2b3c"
down_revision = "bc8d9e0f1a2b"
branch_labels = None
depends_on = None


def upgrade():
    migrate(op.get_bind())


def downgrade():
    raise RuntimeError("Retain assistant idempotency/usage evidence on application rollback")
