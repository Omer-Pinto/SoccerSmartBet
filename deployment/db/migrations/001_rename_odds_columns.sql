-- Migration 001: Rename n1/n2/n3 odds columns to descriptive names
-- Applies to: running DB (use ALTER TABLE, NOT DROP/CREATE)
-- Fresh deployments: handled by updated 001_create_schema.sql

ALTER TABLE games RENAME COLUMN n1 TO home_win_odd;
ALTER TABLE games RENAME COLUMN n2 TO away_win_odd;
ALTER TABLE games RENAME COLUMN n3 TO draw_odd;
