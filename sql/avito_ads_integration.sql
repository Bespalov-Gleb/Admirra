-- Run from trafic_agent/ directory:
-- docker compose exec db psql -U postgres -d saas_project -f sql/avito_ads_integration.sql

-- 1) Enum platform extension (idempotent)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_enum e
                 JOIN pg_type t ON t.oid = e.enumtypid
        WHERE t.typname = 'integrationplatform'
          AND e.enumlabel = 'AVITO_ADS'
    ) THEN
        ALTER TYPE integrationplatform ADD VALUE 'AVITO_ADS';
    END IF;
END $$;

-- 2) User profile fields for Avito credentials
ALTER TABLE users
    ADD COLUMN IF NOT EXISTS avito_credential_type VARCHAR(32),
    ADD COLUMN IF NOT EXISTS avito_api_key TEXT,
    ADD COLUMN IF NOT EXISTS avito_client_id TEXT,
    ADD COLUMN IF NOT EXISTS avito_client_secret TEXT;

-- 3) Avito stats table
CREATE TABLE IF NOT EXISTS avito_stats (
    id BIGSERIAL PRIMARY KEY,
    client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    campaign_id UUID NULL REFERENCES campaigns(id) ON DELETE CASCADE,
    date DATE NOT NULL,
    campaign_name TEXT,
    impressions BIGINT DEFAULT 0,
    clicks BIGINT DEFAULT 0,
    cost NUMERIC(20, 2) DEFAULT 0,
    conversions BIGINT DEFAULT 0,
    cpc NUMERIC(20, 2),
    cpa NUMERIC(20, 2)
);

CREATE INDEX IF NOT EXISTS ix_avito_stats_client_id ON avito_stats (client_id);
CREATE INDEX IF NOT EXISTS ix_avito_stats_date ON avito_stats (date);
CREATE INDEX IF NOT EXISTS ix_avito_stats_campaign_id ON avito_stats (campaign_id);
