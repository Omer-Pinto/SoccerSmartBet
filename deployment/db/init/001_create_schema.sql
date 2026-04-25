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

    -- Live-score enrichment (populated by persist_games FotMob enrichment)
    fotmob_match_id BIGINT NULL,

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
--
-- Schema v2 — Wave 8B/8E. Migration applied to live DB on 2026-04-19.
-- H2H aggregate is keyed by today's team identity (historical roles discarded).
-- ============================================================================
CREATE TABLE game_reports (
    report_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    game_id INTEGER NOT NULL REFERENCES games(game_id) ON DELETE CASCADE,

    -- H2H aggregate (keyed by today's team identity; historical roles discarded)
    h2h_home_team TEXT,
    h2h_away_team TEXT,
    h2h_home_team_wins INTEGER,
    h2h_away_team_wins INTEGER,
    h2h_draws INTEGER,
    h2h_total_meetings INTEGER,
    h2h_bullets JSONB,

    -- Weather
    weather_bullets JSONB,
    weather_cancellation_risk TEXT,

    -- Venue (short stadium name only)
    venue TEXT,

    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT unique_game_report UNIQUE (game_id)
);

CREATE INDEX idx_game_reports_game ON game_reports(game_id);

COMMENT ON COLUMN game_reports.report_id IS 'UUID for parallel agent writes';
COMMENT ON COLUMN game_reports.h2h_bullets IS 'JSONB array of short analytical bullets (<=2, <=20 words each)';
COMMENT ON COLUMN game_reports.weather_bullets IS 'JSONB array of weather bullets (<=3, <=20 words each)';
COMMENT ON COLUMN game_reports.weather_cancellation_risk IS 'low | medium | high | unknown';

-- ============================================================================
-- TABLE: team_reports
-- Purpose: AI-generated team analysis from Team Intelligence Agent
--
-- Schema v2 — Wave 8B/8E. Migration applied to live DB on 2026-04-19.
-- Structured facts (recovery, streak, last-5 rows, league snapshot) plus
-- short analytical bullets as JSONB arrays.
-- ============================================================================
CREATE TABLE team_reports (
    report_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    game_id INTEGER NOT NULL REFERENCES games(game_id) ON DELETE CASCADE,
    team_name VARCHAR(255) NOT NULL, -- Changed from team_id FK to VARCHAR!

    recovery_days INTEGER CHECK (recovery_days >= 0),
    form_streak VARCHAR(5),
    last_5_games JSONB,
    form_bullets JSONB,

    league_rank INTEGER,
    league_points INTEGER,
    league_matches_played INTEGER,
    league_bullets JSONB,

    injury_bullets JSONB,
    news_bullets JSONB,

    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT unique_team_game_report UNIQUE (game_id, team_name)
);

-- Minimal indexes
CREATE INDEX idx_team_reports_game ON team_reports(game_id);

COMMENT ON COLUMN team_reports.report_id IS 'UUID for parallel agent writes (2 per game: home + away)';
COMMENT ON COLUMN team_reports.team_name IS 'VARCHAR not FK - no teams table needed';
COMMENT ON COLUMN team_reports.form_streak IS '5-char streak, most recent LAST, ? for missing';
COMMENT ON COLUMN team_reports.last_5_games IS 'JSONB array of RecentMatch objects, most recent FIRST';
COMMENT ON COLUMN team_reports.form_bullets IS 'JSONB array of form bullets (<=2, <=12 words each)';
COMMENT ON COLUMN team_reports.league_bullets IS 'JSONB array of league/motivation bullets (<=3, <=20 words each)';
COMMENT ON COLUMN team_reports.injury_bullets IS 'JSONB array of impactful-injury bullets (<=5)';
COMMENT ON COLUMN team_reports.news_bullets IS 'JSONB array of pre-match news bullets (<=3, <=20 words each)';

-- ============================================================================
-- TABLE: expert_game_reports
-- Purpose: LLM-generated expert pre-match analysis synthesizing all intel
--
-- Schema v2 — Wave 8B/8E. Migration applied to live DB on 2026-04-19.
-- expert_analysis is a JSONB array of 3-6 bullets, <=20 words each.
-- ============================================================================
CREATE TABLE expert_game_reports (
    report_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    game_id INTEGER NOT NULL REFERENCES games(game_id) ON DELETE CASCADE,
    expert_analysis JSONB NOT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT unique_expert_game_report UNIQUE (game_id)
);
CREATE INDEX idx_expert_game_reports_game ON expert_game_reports(game_id);

COMMENT ON TABLE expert_game_reports IS 'Expert LLM pre-match analysis synthesizing game + team reports with odds';
COMMENT ON COLUMN expert_game_reports.expert_analysis IS 'JSONB array of bullets (3-6, <=20 words each)';

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
    stake DECIMAL(10,2) NOT NULL DEFAULT 100.00 CHECK (stake > 0),
    justification TEXT,
    result VARCHAR(5) CHECK (result IN ('1', 'x', '2')),
    pnl DECIMAL(10,2),

    CONSTRAINT unique_bet_per_game UNIQUE (game_id, bettor)
);

CREATE INDEX idx_bets_game ON bets(game_id);

COMMENT ON COLUMN bets.stake IS 'Variable stake in NIS (50/100/200/500 per gambling UI). Israeli Toto: profit = (odds - 1) * stake.';
COMMENT ON COLUMN bets.result IS 'Actual match outcome copied from games.outcome at post-games time';
COMMENT ON COLUMN bets.pnl IS 'Realized profit/loss in NIS. Won: stake*(odds-1). Lost: -stake.';

-- ============================================================================
-- TABLE: bankroll
-- Purpose: Bankroll tracking - each starts at 10,000 USD
-- ============================================================================
CREATE TABLE bankroll (
    bettor VARCHAR(10) PRIMARY KEY CHECK (bettor IN ('user', 'ai')),
    total_bankroll DECIMAL(10,2) NOT NULL DEFAULT 10000.00,
    games_played INTEGER NOT NULL DEFAULT 0,
    games_won INTEGER NOT NULL DEFAULT 0,
    games_lost INTEGER NOT NULL DEFAULT 0,
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

-- ============================================================================
-- TABLE: daily_runs
-- Purpose: Idempotency guard and startup recovery for the wall-clock scheduler
-- ============================================================================
CREATE TABLE daily_runs (
    run_date DATE PRIMARY KEY,
    pre_gambling_started_at TIMESTAMPTZ,
    pre_gambling_completed_at TIMESTAMPTZ,
    gambling_completed_at TIMESTAMPTZ,
    post_games_trigger_at TIMESTAMPTZ,
    post_games_completed_at TIMESTAMPTZ,
    game_ids INTEGER[],
    games_found INTEGER,
    user_bet_completed BOOLEAN DEFAULT FALSE,
    ai_bet_completed BOOLEAN DEFAULT FALSE,
    no_games_user_confirmed BOOLEAN
);

COMMENT ON TABLE daily_runs IS 'One row per day — tracks scheduler flow state for idempotency and crash recovery';
COMMENT ON COLUMN daily_runs.pre_gambling_started_at IS 'Set before run_pre_gambling_flow(); NULL means not yet started';
COMMENT ON COLUMN daily_runs.pre_gambling_completed_at IS 'Set after flow finishes; NULL with started_at set means crashed mid-run';
COMMENT ON COLUMN daily_runs.game_ids IS 'game_ids selected today; empty array means no-games day';
COMMENT ON COLUMN daily_runs.post_games_trigger_at IS 'max(kickoff_time) + 3h — calculated once when gambling completes';
COMMENT ON COLUMN daily_runs.games_found IS 'Number of games the pre-gambling picker found (before LLM selection)';
COMMENT ON COLUMN daily_runs.no_games_user_confirmed IS 'User response to no-games-day prompt: TRUE = expected, FALSE = suspicious';

-- ============================================================================
-- Wave 10 — Dashboard Platform Foundation
-- NOT YET APPLIED TO LIVE DB AS OF 2026-04-22.
-- Apply only after Omer's explicit OK via: docker exec soccersmartbet-staging psql ...
-- ============================================================================

ALTER TABLE daily_runs ADD COLUMN IF NOT EXISTS status VARCHAR(30) NOT NULL DEFAULT 'idle'
    CHECK (status IN ('idle', 'pre_gambling_running', 'pre_gambling_done',
                      'gambling_running', 'gambling_done',
                      'post_games_running', 'post_games_done', 'failed'));
ALTER TABLE daily_runs ADD COLUMN IF NOT EXISTS last_trigger_source VARCHAR(20);
ALTER TABLE daily_runs ADD COLUMN IF NOT EXISTS attempt_count INTEGER NOT NULL DEFAULT 1;
ALTER TABLE daily_runs ADD COLUMN IF NOT EXISTS last_error TEXT;

CREATE TABLE IF NOT EXISTS run_events (
    event_id      SERIAL PRIMARY KEY,
    run_date      DATE NOT NULL,
    event_type    VARCHAR(40) NOT NULL,
    triggered_by  VARCHAR(20) NOT NULL CHECK (triggered_by IN ('scheduler', 'manual', 'recovery')),
    triggered_at  TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    payload       JSONB
);
CREATE INDEX IF NOT EXISTS idx_run_events_date_time ON run_events(run_date, triggered_at);

CREATE TABLE IF NOT EXISTS bet_edits (
    edit_id    SERIAL PRIMARY KEY,
    bet_id     INTEGER NOT NULL REFERENCES bets(bet_id) ON DELETE CASCADE,
    field      VARCHAR(30) NOT NULL CHECK (field IN ('prediction', 'stake')),
    old_value  TEXT,
    new_value  TEXT,
    edited_at  TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    source     VARCHAR(20) NOT NULL DEFAULT 'dashboard'
);
CREATE INDEX IF NOT EXISTS idx_bet_edits_bet ON bet_edits(bet_id);

COMMENT ON TABLE run_events IS 'Append-only audit log. Intentionally NO FK to daily_runs(run_date) so events outlive their parent row (e.g. after manual purge). Orphan accumulation is bounded.';

CREATE INDEX IF NOT EXISTS idx_bets_bettor ON bets(bettor);
CREATE INDEX IF NOT EXISTS idx_games_league ON games(league);

-- ============================================================================
-- Wave 11A — Bet-edit window enforcement trigger
-- APPLIED TO LIVE DB 2026-04-22 (Wave 11) — trigger active on bet_edits.
-- ============================================================================

-- Function: raise exception if a bet_edits insert falls outside the edit window.
-- The edit window is: gambling_completed_at IS NOT NULL
--   AND kickoff_time - NOW() AT TIME ZONE 'Asia/Jerusalem' > INTERVAL '30 minutes'
CREATE OR REPLACE FUNCTION check_bet_edit_window()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
DECLARE
    v_game_id       INTEGER;
    v_match_date    DATE;
    v_kickoff_time  TIME;
    v_kickoff_dt    TIMESTAMPTZ;
    v_gambling_done TIMESTAMPTZ;
    v_now           TIMESTAMPTZ;
BEGIN
    -- Resolve the game for this bet
    SELECT b.game_id, g.match_date, g.kickoff_time
    INTO   v_game_id, v_match_date, v_kickoff_time
    FROM   bets b
    JOIN   games g ON g.game_id = b.game_id
    WHERE  b.bet_id = NEW.bet_id;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'bet_edits: bet_id % not found', NEW.bet_id;
    END IF;

    -- Build an ISR-aware kickoff timestamp
    v_kickoff_dt := (v_match_date::TEXT || ' ' || v_kickoff_time::TEXT)::TIMESTAMP
                    AT TIME ZONE 'Asia/Jerusalem';

    -- Check gambling_completed_at
    SELECT gambling_completed_at
    INTO   v_gambling_done
    FROM   daily_runs
    WHERE  run_date = v_match_date;

    IF v_gambling_done IS NULL THEN
        RAISE EXCEPTION
            'bet_edits: gambling phase not yet complete for % — edits not allowed',
            v_match_date;
    END IF;

    -- Check 30-minute window
    v_now := NOW();
    IF v_kickoff_dt - v_now <= INTERVAL '30 minutes' THEN
        RAISE EXCEPTION
            'bet_edits: edit window closed — kickoff at % ISR is within 30 minutes',
            TO_CHAR(v_kickoff_dt AT TIME ZONE 'Asia/Jerusalem', 'HH24:MI');
    END IF;

    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_bet_edit_window
BEFORE INSERT ON bet_edits
FOR EACH ROW
EXECUTE FUNCTION check_bet_edit_window();
