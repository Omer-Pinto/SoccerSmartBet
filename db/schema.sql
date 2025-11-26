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
    n1 DECIMAL(5,2) NOT NULL CHECK (n1 > 1.0),
    n2 DECIMAL(5,2) NOT NULL CHECK (n2 > 1.0),
    n3 DECIMAL(5,2) NOT NULL CHECK (n3 > 1.0),
    
    -- Status tracking
    status VARCHAR(50) DEFAULT 'pending' CHECK (status IN (
        'pending', 'selected', 'processing', 'ready_for_betting',
        'betting_open', 'betting_closed', 'completed', 'cancelled'
    )),
    
    -- Results (NULL until game completes - no separate results table)
    home_score INTEGER CHECK (home_score >= 0),
    away_score INTEGER CHECK (away_score >= 0),
    outcome VARCHAR(5) CHECK (outcome IN ('1', 'x', '2')),
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Minimal indexes
CREATE INDEX idx_games_date ON games(match_date);
CREATE INDEX idx_games_status ON games(status);

COMMENT ON TABLE games IS 'Daily selected games with odds and results merged in';
COMMENT ON COLUMN games.n1 IS 'Home win odds (Israeli Toto notation)';
COMMENT ON COLUMN games.n2 IS 'Away win odds';
COMMENT ON COLUMN games.n3 IS 'Draw odds';

-- ============================================================================
-- TABLE: game_reports
-- Purpose: AI-generated game analysis from Game Intelligence Agent
-- ============================================================================
CREATE TABLE game_reports (
    report_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    game_id INTEGER NOT NULL REFERENCES games(game_id) ON DELETE CASCADE,
    
    h2h_insights TEXT,
    atmosphere_summary TEXT,
    weather_risk TEXT,
    venue_factors TEXT,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
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
    rotation_risk TEXT,
    key_players_status TEXT,
    morale_stability TEXT,
    relevant_news TEXT,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT unique_team_game_report UNIQUE (game_id, team_name)
);

-- Minimal indexes
CREATE INDEX idx_team_reports_game ON team_reports(game_id);

COMMENT ON COLUMN team_reports.report_id IS 'UUID for parallel agent writes (2 per game: home + away)';
COMMENT ON COLUMN team_reports.team_name IS 'VARCHAR not FK - no teams table needed';

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
-- TABLE: pnl_totals
-- Purpose: Cumulative P&L tracking (just 2 rows!)
-- ============================================================================
CREATE TABLE pnl_totals (
    bettor VARCHAR(10) PRIMARY KEY CHECK (bettor IN ('user', 'ai')),
    total_pnl DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    games_played INTEGER NOT NULL DEFAULT 0,
    games_won INTEGER NOT NULL DEFAULT 0,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Initialize with starting totals
INSERT INTO pnl_totals (bettor) VALUES ('user'), ('ai');

COMMENT ON TABLE pnl_totals IS 'Cumulative P&L totals - updated daily, no historical game-by-game tracking';
