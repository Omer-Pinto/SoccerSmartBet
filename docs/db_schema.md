# SoccerSmartBet Database Schema

**Version:** 1.1 (Simplified)  
**Tables:** 5 core tables for daily betting

---

## Design Philosophy

This schema supports **daily betting workflow**, not historical sports tracking:
- Today's games selected → odds fetched → AI reports generated → bets placed → results calculated → P&L updated
- **No historical game-by-game storage** - only cumulative P&L totals
- **No team master data** - team names are simple VARCHAR fields
- **Minimal indexes** - add more when queries prove they're needed

---

## Tables

### 1. games
Today's selected games with odds and results merged in.

**Key columns:**
- `home_team`, `away_team` - VARCHAR (no FK to teams table)
- `n1`, `n2`, `n3` - Israeli Toto odds (home win, away win, draw)
- `venue` - Per-game venue (teams play at multiple stadiums)
- `outcome`, `home_score`, `away_score` - Filled when game completes

**Status flow:** pending → selected → processing → ready_for_betting → betting_open → betting_closed → completed

### 2. game_reports
AI-generated game analysis from Game Intelligence Agent (1 per game).

**Key columns:**
- `report_id` - UUID for parallel agent writes
- `h2h_insights`, `atmosphere_summary`, `weather_risk`, `venue_factors`

### 3. team_reports
AI-generated team analysis from Team Intelligence Agent (2 per game: home + away).

**Key columns:**
- `report_id` - UUID for parallel agent writes
- `team_name` - VARCHAR (not FK! No teams table)
- `form_trend`, `injury_impact`, `rotation_risk`, `key_players_status`

**Parallel writes:** UUID PKs + UNIQUE(game_id, team_name) allow 2 agents per game to write simultaneously.

### 4. bets
User and AI predictions for today's games.

**Rules:**
- 1 bet per bettor per game (UNIQUE constraint)
- Always 100 NIS stake (CHECK constraint)
- AI bets include justification TEXT

### 5. bankroll
Bankroll tracking (**just 2 rows!**).

**How it works:**
- Start: user=10,000 USD, ai=10,000 USD
- Each day: previous_bankroll + today's_profit = new_bankroll

**Example:**
- Day 1: User wins at 1.1 odds → profit = (1.1-1)×100 = +10 → bankroll = 10,010
- Day 1: AI loses → profit = -100 → bankroll = 9,900
- Day 2: User loses → profit = -100 → bankroll = 9,910
- Day 2: AI wins at 3.2 odds → profit = (3.2-1)×100 = +220 → bankroll = 10,120

---

## Key Design Decisions

**1. No teams table**
- Team names are just VARCHAR in games/team_reports
- Venue is per-game (Barcelona plays at 3 stadiums, Wembley hosts multiple teams)

**2. Odds merged into games**
- No separate betting_lines table - just n1/n2/n3 columns
- One set of odds per game (fetched from winner.co.il)

**3. Results merged into games**
- No separate results table - just outcome/home_score/away_score columns
- NULL until game completes

**4. Cumulative bankroll tracking only**
- bankroll stores running totals (2 rows, starting at 10,000 USD each)
- No historical game-by-game P&L tracking

**5. UUID for parallel writes**
- game_reports and team_reports use UUID PKs
- Agents generate IDs client-side, no DB sequence contention

**6. Israeli Toto notation**
- n1 = home win, n2 = away win, n3 = draw (not standard 1/X/2 order)

**7. Israeli Toto profit formula**
- Win: profit = (odds - 1) × stake
  - Example: 100 stake at 1.1 odds → profit = (1.1 - 1) × 100 = **+10 USD**
  - Example: 100 stake at 2.1 odds → profit = (2.1 - 1) × 100 = **+110 USD**
- Lose: profit = -stake
  - Example: 100 stake lost → profit = **-100 USD**

---

## Example Daily Workflow

**Pre-Gambling Flow:**
```sql
-- 1. Smart Game Picker inserts today's games
INSERT INTO games (match_date, home_team, away_team, league, venue, n1, n2, n3, status)
VALUES ('2025-11-27', 'Barcelona', 'Real Madrid', 'La Liga', 'Camp Nou', 2.10, 3.50, 3.40, 'selected');

-- 2. Game Intelligence Agent writes report
INSERT INTO game_reports (game_id, h2h_insights, atmosphere_summary, ...)
VALUES (1, 'Last 5 meetings...', 'Hostile crowd expected...', ...);

-- 3. Team Intelligence Agents write reports (parallel)
INSERT INTO team_reports (game_id, team_name, form_trend, injury_impact, ...)
VALUES (1, 'Barcelona', 'Improving...', 'Salah injured (critical)...', ...);
```

**Gambling Flow:**
```sql
-- User and AI place bets
INSERT INTO bets (game_id, bettor, prediction, odds, justification)
VALUES (1, 'user', '1', 2.10, NULL),
       (1, 'ai', 'x', 3.40, 'Weather risk increases draw probability...');
```

**Post-Games Flow:**
```sql
-- 1. Update game results
UPDATE games SET outcome = '1', home_score = 2, away_score = 1, status = 'completed'
WHERE game_id = 1;

-- 2. Calculate profit using Israeli Toto formula: (odds - 1) × stake
-- User bet on '1' (home win) at 2.10 odds and WON
UPDATE bankroll SET
    total_bankroll = total_bankroll + (2.10 - 1) * 100,  -- +110 profit
    games_played = games_played + 1,
    games_won = games_won + 1
WHERE bettor = 'user';
-- Result: 10,000 → 10,110

-- AI bet on 'x' (draw) at 3.40 odds and LOST
UPDATE bankroll SET
    total_bankroll = total_bankroll - 100,  -- Lost stake
    games_played = games_played + 1
WHERE bettor = 'ai';
-- Result: 10,000 → 9,900
```

---

## Schema Size
- **5 tables, ~150 lines of SQL**
- Fits in your head ✅
