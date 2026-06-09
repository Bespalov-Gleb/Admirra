-- Internal admin (SEO, support, audit). Без alembic upgrade.
-- Из каталога trafic_agent:
-- docker compose exec -T db psql -U postgres -d saas_project -f - < sql/internal_admin_tables.sql

-- userrole (если ещё нет staff-ролей)
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_enum e JOIN pg_type t ON t.oid = e.enumtypid WHERE t.typname = 'userrole' AND e.enumlabel = 'SUPERADMIN') THEN
        ALTER TYPE userrole ADD VALUE 'SUPERADMIN';
    END IF;
END $$;
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_enum e JOIN pg_type t ON t.oid = e.enumtypid WHERE t.typname = 'userrole' AND e.enumlabel = 'SUPPORT') THEN
        ALTER TYPE userrole ADD VALUE 'SUPPORT';
    END IF;
END $$;
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_enum e JOIN pg_type t ON t.oid = e.enumtypid WHERE t.typname = 'userrole' AND e.enumlabel = 'SEO') THEN
        ALTER TYPE userrole ADD VALUE 'SEO';
    END IF;
END $$;
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_enum e JOIN pg_type t ON t.oid = e.enumtypid WHERE t.typname = 'userrole' AND e.enumlabel = 'DEVELOPER') THEN
        ALTER TYPE userrole ADD VALUE 'DEVELOPER';
    END IF;
END $$;
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_enum e JOIN pg_type t ON t.oid = e.enumtypid WHERE t.typname = 'userrole' AND e.enumlabel = 'STAFF_MANAGER') THEN
        ALTER TYPE userrole ADD VALUE 'STAFF_MANAGER';
    END IF;
END $$;

ALTER TABLE users
    ADD COLUMN IF NOT EXISTS last_login_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS registration_utm_source VARCHAR,
    ADD COLUMN IF NOT EXISTS registration_utm_medium VARCHAR,
    ADD COLUMN IF NOT EXISTS registration_utm_campaign VARCHAR,
    ADD COLUMN IF NOT EXISTS block_reason VARCHAR,
    ADD COLUMN IF NOT EXISTS ai_quota_resets_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS staff_totp_enabled BOOLEAN NOT NULL DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS staff_totp_secret_encrypted VARCHAR,
    ADD COLUMN IF NOT EXISTS staff_totp_pending_secret_encrypted VARCHAR,
    ADD COLUMN IF NOT EXISTS staff_recovery_codes_hashed JSONB;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'staffstatus') THEN
        CREATE TYPE staffstatus AS ENUM ('pending', 'active', 'inactive');
    END IF;
END $$;

ALTER TABLE users ADD COLUMN IF NOT EXISTS staff_status staffstatus;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'seoblogpoststatus') THEN
        CREATE TYPE seoblogpoststatus AS ENUM ('draft', 'review', 'published', 'archived');
    END IF;
END $$;

CREATE TABLE IF NOT EXISTS ia_support_user_assignments (
    id UUID PRIMARY KEY,
    staff_user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    client_user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    assigned_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    assigned_by UUID REFERENCES users(id) ON DELETE SET NULL,
    CONSTRAINT uq_ia_support_assignment UNIQUE (staff_user_id, client_user_id)
);
CREATE INDEX IF NOT EXISTS ix_ia_support_user_assignments_staff_user_id ON ia_support_user_assignments (staff_user_id);
CREATE INDEX IF NOT EXISTS ix_ia_support_user_assignments_client_user_id ON ia_support_user_assignments (client_user_id);

CREATE TABLE IF NOT EXISTS ia_support_notes (
    id UUID PRIMARY KEY,
    client_user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    author_user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    body TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_ia_support_notes_client_user_id ON ia_support_notes (client_user_id);

CREATE TABLE IF NOT EXISTS ia_admin_audit_logs (
    id UUID PRIMARY KEY,
    staff_user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    staff_email VARCHAR,
    action VARCHAR NOT NULL,
    target_type VARCHAR,
    target_id VARCHAR,
    description TEXT,
    meta JSONB,
    ip_address VARCHAR,
    user_agent VARCHAR,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_ia_admin_audit_logs_staff_user_id ON ia_admin_audit_logs (staff_user_id);
CREATE INDEX IF NOT EXISTS ix_ia_admin_audit_logs_action ON ia_admin_audit_logs (action);
CREATE INDEX IF NOT EXISTS ix_ia_admin_audit_logs_created_at ON ia_admin_audit_logs (created_at);

CREATE TABLE IF NOT EXISTS ia_admin_staff_sessions (
    id UUID PRIMARY KEY,
    staff_user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    session_token_hash VARCHAR NOT NULL UNIQUE,
    ip_address VARCHAR,
    user_agent VARCHAR,
    city VARCHAR,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    last_seen_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    revoked_at TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS ix_ia_admin_staff_sessions_staff_user_id ON ia_admin_staff_sessions (staff_user_id);
CREATE INDEX IF NOT EXISTS ix_ia_admin_staff_sessions_session_token_hash ON ia_admin_staff_sessions (session_token_hash);

CREATE TABLE IF NOT EXISTS ia_admin_settings (
    key VARCHAR PRIMARY KEY,
    value JSONB NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by UUID REFERENCES users(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS ia_ai_usage_logs (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    action VARCHAR NOT NULL DEFAULT 'ai_request',
    tokens_input INTEGER NOT NULL DEFAULT 0,
    tokens_output INTEGER NOT NULL DEFAULT 0,
    tokens_total INTEGER NOT NULL DEFAULT 0,
    cost_usd VARCHAR,
    meta JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_ia_ai_usage_logs_user_id ON ia_ai_usage_logs (user_id);
CREATE INDEX IF NOT EXISTS ix_ia_ai_usage_logs_created_at ON ia_ai_usage_logs (created_at);

CREATE TABLE IF NOT EXISTS ia_seo_blog_posts (
    id UUID PRIMARY KEY,
    slug VARCHAR NOT NULL UNIQUE,
    title VARCHAR NOT NULL,
    content_html TEXT NOT NULL DEFAULT '',
    category VARCHAR,
    status seoblogpoststatus NOT NULL DEFAULT 'draft',
    meta_title VARCHAR,
    meta_description TEXT,
    keywords VARCHAR,
    cover_url VARCHAR,
    traffic_monthly INTEGER NOT NULL DEFAULT 0,
    author_user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    published_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_ia_seo_blog_posts_slug ON ia_seo_blog_posts (slug);

CREATE TABLE IF NOT EXISTS ia_seo_site_pages (
    id UUID PRIMARY KEY,
    path VARCHAR NOT NULL UNIQUE,
    title VARCHAR,
    meta_title VARCHAR,
    meta_description TEXT,
    traffic_monthly INTEGER NOT NULL DEFAULT 0,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by UUID REFERENCES users(id) ON DELETE SET NULL
);
CREATE INDEX IF NOT EXISTS ix_ia_seo_site_pages_path ON ia_seo_site_pages (path);
