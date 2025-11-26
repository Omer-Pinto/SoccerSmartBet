-- ============================================================================
-- SoccerSmartBet PostgreSQL Schema
-- ============================================================================
-- Version: 1.0
-- Purpose: Database schema for AI soccer betting system
-- ============================================================================

-- Enable UUID extension for parallel agent writes
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================================
-- TABLE: teams
-- ============================================================================
CREATE TABLE teams (
    team_id SERIAL PRIMARY KEY,
    external_id VARCHAR(100),
    external_source VARCHAR(50),
    
    name VARCHAR(255) NOT NULL,
    short_name VARCHAR(100),
    league VARCHAR(100),
    venue VARCHAR(255),
    city VARCHAR(100),
    country VARCHAR(100),
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT unique_external_team UNIQUE (external_id, external_source)
);

CREATE INDEX idx_teams_name ON teams(name);

-- ============================================================================
-- TABLE: games
-- ============================================================================
CREATE TABLE games (
    game_id SERIAL PRIMARY KEY,
    external_id VARCHAR(100),
    external_source VARCHAR(50),
    
    match_date DATE NOT NULL,
    kickoff_time TIME NOT NULL,
    timezone VARCHAR(50) DEFAULT 'UTC',
    
    home_team_id INTEGER NOT NULL REFERENCES teams(team_id) ON DELETE RESTRICT,
    away_team_id INTEGER NOT NULL REFERENCES teams(team_id) ON DELETE RESTRICT,
    
    league VARCHAR(100) NOT NULL,
    competition VARCHAR(255),
    venue VARCHAR(255),
    
    -- Status: 'pending', 'selected', 'filtered', 'processing', 
    --         'ready_for_betting', 'betting_open', 'betting_closed',
    --         'in_progress', 'completed', 'cancelled'
    status VARCHAR(50) DEFAULT 'pending',
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT unique_external_game UNIQUE (external_id, external_source),
    CONSTRAINT different_teams CHECK (home_team_id != away_team_id),
    CONSTRAINT valid_status CHECK (status IN (
        'pending', 'selected', 'filtered', 'processing', 
        'ready_for_betting', 'betting_open', 'betting_closed', 
        'in_progress', 'completed', 'cancelled'
    ))
);

CREATE INDEX idx_games_date ON games(match_date);
CREATE INDEX idx_games_status ON games(status);
CREATE INDEX idx_games_home_team ON games(home_team_id);
CREATE INDEX idx_games_away_team ON games(away_team_id);

COMMENT ON COLUMN games.status IS 'Tracks game through Pre-Gambling → Gambling → Post-Games flows';

-- ============================================================================
-- TABLE: betting_lines
-- Purpose: Odds from winner.co.il (Israeli Toto notation)
-- ============================================================================
CREATE TABLE betting_lines (
    line_id SERIAL PRIMARY KEY,
    game_id INTEGER NOT NULL REFERENCES games(game_id) ON DELETE CASCADE,
    
    n1 DECIMAL(5, 2) NOT NULL, -- Home win odds
    n2 DECIMAL(5, 2) NOT NULL, -- Away win odds
    n3 DECIMAL(5, 2) NOT NULL, -- Draw odds (nx)
    
    source VARCHAR(100) DEFAULT 'winner.co.il',
    fetched_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT positive_odds_n1 CHECK (n1 > 1.0),
    CONSTRAINT positive_odds_n2 CHECK (n2 > 1.0),
    CONSTRAINT positive_odds_n3 CHECK (n3 > 1.0)
);

CREATE INDEX idx_betting_lines_game ON betting_lines(game_id);

COMMENT ON TABLE betting_lines IS 'Israeli Toto notation: n1=home, n2=away, n3=draw';

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
    
    data_quality JSONB,
    
    agent_version VARCHAR(50),
    llm_model VARCHAR(100),
    processing_time_seconds DECIMAL(10, 2),
    
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
    team_id INTEGER NOT NULL REFERENCES teams(team_id) ON DELETE CASCADE,
    
    recovery_days INTEGER,
    
    -- AI analysis: Team Intelligence Agent stores injury info as TEXT
    form_trend TEXT,
    injury_impact TEXT,
    rotation_risk TEXT,
    key_players_status TEXT,
    morale_stability TEXT,
    preparation_quality TEXT,
    relevant_news TEXT,
    
    data_quality JSONB,
    
    agent_version VARCHAR(50),
    llm_model VARCHAR(100),
    processing_time_seconds DECIMAL(10, 2),
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT unique_team_game_report UNIQUE (game_id, team_id),
    CONSTRAINT valid_recovery_days CHECK (recovery_days >= 0)
);

CREATE INDEX idx_team_reports_game ON team_reports(game_id);
CREATE INDEX idx_team_reports_game_team ON team_reports(game_id, team_id);

COMMENT ON COLUMN team_reports.report_id IS 'UUID for parallel agent writes (2 per game: home + away)';
COMMENT ON COLUMN team_reports.injury_impact IS 'AI-generated TEXT with injury analysis - no player roster needed';

-- ============================================================================
-- TABLE: bets
-- Purpose: User and AI betting predictions
-- ============================================================================
CREATE TABLE bets (
    bet_id SERIAL PRIMARY KEY,
    game_id INTEGER NOT NULL REFERENCES games(game_id) ON DELETE CASCADE,
    
    bettor VARCHAR(10) NOT NULL,
    prediction VARCHAR(5) NOT NULL, -- '1' (home), 'x' (draw), '2' (away)
    odds DECIMAL(5, 2) NOT NULL,
    stake DECIMAL(10, 2) NOT NULL DEFAULT 100.00,
    
    justification TEXT,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT valid_bettor CHECK (bettor IN ('user', 'ai')),
    CONSTRAINT valid_prediction CHECK (prediction IN ('1', 'x', '2')),
    CONSTRAINT positive_odds CHECK (odds > 1.0),
    CONSTRAINT fixed_stake CHECK (stake = 100.00),
    CONSTRAINT unique_bet_per_game UNIQUE (game_id, bettor)
);

CREATE INDEX idx_bets_game ON bets(game_id);

COMMENT ON COLUMN bets.stake IS 'Always 100 NIS per system rules';

-- ============================================================================
-- TABLE: results
-- Purpose: Match results and P&L calculations
-- ============================================================================
CREATE TABLE results (
    result_id SERIAL PRIMARY KEY,
    game_id INTEGER NOT NULL REFERENCES games(game_id) ON DELETE CASCADE,
    
    outcome VARCHAR(5) NOT NULL,
    home_score INTEGER NOT NULL,
    away_score INTEGER NOT NULL,
    
    user_bet_id INTEGER REFERENCES bets(bet_id) ON DELETE SET NULL,
    ai_bet_id INTEGER REFERENCES bets(bet_id) ON DELETE SET NULL,
    
    user_pnl DECIMAL(10, 2),
    ai_pnl DECIMAL(10, 2),
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT valid_outcome CHECK (outcome IN ('1', 'x', '2')),
    CONSTRAINT valid_scores CHECK (home_score >= 0 AND away_score >= 0),
    CONSTRAINT unique_game_result UNIQUE (game_id)
);

CREATE INDEX idx_results_game ON results(game_id);

COMMENT ON COLUMN results.user_pnl IS 'Win: stake × odds - stake; Loss: -stake';

-- ============================================================================
-- TRIGGERS: Auto-update updated_at timestamps
-- ============================================================================

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_teams_updated_at
    BEFORE UPDATE ON teams
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_games_updated_at
    BEFORE UPDATE ON games
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_betting_lines_updated_at
    BEFORE UPDATE ON betting_lines
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- Schema version tracking
-- ============================================================================
CREATE TABLE schema_version (
    version VARCHAR(20) PRIMARY KEY,
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    description TEXT
);

INSERT INTO schema_version (version, description) 
VALUES ('1.0', 'Simplified schema: 7 core tables, essential indexes only');
