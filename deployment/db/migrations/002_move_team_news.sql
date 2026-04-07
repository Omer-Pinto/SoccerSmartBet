-- Migration 002: Move team_news from game_reports to team_reports
-- team_news is per-team intel, not per-game — belongs in team_reports

ALTER TABLE team_reports ADD COLUMN team_news TEXT;
ALTER TABLE game_reports DROP COLUMN team_news;
