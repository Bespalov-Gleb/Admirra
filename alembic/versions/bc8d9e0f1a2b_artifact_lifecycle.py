"""Durable binary artifact lifecycle, report references and scoped file links."""
from alembic import op
import sqlalchemy as sa

revision = "bc8d9e0f1a2b"
down_revision = "ab7c8d9e0f1a"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""CREATE TABLE stored_artifacts (
        id UUID PRIMARY KEY,
        creator_id UUID REFERENCES users(id) ON DELETE SET NULL,
        account_id UUID REFERENCES users(id) ON DELETE SET NULL,
        scope_ids JSONB NOT NULL CHECK (jsonb_typeof(scope_ids) = 'array' AND jsonb_array_length(scope_ids) BETWEEN 1 AND 1000),
        kind VARCHAR(32) NOT NULL CHECK (kind IN ('report_pdf','report_png','report_docx')),
        size_bytes BIGINT NOT NULL CHECK (size_bytes BETWEEN 0 AND 52428800),
        sha256 VARCHAR(64) NOT NULL CHECK (sha256 ~ '^[0-9a-f]{64}$'),
        request_hash VARCHAR(64) NOT NULL CHECK (request_hash ~ '^[0-9a-f]{64}$'),
        state VARCHAR(16) NOT NULL CHECK (state IN ('uploading','ready','deleting','deleted')),
        generation BIGINT NOT NULL CHECK (generation > 0),
        lease_until TIMESTAMPTZ,
        created_at TIMESTAMPTZ NOT NULL,
        ready_at TIMESTAMPTZ,
        expires_at TIMESTAMPTZ NOT NULL CHECK (expires_at > created_at),
        deleted_at TIMESTAMPTZ,
        UNIQUE (account_id, request_hash),
        CHECK ((state IN ('uploading','deleting')) = (lease_until IS NOT NULL)),
        CHECK ((state = 'deleted') = (deleted_at IS NOT NULL)),
        CHECK (state != 'ready' OR ready_at IS NOT NULL)
    )""")
    op.execute("CREATE INDEX ix_artifacts_account_state ON stored_artifacts (account_id, state)")
    op.execute("CREATE INDEX ix_artifacts_cleanup ON stored_artifacts (state, lease_until, expires_at)")
    op.execute("""CREATE TABLE report_artifact_refs (
        delivery_id UUID NOT NULL REFERENCES report_deliveries(id) ON DELETE CASCADE,
        format VARCHAR(8) NOT NULL CHECK (format IN ('pdf','png','docx')),
        artifact_id UUID NOT NULL REFERENCES stored_artifacts(id) ON DELETE RESTRICT,
        source_hash VARCHAR(64) NOT NULL CHECK (source_hash ~ '^[0-9a-f]{64}$'),
        PRIMARY KEY (delivery_id, format)
    )""")
    op.execute("CREATE INDEX ix_report_artifact_id ON report_artifact_refs (artifact_id)")
    op.execute("""CREATE TABLE artifact_public_links (
        id UUID PRIMARY KEY,
        creator_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        artifact_id UUID NOT NULL REFERENCES stored_artifacts(id) ON DELETE RESTRICT,
        token_hash VARCHAR(64) NOT NULL UNIQUE CHECK (token_hash ~ '^[0-9a-f]{64}$'),
        created_at TIMESTAMPTZ NOT NULL,
        expires_at TIMESTAMPTZ NOT NULL CHECK (expires_at > created_at AND expires_at <= created_at + interval '1 day'),
        revoked_at TIMESTAMPTZ
    )""")
    op.execute("CREATE INDEX ix_artifact_links_creator ON artifact_public_links (creator_id, created_at)")
    op.execute("CREATE INDEX ix_artifact_links_target ON artifact_public_links (artifact_id, expires_at)")


def downgrade():
    # Soft-deleted metadata still needed for restore/evidence: keep unless empty.
    if op.get_bind().scalar(sa.text("SELECT EXISTS (SELECT 1 FROM stored_artifacts)")):
        raise RuntimeError("Archive and reconcile artifact metadata before downgrade")
    op.drop_table("artifact_public_links")
    op.drop_table("report_artifact_refs")
    op.drop_table("stored_artifacts")
