-- Migration 004: Add expert_game_reports table
-- Stores LLM-generated expert pre-match analysis synthesizing all available intel

CREATE TABLE expert_game_reports (
    report_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    game_id INTEGER NOT NULL REFERENCES games(game_id) ON DELETE CASCADE,
    expert_analysis TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT unique_expert_game_report UNIQUE (game_id)
);
CREATE INDEX idx_expert_game_reports_game ON expert_game_reports(game_id);

COMMENT ON TABLE expert_game_reports IS 'Expert LLM pre-match analysis synthesizing game + team reports with odds';
