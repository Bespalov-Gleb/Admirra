-- Add AI comment storage to clients table
-- docker compose exec db psql -U postgres -d saas_project -f sql/ai_comment_client.sql

ALTER TABLE clients
    ADD COLUMN IF NOT EXISTS last_ai_comment TEXT,
    ADD COLUMN IF NOT EXISTS last_ai_comment_at TIMESTAMP;
