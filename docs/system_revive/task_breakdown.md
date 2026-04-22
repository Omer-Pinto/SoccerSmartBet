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
| 2 | Create `calculate_fixture_congestion.py` (STRETCH) | Fixture density analysis | `GET /v4/teams/{id}/matches?status=SCHEDULED&limit=5`. Detect CL/cup congestion. |
| 3 | Create `fetch_suspension_risk.py` (STRETCH) | Yellow card accumulation | football-data.org match data. League-specific thresholds. |
| 4 | Update `tools/game/__init__.py` + `tools/team/__init__.py` | Export new tools | Add all new tools |

### After Wave 2
- Run integration test: `uv run python tests/pre_gambling_flow/tools/integration/test_all_tools.py "Barcelona" "Real Madrid"`
- Confirm: all tool calls pass

---

## Wave 3 — Web App + Cleanup (1 agent)

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

> **Tests**: Original Wave 3B (test suite) was obsolete — hardcoded dates, brittle assertions, no coverage of Waves 4-7. All tests deleted. Testing redesign deferred to Wave 15.

### After Wave 3
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
| 3 | Create `nodes/smart_game_picker.py` | AI agent: fixtures → odds → filter → LLM selection | 1 LLM call for MVP. Uses `fetch_daily_fixtures` + `fetch_winner_odds`. Outputs `SelectedGames`. **Game Selection Preferences (from Omer):** (1) PL & La Liga always preferred, then Bundesliga, Serie A, Ligue 1 in that order. (2) Israeli league: max 1 game, must involve top-6 team. (3) No min odds threshold for now. (4) Within La Liga: prefer Barcelona & Real Madrid over others. (5) Min 3 games per day. |
| 4 | Create `nodes/persist_games.py` | DB insert for selected games | PythonNode. Insert into `games` table. |
| 5 | Create `nodes/combine_reports.py` | Query DB for reports, merge | PythonNode. Query `game_reports` + `team_reports`. |
| 6 | Create `nodes/persist_reports.py` | DB insert for combined reports | Update game status to `ready_for_betting`. |
| 7 | Create `graph_manager.py` | Wire full Pre-Gambling Flow | StateGraph with nodes, edges, conditional routing by Phase. |

### Agent 4B: Intelligence Agents + Subgraph Orchestration
**Type:** `python-pro`
**Scope:** `src/soccersmartbet/pre_gambling_flow/agents/` (new directory), `src/soccersmartbet/pre_gambling_flow/nodes/analyze_game.py` (new)

| # | File / Task | Target | Notes |
|---|-------------|--------|-------|
| 1 | Create `agents/game_intelligence.py` | Game analysis utility | Tools: fetch_h2h, fetch_venue, fetch_weather, fetch_team_news. 1 LLM call (gpt-5.4). Writes GameReport to DB. |
| 2 | Create `agents/team_intelligence.py` | Team analysis utility | Tools: fetch_form, fetch_injuries, fetch_league_position, calculate_recovery_time. 1 LLM call (gpt-5.4). Writes TeamReport to DB. |
| 3 | Create `nodes/analyze_game.py` subgraph | LangGraph subgraph with Send() fan-out | Per-game subgraph: 3 parallel nodes (game_intelligence, team_intel_home, team_intel_away). Main graph fans out N subgraph invocations via Send(). Two-level parallelism: outer=games, inner=intelligence calls. |
| 4 | Add DB write utilities | Shared DB insert/update helpers | `agents/db_utils.py`: insert_game_report, insert_team_report, update_game_status (upsert). |

### After Wave 4
- Test smart_game_picker standalone against real APIs (football-data.org + winner.co.il)
- Test game_intelligence + team_intelligence standalone with real FotMob + LLM
- Run end-to-end Pre-Gambling Flow with real data
- Check LangSmith traces for subgraph behavior (two-level parallelism)
- **CHECKPOINT**: Pre-Gambling Flow works end-to-end

---

## Wave 5 — Telegram Bot + Triggers + Game Reports + ISR Time (2-3 agents, ~8 files)

### Agent 5A: ISR Timezone Utility
**Type:** `python-pro`
**Scope:** `src/soccersmartbet/utils/timezone.py` (new)

| # | File / Task | Target | Notes |
|---|-------------|--------|-------|
| 1 | Create `utils/timezone.py` | UTC → Israel time conversion utility | `zoneinfo` based (Asia/Jerusalem). ISR = UTC+2 / UTC+3 (DST). Simple, used everywhere. |
| 2 | Apply to `smart_game_picker.py` | Selected games show ISR kick-off times | Convert match times from football-data.org (UTC) to ISR |
| 3 | Apply to all scheduling/logging | Consistent ISR timestamps | Triggers, logs, DB records |

### Agent 5B: Telegram Bot + Flow Triggers
**Type:** `python-pro`
**Scope:** `src/soccersmartbet/telegram/` (new directory)
**Prerequisite:** Omer creates bot via @BotFather → provides bot token in `.env` as `TELEGRAM_BOT_TOKEN`

| # | File / Task | Target | Notes |
|---|-------------|--------|-------|
| 0 | **[USER]** Create bot via @BotFather | Get bot token | Add to `.env` as `TELEGRAM_BOT_TOKEN` |
| 1 | Create `telegram/bot.py` | Telegram bot client | python-telegram-bot, async, send/receive messages |
| 2 | Create Pre-Gambling daily trigger | Cron job at 13:00 ISR | Automatically triggers Pre-Gambling Flow every day |
| 3 | Create Gambling trigger | Fires when Pre-Gambling Flow completes | Sends "gambling time" Telegram message with game report links |

### Agent 5C: HTML Game Report Pages + Telegram Message Design
**Type:** `fullstack-developer`
**Scope:** `src/soccersmartbet/reports/` (new directory)

| # | File / Task | Target | Notes |
|---|-------------|--------|-------|
| 1 | Create static HTML report per game | All tool data + expert summary | Similar to web UI visualization but improved — no button/team selection |
| 2 | Design Telegram "gambling time" message | Bullet per game: teams, ISR time, stadium, competition + HTML link | One link per game opens full game report page |
| 3 | Serve HTML pages accessible via Telegram links | Static file serving or lightweight endpoint | Must be reachable from Telegram message URLs |

### After Wave 5
- Verify Telegram bot sends/receives messages
- Verify daily cron trigger fires Pre-Gambling at 13:00 ISR
- Verify Gambling trigger sends formatted message after Pre-Gambling completes
- Verify HTML report pages render correctly with all tool data + expert summary
- Verify all times in ISR throughout the system
- **CHECKPOINT**: Daily automation + user communication working

---

## Wave 6 — Gambling Flow + Post-Games + Offline Analysis (3 agents, ~10 files)

### Agent 6A: Gambling Flow (Hybrid: Telegram handlers + LangGraph)
**Type:** `python-pro`
**Scope:** `src/soccersmartbet/gambling_flow/` (new directory), `src/soccersmartbet/pre_gambling_flow/nodes/notify_telegram.py`, `src/soccersmartbet/telegram/triggers.py`

Trigger chain: pre-gambling `notify_telegram` → "Want to bet?" message → user taps Yes → betting UI → SEND BET → gambling LangGraph flow (AI bet + verify + persist)

| # | File / Task | Target | Notes |
|---|-------------|--------|-------|
| 1 | Update `notify_telegram.py` | Add "Want to bet? [Yes] [No]" with deadline | Deadline = min(kickoff_time) - 30min |
| 2 | Create `gambling_flow/__init__.py` | Package marker | |
| 3 | Create `gambling_flow/handlers.py` | Telegram callback handlers | Yes/No, per-game 1/X/2 + stake, SEND BET, lock after send |
| 4 | Create `gambling_flow/ai_betting_agent.py` | AI places bets | Query reports + AI balance, 1 LLM call, structured output per game |
| 5 | Create `gambling_flow/bet_verifier.py` | Validate + persist bets | Check predictions valid (1/x/2), stake numeric. No balance check. Insert `bets` table. |
| 6 | Create `gambling_flow/graph_manager.py` | LangGraph: ai_bet → verify → persist → notify | LangSmith traced. Invoked by handlers.py after user SEND BET. |
| 7 | Register handlers in `triggers.py` | Wire gambling callbacks into bot Application | Add CallbackQueryHandler for bet_* / stake_* / send_bet patterns |

### Agent 6B: Post-Games Flow
**Type:** `python-pro`
**Scope:** `src/soccersmartbet/post_games_flow/` (new directory), `deployment/db/init/001_create_schema.sql`

No AI calls — pure data pipeline. Trigger: max(kickoff_time) + 3 hours.

| # | File / Task | Target | Notes |
|---|-------------|--------|-------|
| 1 | Schema changes | Add columns to bets + bankroll | `bets`: add `result VARCHAR(5)` (actual 1/x/2) + `pnl DECIMAL(10,2)`. `bankroll`: add `games_lost INTEGER DEFAULT 0`. |
| 2 | Create `post_games_flow/fetch_results.py` | LangGraph node: fetch final scores | football-data.org `/v4/matches?dateFrom=X&dateTo=X&status=FINISHED`. Match to games in DB by teams + date. Update `games.home_score`, `games.away_score`, `games.outcome`. |
| 3 | Create `post_games_flow/pnl_calculator.py` | LangGraph node: calculate P&L per bet | Won: `pnl = stake * (odds - 1)`. Lost: `pnl = -stake`. Write `result` + `pnl` to bets. Update bankroll: `total_bankroll += sum(pnl)`, `games_played += N`, `games_won += wins`, `games_lost += losses`. |
| 4 | Create `post_games_flow/notify_summary.py` | LangGraph node: Telegram daily summary | Per-game: score, user bet + AI bet + who won. Bottom: bankroll totals for both. HTML formatting. |
| 5 | Create `post_games_flow/graph_manager.py` | Wire Post-Games graph | `START → fetch_results → pnl_calculator → notify_summary → END`. Entry: `run_post_games_flow(game_ids)`. |

### After Wave 6
- End-to-end test: Pre-Gambling → Gambling → Post-Games ✅
- **CHECKPOINT**: 3 core flows operational

---

## Wave 7 — Daily Runs Tracking + Full Automation (1-2 agents, ~5 files)

### Critical context: macOS scheduler problem

APScheduler's `AsyncIOScheduler` (used by python-telegram-bot's `JobQueue`) relies on `CLOCK_MONOTONIC` which **freezes when macOS sleeps**. A job scheduled for 13:00 can silently skip if the Mac sleeps. `misfire_grace_time` drops late jobs with no error and no retry.

**Solution: wall-clock polling.** Replace `job_queue.run_daily()` with an asyncio background task that loops every 60 seconds, checking `datetime.now(ISR_TZ)` (wall clock, not monotonic). After system resume, the first iteration sees wall-clock already past the target and fires immediately. macOS DarkWakes every ~15 min but only 2 seconds — Docker VM may not fully resume, so expect variable delay (not instant).

**Process architecture:**
- Bot runs as long-lived process: `run_bot.py` → `start_scheduler()` → `application.run_polling()`
- Pre-gambling flow runs inside bot process via `asyncio.to_thread(run_pre_gambling_flow)`
- Gambling UI is callback-driven (Telegram inline buttons → `handlers.py` in same bot process)
- Post-games trigger: wall-clock poller checks if `max(kickoff_time) + 3h` has passed
- `_sessions` dict in `handlers.py` is in-memory — `gamble_yes` handler queries DB directly as fallback
- Betting deadline = `min(kickoff_time) - 15 minutes` (enforced in handlers)
- `daily_runs` table prevents double-runs and enables startup recovery

### Agent 7A: daily_runs Table + Scheduler Fix
**Type:** `python-pro`
**Scope:** `deployment/db/init/001_create_schema.sql`, `src/soccersmartbet/telegram/triggers.py`, flow nodes

| # | File / Task | Target | Notes |
|---|-------------|--------|-------|
| 1 | Add `daily_runs` table to schema | Track daily pipeline lifecycle | `run_date DATE PK`, pre_gambling/gambling/post_games timestamps, `game_ids INTEGER[]`, `user_bet_completed BOOLEAN`, `ai_bet_completed BOOLEAN` |
| 2 | Replace `job_queue.run_daily()` with wall-clock poller | Immune to macOS sleep suspending monotonic timers | 60s asyncio loop checking `datetime.now(ISR_TZ)`, fires if past 13:00 and no run today in `daily_runs` |
| 3 | Add startup recovery to `start_scheduler()` | Catch missed runs on bot restart | Query `daily_runs` for today, if no pre-gambling run and past 13:00 → fire immediately |
| 4 | Wire pre-gambling flow to write `daily_runs` | Audit trail | `smart_game_picker` writes started_at, `persist_reports`/`notify_telegram` writes completed_at + game_ids |
| 5 | Schedule post-games trigger | Auto-fire post-games flow | max(kickoff_time) + 3h, wall-clock based |
| 6 | Handle no-games days gracefully | Picker returns 0 games | Send "No games today" Telegram message, skip gambling + post-games, mark daily_runs as complete |

### After Wave 7
- 🟢 Verify: close laptop lid, wake after trigger → flow fires within 60s (proven 2026-04-12)
- 🟢 Verify: `daily_runs` table populated correctly after flow run (proven daily since 2026-04-12)
- Remaining verification items moved to Wave 8.

---

## Wave 8 — Report Refactor Track (sequential)

Tightly-coupled chain: diagnose → schema → data-source fix → residual fix → renderer. Sequential execution, one end-to-end review at the end of the track.

**Execution order:** 8A → 8B → 8C → 8D → 8E.

**Guiding constraints:**
- Target device: 5-inch phone, Telegram in-app browser. Omer opens 3–8 reports back-to-back before betting.
- **Numbers lead, prose follows as short bullets.** Never paragraphs. No opening flourishes ("This is the kind of…", "Critical —", "Improving —"). No scene-setting.
- `games` table is a registry of games we're betting on / about to bet on. **It is NOT a world game registry.** No new rows for non-bet games.
- Primary data source for football context is FotMob. football-data.org is a weak fallback.
- All LLM work goes through the `ai-engineer` subagent and uses structured Pydantic outputs. No prose blobs.

### Agent 8A: Contract Investigation + H2H Diagnosis (read-only)
**Type:** `python-pro`
**Scope:** read-only pass over existing code; outputs `docs/system_revive/wave8_contract.md`.

| # | File / Task | Target | Notes |
|---|-------------|--------|-------|
| 1 | Read current code | `agents/game_intelligence.py`, `agents/team_intelligence.py`, `structured_outputs.py`, current prompts, `reports/html_report.py` | Inventory current Pydantic fields and what each report section reads. |
| 2 | Diagnose H2H empty bug | Live logs + DB inspection + `fetch_h2h.py` review | Is H2H empty because: (a) prompt drops it, (b) LLM returns empty string, (c) DB write path swallows it, (d) `fetch_h2h.py` returns nothing, (e) rate limiting by football-data.org? Report root cause with evidence. |
| 3 | Write `wave8_contract.md` | New file under `docs/system_revive/` | Contents: (a) final Pydantic field list 8B delivers; (b) H2H root cause + which later agent (8C rate-limit vs 8D residual fix) acts on it; (c) file-ownership map for 8D + 8E; (d) any surprises that change the plan. |

### Agent 8B: Tighten Agent Prompts + Structured Outputs
**Type:** `ai-engineer`
**Scope:** `src/soccersmartbet/pre_gambling_flow/structured_outputs.py`, `agents/game_intelligence.py`, `agents/team_intelligence.py`, `agents/db_utils.py`, `prompts.py`, `db/schema.sql`, `deployment/db/init/001_create_schema.sql`.

| # | File / Task | Target | Notes |
|---|-------------|--------|-------|
| 1 | Split structured outputs: raw vs bullets | Pydantic models | Raw fields as their own typed fields: form streak, league rank (int), points (int), matches played (int), recovery days (int), last-5 matches list. Commentary fields as `list[str]` of short bullets. |
| 2 | H2H aggregate keyed by team identity | Pydantic models | W/D/L totals between today's home and away team. NO historical per-match list (past meetings' home/away roles unreliable). |
| 3 | Soft length caps in prompts | game/team intelligence prompts | Caps: form bullets ≤2 × 12 words; injuries bullets ≤5; team news bullets ≤3; expert analysis bullets ≤6 × 20 words. Soft — do not reject or truncate LLM output. |
| 4 | Forbid opening flourishes | Prompt instructions | Explicitly disallow scene-setting sentences, "This is the kind of…", "Critical —", "Improving —", and bedtime-story tone. Bullets start with concrete facts. |
| 5 | Keep "analyze, not verdict" directive | Prompt instructions | Analysis of the data, not a bet recommendation. |
| 6 | Stage DDL in schema files only | `db/schema.sql` + `deployment/db/init/001_create_schema.sql` | DO NOT apply to live DB. Migration DDL runs at merge time with explicit OK. |

### Agent 8C: H2H Rate-Limit Mitigation
**Type:** `python-pro`
**Scope:** `src/soccersmartbet/pre_gambling_flow/tools/game/fetch_h2h.py` + the LangGraph wiring that threads the league hint into it.

Context: 8A confirmed rate limiting by football-data.org — up to 63 requests fired in seconds against a 10 req/min free-tier cap. Pre-gambling can acceptably extend to 3–4 minutes if that buys reliable H2H. Omer's explicit design directive: keep LangGraph-native parallelization, no shared rate-limiter state, no threading primitives, no cross-game coordination.

| # | File / Task | Target | Notes |
|---|-------------|--------|-------|
| 1 | League hint threaded end-to-end | `state.py`, `graph_manager.py`, `nodes/analyze_game.py`, `agents/game_intelligence.py`, `fetch_h2h.py` | Add `league: str` to `AnalyzeGameState`, include in `Send()` payload, forward through `run_game_intelligence` to `fetch_h2h`. |
| 2 | 1 scan + 1 H2H per game | `fetch_h2h.py` | Module-level `LEAGUE_CODE_MAP` (PL/PD/SA/BL1/FL1/CL/EC/WC/ELC/DED/PPL/BSA). Hint present + supported → scan exactly that one competition. No hint or unsupported league → graceful-degradation dict, no API hit. |
| 3 | Per-call exponential backoff on 429 | `fetch_h2h.py::_get_with_backoff` | Sleep sequence `[5, 10, 20, 40, 80]`. Applied independently to the scan GET and the final H2H GET. After the 80s attempt still 429 → return `None` → caller maps to graceful dict. No jitter, no shared state. |
| 4 | Graceful degradation string | `fetch_h2h.py::_graceful` | On retry exhaustion or unsupported league, `error="couldn't retrieve h2h due to API issues"` — exact string. Other existing error paths unchanged. |
| 5 | Timeout bump | `fetch_h2h.py` | `TIMEOUT = 30`, env override `FDORG_H2H_TIMEOUT_S`. |
| 6 | No pytest reinstatement | Verification | Smoke imports + graph compile only. Tool tests stay removed. Verify end-to-end on a real pre-gambling run once 8E lands. |

### Agent 8D: H2H Fix Application — SKIPPED

Superseded by 8B + 8C. 8B's `_build_h2h_aggregate` populates the structured `H2HAggregate` field from raw tool output and returns `None` when source data is missing; 8C made `fetch_h2h` reliable for supported leagues and graceful for the rest. No residual layer needs a fix.

End-to-end verification happens naturally on the first pre-gambling run after 8E's live-DB migration.

### Agent 8E: Report HTML Full Overhaul (5-inch mobile, table-comparison)
**Type:** `ui-designer` (design spec produced 2026-04-17) + `python-pro` (implementation)
**Scope:** `src/soccersmartbet/reports/html_report.py`, `src/soccersmartbet/pre_gambling_flow/nodes/combine_reports.py` (SELECT migration), `src/soccersmartbet/gambling_flow/ai_betting_agent.py` (intelligence-bundle migration), `reports/telegram_message.py` if affected. Consumes 8B's Pydantic fields per 8A's contract.

| # | File / Task | Target | Notes |
|---|-------------|--------|-------|
| 1 | Full rewrite of `html_report.py` | Mobile-first, 5" phone (≈375px portrait, ≈667px landscape) | Per ui-designer spec. Professional bettor's spreadsheet aesthetic. |
| 2 | Layout — table comparison | 3-col table: home \| stat label \| away | Split rows: form (streak + bullets), league position (rank · pts · MP), recovery, injuries. Shared rows (full width): H2H, venue, weather. |
| 3 | Match header | Team names, kickoff (ISR), league | Cup-tie first-leg inline rendering deferred to Wave 13. |
| 4 | Compact odds row | Single line | `1 1.15 · X 6.60 · 2 11.10`. Source label "winner.co.il" small, right-aligned. No big cards. |
| 5 | Implied-probability bar | Thin horizontal bar under odds row | Neutral color segments proportional to implied probability. No home/away color coding. |
| 6 | Form as pills row | `L D D W W` visual pills | Pills first, bullets after. Last-5 games table (result, GF:GA, opponent, home/away) below pills. |
| 7 | Injuries, team news, expert analysis — bullets only | Strict caps enforced by 8B prompts | No prose paragraphs. No opening flourishes. |
| 8 | Venue display | Short name from `games.venue`, enriched with surface + capacity if available | Use FotMob's short/popular venue name IF FotMob exposes one. No local dict. Single line. |
| 9 | Fix venue duplication bug | Header + shared row | Header uses `games.venue` (short). Shared row shows venue + surface + capacity. Never LLM prose in the header. |
| 10 | Palette + typography | Near-black bg `#0f0f0f`, hairline separators `#222`, muted gold `#c8a84b` accent | Data-dense, flat, no gradients. |
| 11 | Delete — crests, VS badge, emoji section titles, home=green/away=red coding, oversized recovery number | Generator | All removed. |
| 12 | H2H display — aggregate W/D/L or "No data available" | Renderer | Team_A W – D – Team_B W when present. Explicit gap when missing. |
| 13 | Migrate `combine_reports.py` SELECT + template | Consumer | Read new columns; render from structured fields + JSONB bullet arrays. |
| 14 | Migrate `ai_betting_agent.py` intelligence bundle | Consumer | Rebuild prompt payload from new JSONB bullets + structured fields. |
| 15 | Apply migration DDL to live DB | Live DB via docker exec | Per CLAUDE.md: surface exact SQL for explicit OK, then apply. Only at this point does the track become mergeable. |

### After Wave 8
- End-to-end pre-gambling report runs with new Pydantic shape, new prompts, populated H2H, and mobile-first HTML rendered to Telegram.
- Live DB migration applied. Bot resumes daily automation.

---

## Wave 9 — Robustness Carryovers (independent)

Unrelated to the report refactor. Can run any time — files are disjoint from Wave 8.

### Agent 9A: Post-Games Missing-Results Alert
**Type:** `python-pro`
**Scope:** `src/soccersmartbet/post_games_flow/fetch_results.py` + notification path

| # | File / Task | Target | Notes |
|---|-------------|--------|-------|
| 1 | Alert on missing result | Issue #55 | Post-games currently silently skips games with no FotMob match. Must send a Telegram alert listing the skipped games, not swallow them. |

### Agent 9B: No-Games-Day Robustness Verification
**Type:** `python-pro`
**Scope:** `src/soccersmartbet/pre_gambling_flow/`, `telegram/triggers.py` (verification; fix only if broken)

| # | File / Task | Target | Notes |
|---|-------------|--------|-------|
| 1 | Verify no-games day path | smart_game_picker returns 0 | No crash, no orphan state, `daily_runs` marked complete, "No games today" Telegram message sent. |

### Agent 9C: Startup Recovery Verification
**Type:** `python-pro`
**Scope:** `telegram/triggers.py` startup recovery logic (verification; fix only if broken)

| # | File / Task | Target | Notes |
|---|-------------|--------|-------|
| 1 | Verify startup recovery | Bot restart after missed 13:00 ISR | Recovery fires pre-gambling flow immediately on startup if today's run is missing and wall-clock is past 13:00 ISR. |

### After Wave 9
- Post-games alerts on missing results.
- No-games day + startup recovery verified.

---

## Operator Dashboard — Three-Wave Sequence (Waves 10 → 11 → 12)

The dashboard is split across three waves because of real dependencies — Wave 11 can only start after Wave 10 lands, Wave 12 can only start after Wave 11 lands. Within each wave, agents run in parallel in isolated worktrees.

Aesthetic: carnival/Waka-Waka — tokens live in `webapp/static/today.css` and `webapp/static/shared.css`.

### Architectural constraints (LOCKED for all three waves — change requires Omer's explicit OK)

1. **One process, one asyncio loop.** FastAPI + Telegram updater + wall-clock poller + LangGraph flows co-located. `uvicorn.Server(...).serve()` runs as an asyncio task alongside the poller (replaces `application.run_polling()` with manual lifecycle: `initialize()` → `start_polling()` → `start()` → `gather(uvicorn.serve(), _wall_clock_poller())`).
2. **Flow mutex = `daily_runs.status` + `SELECT ... FOR UPDATE NOWAIT`.** No `asyncio.Lock`. No in-memory flags. DB is the system of record.
3. **Keep sync `graph.invoke()` + `asyncio.to_thread` bridge.** Do NOT convert nodes to async. LangGraph's own thread pool handles `Send()` fan-out; we don't resize or touch it.
4. **Status visibility = 2–5s polling** of `GET /api/status/today` with server-side 1s TTL cache. No SSE, no WebSocket.
5. **Connection pool required before first HTTP endpoint.** `psycopg_pool.ConnectionPool` (psycopg3, min=1 / max=10). Replace per-call `psycopg2.connect()` in `daily_runs.py` and every new module. (Pre-existing flow code under `gambling_flow/`, `pre_gambling_flow/`, `post_games_flow/`, `team_registry`, `reports/` stays on direct `psycopg2.connect()` per ai-engineer verdict — fan-out width would starve a bounded pool.)
6. **All LLM calls from HTTP handlers are async jobs.** Handlers return 202 + job_id within 200ms; dashboard polls for completion. Sync LLM-in-handler is forbidden.
7. **Bet edits**: allowed only when `daily_runs.gambling_completed_at IS NOT NULL` for that bet's date AND `game.kickoff_time - now_isr() > 30min`. Enforce in SQL (CHECK or trigger) AND in API layer. Every edit appends to `bet_edits`.
8. **Force-rerun path**: transactional cleanup — DELETE `games` + `game_reports` + `expert_game_reports` for that `run_date` BEFORE re-inserting. Bump `attempt_count`.
9. **No multi-user, no auth, no remote access, no SSE, no async node rewrite, no second process, no queue.** Permanently out of scope.
10. **Live DDL only after Omer's explicit OK** per CLAUDE.md.

### Schema additions (stage in `deployment/db/init/001_create_schema.sql`, apply to live DB only after Omer's OK — part of Wave 10)

```sql
ALTER TABLE daily_runs ADD COLUMN status VARCHAR(30) NOT NULL DEFAULT 'idle'
    CHECK (status IN ('idle', 'pre_gambling_running', 'pre_gambling_done',
                      'gambling_running', 'gambling_done',
                      'post_games_running', 'post_games_done', 'failed'));
ALTER TABLE daily_runs ADD COLUMN last_trigger_source VARCHAR(20);
ALTER TABLE daily_runs ADD COLUMN attempt_count INTEGER NOT NULL DEFAULT 1;
ALTER TABLE daily_runs ADD COLUMN last_error TEXT;

CREATE TABLE run_events (
    event_id      SERIAL PRIMARY KEY,
    run_date      DATE NOT NULL,
    event_type    VARCHAR(40) NOT NULL,
    triggered_by  VARCHAR(20) NOT NULL CHECK (triggered_by IN ('scheduler', 'manual', 'recovery')),
    triggered_at  TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    payload       JSONB
);
CREATE INDEX ON run_events(run_date, triggered_at);

CREATE TABLE bet_edits (
    edit_id    SERIAL PRIMARY KEY,
    bet_id     INTEGER NOT NULL REFERENCES bets(bet_id) ON DELETE CASCADE,
    field      VARCHAR(30) NOT NULL,
    old_value  TEXT,
    new_value  TEXT,
    edited_at  TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    source     VARCHAR(20) NOT NULL DEFAULT 'dashboard'
);
CREATE INDEX ON bet_edits(bet_id);

CREATE INDEX IF NOT EXISTS idx_bets_bettor ON bets(bettor);
CREATE INDEX IF NOT EXISTS idx_games_league ON games(league);
```

---

## Wave 10 — Dashboard Platform Foundation 🟡 CODE + DDL DONE — AWAITING BOT RESTART + ENDPOINT VERIFICATION (1 agent)

Single-agent wave. Blocks Waves 11 and 12. Everything downstream consumes this foundation.

### Agent 10A: Platform Foundation
**Type:** `python-pro`
**Scope:** new `src/soccersmartbet/webapp/` package; edits to `src/soccersmartbet/telegram/triggers.py`, `src/soccersmartbet/daily_runs.py`, `deployment/db/init/001_create_schema.sql`

| # | File / Task | Target | Notes |
|---|-------------|--------|-------|
| 1 | FastAPI app shell | `src/soccersmartbet/webapp/app.py` | Bind to `127.0.0.1:8083`. Static-file serving for HTML/JS from `webapp/static/`. Single error-handler middleware. No auth. |
| 2 | Uvicorn lifecycle integration | `src/soccersmartbet/telegram/triggers.py` | Replace `application.run_polling()` with manual `initialize()` / `updater.start_polling()` / `start()` sequence, then `asyncio.gather(uvicorn.Server(config).serve(), _wall_clock_poller())`. Graceful shutdown. |
| 3 | Connection pool | `src/soccersmartbet/db.py` (new module) | `psycopg_pool.ConnectionPool` (psycopg3, min=1 / max=10). Context-manager helpers `get_conn()` / `get_cursor()`. Replace all `psycopg2.connect()` call-sites in `daily_runs.py`. Subsequent waves use this module. |
| 4 | Schema migration | `deployment/db/init/001_create_schema.sql` | Stage the SQL block above. Do NOT apply to live DB — await Omer's explicit OK before `docker exec ... psql ...`. |
| 5 | Audit write helpers | `src/soccersmartbet/webapp/audit.py` (new) | `write_run_event(run_date, event_type, triggered_by, payload)` and `write_bet_edit(bet_id, field, old, new, source)`. Used by every subsequent trigger/edit path. |
| 6 | Mutex helper | `src/soccersmartbet/webapp/run_mutex.py` (new) | `acquire_flow(run_date, flow_type)` function: opens a transaction, `SELECT status FROM daily_runs WHERE run_date = %s FOR UPDATE NOWAIT`, validates state transition, writes new `status`, commits. Returns `RunContext` / raises `FlowConflict` (HTTP 409). |
| 7 | `GET /api/status/today` | webapp route | Returns joined `daily_runs` row + last 10 `run_events`. Server-side 1s TTL cache (module-level dict with timestamp). Used by every dashboard tab as the keep-alive/heartbeat. |
| 8 | `GET /api/health` | webapp route | Trivial: DB ping + last poller tick time + process uptime. Used for liveness checks. |

### Wave 10 completion criteria
- Bot still runs the existing flows identically (no regression on 08:35 pre-gambling or 01:30 post-games).
- `curl http://127.0.0.1:8083/api/health` returns 200.
- `curl http://127.0.0.1:8083/api/status/today` returns correct JSON for today.
- New schema additions applied to live DB (after explicit OK).
- `run_events` table gets one row per flow fire (scheduler writes via the new helper).

---

## Wave 11 — Today Tab + Query DSL ⬜ NOT STARTED (2 agents, parallel, depends on Wave 10)

Two independent agents running in parallel worktrees. Neither consumes the other; both consume Wave 10.

### Agent 11A: Today Tab — Control Panel + Bet Modification
**Type:** `fullstack-developer`
**Scope:** new `src/soccersmartbet/webapp/routes/today.py`, new `webapp/static/today.html` + CSS + minimal JS

| # | File / Task | Target | Notes |
|---|-------------|--------|-------|
| 1 | `POST /api/runs` endpoint | `{run_date, flow_type: "pre_gambling"\|"post_games"\|"regenerate_report", force: bool, params?}` | Uses Wave 10's `acquire_flow()` mutex. Writes `run_events`. Spawns `asyncio.create_task(_wrap_flow(...))` around `asyncio.to_thread(run_*_flow, ...)`. Returns 202 + `{event_id, status: "starting"}`. On force=true for completed run: transactional DELETE of today's games/reports before invoke. |
| 2 | `PATCH /api/bets/{bet_id}` endpoint | body `{prediction?, stake?}` | Guards (SQL + API layer): `daily_runs.gambling_completed_at IS NOT NULL` AND `min(games.kickoff_time) - now_isr() > 30min`. Writes `bet_edits` row per field changed. Returns 200 + updated bet. |
| 3 | Today tab HTML | `webapp/static/today.html` | From mockup v2 aesthetic. Live status strip, 4 control buttons, today's matches table, bankroll block, 30-day P&L sparkline (reuses aggregation from `daily_runs`). |
| 4 | Control-button UX | same file + minimal JS | Optimistic disable on click ("Queued…" → "Running"). Two-phase override button (5s auto-revert) + modal with explicit run_date. All buttons lock while any flow is `*_running`. |
| 5 | Bet-row edit affordance | same file + minimal JS | Inline prediction/stake edit form. Countdown chip per bet: green (>30m), amber (5-30m), red (<5m). Auto-locks visually when `now >= kickoff - 30m`. Tooltip explains lock with exact lock time. |
| 6 | Status polling | minimal JS | `setInterval(() => fetch("/api/status/today"), 2500)`. Updates status strip + unlocks/locks buttons based on status. |

### Agent 11B: Query DSL Engine
**Type:** `python-pro`
**Scope:** new `src/soccersmartbet/webapp/query/` package (parser, compiler, models). NO routes — routes are Wave 12's consumers.

| # | File / Task | Target | Notes |
|---|-------------|--------|-------|
| 1 | DSL parser | `webapp/query/parser.py` | Grammar: `key:value` pairs separated by spaces. Keys: `league`, `team`, `date`, `month`, `stake`, `odds`, `outcome`, `bettor`, `prediction`. Values support ranges (`>2.5`, `<1.5`, `1.5-3.0`), lists (`real-madrid,barcelona`), negation (`!draw`). ~80 lines hand-rolled — no pyparsing. |
| 2 | Filter-to-SQL compiler | `webapp/query/compiler.py` | Takes parsed filter → returns `(SQL WHERE clause string, params dict)`. Safe parameter binding throughout — no string interpolation. Returns a reusable SELECT over `bets JOIN games` with the WHERE clause injected. |
| 3 | Pydantic result models | `webapp/query/models.py` | `BetRow`, `FilterResult` (rows + aggregates: count, total_stake, total_pnl, win_rate). |
| 4 | Shared query service | `webapp/query/service.py` | `run_filter(filter_dsl: str) -> FilterResult`. Single entrypoint used by Wave 12 agents. Caps result set at 2000 rows (safety net; user default cap is 500 for AI insights). |
| 5 | Unit tests | `tests/webapp/query/` | Parse 10 representative query strings. Verify SQL generation is injection-safe (pass crafted malicious input, confirm parameterization). Tests use pytest — follow existing Wave 3 test style (deleted; build from scratch or flag for Wave 15). |

### Wave 11 completion criteria
- Today tab functional at `http://127.0.0.1:8083/today` — manual triggers work, bet edit works with window enforcement.
- Query DSL parses and executes against the live `bets` table, returns correct result sets for 5+ test queries.

---

## Wave 12 — Stats Pages + AI Insights ⬜ NOT STARTED (2 agents, parallel, depends on Wave 11's Query DSL)

Two independent agents. Both consume the Query DSL from Wave 11B.

### Agent 12A: History, P&L, Team/League Tabs
**Type:** `fullstack-developer`
**Scope:** new `src/soccersmartbet/webapp/routes/stats.py`, static pages for History / P&L / Team / League tabs

| # | File / Task | Target | Notes |
|---|-------------|--------|-------|
| 1 | `GET /api/bets?filter=<dsl>` endpoint | | Uses 11B's query service. Returns `FilterResult` JSON. URL-shareable — dashboard sets filter in address bar. |
| 2 | `GET /api/pnl?filter=<dsl>` endpoint | | Time-series aggregation of filtered bets — cumulative P&L by day, per-bettor. Returns JSON array consumable by chart. |
| 3 | `GET /api/teams/{team_id}/stats` + `GET /api/leagues/{league}/stats` | | Per-team and per-league rollups: total bets, win rate, P&L, notable games. |
| 4 | History tab HTML | `webapp/static/history.html` | Filter panel (dropdowns) + DSL text input (synced to URL). Filtered bet table in carnival aesthetic. "Generate insight" button calls Wave 12B's endpoint. |
| 5 | P&L tab HTML | `webapp/static/pnl.html` | Two-line chart (user vs AI, cumulative P&L). Filter reactive. Inline SVG rendering — no chart library build step. |
| 6 | Team/League hub HTML | `webapp/static/team.html`, `league.html` | Per-entity summary + full bet history for that team/league. Links from match-row team names. |

### Agent 12B: AI Insights Endpoint
**Type:** `ai-engineer`
**Scope:** new `src/soccersmartbet/webapp/routes/insights.py`, new `src/soccersmartbet/webapp/insights/` package (prompt, job manager)

| # | File / Task | Target | Notes |
|---|-------------|--------|-------|
| 1 | `POST /api/insights` endpoint | body `{filter_dsl}` | Runs 11B's query service (cap: 500 rows). If result is empty → 422. Otherwise enqueue an async job and return 202 + `{job_id}`. |
| 2 | `GET /api/insights/{job_id}` endpoint | | Returns job state: `queued` / `running` / `done` (markdown body) / `failed` (error). Dashboard polls every 2-3s. |
| 3 | Job manager | `webapp/insights/jobs.py` | In-memory `dict[job_id, InsightJob]` — no new DB table per user's request. Jobs expire after 1h. Bound concurrency to 2 concurrent LLM calls process-wide. |
| 4 | Prompt + LLM call | `webapp/insights/prompt.py` | **NOT a LangGraph flow** — single direct `openai.chat.completions.create(...)` call. System prompt: "expert user, deep football knowledge, skip obvious stats, focus on edge against AI / stake correlation / league blind spots. Max 5 bullets." Serialize bet rows as markdown table into the user message. Structured output — force markdown, no JSON. |
| 5 | Frontend trigger | Integrated into History tab (12A's file) | "Generate insight" button on the history page. Shows loading spinner → polls job endpoint → renders markdown below the filter table. |

### Wave 12 completion criteria
- All four tabs (Today, History, P&L, Team/League) render correctly with carnival aesthetic.
- Filter DSL drives both query results and on-demand AI insights.
- Dashboard complete at `http://127.0.0.1:8083/` with navigation between tabs.

### After Wave 12
- Dashboard fully operational.
- Manual flow triggers + override + bet modification live.
- Filter DSL drives history, P&L, and AI insights.
- All triggers audited in `run_events`; all bet edits audited in `bet_edits`.

---

## Wave 13 — Cup-Tie Context (2-Leg Match Support) ⬜ NOT STARTED

Extend the pre-gambling report to render 2-legged cup ties correctly: when today's game is a 2nd leg, show the 1st-leg result inline with correct team/goal attribution; when it's a 1st leg, surface return-leg info if known.

Deferred from Wave 8 on 2026-04-18 — no 2-legged cup ties currently on the schedule to validate against. Pick up when an actual 2nd leg appears.

### Agent 13A: Cup-Tie First-Leg Context (helper + renderer wiring)
**Type:** `python-pro`
**Scope:** new helper `src/soccersmartbet/pre_gambling_flow/tools/game/fetch_cup_tie_context.py`; renderer updates in `src/soccersmartbet/reports/html_report.py`. No schema changes, no DB writes.

| # | File / Task | Target | Notes |
|---|-------------|--------|-------|
| 1 | New helper — cup-tie detector | FotMob match response | Read `roundInfo` / aggregate metadata from `get_match_data(match_id)`. Detect if the fixture is part of a 2-legged cup tie and which leg it is. If regular league match → return `is_cup_tie=False` and nothing else. |
| 2 | If 2nd leg — extract 1st-leg result | Same FotMob response | Pull 1st-leg score + date from the match payload. **Critical invariant: 2nd-leg home team was the 1st-leg away team.** Return raw structured data keyed by team identity (not by home/away role), so the renderer cannot confuse sides. Include aggregate if present. |
| 3 | If 1st leg — surface return-leg info | Same FotMob response | Return 2nd-leg venue + date if exposed. |
| 4 | Optional enrichment from our DB | `games` table | If the 1st-leg match happens to exist in our `games` table (because we bet on it), attach the stored row. Read-only. No inserts. No schema changes. |
| 5 | Pydantic output model | New file (not in shared `structured_outputs.py`) | `{is_cup_tie, leg, first_leg: {team_a, team_b, score_a, score_b, date}, aggregate, return_leg_venue, return_leg_date}`. Keyed by team identity, not home/away. |
| 6 | Wire renderer — match header cup-tie inline | `html_report.py` match header | First-leg result inline when helper returns cup-tie data. Inversion already handled inside helper's structured data (team-identity-keyed). |

**Verify:** call against a known 2nd-leg fixture (e.g. a CL/EL knockout 2nd leg) and a regular league match. Confirm inversion handled correctly. Then verify the rendered report displays first-leg result correctly for the team-identity mapping.

---

## Wave 14 — Competition Expansion + Polish (1 agent)

### Agent 14A: League Expansion + Final Polish
**Type:** `python-pro`
**Scope:** `db/seeds/`, `src/soccersmartbet/team_registry.py`, documentation

| # | File / Task | Target | Notes |
|---|-------------|--------|-------|
| 1 | Add Euro / World Cup national team support | football-data.org EC/WC | Seasonal activation |
| 2 | Final documentation update | Update README, ORCHESTRATION_STATE | Reflect current system state |
| 3 | Database backup to disk | Automated pg_dump to a local backup directory | Cron or script that dumps the staging DB to `~/backups/soccersmartbet/` with date-stamped filenames. Must survive docker-compose restarts. |

### After Wave 14
- Full system test across multiple leagues
- Verify: DB backup file exists and is restorable

---

## Wave 15 — Testing Scheme ⬜ TBD

Full testing redesign. Scope, strategy, and tooling to be planned separately.
