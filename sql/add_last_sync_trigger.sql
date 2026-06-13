-- Migration: track whether the last sync was auto (nightly scheduler) or manual (user-triggered)
ALTER TABLE integrations
    ADD COLUMN IF NOT EXISTS last_sync_trigger VARCHAR(16);
