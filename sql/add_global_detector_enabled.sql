-- Migration: add global_detector_enabled toggle to users (TZ 1.12)
ALTER TABLE users
    ADD COLUMN IF NOT EXISTS global_detector_enabled BOOLEAN NOT NULL DEFAULT TRUE;
