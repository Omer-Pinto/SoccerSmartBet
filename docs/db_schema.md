# SoccerSmartBet Database Schema Documentation

**Version:** 1.0  
**Date:** 2025-11-21  
**RDBMS:** PostgreSQL 14+

---

## Table of Contents

1. [Overview](#overview)
2. [Entity-Relationship Diagram](#entity-relationship-diagram)
3. [Table Descriptions](#table-descriptions)
4. [Relationships](#relationships)
5. [Indexes Strategy](#indexes-strategy)
6. [Parallel Write Support](#parallel-write-support)
7. [Data Flow](#data-flow)
8. [Performance Considerations](#performance-considerations)
9. [Migration Strategy](#migration-strategy)

---

## Overview

The SoccerSmartBet database schema supports a **non-monetary AI soccer betting system** with four main application flows:

1. **Pre-Gambling Flow**: Daily game selection, data fetching, AI report generation
2. **Gambling Flow**: User and AI bet collection
3. **Post-Games Flow**: Results fetching and P&L calculation
4. **Offline Analysis Flow**: Historical analytics and statistics

### Key Design Principles

- **Relational Integrity**: Foreign keys enforce referential integrity across all tables
- **Performance**: Strategic indexes on frequently queried columns
- **Parallel Writes**: Support for concurrent agent writes to `game_reports` and `team_reports`
- **Audit Trail**: Timestamps (`created_at`, `updated_at`) on all mutable tables
- **Data Validation**: Check constraints for odds, scores, stakes, and enums
- **Flexibility**: JSONB columns for evolving data structures (data quality, game snapshots)

---

## Entity-Relationship Diagram

```
┌─────────────┐
│   teams     │
│─────────────│
│ team_id (PK)│◄──┐
│ name        │   │
│ league      │   │
│ venue       │   │
└─────────────┘   │
                  │
       ┌──────────┼──────────┐
       │          │          │
       │          │          │
┌──────▼──────┐   │   ┌──────▼──────┐
│   players   │   │   │    games    │
│─────────────│   │   │─────────────│
│player_id(PK)│   │   │ game_id (PK)│◄────┐
│team_id (FK) │───┘   │home_team(FK)│     │
│name         │       │away_team(FK)│     │
│is_key_player│       │match_date   │     │
└─────────────┘       │status       │     │
                      └──────┬──────┘     │
                             │            │
          ┌──────────────────┼────────────┼─────────────────┐
          │                  │            │                 │
          │                  │            │                 │
  ┌───────▼────────┐  ┌──────▼──────┐ ┌──▼──────────┐ ┌────▼─────┐
  │betting_lines   │  │game_reports │ │team_reports │ │   bets   │
  │────────────────│  │─────────────│ │─────────────│ │──────────│
  │line_id (PK)    │  │report_id(PK)│ │report_id(PK)│ │bet_id(PK)│
  │game_id (FK)    │  │game_id (FK) │ │game_id (FK) │ │game_id   │
  │n1, n2, n3      │  │h2h_insights │ │team_id (FK) │ │bettor    │
  │source          │  │atmosphere   │ │form_trend   │ │prediction│
  └────────────────┘  │weather_risk │ │injury_impact│ │odds      │
                      │venue_factors│ │rotation_risk│ └──────────┘
                      └─────────────┘ └─────────────┘       │
                                                             │
                      ┌──────────────────┐                  │
                      │unfiltered_games  │                  │
                      │──────────────────│                  │
                      │snapshot_id (PK)  │                  │
                      │snapshot_date     │                  │
                      │game_data (JSONB) │                  │
                      │was_selected      │                  │
                      └──────────────────┘                  │
                                                             │
                      ┌──────────────────┐                  │
                      │    results       │                  │
                      │──────────────────│                  │
                      │result_id (PK)    │                  │
                      │game_id (FK)      │◄─────────────────┘
                      │user_bet_id (FK)  │──────────────────┐
                      │ai_bet_id (FK)    │──────────────────┤
                      │outcome           │                  │
                      │user_pnl          │                  │
                      │ai_pnl            │                  │
                      └──────────────────┘                  │
                                                             │
                                         References bets ───┘
```

---

## Table Descriptions

### 1. `teams`

**Purpose:** Master data for football teams  
**Data Sources:** football-data.org, API-Football

| Column | Type | Description |
|--------|------|-------------|
| `team_id` | SERIAL (PK) | Internal unique identifier |
| `external_id` | VARCHAR(100) | ID from external API (e.g., 33 for Man United in API-Football) |
| `external_source` | VARCHAR(50) | API source name ('football-data', 'api-football') |
| `name` | VARCHAR(255) | Full team name |
| `short_name` | VARCHAR(100) | Abbreviated name |
| `league` | VARCHAR(100) | League name (Premier League, La Liga, etc.) |
| `venue` | VARCHAR(255) | Home stadium name |
| `city` | VARCHAR(100) | Team city |
| `country` | VARCHAR(100) | Country |
| `created_at` | TIMESTAMP | Record creation timestamp |
| `updated_at` | TIMESTAMP | Last update timestamp (auto-updated) |

**Constraints:**
- `UNIQUE (external_id, external_source)` - Prevents duplicate team imports

**Indexes:**
- `idx_teams_name` - Fast team name lookups
- `idx_teams_league` - League filtering
- `idx_teams_external` - API ID lookups

---

### 2. `players`

**Purpose:** Player roster for injury/suspension tracking  
**Data Sources:** API-Football sidelined endpoint

| Column | Type | Description |
|--------|------|-------------|
| `player_id` | SERIAL (PK) | Internal unique identifier |
| `external_id` | VARCHAR(100) | External API player ID |
| `external_source` | VARCHAR(50) | API source name |
| `team_id` | INTEGER (FK) | References `teams.team_id` |
| `name` | VARCHAR(255) | Player full name |
| `position` | VARCHAR(50) | Position (Goalkeeper, Defender, Midfielder, Forward) |
| `is_key_player` | BOOLEAN | Flag for critical players (affects injury impact analysis) |
| `created_at` | TIMESTAMP | Record creation timestamp |
| `updated_at` | TIMESTAMP | Last update timestamp |

**Constraints:**
- `FOREIGN KEY team_id REFERENCES teams ON DELETE CASCADE`
- `UNIQUE (external_id, external_source)`

**Indexes:**
- `idx_players_team` - Team roster queries
- `idx_players_key` - Partial index on key players only

**Critical for:** Team Intelligence Agent's **injury impact assessment** - must identify if injured players are starters vs bench warmers.

---

### 3. `games`

**Purpose:** Daily match fixtures and processing status  
**Data Sources:** football-data.org, API-Football

| Column | Type | Description |
|--------|------|-------------|
| `game_id` | SERIAL (PK) | Internal unique identifier |
| `external_id` | VARCHAR(100) | External API fixture ID |
| `external_source` | VARCHAR(50) | API source name |
| `match_date` | DATE | Match date |
| `kickoff_time` | TIME | Kickoff time |
| `timezone` | VARCHAR(50) | Timezone (default: UTC) |
| `home_team_id` | INTEGER (FK) | References `teams.team_id` |
| `away_team_id` | INTEGER (FK) | References `teams.team_id` |
| `league` | VARCHAR(100) | League name |
| `competition` | VARCHAR(255) | Competition name |
| `venue` | VARCHAR(255) | Stadium name |
| `status` | VARCHAR(50) | Processing status (see below) |
| `created_at` | TIMESTAMP | Record creation timestamp |
| `updated_at` | TIMESTAMP | Last update timestamp |

**Status Values:**
- `pending`: Initial state after Smart Game Picker selection
- `selected`: Passed odds filter from winner.co.il
- `filtered`: Did not meet minimum odds threshold
- `processing`: Reports being generated by agents
- `ready_for_betting`: Reports completed, ready for Gambling Flow
- `betting_open`: User/AI can place bets
- `betting_closed`: Deadline passed
- `in_progress`: Match started
- `completed`: Match finished, results available
- `cancelled`: Match cancelled (weather, etc.)

**Constraints:**
- `FOREIGN KEY home_team_id, away_team_id REFERENCES teams ON DELETE RESTRICT`
- `CHECK (home_team_id != away_team_id)` - Prevents team playing itself
- `CHECK status IN (...)` - Enforces valid status values

**Indexes:**
- `idx_games_date` - Daily game queries
- `idx_games_status` - Status-based filtering
- `idx_games_date_status` - **Composite index** for frequent daily + status queries
- `idx_games_active` - **Partial index** on active statuses only (performance optimization)

---

### 4. `betting_lines`

**Purpose:** Odds data from winner.co.il (Israeli Toto)  
**Data Source:** winner.co.il web scraping

| Column | Type | Description |
|--------|------|-------------|
| `line_id` | SERIAL (PK) | Internal unique identifier |
| `game_id` | INTEGER (FK) | References `games.game_id` |
| `n1` | DECIMAL(5,2) | Home win odds (e.g., 2.10) |
| `n2` | DECIMAL(5,2) | Away win odds (e.g., 3.50) |
| `n3` | DECIMAL(5,2) | Draw odds (e.g., 3.40) |
| `source` | VARCHAR(100) | Always 'winner.co.il' |
| `fetched_at` | TIMESTAMP | When odds were scraped |
| `created_at` | TIMESTAMP | Record creation timestamp |
| `updated_at` | TIMESTAMP | Last update timestamp |

**Constraints:**
- `FOREIGN KEY game_id REFERENCES games ON DELETE CASCADE`
- `CHECK (n1 > 1.0)` - Odds must be profitable
- `CHECK (n2 > 1.0)`
- `CHECK (n3 > 1.0)`

**Indexes:**
- `idx_betting_lines_game` - Game odds lookup
- `idx_betting_lines_fetched` - Temporal queries (most recent odds)

**Note:** Israeli Toto notation: n1=home, n2=away, n3=draw (different from standard 1/X/2 ordering)

---

### 5. `game_reports`

**Purpose:** AI-generated game analysis from Game Intelligence Agent  
**Data Sources:** API-Football H2H, venue data, Open-Meteo weather, news scraping

| Column | Type | Description |
|--------|------|-------------|
| `report_id` | UUID (PK) | Unique report identifier |
| `game_id` | INTEGER (FK) | References `games.game_id` |
| `h2h_insights` | TEXT | AI analysis of head-to-head patterns |
| `atmosphere_summary` | TEXT | Fan sentiment, crowd factors |
| `weather_risk` | TEXT | Cancellation risk, draw probability impact |
| `venue_factors` | TEXT | Home advantage, crowd size/hostility |
| `data_quality` | JSONB | Completeness tracking (e.g., {"h2h": "complete", "weather": "partial"}) |
| `agent_version` | VARCHAR(50) | Agent version for debugging |
| `llm_model` | VARCHAR(100) | LLM model used (e.g., 'gpt-4o-mini') |
| `processing_time_seconds` | DECIMAL(10,2) | Performance tracking |
| `created_at` | TIMESTAMP | Report creation timestamp |

**Constraints:**
- `FOREIGN KEY game_id REFERENCES games ON DELETE CASCADE`
- `UNIQUE (game_id)` - **One report per game**

**Indexes:**
- `idx_game_reports_game` - Game report lookup
- `idx_game_reports_quality` - **GIN index** on JSONB for data quality queries

**Parallel Write Support:** UUID primary key prevents conflicts when multiple Game Intelligence Agent instances write simultaneously (though typically 1:1 game:agent).

---

### 6. `team_reports`

**Purpose:** AI-generated team analysis from Team Intelligence Agent  
**Data Sources:** API-Football (form, injuries, suspensions), news scraping

| Column | Type | Description |
|--------|------|-------------|
| `report_id` | UUID (PK) | Unique report identifier |
| `game_id` | INTEGER (FK) | References `games.game_id` |
| `team_id` | INTEGER (FK) | References `teams.team_id` |
| `recovery_days` | INTEGER | Days since last match |
| `form_trend` | TEXT | AI assessment: "improving", "declining", "stable" + reasoning |
| `injury_impact` | TEXT | **Critical**: "critical starters missing" vs "minor depth issues" |
| `rotation_risk` | TEXT | Prediction based on upcoming fixtures |
| `key_players_status` | TEXT | Form assessment of top performers |
| `morale_stability` | TEXT | Sentiment from news (coach pressure, controversies) |
| `preparation_quality` | TEXT | Training/prep signals from news |
| `relevant_news` | TEXT | Betting-relevant news only (AI-filtered) |
| `data_quality` | JSONB | Completeness tracking |
| `agent_version` | VARCHAR(50) | Agent version |
| `llm_model` | VARCHAR(100) | LLM model used |
| `processing_time_seconds` | DECIMAL(10,2) | Performance tracking |
| `created_at` | TIMESTAMP | Report creation timestamp |

**Constraints:**
- `FOREIGN KEY game_id REFERENCES games ON DELETE CASCADE`
- `FOREIGN KEY team_id REFERENCES teams ON DELETE CASCADE`
- `UNIQUE (game_id, team_id)` - **One report per team per game**
- `CHECK (recovery_days >= 0)`

**Indexes:**
- `idx_team_reports_game` - Game-based queries
- `idx_team_reports_team` - Team history queries
- `idx_team_reports_game_team` - **Composite index** for efficient lookups
- `idx_team_reports_quality` - **GIN index** on JSONB

**Parallel Write Support:** **Critical design** - UUID primary keys + composite UNIQUE constraint allow **2 Team Intelligence Agents per game** (home + away) to write **simultaneously** without conflicts.

---

### 7. `unfiltered_games`

**Purpose:** Historical snapshot of ALL games considered by Smart Game Picker  
**Use Case:** Offline analysis of filtering decisions

| Column | Type | Description |
|--------|------|-------------|
| `snapshot_id` | SERIAL (PK) | Unique snapshot identifier |
| `snapshot_date` | DATE | Date of game selection run |
| `game_data` | JSONB | Full fixture data from API (flexible schema) |
| `was_selected` | BOOLEAN | Whether game passed filters |
| `filter_reason` | TEXT | Why excluded: "low_odds", "uninteresting_matchup", etc. |
| `picker_reasoning` | TEXT | AI justification from Smart Game Picker |
| `created_at` | TIMESTAMP | Snapshot timestamp |

**Indexes:**
- `idx_unfiltered_games_date` - Temporal queries
- `idx_unfiltered_games_selected` - Filter analysis
- `idx_unfiltered_games_data` - **GIN index** on JSONB for flexible queries

**Design Rationale:** JSONB allows storing full API responses without rigid schema, supporting future API changes and ad-hoc analysis.

---

### 8. `bets`

**Purpose:** User and AI betting predictions  
**Rules:** Single bets per game, 100 NIS stake

| Column | Type | Description |
|--------|------|-------------|
| `bet_id` | SERIAL (PK) | Unique bet identifier |
| `game_id` | INTEGER (FK) | References `games.game_id` |
| `bettor` | VARCHAR(10) | 'user' or 'ai' |
| `prediction` | VARCHAR(5) | '1' (home win), 'x' (draw), '2' (away win) |
| `odds` | DECIMAL(5,2) | Odds at time of bet placement |
| `stake` | DECIMAL(10,2) | Always 100.00 NIS |
| `justification` | TEXT | AI reasoning (empty for user bets) |
| `created_at` | TIMESTAMP | Bet placement timestamp |

**Constraints:**
- `FOREIGN KEY game_id REFERENCES games ON DELETE CASCADE`
- `CHECK bettor IN ('user', 'ai')`
- `CHECK prediction IN ('1', 'x', '2')`
- `CHECK (odds > 1.0)`
- `CHECK (stake = 100.00)` - **Enforces fixed stake rule**
- `UNIQUE (game_id, bettor)` - **One bet per bettor per game**

**Indexes:**
- `idx_bets_game` - Game bets lookup
- `idx_bets_bettor` - User vs AI analysis
- `idx_bets_created` - Temporal queries

---

### 9. `results`

**Purpose:** Match results and P&L calculations  
**Computed Fields:** `user_pnl`, `ai_pnl`

| Column | Type | Description |
|--------|------|-------------|
| `result_id` | SERIAL (PK) | Unique result identifier |
| `game_id` | INTEGER (FK) | References `games.game_id` |
| `outcome` | VARCHAR(5) | '1' (home win), 'x' (draw), '2' (away win) |
| `home_score` | INTEGER | Final home score |
| `away_score` | INTEGER | Final away score |
| `user_bet_id` | INTEGER (FK) | References `bets.bet_id` (nullable) |
| `ai_bet_id` | INTEGER (FK) | References `bets.bet_id` (nullable) |
| `user_pnl` | DECIMAL(10,2) | User profit/loss in NIS |
| `ai_pnl` | DECIMAL(10,2) | AI profit/loss in NIS |
| `created_at` | TIMESTAMP | Result entry timestamp |

**P&L Calculation:**
- **Win:** `pnl = stake × odds - stake` (e.g., 100 × 2.10 - 100 = 110 NIS profit)
- **Loss:** `pnl = -stake` (e.g., -100 NIS)

**Constraints:**
- `FOREIGN KEY game_id REFERENCES games ON DELETE CASCADE`
- `FOREIGN KEY user_bet_id, ai_bet_id REFERENCES bets ON DELETE SET NULL`
- `CHECK outcome IN ('1', 'x', '2')`
- `CHECK (home_score >= 0 AND away_score >= 0)`
- `UNIQUE (game_id)` - **One result per game**

**Indexes:**
- `idx_results_game` - Game result lookup
- `idx_results_outcome` - Outcome analysis
- `idx_results_created` - Temporal queries

---

## Relationships

### Primary Relationships

1. **teams → games** (1:N)
   - One team plays in many games (as home or away)
   - `games.home_team_id → teams.team_id`
   - `games.away_team_id → teams.team_id`
   - `ON DELETE RESTRICT` - Cannot delete team with existing games

2. **teams → players** (1:N)
   - One team has many players
   - `players.team_id → teams.team_id`
   - `ON DELETE CASCADE` - Delete players when team deleted

3. **games → betting_lines** (1:N)
   - One game can have multiple odds records (historical tracking)
   - `betting_lines.game_id → games.game_id`
   - `ON DELETE CASCADE`

4. **games → game_reports** (1:1)
   - One game has exactly one AI-generated report
   - `game_reports.game_id → games.game_id`
   - `UNIQUE (game_id)` enforces 1:1
   - `ON DELETE CASCADE`

5. **games → team_reports** (1:2)
   - One game has exactly **two** team reports (home + away)
   - `team_reports.game_id → games.game_id`
   - `team_reports.team_id → teams.team_id`
   - `UNIQUE (game_id, team_id)` enforces 1:2
   - `ON DELETE CASCADE`

6. **games → bets** (1:2)
   - One game can have up to 2 bets (user + AI)
   - `bets.game_id → games.game_id`
   - `UNIQUE (game_id, bettor)` enforces max 2
   - `ON DELETE CASCADE`

7. **games → results** (1:1)
   - One game has exactly one result record
   - `results.game_id → games.game_id`
   - `results.user_bet_id → bets.bet_id`
   - `results.ai_bet_id → bets.bet_id`
   - `UNIQUE (game_id)` enforces 1:1
   - `ON DELETE CASCADE` for game, `ON DELETE SET NULL` for bets

### Referential Integrity Strategy

- **CASCADE**: Child records deleted when parent deleted (reports, bets, betting_lines)
- **RESTRICT**: Prevents parent deletion if children exist (teams with games)
- **SET NULL**: Orphans child records but preserves them (results when bets deleted)

---

## Indexes Strategy

### Index Types Used

1. **B-Tree Indexes** (default)
   - Single column: `idx_games_date`, `idx_teams_name`
   - Composite: `idx_games_date_status`, `idx_team_reports_game_team`

2. **GIN Indexes** (JSONB)
   - `idx_game_reports_quality ON (data_quality)`
   - `idx_unfiltered_games_data ON (game_data)`

3. **Partial Indexes** (filtered)
   - `idx_games_active WHERE status IN (...)` - Only active games
   - `idx_players_key WHERE is_key_player = TRUE` - Only key players

### Query Performance Targets

| Query Type | Target | Index |
|------------|--------|-------|
| Today's games | <10ms | `idx_games_date_status` |
| Game reports lookup | <5ms | `idx_game_reports_game` |
| Team reports for game | <5ms | `idx_team_reports_game_team` |
| Daily P&L summary | <50ms | `idx_results_created`, view materialization |
| Team injury list | <10ms | `idx_players_team` |

### Index Maintenance

- PostgreSQL auto-vacuum handles index maintenance
- Monitor index usage with `pg_stat_user_indexes`
- Drop unused indexes if identified

---

## Parallel Write Support

### Challenge

Pre-Gambling Flow runs **parallel subgraphs**:
- **N Game Intelligence Agents** writing to `game_reports` (1 per selected game)
- **2N Team Intelligence Agents** writing to `team_reports` (2 per game: home + away)

### Solution

1. **UUID Primary Keys**
   - `game_reports.report_id` = UUID (not SERIAL)
   - `team_reports.report_id` = UUID (not SERIAL)
   - **Benefit:** Agents generate unique IDs client-side, no DB sequence contention

2. **Unique Constraints**
   - `game_reports`: `UNIQUE (game_id)` prevents duplicate game reports
   - `team_reports`: `UNIQUE (game_id, team_id)` prevents duplicate team reports
   - **Benefit:** Database enforces 1 report per game, 2 reports per game (home+away)

3. **Conflict Handling**
   - Use `INSERT ... ON CONFLICT DO UPDATE` for idempotent writes
   - If agent retries, update existing report instead of failing

### Example Parallel Write Pattern

```python
# Team Intelligence Agent writes to DB
import uuid

def write_team_report(game_id, team_id, report_data):
    report_id = uuid.uuid4()
    
    query = """
        INSERT INTO team_reports (
            report_id, game_id, team_id, 
            form_trend, injury_impact, ...
        )
        VALUES (%s, %s, %s, %s, %s, ...)
        ON CONFLICT (game_id, team_id) 
        DO UPDATE SET
            form_trend = EXCLUDED.form_trend,
            injury_impact = EXCLUDED.injury_impact,
            ...
    """
    
    execute(query, [report_id, game_id, team_id, ...])
```

**Result:** 2N agents can write simultaneously without deadlocks or conflicts.

---

## Data Flow

### Pre-Gambling Flow

```
1. Smart Game Picker
   ↓ writes
   [unfiltered_games] (all considered games)
   ↓ selects
   [games] (status='pending')

2. Fetch Lines from winner.co.il
   ↓ writes
   [betting_lines] (n1, n2, n3)
   ↓ filters
   [games] (status='selected' if odds >= threshold, else 'filtered')

3. Game Intelligence Agents (parallel)
   ↓ write
   [game_reports] (1 per game)

4. Team Intelligence Agents (parallel)
   ↓ write
   [team_reports] (2 per game: home + away)

5. Combine Results
   ↓ updates
   [games] (status='ready_for_betting')
```

### Gambling Flow

```
1. Fetch Games
   ↓ reads
   [games WHERE status='ready_for_betting']
   [game_reports], [team_reports]

2. User + AI Bet Collection
   ↓ writes
   [bets] (user bet)
   [bets] (ai bet)

3. Validator
   ↓ updates
   [games] (status='betting_open' or 'betting_closed')
```

### Post-Games Flow

```
1. Fetch Results
   ↓ reads
   [games WHERE status='betting_closed']

2. Scrape Results
   ↓ writes
   [results] (outcome, home_score, away_score)

3. Calculate P&L
   ↓ updates
   [results] (user_pnl, ai_pnl)
   [games] (status='completed')
```

### Offline Analysis Flow

```
1. Query DB
   ↓ reads
   [results], [bets], [games], [teams]
   ↓ uses
   [daily_pnl_summary] view

2. AI Analytics Agent
   ↓ generates insights
   (no DB writes, read-only)
```

---

## Performance Considerations

### Query Optimization

1. **Use Composite Indexes**
   - `idx_games_date_status` for `WHERE match_date = X AND status = Y`
   - Avoids index merging overhead

2. **Leverage Partial Indexes**
   - `idx_games_active` only indexes active games
   - 50-80% smaller than full index, faster writes

3. **JSONB Query Optimization**
   - GIN indexes on `data_quality` columns
   - Use `->` and `->>` operators efficiently
   - Example: `data_quality->>'h2h' = 'complete'`

4. **Use Views for Complex Queries**
   - `games_ready_for_betting` pre-joins games + teams + odds + reports
   - `daily_pnl_summary` aggregates results by date
   - Consider **materialized views** for heavy analytics (refresh strategy needed)

### Write Performance

1. **Batch Inserts**
   - Insert multiple `unfiltered_games` in one transaction
   - Use `COPY` for bulk imports

2. **Connection Pooling**
   - Use pgBouncer or SQLAlchemy connection pooling
   - Avoids connection overhead for parallel agents

3. **Avoid N+1 Queries**
   - Pre-fetch related data with JOINs
   - Example: Fetch games with teams in one query, not per-game team queries

### Database Sizing

**Estimated Growth (1 year):**
- Games: ~3 games/day × 365 = ~1,100 rows (negligible)
- Team Reports: ~6 reports/day × 365 = ~2,200 rows (text-heavy, ~5MB)
- Game Reports: ~3 reports/day × 365 = ~1,100 rows (~3MB)
- Bets: ~6 bets/day × 365 = ~2,200 rows (negligible)
- Results: ~3 results/day × 365 = ~1,100 rows (negligible)

**Total estimated DB size after 1 year:** <50MB (excluding unfiltered_games JSONB bloat)

**Recommendation:** No partitioning needed for first year. Consider time-series partitioning if scaling to 10+ games/day.

---

## Migration Strategy

### Initial Deployment

1. Run `schema.sql` on staging environment
2. Test data insertion with mock data
3. Verify indexes with `EXPLAIN ANALYZE`
4. Run on production environment

### Future Migrations

1. Use `db/migrations/` directory with numbered files:
   - `001_initial_schema.sql`
   - `002_add_player_nationality.sql`
   - `003_add_game_importance_score.sql`

2. Track applied migrations in `schema_version` table

3. Use migration tools (optional):
   - Alembic (Python)
   - Flyway (Java)
   - Custom Python script

### Backward Compatibility

- **Additive changes** (new columns): Safe, no app changes needed
- **Column renames**: Requires app code updates, deploy app first
- **Column deletions**: Deploy app updates first, then drop columns
- **Table renames/deletions**: Coordinate with all flows

### Rollback Strategy

- Keep migration rollback scripts: `002_add_player_nationality_rollback.sql`
- Test rollbacks in staging before production deployments
- Backup database before schema changes (automated)

---

## Security Considerations

### Access Control

```sql
-- Example role-based access (adjust for production)
CREATE ROLE soccersmartbet_app WITH LOGIN PASSWORD 'secure_password';
CREATE ROLE soccersmartbet_readonly WITH LOGIN PASSWORD 'readonly_password';

-- Application role: read/write
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO soccersmartbet_app;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO soccersmartbet_app;

-- Analytics role: read-only
GRANT SELECT ON ALL TABLES IN SCHEMA public TO soccersmartbet_readonly;
```

### Data Protection

1. **No PII**: System does not store personal user data (anonymous betting simulation)
2. **Connection Encryption**: Use SSL/TLS for database connections
3. **Password Management**: Never hardcode passwords, use environment variables
4. **Backup Encryption**: Encrypt database backups at rest

### SQL Injection Prevention

- **Always use parameterized queries** (prepared statements)
- Example (Python with psycopg2):
  ```python
  cursor.execute("SELECT * FROM games WHERE game_id = %s", [game_id])
  ```
- **Never concatenate SQL strings** with user input

---

## Troubleshooting

### Common Issues

1. **Foreign Key Violations**
   - **Error:** `insert or update on table "games" violates foreign key constraint`
   - **Solution:** Ensure referenced team exists in `teams` before inserting game

2. **Unique Constraint Violations**
   - **Error:** `duplicate key value violates unique constraint "unique_game_report"`
   - **Solution:** Check if report already exists, use `ON CONFLICT DO UPDATE`

3. **Check Constraint Violations**
   - **Error:** `new row violates check constraint "fixed_stake"`
   - **Solution:** Ensure stake is exactly 100.00 NIS

4. **Slow Queries**
   - **Symptom:** Queries taking >100ms
   - **Diagnosis:** Run `EXPLAIN ANALYZE` on slow query
   - **Solution:** Add missing index or optimize query

### Monitoring Queries

```sql
-- Check index usage
SELECT 
    schemaname, tablename, indexname, idx_scan, idx_tup_read, idx_tup_fetch
FROM pg_stat_user_indexes
ORDER BY idx_scan DESC;

-- Find unused indexes (idx_scan = 0)
SELECT indexname FROM pg_stat_user_indexes WHERE idx_scan = 0;

-- Table sizes
SELECT 
    tablename,
    pg_size_pretty(pg_total_relation_size(tablename::regclass)) AS size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(tablename::regclass) DESC;
```

---

## Appendix: Sample Queries

### Query 1: Get Today's Games Ready for Betting

```sql
SELECT * FROM games_ready_for_betting
WHERE match_date = CURRENT_DATE;
```

### Query 2: Fetch Complete Report for a Game

```sql
SELECT 
    g.game_id,
    ht.name AS home_team,
    at.name AS away_team,
    g.match_date,
    g.kickoff_time,
    bl.n1, bl.n2, bl.n3,
    gr.h2h_insights,
    gr.atmosphere_summary,
    gr.weather_risk,
    tr_home.form_trend AS home_form,
    tr_home.injury_impact AS home_injuries,
    tr_away.form_trend AS away_form,
    tr_away.injury_impact AS away_injuries
FROM games g
JOIN teams ht ON g.home_team_id = ht.team_id
JOIN teams at ON g.away_team_id = at.team_id
LEFT JOIN betting_lines bl ON g.game_id = bl.game_id
LEFT JOIN game_reports gr ON g.game_id = gr.game_id
LEFT JOIN team_reports tr_home ON g.game_id = tr_home.game_id AND g.home_team_id = tr_home.team_id
LEFT JOIN team_reports tr_away ON g.game_id = tr_away.game_id AND g.away_team_id = tr_away.team_id
WHERE g.game_id = $1;
```

### Query 3: User vs AI Performance (All Time)

```sql
SELECT 
    COUNT(r.result_id) AS total_games,
    SUM(CASE WHEN r.user_pnl > 0 THEN 1 ELSE 0 END) AS user_wins,
    SUM(CASE WHEN r.ai_pnl > 0 THEN 1 ELSE 0 END) AS ai_wins,
    SUM(r.user_pnl) AS user_total_pnl,
    SUM(r.ai_pnl) AS ai_total_pnl,
    AVG(r.user_pnl) AS user_avg_pnl,
    AVG(r.ai_pnl) AS ai_avg_pnl
FROM results r;
```

### Query 4: Games with Missing Reports (Data Quality Check)

```sql
SELECT 
    g.game_id,
    g.match_date,
    ht.name AS home_team,
    at.name AS away_team,
    EXISTS(SELECT 1 FROM game_reports WHERE game_id = g.game_id) AS has_game_report,
    (SELECT COUNT(*) FROM team_reports WHERE game_id = g.game_id) AS team_reports_count
FROM games g
JOIN teams ht ON g.home_team_id = ht.team_id
JOIN teams at ON g.away_team_id = at.team_id
WHERE g.status = 'selected'
AND (
    NOT EXISTS(SELECT 1 FROM game_reports WHERE game_id = g.game_id)
    OR (SELECT COUNT(*) FROM team_reports WHERE game_id = g.game_id) < 2
);
```

### Query 5: Top Performing Leagues (by AI win rate)

```sql
SELECT 
    g.league,
    COUNT(r.result_id) AS games_count,
    SUM(CASE WHEN r.ai_pnl > 0 THEN 1 ELSE 0 END)::FLOAT / COUNT(r.result_id) AS ai_win_rate,
    SUM(r.ai_pnl) AS ai_total_pnl
FROM results r
JOIN games g ON r.game_id = g.game_id
GROUP BY g.league
HAVING COUNT(r.result_id) >= 5
ORDER BY ai_win_rate DESC;
```

---

## Conclusion

This PostgreSQL schema provides a **robust, performant, and scalable foundation** for the SoccerSmartBet system. Key highlights:

✅ **Relational integrity** with foreign keys and constraints  
✅ **Performance-optimized** with strategic indexes  
✅ **Parallel write support** for AI agent workflows  
✅ **Audit trail** with timestamps on all tables  
✅ **Flexible data structures** with JSONB for evolving needs  
✅ **Production-ready** with views, triggers, and security considerations

**Next Steps:**
1. Deploy to staging environment via Docker Compose (Task 1.4)
2. Implement database access layer in Python (SQLAlchemy or psycopg2)
3. Create seed data for testing
4. Instrument schema with LangSmith tracing for query performance

---

**Document Version:** 1.0  
**Last Updated:** 2025-11-21  
**Author:** Infrastructure Droid
