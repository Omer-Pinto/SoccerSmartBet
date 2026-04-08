-- ============================================================================
-- SoccerSmartBet PostgreSQL Schema - Simplified
-- ============================================================================
-- Version: 1.1
-- Tables: 5 core tables for daily betting workflow
-- ============================================================================

-- Enable UUID extension for parallel agent writes
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================================
-- TABLE: games
-- Purpose: Today's selected games with odds and results merged in
-- ============================================================================
CREATE TABLE games (
    game_id SERIAL PRIMARY KEY,
    match_date DATE NOT NULL,
    kickoff_time TIME NOT NULL,
    
    -- Teams as simple strings (NO FK to teams table)
    home_team VARCHAR(255) NOT NULL,
    away_team VARCHAR(255) NOT NULL,
    
    league VARCHAR(100) NOT NULL,
    venue VARCHAR(255), -- Per-game venue (teams play at multiple stadiums)
    
    -- Odds directly here (no separate betting_lines table)
    home_win_odd DECIMAL(5,2) NOT NULL CHECK (home_win_odd > 1.0),
    away_win_odd DECIMAL(5,2) NOT NULL CHECK (away_win_odd > 1.0),
    draw_odd DECIMAL(5,2) NOT NULL CHECK (draw_odd > 1.0),
    
    -- Status tracking
    status VARCHAR(50) DEFAULT 'pending' CHECK (status IN (
        'pending', 'selected', 'processing', 'ready_for_betting',
        'betting_open', 'betting_closed', 'completed', 'cancelled'
    )),
    
    -- Results (NULL until game completes - no separate results table)
    home_score INTEGER CHECK (home_score >= 0),
    away_score INTEGER CHECK (away_score >= 0),
    outcome VARCHAR(5) CHECK (outcome IN ('1', 'x', '2')),
    
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- Minimal indexes
CREATE INDEX idx_games_date ON games(match_date);
CREATE INDEX idx_games_status ON games(status);

COMMENT ON TABLE games IS 'Daily selected games with odds and results merged in';
COMMENT ON COLUMN games.home_win_odd IS 'Home win odds (1 in Israeli Toto notation)';
COMMENT ON COLUMN games.away_win_odd IS 'Away win odds (2 in Israeli Toto notation)';
COMMENT ON COLUMN games.draw_odd IS 'Draw odds (X in Israeli Toto notation)';

-- ============================================================================
-- TABLE: game_reports
-- Purpose: AI-generated game analysis from Game Intelligence Agent
-- ============================================================================
CREATE TABLE game_reports (
    report_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    game_id INTEGER NOT NULL REFERENCES games(game_id) ON DELETE CASCADE,
    
    h2h_insights TEXT,
    weather_risk TEXT,
    venue TEXT,

    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT unique_game_report UNIQUE (game_id)
);

CREATE INDEX idx_game_reports_game ON game_reports(game_id);

COMMENT ON COLUMN game_reports.report_id IS 'UUID for parallel agent writes';

-- ============================================================================
-- TABLE: team_reports
-- Purpose: AI-generated team analysis from Team Intelligence Agent
-- ============================================================================
CREATE TABLE team_reports (
    report_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    game_id INTEGER NOT NULL REFERENCES games(game_id) ON DELETE CASCADE,
    team_name VARCHAR(255) NOT NULL, -- Changed from team_id FK to VARCHAR!
    
    recovery_days INTEGER CHECK (recovery_days >= 0),
    form_trend TEXT,
    injury_impact TEXT,
    league_position TEXT,
    team_news TEXT,

    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT unique_team_game_report UNIQUE (game_id, team_name)
);

-- Minimal indexes
CREATE INDEX idx_team_reports_game ON team_reports(game_id);

COMMENT ON COLUMN team_reports.report_id IS 'UUID for parallel agent writes (2 per game: home + away)';
COMMENT ON COLUMN team_reports.team_name IS 'VARCHAR not FK - no teams table needed';

-- ============================================================================
-- TABLE: expert_game_reports
-- Purpose: LLM-generated expert pre-match analysis synthesizing all intel
-- ============================================================================
CREATE TABLE expert_game_reports (
    report_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    game_id INTEGER NOT NULL REFERENCES games(game_id) ON DELETE CASCADE,
    expert_analysis TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT unique_expert_game_report UNIQUE (game_id)
);
CREATE INDEX idx_expert_game_reports_game ON expert_game_reports(game_id);

COMMENT ON TABLE expert_game_reports IS 'Expert LLM pre-match analysis synthesizing game + team reports with odds';

-- ============================================================================
-- TABLE: bets
-- Purpose: User and AI betting predictions
-- ============================================================================
CREATE TABLE bets (
    bet_id SERIAL PRIMARY KEY,
    game_id INTEGER NOT NULL REFERENCES games(game_id) ON DELETE CASCADE,
    bettor VARCHAR(10) NOT NULL CHECK (bettor IN ('user', 'ai')),
    prediction VARCHAR(5) NOT NULL CHECK (prediction IN ('1', 'x', '2')),
    odds DECIMAL(5,2) NOT NULL CHECK (odds > 1.0),
    stake DECIMAL(10,2) NOT NULL DEFAULT 100.00 CHECK (stake = 100.00),
    justification TEXT,
    
    CONSTRAINT unique_bet_per_game UNIQUE (game_id, bettor)
);

CREATE INDEX idx_bets_game ON bets(game_id);

COMMENT ON COLUMN bets.stake IS 'Always 100 NIS per system rules';

-- ============================================================================
-- TABLE: bankroll
-- Purpose: Bankroll tracking - each starts at 10,000 USD
-- ============================================================================
CREATE TABLE bankroll (
    bettor VARCHAR(10) PRIMARY KEY CHECK (bettor IN ('user', 'ai')),
    total_bankroll DECIMAL(10,2) NOT NULL DEFAULT 10000.00,
    games_played INTEGER NOT NULL DEFAULT 0,
    games_won INTEGER NOT NULL DEFAULT 0,
    last_updated TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- Initialize with 10,000 USD each
INSERT INTO bankroll (bettor, total_bankroll) VALUES 
    ('user', 10000.00), 
    ('ai', 10000.00);

COMMENT ON TABLE bankroll IS 'Bankroll tracking - each starts at 10,000 USD, bets 100 USD per game. Israeli Toto: profit = (odds - 1) × stake';

-- ============================================================================
-- TABLE: teams
-- Purpose: Canonical team registry with cross-source name resolution
-- ============================================================================
CREATE TABLE teams (
    team_id SERIAL PRIMARY KEY,
    canonical_name VARCHAR(255) NOT NULL UNIQUE,
    short_name VARCHAR(100),
    aliases JSONB DEFAULT '[]',
    fotmob_id INTEGER,
    football_data_id INTEGER,
    winner_name_he VARCHAR(255),
    league VARCHAR(100),
    country VARCHAR(100),
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_teams_canonical ON teams(canonical_name);
CREATE INDEX idx_teams_fotmob ON teams(fotmob_id);
CREATE INDEX idx_teams_football_data ON teams(football_data_id);

COMMENT ON TABLE teams IS 'Canonical team registry — maps team names across FotMob, football-data.org, winner.co.il (Hebrew)';
COMMENT ON COLUMN teams.aliases IS 'JSON array of alternative names: ["Atletico", "Atlético de Madrid", "Club Atlético de Madrid"]';
COMMENT ON COLUMN teams.winner_name_he IS 'Hebrew team name as used by winner.co.il';
