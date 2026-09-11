"""Revocable HTML report links, independent of one API process."""
from alembic import op
import sqlalchemy as sa

revision = "ab7c8d9e0f1a"
down_revision = "ff6a7b8c9d0e"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""CREATE TABLE public_report_links (
        id UUID PRIMARY KEY,
        creator_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        account_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        token_hash VARCHAR(64) NOT NULL UNIQUE CHECK (token_hash ~ '^[0-9a-f]{64}$'),
        scope_ids JSONB NOT NULL CHECK (jsonb_typeof(scope_ids) = 'array'
            AND jsonb_array_length(scope_ids) BETWEEN 1 AND 1000),
        snapshot TEXT NOT NULL CHECK (jsonb_typeof(snapshot::jsonb) = 'object'),
        snapshot_hash VARCHAR(64) NOT NULL CHECK (snapshot_hash ~ '^[0-9a-f]{64}$'),
        snapshot_bytes INTEGER NOT NULL CHECK (snapshot_bytes BETWEEN 2 AND 1048576
            AND snapshot_bytes = octet_length(snapshot)),
        created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        expires_at TIMESTAMPTZ NOT NULL,
        revoked_at TIMESTAMPTZ,
        CHECK (expires_at > created_at AND expires_at <= created_at + interval '1 day')
    )""")
    op.execute("CREATE INDEX ix_public_report_links_owner ON public_report_links (creator_id, created_at, id)")
    op.execute("CREATE INDEX ix_public_report_links_expiry ON public_report_links (expires_at)")
    op.execute("CREATE INDEX ix_public_report_links_revoked ON public_report_links (revoked_at) WHERE revoked_at IS NOT NULL")


def downgrade():
    active = op.get_bind().scalar(sa.text("""SELECT EXISTS (SELECT 1 FROM public_report_links
        WHERE revoked_at IS NULL AND expires_at > clock_timestamp())"""))
    if active:
        raise RuntimeError("Expire or revoke public report links before downgrade")
    op.drop_table("public_report_links")
