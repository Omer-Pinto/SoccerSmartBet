# SoccerSmartBet System Revival Plan

**Created:** 2026-04-05
**Status:** DRAFT — awaiting wave-planner breakdown

---

## Situation Summary

Project was abandoned ~5 months ago (late 2025). Pre-Gambling Flow was ~35% done.
Primary data source (FotMob/mobfot) broke — API endpoints moved.
Two Batch 6 PRs (#39, #40) were merged then reverted.

### What's Actually Verified (April 2026)

| Source | Status | Evidence |
|--------|--------|----------|
| **FotMob** | API moved, cracked | Endpoints changed to `/api/data/*` with `x-mas` signed header. MD5 signing reverse-engineered. All data still available + NEW team news endpoint. |
| **winner.co.il** | **WORKING REST API** | `api.winner.co.il/v2/publicapi/GetCMobileLine` returns all betting markets. No JS scraping needed. Needs custom headers (deviceid, appversion, requestid). 698 football markets found including Israeli league. |
| **football-data.org** | Working | 200 OK. Fixtures, standings (full 20-team), team form, squad/coach, H2H. 12 competitions including Euro/WC. |
| **The Odds API** | Working | 200 OK. 479 credits remaining. Decimal odds. |
| **Open-Meteo** | Working | 200 OK. Free, no key needed. |
| **Sofascore** | To verify | `sofascore-py` package exists. Unofficial API. Per-match player ratings. |
| **FBref** | To verify | Scraping needed. Per-90 stats, xG/xA. Stable table structure. |

### What's Dead
- `mobfot` Python package (1.4.0) — calls old endpoints, gets 404
- `apifootball.com` — trial expired (old code still referenced in .env.example)
- All 6 FotMob-dependent tools (venue, weather, form, injuries, league position, recovery time)

---

## Tasks

### Phase 0: Foundations (Fix What's Broken)

#### 0.1 Fix FotMob Client — New API with Signing
Rewrite `fotmob_client.py` to use new endpoints:
- Old: `GET /api/leagues?id=87` → New: `GET /api/data/tltable?leagueId=87`
- Old: `GET /api/teams?id=X` → New: `GET /api/data/teams?id=X`
- Old: `GET /api/matchDetails?matchId=X` → New: `GET /api/data/match?id=X`
- Add `x-mas` header signing: `base64(json({body: {url, code: epoch_ms, foo: "production:74ac2edaa7d42530fa49330efe1eedcfb21b555d"}, signature: MD5(body_json)}))`
- Monitor: the `foo` hash may change with deploys — extract from JS bundle or check periodically
- **New endpoint discovered**: `/api/data/tlnews?id=X&type=team&language=en` → team news!

**Files:** `src/soccersmartbet/pre_gambling_flow/tools/fotmob_client.py`

#### 0.2 Fix All FotMob-Dependent Tools
Update all 6 tools that use fotmob_client to work with new response structures:
- `fetch_venue.py` — venue data now at `overview.venue.widget` (verified: `{name: "Riyadh Air Metropolitano", city: "Madrid"}`)
- `fetch_form.py` — form data at `overview.teamForm` (verified: 5 entries, resultString works)
- `fetch_injuries.py` — match lineup via `/api/data/match?id=X`, check `content.lineup`
- `fetch_league_position.py` — standings via `/api/data/tltable?leagueId=X`
- `calculate_recovery_time.py` — lastMatch at `overview.lastMatch`
- `fetch_weather.py` — depends on venue city from fotmob (chain: team→venue→geocode→weather)

**Files:** `src/soccersmartbet/pre_gambling_flow/tools/team/*.py`, `src/soccersmartbet/pre_gambling_flow/tools/game/fetch_venue.py`, `src/soccersmartbet/pre_gambling_flow/tools/game/fetch_weather.py`

#### 0.3 Implement winner.co.il Odds Fetcher
New tool: `fetch_winner_odds.py` — replaces/supplements The Odds API.
- Endpoint: `api.winner.co.il/v2/publicapi/GetCMobileLine?lineChecksum=X`
- First call `GetCMobileHashes` to get fresh checksum
- Headers: `deviceid` (static hash), `appversion` ("2.6.0"), `requestid` (uuid), `useragentdata` (JSON)
- Filter markets for 1X2 type (3 outcomes with X)
- Parse Hebrew team names → needs name mapping (Task 0.5)
- Returns Israeli Toto format natively (home/X/away decimal odds)
- Can get ALL games for ALL leagues in 1 API call (no per-league credits like Odds API)

**Files:** `src/soccersmartbet/pre_gambling_flow/tools/game/fetch_winner_odds.py`

#### 0.4 Implement Daily Fixtures Tool
New tool: `fetch_daily_fixtures.py` — critical missing piece.
- Primary: `football-data.org /v4/matches?dateFrom=X&dateTo=X` (all 12 competitions in 1 call)
- Returns: home team, away team, league, time, venue, status
- Needed by Smart Game Picker to know what games exist today
- **Note**: football-data.org team names differ from FotMob/winner (e.g., "Club Atlético de Madrid" vs "אתלטיקו מדריד") — needs name mapping (Task 0.5)

**Files:** `src/soccersmartbet/pre_gambling_flow/tools/game/fetch_daily_fixtures.py`

#### 0.5 Team Name Consistency Layer
Create a team registry with canonical names and aliases.
- Seed with teams from: top 2 leagues of Spain, England, Germany, France, Italy + Israeli Premier League + Champions League + Euro/World Cup national teams
- Store in PostgreSQL `teams` table: `canonical_name`, `aliases` (JSON array), `fotmob_id`, `football_data_id`, `winner_name_he`
- Matching algorithm: Levenshtein distance or token-based similarity (no LLM needed for this)
- Handle: accents (Atlético/Atletico), prefixes (FC/CF/SC), Hebrew↔English, abbreviations
- When a tool receives a team name, resolve to canonical first, then use source-specific name
- Use football-data.org `/v4/competitions/X/teams` to seed English names + IDs
- Use winner.co.il market data to extract Hebrew names
- Manual mapping for edge cases

**Files:** `src/soccersmartbet/team_registry.py`, `db/seeds/teams.sql`

#### 0.6 Implement Team News Tool (NEW — Previously Disabled)
New tool: `fetch_team_news.py`
- FotMob: `/api/data/tlnews?id=X&type=team&language=en&startIndex=0` — returns structured news
- This was previously flagged as "scraping only, disabled" — but FotMob now exposes it via API
- Returns news titles and content — feed to LLM for betting-relevant analysis

**Files:** `src/soccersmartbet/pre_gambling_flow/tools/team/fetch_team_news.py`

#### 0.7 Fix Web App Tool Tester
Get the web app working again with fixed tools.
- Update imports if tool signatures changed
- Verify all 12 tool calls pass for a real match
- Run: `uv run python src/web_app/main.py` → test at localhost:8000

**Files:** `src/web_app/main.py`

#### 0.8 Clean Up Dead References
- Remove `APIFOOTBALL_API_KEY` from `.env.example`
- Update `ORCHESTRATION_STATE.md` — Batch 6 is reverted, not "IN PROGRESS"
- Pin `langgraph>=1.0.0` in `pyproject.toml`
- Remove or archive `status/pre_gambling_flow/PRE_GAMBLING_FLOW_TASKS_OLD.md`

**Files:** `.env.example`, `status/pre_gambling_flow/ORCHESTRATION_STATE.md`, `pyproject.toml`

---

### Phase 1: Enriched Data Sources

#### 1.1 Verify and Integrate Sofascore API
Test `sofascore-py` package for per-match player ratings.
- Install: `uv add sofascore-py`
- Verify it works for today's matches
- If working, create `fetch_player_ratings.py` tool
- Data: player ratings (0-10), goals, assists, tackles per match

#### 1.2 FBref Player Stats Scraper
Build scraper for season-level player stats.
- Scrape team page: `fbref.com/en/squad/{id}/{team}-Stats`
- Extract: goals, assists, minutes, xG, xA per player
- Cache weekly (data doesn't change intra-day)
- Create `fetch_player_stats.py` tool

#### 1.3 Yellow Card / Suspension Tracker
Build suspension risk calculator.
- Source: football-data.org match details or FotMob match stats
- Track yellow card accumulation per player per league
- Calculate suspension risk (5 or 10 yellows = 1 game ban, league-specific)
- Create `fetch_suspension_risk.py` tool

#### 1.4 Fixture Congestion Analysis
Calculate rest days and upcoming fixture impact.
- Source: football-data.org `/v4/teams/{id}/matches?status=SCHEDULED`
- Detect: CL midweek → league weekend fatigue risk
- Detect: cup fixture → rotation probability
- Create `calculate_fixture_congestion.py` tool

---

### Phase 2: LangGraph Refactor & Pre-Gambling Flow

#### 2.1 Refactor to LangGraph 1.x Direct (Drop LangGraphWrappers)
- Remove dependency on vendored `LangGraphWrappers/` for flow code
- Use LangGraph StateGraph, ToolNode, MemorySaver directly
- Keep `ModelWrapper` if useful for provider switching, otherwise use langchain model classes directly
- Update `pyproject.toml` dependencies

#### 2.2 Build Smart Game Picker Node
NodeWrapper with AI agent that:
- Calls `fetch_daily_fixtures()` to get today's matches
- Calls `fetch_winner_odds()` to get odds for all matches
- Filters by odds threshold (all of 1/X/2 > configurable min, e.g., 1.3)
- LLM selects interesting games from filtered list based on rivalry/stakes/context
- Outputs: `SelectedGames` structured output
- **1 LLM call** for MVP, can scale to multi-call later

#### 2.3 Build Game Intelligence Agent
Agent with tools: `fetch_h2h`, `fetch_venue`, `fetch_weather`, `fetch_team_news`
- Calls tools, synthesizes into `GameReport`
- **1-2 LLM calls**: tool calling + synthesis
- Writes `GameReport` to DB

#### 2.4 Build Team Intelligence Agent
Agent with tools: `fetch_form`, `fetch_injuries`, `fetch_league_position`, `calculate_recovery_time`, `fetch_player_stats` (if available), `fetch_suspension_risk`, `calculate_fixture_congestion`
- **1-2 LLM calls**: tool calling + synthesis
- Writes `TeamReport` to DB

#### 2.5 Build Parallel Orchestration
Use LangGraph `Send()` API for fan-out:
- For each selected game: spawn 1 Game Intelligence + 2 Team Intelligence subgraphs
- All run in parallel, write to DB
- Reduce: check all reports arrived, update game status

#### 2.6 Build Remaining Pipeline Nodes
- Persist Unfiltered Games (DB insert)
- Combine Results to Reports (query DB, merge)
- Persist Reports (DB insert, update status)
- Send Gambling Trigger

#### 2.7 Wire Pre-Gambling Flow Graph Manager
Connect all nodes with edges, conditional routing by Phase enum.
- `setup()` → `run_graph()` → `cleanup()`
- End-to-end test with real data

---

### Phase 3: Gambling Flow

#### 3.1 Telegram Bot MVP
- Bot receives game reports, presents to user
- User places bet (1/X/2) per game
- Bot confirms and stores

#### 3.2 AI Betting Agent
- Receives same reports as user
- LLM analyzes and places bet with justification
- 1 LLM call per game

#### 3.3 Bet Validation & Persistence
- Verify both bets arrived before deadline
- Store in `bets` table
- Schedule Post-Games Flow trigger

---

### Phase 4: Post-Games & Analysis

#### 4.1 Fetch Results Tool
- Source: football-data.org `/v4/matches?dateFrom=X&dateTo=X&status=FINISHED`
- Get final scores

#### 4.2 P&L Calculator
- Compute: win = (odds - 1) * 100 NIS, loss = -100 NIS
- Update `bankroll` table

#### 4.3 Daily Summary Notification
- Send results via Telegram

#### 4.4 Operator Dashboard (Waves 10 → 11 → 12 — scope expanded from original "Offline Analysis Flow")
Originally scoped as a background analysis flow; expanded to a full **localhost FastAPI operator dashboard** inside the bot process. Split across three sequential waves because of real dependencies.

**Wave 10 — Platform Foundation (1 agent)**: FastAPI app shell, `psycopg2.pool.ThreadedConnectionPool`, schema additions (`daily_runs.status/attempt_count/last_trigger_source/last_error`, `run_events`, `bet_edits`), mutex helper (`SELECT FOR UPDATE NOWAIT`), `GET /api/status/today`, `GET /api/health`. Blocks Waves 11 and 12.

**Wave 11 — Today Tab + Query DSL (2 parallel agents)**:
- 11A: Today tab — control panel + manual triggers (`POST /api/runs` with `force` override) + bet modification (`PATCH /api/bets/{id}` with 30-min-before-kickoff + gambling-done guards).
- 11B: Query DSL engine — parser + filter-to-SQL compiler. URL-shareable (`league:la-liga team:real-madrid,barcelona month:2026-12 stake:>1.5`).

**Wave 12 — Stats Pages + AI Insights (2 parallel agents, depends on Wave 11's DSL)**:
- 12A: History / P&L / Team / League tabs — line charts, filter-reactive, per-team and per-league rollups.
- 12B: On-demand AI insights — per-query LLM call over filtered rows, async job pattern (**not** a LangGraph flow).

Architectural invariants (locked): one process, one asyncio loop, `daily_runs.status` + `SELECT FOR UPDATE NOWAIT` mutex, sync `graph.invoke` + `asyncio.to_thread`, 2-5s polling, connection-pooled `psycopg2`, no SSE, no auth, no remote access, no async node rewrite, no second process. See `task_breakdown.md` Waves 10/11/12 for full constraints + schema additions + agent-level breakdown.

Waves 13/14/15 (Cup-Tie / Competition Expansion / Testing) follow after.

---

### Phase 5: Competition Support Expansion

#### 5.1 Add Israeli Premier League (Ligat Ha'Al)
- Seed team registry with Israeli teams
- winner.co.il already has "ליגת Winner" with 54 markets
- Check if FotMob covers Israeli league (if not, use football-data.org or winner.co.il only)

#### 5.2 Add Champions League & Europa League
- Already supported by football-data.org (competition codes CL, EL)
- winner.co.il has 49 Champions League markets
- Seed team registry with CL/EL teams

#### 5.3 Euro & World Cup Support
- football-data.org has EC (European Championship) and WC (FIFA World Cup)
- Seed team registry with national teams
- These are seasonal — activate when tournaments run

---

## Infrastructure Decisions (Validated)

| Component | Decision | Rationale |
|-----------|----------|-----------|
| **PostgreSQL** | KEEP | Relational data (games, bets, reports), proven schema, Docker ready |
| **Docker Compose** | KEEP | Staging/prod isolation works, PostgreSQL 16-alpine |
| **Schema** | UPDATE | Add `teams` table for name registry. Current 5-table schema is sound. |
| **Python 3.13** | KEEP | Project already uses it |
| **uv** | KEEP | Package management working |
| **FastAPI** | KEEP for testing | Web app for tool testing. Telegram for production betting. |
| **LLM** | GPT-4o-mini / GPT-5.4-mini | Cost-effective, Omer has OpenAI credits |
| **LangGraph** | Upgrade to 1.x direct | Drop LangGraphWrappers, use StateGraph/Send() natively |

---

## Data Source Priority

| Priority | Source | What It Provides | Cost | Calls/Day |
|----------|--------|-------------------|------|-----------|
| 1 | **winner.co.il** | Israeli Toto odds for ALL leagues (1 call) | Free | 1-2 |
| 2 | **football-data.org** | Fixtures, standings, form, H2H, squad | Free (key) | 10-20 |
| 3 | **FotMob (new API)** | Venue, injuries, team news, recovery, form | Free | 20-30 |
| 4 | **Open-Meteo** | Weather forecasts | Free | 3-5 |
| 5 | **The Odds API** | Backup odds / international bookmaker odds | Free (key) | 3-5 |
| 6 | **Sofascore** | Per-match player ratings | Free | 10-20 |
| 7 | **FBref** | Season player stats (xG/xA) | Free (scrape) | Weekly |

---

## Risk Register

| Risk | Mitigation |
|------|-----------|
| FotMob `x-mas` signing changes | Monitor `foo` hash, re-extract from JS bundle if needed |
| winner.co.il blocks API access | Fall back to The Odds API (already working) |
| football-data.org rate limits (10/min) | Batch requests, cache results, use FotMob as supplement |
| Sofascore unofficial API breaks | Not critical — enrichment layer, degrade gracefully |
| LangGraph breaking changes | Pin to 1.0.x, test before upgrading |
| Team name mismatches | Name registry with aliases handles this |
