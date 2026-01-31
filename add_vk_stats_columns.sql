-- SQL script to add cpc and cpa columns to vk_stats table
-- This can be executed directly in the database if migrations are not in sync

ALTER TABLE vk_stats 
ADD COLUMN IF NOT EXISTS cpc NUMERIC(20, 2) NULL,
ADD COLUMN IF NOT EXISTS cpa NUMERIC(20, 2) NULL;

