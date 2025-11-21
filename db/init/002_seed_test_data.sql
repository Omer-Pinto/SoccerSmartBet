-- ============================================================================
-- SoccerSmartBet Test Data Seed
-- ============================================================================
-- Purpose: Optional test data for development/testing
-- Usage: Automatically loaded on first database initialization
-- Note: This file runs AFTER 001_create_schema.sql
-- ============================================================================

-- Insert test teams
INSERT INTO teams (external_id, external_source, name, short_name, league, venue, city, country) VALUES
    ('33', 'api-football', 'Manchester United', 'Man United', 'Premier League', 'Old Trafford', 'Manchester', 'England'),
    ('40', 'api-football', 'Liverpool', 'Liverpool', 'Premier League', 'Anfield', 'Liverpool', 'England'),
    ('50', 'api-football', 'Manchester City', 'Man City', 'Premier League', 'Etihad Stadium', 'Manchester', 'England'),
    ('42', 'api-football', 'Arsenal', 'Arsenal', 'Premier League', 'Emirates Stadium', 'London', 'England'),
    ('49', 'api-football', 'Chelsea', 'Chelsea', 'Premier League', 'Stamford Bridge', 'London', 'England'),
    ('47', 'api-football', 'Tottenham', 'Spurs', 'Premier League', 'Tottenham Hotspur Stadium', 'London', 'England'),
    ('529', 'api-football', 'Barcelona', 'Barcelona', 'La Liga', 'Camp Nou', 'Barcelona', 'Spain'),
    ('541', 'api-football', 'Real Madrid', 'Real Madrid', 'La Liga', 'Santiago Bernabéu', 'Madrid', 'Spain'),
    ('157', 'api-football', 'Bayern Munich', 'Bayern', 'Bundesliga', 'Allianz Arena', 'Munich', 'Germany'),
    ('165', 'api-football', 'Borussia Dortmund', 'BVB', 'Bundesliga', 'Signal Iduna Park', 'Dortmund', 'Germany')
ON CONFLICT (external_id, external_source) DO NOTHING;

-- Insert test players (key players for injury impact testing)
INSERT INTO players (external_id, external_source, team_id, name, position, is_key_player) VALUES
    ('1100', 'api-football', (SELECT team_id FROM teams WHERE name = 'Manchester United'), 'Bruno Fernandes', 'Midfielder', TRUE),
    ('1101', 'api-football', (SELECT team_id FROM teams WHERE name = 'Manchester United'), 'Marcus Rashford', 'Forward', TRUE),
    ('1200', 'api-football', (SELECT team_id FROM teams WHERE name = 'Liverpool'), 'Mohamed Salah', 'Forward', TRUE),
    ('1201', 'api-football', (SELECT team_id FROM teams WHERE name = 'Liverpool'), 'Virgil van Dijk', 'Defender', TRUE),
    ('1300', 'api-football', (SELECT team_id FROM teams WHERE name = 'Manchester City'), 'Erling Haaland', 'Forward', TRUE),
    ('1301', 'api-football', (SELECT team_id FROM teams WHERE name = 'Manchester City'), 'Kevin De Bruyne', 'Midfielder', TRUE),
    ('1400', 'api-football', (SELECT team_id FROM teams WHERE name = 'Arsenal'), 'Bukayo Saka', 'Forward', TRUE),
    ('1401', 'api-football', (SELECT team_id FROM teams WHERE name = 'Arsenal'), 'Martin Ødegaard', 'Midfielder', TRUE),
    ('1500', 'api-football', (SELECT team_id FROM teams WHERE name = 'Real Madrid'), 'Vinícius Júnior', 'Forward', TRUE),
    ('1501', 'api-football', (SELECT team_id FROM teams WHERE name = 'Real Madrid'), 'Jude Bellingham', 'Midfielder', TRUE)
ON CONFLICT (external_id, external_source) DO NOTHING;

-- Insert test games (upcoming fixtures)
INSERT INTO games (
    external_id, 
    external_source, 
    match_date, 
    kickoff_time, 
    home_team_id, 
    away_team_id, 
    league, 
    competition, 
    venue,
    status
) VALUES
    (
        '12345', 
        'api-football', 
        CURRENT_DATE + INTERVAL '1 day', 
        '15:00:00', 
        (SELECT team_id FROM teams WHERE name = 'Manchester United'),
        (SELECT team_id FROM teams WHERE name = 'Liverpool'),
        'Premier League',
        'Premier League 2024/25',
        'Old Trafford',
        'pending'
    ),
    (
        '12346', 
        'api-football', 
        CURRENT_DATE + INTERVAL '1 day', 
        '17:30:00', 
        (SELECT team_id FROM teams WHERE name = 'Manchester City'),
        (SELECT team_id FROM teams WHERE name = 'Arsenal'),
        'Premier League',
        'Premier League 2024/25',
        'Etihad Stadium',
        'pending'
    ),
    (
        '12347', 
        'api-football', 
        CURRENT_DATE + INTERVAL '2 days', 
        '20:00:00', 
        (SELECT team_id FROM teams WHERE name = 'Real Madrid'),
        (SELECT team_id FROM teams WHERE name = 'Barcelona'),
        'La Liga',
        'La Liga 2024/25',
        'Santiago Bernabéu',
        'pending'
    )
ON CONFLICT (external_id, external_source) DO NOTHING;

-- Insert test betting lines
INSERT INTO betting_lines (game_id, n1, n2, n3, source) VALUES
    (
        (SELECT game_id FROM games WHERE external_id = '12345'),
        2.10, -- Man United win
        3.80, -- Liverpool win
        3.40  -- Draw
    ),
    (
        (SELECT game_id FROM games WHERE external_id = '12346'),
        1.85, -- Man City win
        4.20, -- Arsenal win
        3.60  -- Draw
    ),
    (
        (SELECT game_id FROM games WHERE external_id = '12347'),
        2.30, -- Real Madrid win
        3.20, -- Barcelona win
        3.50  -- Draw
    )
ON CONFLICT DO NOTHING;

-- Insert test game reports (simulating Game Intelligence Agent output)
INSERT INTO game_reports (
    game_id,
    h2h_insights,
    atmosphere_summary,
    weather_risk,
    venue_factors,
    data_quality,
    agent_version,
    llm_model,
    processing_time_seconds
) VALUES
    (
        (SELECT game_id FROM games WHERE external_id = '12345'),
        'Manchester United and Liverpool have a fierce rivalry. Last 5 meetings: 2 United wins, 2 Liverpool wins, 1 draw. High-scoring tendency with 3+ goals in 4 of last 5 encounters.',
        'Historic rivalry ensures hostile atmosphere at Old Trafford. Expect 75,000+ passionate fans creating significant home advantage. Security heightened for this fixture.',
        'Clear weather forecast, no cancellation risk. Dry pitch favors attacking play.',
        'Old Trafford packed to capacity. Hostile environment for Liverpool, historically boosts United performance by 15-20% in betting odds accuracy.',
        '{"h2h": "complete", "weather": "complete", "news": "complete", "venue": "complete"}',
        '1.0',
        'gpt-4o-mini',
        8.5
    ),
    (
        (SELECT game_id FROM games WHERE external_id = '12346'),
        'City dominant in recent meetings with 4 wins in last 5. Arsenal growing competitive but still trailing head-to-head record.',
        'Title race implications create intense atmosphere. Etihad crowd will be loud but Arsenal traveling support also significant.',
        'Overcast but dry, no weather concerns.',
        'Etihad advantage for City, though Arsenal has improved away record this season.',
        '{"h2h": "complete", "weather": "complete", "news": "partial", "venue": "complete"}',
        '1.0',
        'gpt-4o-mini',
        7.2
    )
ON CONFLICT (game_id) DO NOTHING;

-- Insert test team reports (simulating Team Intelligence Agent output)
INSERT INTO team_reports (
    game_id,
    team_id,
    recovery_days,
    form_trend,
    injury_impact,
    rotation_risk,
    key_players_status,
    morale_stability,
    preparation_quality,
    relevant_news,
    data_quality,
    agent_version,
    llm_model,
    processing_time_seconds
) VALUES
    -- Manchester United report
    (
        (SELECT game_id FROM games WHERE external_id = '12345'),
        (SELECT team_id FROM teams WHERE name = 'Manchester United'),
        4,
        'Improving: 3 wins in last 5 games, scoring freely (12 goals). Defensive solidity returning.',
        'Minor depth issues: backup goalkeeper questionable. Key starters Bruno Fernandes and Rashford fully fit.',
        'Low rotation risk: Important fixture, full-strength lineup expected. Next match in 6 days allows recovery.',
        'Bruno Fernandes excellent form: 3 goals, 2 assists in last 5. Rashford finding rhythm with 4 goals.',
        'High morale after recent wins. Manager under less pressure, squad confident.',
        'Full training attendance reported. Tactical prep focused on Liverpool counter-attacks.',
        'No distractions. Focused preparation for crucial rivalry match.',
        '{"form": "complete", "injuries": "complete", "news": "complete", "rotation": "complete"}',
        '1.0',
        'gpt-4o-mini',
        12.3
    ),
    -- Liverpool report
    (
        (SELECT game_id FROM games WHERE external_id = '12345'),
        (SELECT team_id FROM teams WHERE name = 'Liverpool'),
        3,
        'Stable: 2 wins, 2 draws, 1 loss in last 5. Consistent but not dominant.',
        'CRITICAL: Mohamed Salah nursing minor knock (75% chance to play). Virgil van Dijk suspended (yellow card accumulation). Missing key defensive leader.',
        'Medium rotation risk: Champions League match in 4 days may influence selection. Possible rest for midfielders.',
        'Salah form excellent if fit (5 goals in last 5). Concern over defensive organization without Van Dijk.',
        'Moderate morale: Recent draw dented confidence. Manager under scrutiny for defensive tactics.',
        'Training reports mixed: Salah participated in light session only. Defensive drills emphasized.',
        'Media speculation about Salah fitness. Manager downplaying concerns but injury impact significant.',
        '{"form": "complete", "injuries": "complete", "news": "complete", "rotation": "partial"}',
        '1.0',
        'gpt-4o-mini',
        14.8
    ),
    -- Manchester City report
    (
        (SELECT game_id FROM games WHERE external_id = '12346'),
        (SELECT team_id FROM teams WHERE name = 'Manchester City'),
        5,
        'Dominant: 4 wins, 1 draw in last 5. Scoring at will (18 goals). Best form in league.',
        'Full strength: No key injuries. Haaland and De Bruyne both fit and firing.',
        'Very low rotation risk: Title race implications mean strongest XI will start.',
        'Haaland in incredible form: 7 goals in last 5 games. De Bruyne creating chances at elite rate.',
        'Sky-high morale: Team believes they are unstoppable. Manager confident in tactics.',
        'Perfect preparation: All players available, tactical clarity in training.',
        'No concerns. Team focused and ready for title showdown.',
        '{"form": "complete", "injuries": "complete", "news": "complete", "rotation": "complete"}',
        '1.0',
        'gpt-4o-mini',
        11.5
    ),
    -- Arsenal report
    (
        (SELECT game_id FROM games WHERE external_id = '12346'),
        (SELECT team_id FROM teams WHERE name = 'Arsenal'),
        4,
        'Improving: 3 wins in last 5, growing confidence. Young squad maturing.',
        'Minor issue: Backup defender out, but starters all fit. Saka and Ødegaard healthy.',
        'Low rotation risk for this crucial title race match. Will play strongest team.',
        'Saka excellent: 3 goals, 4 assists in last 5. Ødegaard orchestrating attacks brilliantly.',
        'High morale: Team believes they can challenge City. Manager praising squad mentality.',
        'Strong preparation: Focus on defensive compactness against City attack.',
        'Positive media coverage. Squad unity strong, no distractions.',
        '{"form": "complete", "injuries": "complete", "news": "complete", "rotation": "complete"}',
        '1.0',
        'gpt-4o-mini',
        13.2
    )
ON CONFLICT (game_id, team_id) DO NOTHING;

-- Insert test bets (simulating user and AI predictions)
INSERT INTO bets (game_id, bettor, prediction, odds, stake, justification) VALUES
    (
        (SELECT game_id FROM games WHERE external_id = '12345'),
        'user',
        '1', -- Manchester United win
        2.10,
        100.00,
        NULL -- Users don't provide justification
    ),
    (
        (SELECT game_id FROM games WHERE external_id = '12345'),
        'ai',
        'x', -- Draw
        3.40,
        100.00,
        'Liverpool missing Van Dijk (key defender) and Salah questionable. United in good form but Liverpool resilient. High-stakes rivalry often produces tight draws. Weather and venue favor neither side decisively.'
    ),
    (
        (SELECT game_id FROM games WHERE external_id = '12346'),
        'user',
        '2', -- Arsenal win
        4.20,
        100.00,
        NULL
    ),
    (
        (SELECT game_id FROM games WHERE external_id = '12346'),
        'ai',
        '1', -- Manchester City win
        1.85,
        100.00,
        'City in exceptional form (4 wins in last 5, 18 goals). Haaland unstoppable (7 goals). Arsenal improving but City superior head-to-head. Home advantage at Etihad significant. Low value odds but high confidence prediction.'
    )
ON CONFLICT (game_id, bettor) DO NOTHING;

-- ============================================================================
-- Verification Queries (commented out - uncomment to test)
-- ============================================================================

-- SELECT COUNT(*) AS teams_count FROM teams;
-- SELECT COUNT(*) AS players_count FROM players;
-- SELECT COUNT(*) AS games_count FROM games;
-- SELECT COUNT(*) AS betting_lines_count FROM betting_lines;
-- SELECT COUNT(*) AS game_reports_count FROM game_reports;
-- SELECT COUNT(*) AS team_reports_count FROM team_reports;
-- SELECT COUNT(*) AS bets_count FROM bets;

-- View games ready for betting with all data
-- SELECT * FROM games_ready_for_betting;

-- ============================================================================
-- END OF TEST DATA
-- ============================================================================
