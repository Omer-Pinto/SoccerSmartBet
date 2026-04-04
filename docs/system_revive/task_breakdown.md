# SoccerSmartBet Revival — Task Breakdown

> **Created:** 2026-04-05 | **Status:** Draft | **Branch:** `revive`

## Guiding Principle

Every tool must be independently testable via the web app or CLI before being wired into LangGraph flows. Data source access is fragile — tools must handle failures gracefully and never crash the pipeline. The team name consistency layer underpins ALL tools and must be rock-solid before building flows.

---

## Wave 0 — Setup + Tools Curation (Orchestrator Only)

### 0.1 — Clean dead references + deps
- Remove `APIFOOTBALL_API_KEY` from `.env.example`
- Pin `langgraph>=1.0.0` in `pyproject.toml`
- Update `ORCHESTRATION_STATE.md` — mark Batch 6 as "REVERTED"
- `uv add asyncpg psycopg2-binary` (DB access from nodes)

### 0.2 — Tools curation session
Decide which data verticals make the cut. For each, evaluate:
- Source: which API/scraper provides it?
- Verified working? (actual test, not assumption)
- Effort to implement/fix
- Betting value to Omer (expert who already knows 80%)

**Verticals to evaluate:**

| # | Vertical | Current State | Source | Decision |
|---|----------|--------------|--------|----------|
| 1 | Daily fixtures | MISSING — no tool exists | football-data.org | |
| 2 | Odds (Israeli Toto) | NEW — winner.co.il discovered | winner.co.il API | |
| 3 | Odds (international) | WORKING | The Odds API | |
| 4 | H2H history | WORKING | football-data.org | |
| 5 | Venue info | BROKEN — FotMob 404 | FotMob new API (cracked) | |
| 6 | Weather | BROKEN — depends on venue | FotMob + Open-Meteo | |
| 7 | Team form (W/D/L) | BROKEN — FotMob 404 | FotMob new API | |
| 8 | Injuries/unavailable | BROKEN — FotMob 404 | FotMob new API | |
| 9 | League standings | BROKEN — FotMob 404 | FotMob new API | |
| 10 | Recovery time | BROKEN — FotMob 404 | FotMob new API | |
| 11 | Team news | PREVIOUSLY DISABLED — now available | FotMob `/api/data/tlnews` | |
| 12 | Player stats (per-match) | NEVER HAD | Sofascore (to verify) | |
| 13 | Player stats (season xG) | NEVER HAD | FBref scraping | |
| 14 | Suspension risk (yellows) | NEVER HAD | football-data.org / FotMob | |
| 15 | Fixture congestion | NEVER HAD | football-data.org | |
| 16 | Player ratings | NEVER HAD | Sofascore (to verify) | |
| 17 | Expected lineups | NEVER HAD | Scraping (high effort) | |
| 18 | Coach/locker room news | NEVER HAD | Scraping (fragile) | |

Omer decides which verticals are IN, which are OUT, which are STRETCH.
This decision shapes all subsequent waves.

### 0.3 — Schema update for team registry
Add `teams` table to `db/schema.sql`:
```sql
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
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_teams_canonical ON teams(canonical_name);
CREATE INDEX idx_teams_fotmob ON teams(fotmob_id);
```
Add to `deployment/db/init/001_create_schema.sql`.

### 0.4 — Verify enrichment sources (Sofascore, FBref)
Actually test these before committing to them in the plan:
- `uv add sofascore-py && uv run python -c "from sofascore import ..."`
- Try FBref scraping with requests + BeautifulSoup
- Results feed into tools curation decision

---

## Wave 1 — Core Infrastructure: FotMob Client + Team Registry + Winner Client (3 agents, ~8 files)

These are the foundational pieces everything else depends on. No file overlaps between agents.

### Agent 1A: FotMob Client Rewrite
**Type:** `python-pro`
**Scope:** `src/soccersmartbet/pre_gambling_flow/tools/fotmob_client.py`

| # | File / Task | Target | Notes |
|---|-------------|--------|-------|
| 1 | Rewrite `fotmob_client.py` | New signed API client | Replace `mobfot` dependency with direct `requests` calls to `/api/data/*` endpoints |
| 2 | Implement `x-mas` header signing | MD5-based token generation | `base64(json({body: {url, code: epoch_ms, foo: "production:74ac2edaa7d42530fa49330efe1eedcfb21b555d"}, signature: MD5(body_json)}))` |
| 3 | Implement `get_league_table(league_id)` | Returns full standings | Endpoint: `/api/data/tltable?leagueId=X` |
| 4 | Implement `get_team_data(team_id)` | Returns team overview | Endpoint: `/api/data/teams?id=X`. Response has: overview.venue, overview.teamForm, overview.lastMatch, overview.nextMatch |
| 5 | Implement `get_match_data(match_id)` | Returns match details | Endpoint: `/api/data/match?id=X`. Response has: content.lineup (injuries) |
| 6 | Implement `get_team_news(team_id)` | Returns news articles | NEW endpoint: `/api/data/tlnews?id=X&type=team&language=en&startIndex=0` |
| 7 | Keep `find_team(name)` with league search | Team name → FotMob ID resolution | Same logic but calling new endpoints. Cache league data with TTL. |

**Verify:** `uv run python -c "from soccersmartbet.pre_gambling_flow.tools.fotmob_client import get_fotmob_client; c = get_fotmob_client(); print(c.get_team_data(8634))"`

### Agent 1B: Team Name Registry
**Type:** `python-pro`
**Scope:** `src/soccersmartbet/team_registry.py` (new file), `db/seeds/` (new directory)

| # | File / Task | Target | Notes |
|---|-------------|--------|-------|
| 1 | Create `src/soccersmartbet/team_registry.py` | Team name resolution module | Functions: `resolve_team(name) -> canonical`, `get_team_aliases(canonical) -> list`, `get_source_name(canonical, source) -> str` |
| 2 | Implement fuzzy matching | Levenshtein + token normalization | Handle: accents (é→e), prefixes (FC/CF/SC/AFC), suffixes, Hebrew chars |
| 3 | Create `db/seeds/teams_seed.py` | Seed script using football-data.org API | Fetch teams from: PL, PD, SA, BL1, FL1, CL, EC, WC. Store canonical_name + football_data_id |
| 4 | Add winner.co.il Hebrew name extraction | Parse GetCMobileLine response | Extract Hebrew team names from market `desc` field, map to canonical names |
| 5 | Create seed data for Israeli Premier League | Manual + winner.co.il data | "ליגת Winner" teams from winner.co.il market data |

**Verify:** `uv run python -c "from soccersmartbet.team_registry import resolve_team; print(resolve_team('Atletico Madrid'))"`

### Agent 1C: winner.co.il Odds Client
**Type:** `python-pro`
**Scope:** `src/soccersmartbet/pre_gambling_flow/tools/game/fetch_winner_odds.py` (new file)

| # | File / Task | Target | Notes |
|---|-------------|--------|-------|
| 1 | Create `fetch_winner_odds.py` | Winner.co.il odds fetcher | Call `GetCMobileHashes` → `GetCMobileLine` with proper headers |
| 2 | Implement header generation | deviceid, appversion, requestid, useragentdata | Static deviceid (hash), random requestid (uuid4), fixed useragentdata JSON |
| 3 | Implement market parsing | Extract 1X2 odds from markets array | Filter: 3 outcomes, one containing "X". Parse Hebrew desc for team names. |
| 4 | Implement league filtering | Filter by Hebrew league names | Map: "ספרדית ראשונה"→La Liga, "אנגלית ראשונה"→Premier League, "ליגת Winner"→Israeli PL, etc. |
| 5 | Return structure matching `fetch_odds` interface | Same dict format as existing odds tool | `{home_team, away_team, odds_home, odds_draw, odds_away, bookmaker: "winner.co.il"}` |

**Verify:** `uv run python -c "from soccersmartbet.pre_gambling_flow.tools.game.fetch_winner_odds import fetch_winner_odds; print(fetch_winner_odds('Barcelona', 'Atletico Madrid'))"`

### After Wave 1
- Orchestrator cherry-picks all agent commits onto `revive`
- Run: `uv run python -c "from soccersmartbet.pre_gambling_flow.tools.fotmob_client import get_fotmob_client; c = get_fotmob_client(); t = c.find_team('Barcelona'); print(t)"`
- Confirm: FotMob client returns data, team registry resolves names, winner odds work

---

## Wave 2 — Fix Existing Tools + New Tools (3 agents, ~10 files)

Depends on Wave 1: all tools need `fotmob_client.py` (1A) working. Some need team registry (1B).

### Agent 2A: Fix FotMob Game Tools
**Type:** `python-pro`
**Scope:** `src/soccersmartbet/pre_gambling_flow/tools/game/fetch_venue.py`, `fetch_weather.py`

| # | File / Task | Target | Notes |
|---|-------------|--------|-------|
| 1 | Fix `fetch_venue.py` | Use new FotMob client | Venue at `overview.venue.widget` → `{name, city, capacity}` |
| 2 | Fix `fetch_weather.py` | Use new FotMob client for venue city | Chain: fotmob→venue city→Nominatim geocode→Open-Meteo. Only venue lookup changed. |

### Agent 2B: Fix FotMob Team Tools + New Tools
**Type:** `python-pro`
**Scope:** `src/soccersmartbet/pre_gambling_flow/tools/team/` (all files)

| # | File / Task | Target | Notes |
|---|-------------|--------|-------|
| 1 | Fix `fetch_form.py` | Use new FotMob client | Form data at `overview.teamForm` — same structure, new fetch method |
| 2 | Fix `fetch_injuries.py` | Use new FotMob client + match endpoint | Get next match via `overview.nextMatch.id`, then `/api/data/match?id=X` for lineup.unavailable |
| 3 | Fix `fetch_league_position.py` | Use new FotMob client | Standings via `get_league_table(league_id)` |
| 4 | Fix `calculate_recovery_time.py` | Use new FotMob client | lastMatch at `overview.lastMatch` |
| 5 | Create `fetch_team_news.py` (NEW) | FotMob team news tool | Use `get_team_news(team_id)` from new client. Return news titles/summaries. |
| 6 | Update `tools/team/__init__.py` | Add new tool exports | Add `fetch_team_news` + any other new tools from curation |

### Agent 2C: Daily Fixtures + Enrichment Tools
**Type:** `python-pro`
**Scope:** `src/soccersmartbet/pre_gambling_flow/tools/game/fetch_daily_fixtures.py` (new), enrichment tools decided in Wave 0 curation

| # | File / Task | Target | Notes |
|---|-------------|--------|-------|
| 1 | Create `fetch_daily_fixtures.py` | Daily fixtures from football-data.org | `GET /v4/matches?dateFrom=X&dateTo=X`. Returns all 12 competitions. |
| 2 | Create enrichment tools decided in Wave 0 | (TBD from curation) | e.g., `calculate_fixture_congestion.py`, `fetch_suspension_risk.py` |
| 3 | Update `tools/game/__init__.py` | Export new tools | Add `fetch_daily_fixtures` + any new game tools |

### After Wave 2
- Run integration test: `uv run python tests/pre_gambling_flow/tools/integration/test_all_tools.py "Barcelona" "Real Madrid"`
- Confirm: all tool calls pass

---

## Wave 3 — Web App + Tests + Cleanup (2 agents, ~12 files)

### Agent 3A: Fix Web App Tool Tester
**Type:** `fullstack-developer`
**Scope:** `src/web_app/`

| # | File / Task | Target | Notes |
|---|-------------|--------|-------|
| 1 | Update `main.py` imports | Add new tools (winner odds, fixtures, team news, etc.) | Wire new tools into `/api/fetch-match-data` endpoint |
| 2 | Add winner.co.il odds display | Show Israeli Toto odds alongside Odds API | Side-by-side comparison |
| 3 | Add team news display | Show FotMob news results | New section in results |
| 4 | Add enrichment data display | Show any new tools from curation | New sections as needed |
| 5 | Verify end-to-end | Test with real teams at localhost:8000 | |

### Agent 3B: Update Tests + Cleanup
**Type:** `test-automator`
**Scope:** `tests/`, `.env.example`, `status/`

| # | File / Task | Target | Notes |
|---|-------------|--------|-------|
| 1 | Update all existing tool tests | Adapt to new FotMob client | test_venue, test_weather, test_form, test_injuries, test_recovery |
| 2 | Create tests for new tools | winner odds, daily fixtures, team news | One test file per tool |
| 3 | Update `test_all_tools.py` | Add all new tools to integration test | Test all tool calls |
| 4 | Clean `.env.example` | Remove dead `APIFOOTBALL_API_KEY` | |
| 5 | Update `ORCHESTRATION_STATE.md` | Mark Batch 6 as REVERTED, add revival status | |

### After Wave 3
- Run full integration test: `uv run python tests/pre_gambling_flow/tools/integration/test_all_tools.py "Arsenal" "Chelsea"`
- Start web app: `uv run python src/web_app/main.py` and test at localhost:8000
- **CHECKPOINT**: All tools working, web app live. Everything below this wave needs working tools.

---

## Wave 4 — LangGraph Pre-Gambling Flow (2 agents, ~10 files)

### Agent 4A: Core Flow + Smart Picker + Pipeline Nodes
**Type:** `python-pro`
**Scope:** `src/soccersmartbet/pre_gambling_flow/nodes/` (new directory), `src/soccersmartbet/pre_gambling_flow/graph_manager.py` (new)

| # | File / Task | Target | Notes |
|---|-------------|--------|-------|
| 1 | Refactor `state.py` if needed | Verify LangGraph 1.x compat | Imports should work but verify |
| 2 | Update `structured_outputs.py` | Add fields for new enrichment data | New Pydantic fields if new tools provide new data |
| 3 | Create `nodes/smart_game_picker.py` | AI agent: fixtures → odds → filter → LLM selection | 1 LLM call for MVP. Uses `fetch_daily_fixtures` + `fetch_winner_odds`. Outputs `SelectedGames`. |
| 4 | Create `nodes/persist_games.py` | DB insert for selected games | PythonNode. Insert into `games` table. |
| 5 | Create `nodes/combine_reports.py` | Query DB for reports, merge | PythonNode. Query `game_reports` + `team_reports`. |
| 6 | Create `nodes/persist_reports.py` | DB insert for combined reports | Update game status to `ready_for_betting`. |
| 7 | Create `graph_manager.py` | Wire full Pre-Gambling Flow | StateGraph with nodes, edges, conditional routing by Phase. |

### Agent 4B: Intelligence Agents + Parallel Orchestration
**Type:** `python-pro`
**Scope:** `src/soccersmartbet/pre_gambling_flow/agents/` (new directory)

| # | File / Task | Target | Notes |
|---|-------------|--------|-------|
| 1 | Create `agents/game_intelligence.py` | Game analysis agent | Tools: fetch_h2h, fetch_venue, fetch_weather, fetch_team_news. 1-2 LLM calls. Writes GameReport to DB. |
| 2 | Create `agents/team_intelligence.py` | Team analysis agent | Tools: fetch_form, fetch_injuries, fetch_league_position, calculate_recovery_time + enrichment tools. 1-2 LLM calls. Writes TeamReport to DB. |
| 3 | Create `agents/parallel_orchestrator.py` | Fan-out/fan-in with Send() | For each game: spawn 1 game + 2 team agents. |
| 4 | Add DB write utilities | Shared DB insert/update helpers | Used by agents for writing reports |

### After Wave 4
- Run end-to-end Pre-Gambling Flow with real data
- Check LangSmith traces for agent behavior
- **CHECKPOINT**: Pre-Gambling Flow works end-to-end

---

## Wave 5 — Gambling Flow + Post-Games + Offline Analysis (3 agents, ~12 files)

### Agent 5A: Telegram Bot + Gambling Flow
**Type:** `python-pro`
**Scope:** `src/soccersmartbet/gambling_flow/` (new directory)

| # | File / Task | Target | Notes |
|---|-------------|--------|-------|
| 1 | Create `gambling_flow/telegram_bot.py` | Telegram bot for user bets | Present reports, collect 1/X/2 bets per game |
| 2 | Create `gambling_flow/ai_betting_agent.py` | AI places bets | 1 LLM call per game with report context |
| 3 | Create `gambling_flow/bet_validator.py` | Validate + persist bets | Check both arrived, insert into `bets` table |
| 4 | Create `gambling_flow/graph_manager.py` | Wire Gambling Flow | LangGraph StateGraph |

### Agent 5B: Post-Games Flow
**Type:** `python-pro`
**Scope:** `src/soccersmartbet/post_games_flow/` (new directory)

| # | File / Task | Target | Notes |
|---|-------------|--------|-------|
| 1 | Create `post_games_flow/fetch_results.py` | Get match results | football-data.org `/v4/matches?status=FINISHED` |
| 2 | Create `post_games_flow/pnl_calculator.py` | Compute P&L | Win: (odds-1)*100, Loss: -100. Update bankroll. |
| 3 | Create `post_games_flow/daily_summary.py` | Send Telegram summary | Results + P&L for both user and AI |
| 4 | Create `post_games_flow/graph_manager.py` | Wire Post-Games Flow | LangGraph StateGraph |

### Agent 5C: Offline Analysis Flow
**Type:** `python-pro`
**Scope:** `src/soccersmartbet/offline_analysis_flow/` (new directory)

| # | File / Task | Target | Notes |
|---|-------------|--------|-------|
| 1 | Create `offline_analysis_flow/query_stats.py` | Query P&L, success rates, team/league breakdowns | SQL queries on games + bets + bankroll tables |
| 2 | Create `offline_analysis_flow/ai_insights.py` | LLM-generated insights from stats | 1 LLM call with stats context, produces narrative |
| 3 | Create `offline_analysis_flow/graph_manager.py` | Wire Offline Analysis Flow | On-demand trigger, query → analyze → display |

### After Wave 5
- End-to-end test: Pre-Gambling → Gambling → Post-Games
- Test Offline Analysis independently
- **CHECKPOINT**: All 4 flows operational

---

## Wave 6 — Competition Expansion + Polish (1 agent)

### Agent 6A: League Expansion + Final Polish
**Type:** `python-pro`
**Scope:** `db/seeds/`, `src/soccersmartbet/team_registry.py`, documentation

| # | File / Task | Target | Notes |
|---|-------------|--------|-------|
| 1 | Seed Israeli Premier League teams | winner.co.il "ליגת Winner" teams | Hebrew↔English mapping |
| 2 | Seed Champions League / Europa League teams | football-data.org CL/EL | Team IDs + aliases |
| 3 | Add Euro / World Cup national team support | football-data.org EC/WC | Seasonal activation |
| 4 | Add FotMob IDs to team registry | Cross-reference FotMob team search | Enables direct FotMob lookups |
| 5 | Final documentation update | Update README, ORCHESTRATION_STATE | Reflect current system state |

### After Wave 6
- Full system test across multiple leagues
- Verify: Israeli league, CL, name resolution across all sources
