# SoccerSmartBet Revival — Progress Tracker

> **Last updated:** 2026-04-22 (Wave 10A code shipped — live DDL gated on Omer's OK) | **Branch:** Dashboard-Platform-Foundation

## Summary

```
Progress: [🟩🟩🟩🟩🟩🟩🟩🟩🟩⬜⬜⬜⬜⬜⬜] 9/15 waves done
```

| What | Status |
|------|--------|
| 11 data tools (FotMob, football-data.org, The Odds API, winner.co.il) | Working |
| Team registry (107 teams, Hebrew, fuzzy match, top-5 leagues + Israeli) | Working, thread-safe with reload |
| Web app tool tester (SSE streaming, concurrent, dual odds) | Working |
| DB schema (7 tables) | Running on PostgreSQL (docker-compose, port 5433, TZ=Asia/Jerusalem), pgweb on 8082 |
| State + prompts + structured outputs | Updated and wired into graph |
| Pre-Gambling LangGraph flow | **Working E2E** — wall-clock scheduler, daily automation |
| Telegram bot + triggers + ISR time + game reports | **Working** — tested E2E, notify node in graph |
| Gambling Flow (AI bets + validation) | **Working E2E** — Telegram UI + LangGraph AI betting + verification |
| Post-Games Flow (results + P&L) | **Working E2E** — FotMob overviewFixtures results, PnL calculator, Telegram summary, auto-triggered |
| Daily automation (wall-clock scheduler) | **Working E2E** — full cycle proven daily since 2026-04-12 |
| Operator Dashboard (webapp) | **NOT BUILT** — Waves 10/11/12 |
| Cup-Tie 2-leg support | **NOT BUILT** — Wave 13 |

---

## Wave Status

| Wave | Status | Notes |
|------|--------|-------|
| 0 | 🟢 Done | Setup, curation, schema, enrichment verification |
| 1 | 🟢 Done | FotMob client, team registry, winner client |
| 2 | 🟢 Done | All 11 tools working against live APIs |
| 3 | 🟢 Done | Web app works. Tests obsolete — deleted, deferred to Wave 15. |
| 4 | 🟢 Done | Subgraph architecture, E2E verified with expert summary |
| 5 | 🟢 Done | Telegram bot, triggers, game reports HTML, ISR timezone |
| 6 | 🟢 Done | Gambling (6A) + Post-Games (6B). E2E tested. |
| 7 | 🟢 Done | daily_runs table, wall-clock scheduler, full automation |
| 8 | 🟢 Done | Report refactor track: 8A + 8B + 8C + 8E done. 8D skipped. Live-DB migration applied 2026-04-19 (backup: `~/soccersmartbet_backup_before_wave8_20260418_163145.sql`, 360KB, zero row loss). |
| 9 | 🟢 Done | Robustness carryovers: 9A missing-results alert (#55), 9B no-games-day verification + fetch-failure conflation fix (#62), 9C startup-recovery verified (no code change). Post-review pass added operator Telegram alerts on pre-gambling AND post-games crashes, `TELEGRAM_CHAT_ID` startup check, date-embedded no-games callbacks, and zeroed all remaining timezone-rule violations (two new helpers: `today_isr()`, `isr_datetime()`). Bug #63 filed for the deferred not-finished-games edge case. Branch `wave9`, 13 commits. |
| 10 | 🟡 Code Ready / DDL Pending | Dashboard platform foundation. 10A code shipped (FastAPI shell, conn pool, audit, mutex, status/health endpoints, async lifecycle). Live DDL is staged in `001_create_schema.sql` but NOT applied — bot will fail to start until Omer OKs `docker exec ... psql ...` for the 4 ALTER + 2 CREATE TABLE + 4 CREATE INDEX statements. Blocks Waves 11/12. |
| 11 | ⬜ Not Started | Dashboard: Today tab + Query DSL (2 parallel agents, depends on Wave 10). |
| 12 | ⬜ Not Started | Dashboard: Stats/P&L/History tabs + AI insights (2 parallel agents, depends on Wave 11's Query DSL). |
| 13 | ⬜ Not Started | Cup-Tie 2-leg Match Support — pick up when an actual 2nd leg appears on schedule. |
| 14 | 🟡 Partial | Competition expansion + polish: Israeli league + CL/EL done. Euro/WC + backup pending. |
| 15 | ⬜ TBD | Testing scheme — to be planned separately |

---

## Wave 0 — Setup + Tools Curation ✅

| # | Task | Status |
|---|------|--------|
| 0.1 | Clean dead refs + deps | 🟢 Done |
| 0.2 | Tools curation session | 🟢 Done |
| 0.3 | Schema update (teams table) | 🟢 Done |
| 0.4 | Verify enrichment sources | 🟢 Done |

---

## Wave 1 — Core Infrastructure ✅

### Agent 1A: FotMob Client
| # | Task | Status | Notes |
|---|------|--------|-------|
| 1 | Rewrite fotmob_client.py | 🟢 Done | x-mas signing, direct requests |
| 2 | get_league_table | 🟢 Done | |
| 3 | get_team_data / get_match_data | 🟢 Done | |
| 4 | get_team_news | 🟢 Done | |
| 5 | find_team | 🟢 Done | |

### Agent 1B: Team Name Registry
| # | Task | Status | Notes |
|---|------|--------|-------|
| 1 | team_registry.py + fuzzy matching | 🟢 Done | Levenshtein + substring + exact, thread-safe |
| 2 | teams in DB | 🟢 Done | 107 teams with Hebrew names, FotMob IDs |
| 3 | teams_seed.py | 🟢 Done | football-data.org bulk seeder |
| 4 | Israeli Premier League (14 teams) | 🟢 Done | |
| 5 | Hebrew name mappings | 🟢 Done | All top-5 league teams mapped |

### Agent 1C: winner.co.il Odds Client
| # | Task | Status | Notes |
|---|------|--------|-------|
| 1 | fetch_winner_odds.py | 🟢 Done | |
| 2 | API endpoint | 🟢 Done | www.winner.co.il/api/v2/publicapi/ |
| 3 | Market parsing | 🟢 Done | |
| 4 | League filtering | 🟢 Done | |
| 5 | fetch_all_winner_odds | 🟢 Done | |

---

## Wave 2 — Fix Existing + New Tools ✅

### Agent 2A: Fix FotMob Game Tools
| # | Task | Status |
|---|------|--------|
| 1 | Fix fetch_venue.py | 🟢 Done |
| 2 | Fix fetch_weather.py | 🟢 Done |

### Agent 2B: Fix FotMob Team Tools
| # | Task | Status |
|---|------|--------|
| 1 | Fix fetch_form.py | 🟢 Done |
| 2 | Fix fetch_injuries.py | 🟢 Done |
| 3 | Fix fetch_league_position.py | 🟢 Done |
| 4 | Fix calculate_recovery_time.py | 🟢 Done |
| 5 | Create fetch_team_news.py | 🟢 Done |

### Agent 2C: Daily Fixtures
| # | Task | Status |
|---|------|--------|
| 1 | Create fetch_daily_fixtures.py | 🟢 Done |

---

## Wave 3 — Web App + Cleanup ✅

### Agent 3A: Web App
| # | Task | Status |
|---|------|--------|
| 1 | Wire new tools | 🟢 Done |
| 2 | Winner odds display | 🟢 Done |
| 3 | Team news display | 🟢 Done |
| 4 | SSE streaming | 🟢 Done |
| 5 | Concurrent execution | 🟢 Done |

> Tests (former Agent 3B) were obsolete — hardcoded dates, brittle assertions, zero coverage of Waves 4-7. Deleted. Testing redesign deferred to Wave 15.

---

## Wave 4 — LangGraph Pre-Gambling Flow ✅

### Agent 4A: Core Flow + Pipeline Nodes
| # | Task | Status |
|---|------|--------|
| 1 | Verify state.py for LangGraph 1.x | 🟢 Done |
| 2 | Update structured_outputs.py | 🟢 Done |
| 3 | Create smart_game_picker.py | 🟢 Done |
| 4 | Create persist_games.py | 🟢 Done |
| 5 | Create combine_reports.py | 🟢 Done |
| 6 | Create persist_reports.py | 🟢 Done |
| 7 | Create graph_manager.py | 🟢 Done |

### Agent 4B: Intelligence Agents + Subgraph Orchestration
| # | Task | Status |
|---|------|--------|
| 1 | Create game_intelligence.py | 🟢 Done |
| 2 | Create team_intelligence.py | 🟢 Done |
| 3 | Create analyze_game.py subgraph | 🟢 Done |
| 4 | Add DB write utilities | 🟢 Done |

---

## Wave 5 — Telegram Bot + Triggers + Game Reports + ISR Time ✅

### Agent 5A: ISR Timezone Utility
| # | Task | Status |
|---|------|--------|
| 1 | Create timezone utility | 🟢 Done |
| 2 | Apply to game picker | 🟢 Done |
| 3 | Apply to all time references | 🟢 Done |

### Agent 5B: Telegram Bot + Flow Triggers
| # | Task | Status |
|---|------|--------|
| 1 | Create Telegram bot client | 🟢 Done |
| 2 | Create Pre-Gambling daily trigger | 🟢 Done |
| 3 | Create Gambling trigger | 🟢 Done |

### Agent 5C: HTML Game Report Pages
| # | Task | Status |
|---|------|--------|
| 1 | Static HTML report per game | 🟢 Done |
| 2 | Design Telegram gambling time message | 🟢 Done |
| 3 | Serve HTML pages | 🟢 Done |

---

## Wave 6 — Gambling + Post-Games ✅

### Agent 6A: Gambling Flow
| # | Task | Status |
|---|------|--------|
| 1 | "Want to bet?" with Yes/No + deadline | 🟢 Done |
| 2 | Betting UI (1️⃣/𝕏/2️⃣ + variable stakes) | 🟢 Done |
| 3 | AI betting agent | 🟢 Done |
| 4 | Bet verifier | 🟢 Done |
| 5 | Gambling graph_manager.py | 🟢 Done |
| 6 | Register handlers in bot | 🟢 Done |

### Agent 6B: Post-Games Flow
| # | Task | Status |
|---|------|--------|
| 1 | Schema: result + pnl columns | 🟢 Done |
| 2 | fetch_results.py (FotMob) | 🟢 Done |
| 3 | pnl_calculator.py | 🟢 Done |
| 4 | notify_daily_summary.py | 🟢 Done |
| 5 | post_games graph_manager.py | 🟢 Done |

---

## Wave 7 — Daily Runs Tracking + Wall-Clock Scheduler ✅

### Agent 7A: daily_runs DB Table + Scheduler Fix
| # | Task | Status |
|---|------|--------|
| 1 | Create daily_runs table | 🟢 Done |
| 2 | Wall-clock poller (replace APScheduler) | 🟢 Done |
| 3 | Startup recovery | 🟢 Done |
| 4 | Wire flow nodes to daily_runs | 🟢 Done |
| 5 | Post-games auto-trigger (midnight-crossing safe) | 🟢 Done |
| 6 | No-games day interactive prompt | 🟢 Done |

---

## Wave 8 — Report Refactor Track 🟢 DONE (sequential)

Execution order: **8A → 8B → 8C → 8D → 8E.** 8D skipped (superseded by 8B + 8C).

Accepted design deviations from the original plan (approved by Omer during v3–v6 iterations):
- Task 8E #5 "implied-probability bar" — **removed** entirely (added no signal above the raw odds).
- Task 8E #10 palette — shipped near-black with green undertone (`#0d1410` bg, `#1e2a22` hairlines, `#2e6b2d` / `#3d7a37` structural green, `#c8a84b` gold accent) instead of the originally planned `#0f0f0f` + `#222`.
- Editorial-terminal redesign (v7) was rejected and reverted to v6 green.

| # | Agent | Type | Status |
|---|-------|------|--------|
| 8A | Contract Investigation + H2H Diagnosis | python-pro | 🟢 Done |
| 8B | Tighten Agent Prompts + Structured Outputs | ai-engineer | 🟢 Done |
| 8C | H2H Rate-Limit Mitigation | python-pro | 🟢 Done | League hint threaded end-to-end (state → Send → game_intelligence → fetch_h2h). 1 competition scan + 1 H2H per game. Per-call exponential backoff `[5,10,20,40,80]`. Unsupported league or retry exhaustion → `"couldn't retrieve h2h due to API issues"`. Zero shared state — no buckets, no locks, no caches. LangGraph `Send()` owns parallelism. |
| 8D | H2H Fix Application (conditional) | — | ⚫ Skipped | Superseded by 8B + 8C. 8B built `_build_h2h_aggregate` from raw tool output; 8C made `fetch_h2h` reliable for supported leagues with graceful degradation for the rest. No residual layer needs a fix. End-to-end verification will happen naturally on the first pre-gambling run after 8E's live-DB migration. |
| 8E | Report HTML Full Overhaul | python-pro | 🟢 Done | Full mobile-first rewrite of `html_report.py` (5" phone, bettor's-spreadsheet aesthetic, table-comparison layout, implied-probability bar, form pills, no crests/VS/emoji/color coding). `combine_reports.py` + `ai_betting_agent.py` migrated to new column shape (bullets + structured fields). Live DB migration applied with backup + row-count verification. |

---

## Wave 9 — Robustness Carryovers 🟢 DONE (2026-04-22)

| # | Agent | Status |
|---|-------|--------|
| 9A | Post-Games Missing-Results Alert (#55) | 🟢 Done |
| 9B | No-Games-Day Robustness + Fetch-Failure Fix (#62) | 🟢 Done |
| 9C | Startup Recovery Verification | 🟢 Done (no code change) |

**Bottom line**: skipped games now surface in Telegram; fetch failures no longer masquerade as no-games days; post-games can't double-fire on crash; no-games callback survives midnight; `TELEGRAM_CHAT_ID` checked at startup; zero remaining timezone-rule violations (new helpers `today_isr()`, `isr_datetime()`). No DB / schema changes. Branch `wave9`, 14 commits.

Issues: #55 closed, #62 closed, #63 filed (not-yet-finished edge case, low priority).

---

## Wave 10 — Dashboard Platform Foundation 🟡 CODE READY / DDL PENDING (1 agent)

Single-agent blocker wave. Everything in Waves 11 and 12 depends on this landing.

| # | Agent | Type | Status |
|---|-------|------|--------|
| 10A | Platform foundation (FastAPI shell, `psycopg2.pool.ThreadedConnectionPool`, schema additions, `run_events`/`bet_edits` writers, `daily_runs.status` mutex helper, `GET /api/status/today` + `/api/health`) | python-pro | 🟢 Done (code) — ⏳ live DDL gated on Omer's OK |

**Bottom line (code shipped):**
- `webapp/` package created: `app.py` (FastAPI on `127.0.0.1:8083`, error middleware that does NOT leak `str(exc)`, 1s TTL status cache), `audit.py` (`EventType` constants + `write_run_event` + `write_bet_edit`), `run_mutex.py` (`acquire_flow` short-tx mutex, `release_flow`, `mark_failed` with `LockNotAvailable` swallow, `*_running` collisions translate to `FlowConflict`), `runtime_state.py` (shared `LAST_POLLER_TICK` — clean dependency direction).
- `db.py` — `psycopg2.pool.ThreadedConnectionPool(size 5)` with `get_conn()` / `get_cursor()` context managers. All 4 `daily_runs.py` call-sites migrated. **14 OTHER call-sites (gambling/, pre_gambling/, post_games/, team_registry, reports/) still use direct `psycopg2.connect()` — pool is largely unused on the hot paths until those migrate.** Track for follow-up wave.
- `triggers.py` — `start_scheduler()` is now async; manual PTB lifecycle (`initialize` / `updater.start_polling` / `start`) replaces `application.run_polling()`. uvicorn server task + poller task under `asyncio.gather`. SIGTERM/SIGINT handler + 30s bounded shutdown via `asyncio.wait_for`. Mutex + `run_events` audit integrated into `trigger_pre_gambling_and_notify` and `_fire_post_games`. Both flows now spawned via `asyncio.create_task` so the 60s poller heartbeat (`LAST_POLLER_TICK`) stays fresh during multi-minute runs.
- `pyproject.toml` — `fastapi` + `uvicorn` moved from `[web]` extras into core dependencies.
- Schema staged: `001_create_schema.sql` appended with idempotent block (`ADD COLUMN IF NOT EXISTS`, `CREATE TABLE IF NOT EXISTS`, named `IF NOT EXISTS` indexes) — 4 ALTER on `daily_runs` (status / last_trigger_source / attempt_count / last_error), `run_events` table, `bet_edits` table, `idx_run_events_date_time`, `idx_bet_edits_bet`, `idx_bets_bettor`, `idx_games_league`.
- Verification: all imports clean, `start_scheduler` is a coroutine, zero `datetime.now`/`utcnow` regressions, pool can `SELECT 1` against live DB.

**⏳ Action required from Omer before bot restart:**
Live-DDL must be applied via `docker exec soccersmartbet-staging psql -U postgres -d soccersmartbet_staging -f /docker-entrypoint-initdb.d/001_create_schema.sql` OR by running the Wave 10 block standalone. Without it: `get_daily_run` SELECTs `status`/`last_trigger_source`/`attempt_count`/`last_error` and the bot crashes at first poller tick. Per CLAUDE.md, this needs Omer's explicit OK for the specific DDL.

**Open follow-up (not blocking commit, tracked):**
- Migrate 14 remaining `psycopg2.connect()` call-sites to `db.get_conn()` so the pool is meaningful (separate wave).
- Wave 11 needs a startup-recovery routine that scans for stuck `*_running` rows older than N hours and transitions them to `failed` (otherwise a process crash mid-flow blocks all future fires for that date).

Architectural constraints (single process, `daily_runs.status` mutex with `SELECT FOR UPDATE NOWAIT`, sync `graph.invoke` + `asyncio.to_thread`, 2-5s polling, connection pool required, no async node rewrite, no SSE, no second process, no auth) are LOCKED — see `task_breakdown.md` for full list. Design mockup: `docs/wave10/mockup_today_v2.html`.

---

## Wave 11 — Dashboard: Today Tab + Query DSL ⬜ NOT STARTED (2 parallel agents)

Depends on Wave 10. Neither agent consumes the other.

| # | Agent | Type | Status |
|---|-------|------|--------|
| 11A | Today tab — control panel + bet modification (`POST /api/runs`, `PATCH /api/bets/{id}`, Today HTML, countdown chips, override button) | fullstack-developer | ⬜ Pending |
| 11B | Query DSL engine (parser + filter-to-SQL compiler + shared query service) | python-pro | ⬜ Pending |

---

## Wave 12 — Dashboard: Stats Pages + AI Insights ⬜ NOT STARTED (2 parallel agents)

Depends on Wave 11's Query DSL (11B). Both agents consume it.

| # | Agent | Type | Status |
|---|-------|------|--------|
| 12A | History / P&L / Team / League tabs (`GET /api/bets`, `GET /api/pnl`, per-team/league stats, carnival aesthetic) | fullstack-developer | ⬜ Pending |
| 12B | AI insights endpoint (`POST /api/insights` + `GET /api/insights/{job_id}`, single-LLM-call — NOT a LangGraph flow, in-memory job store) | ai-engineer | ⬜ Pending |

---

## Wave 13 — Cup-Tie 2-Leg Match Support ⬜ NOT STARTED

Trigger: pick up when an actual 2-legged cup tie appears on the schedule so the helper can be validated end-to-end.

### Agent 13A: Cup-Tie First-Leg Context
| # | Task | Status |
|---|------|--------|
| 1 | Create fetch_cup_tie_context.py helper (FotMob roundInfo/aggregate) | ⬜ Pending |
| 2 | Pydantic output keyed by team identity (not home/away) | ⬜ Pending |
| 3 | Wire renderer — cup-tie inline in match header (html_report.py) | ⬜ Pending |
| 4 | Verify FotMob cup-tie metadata against a real 2-legged tie | ⬜ Pending |

---

## Wave 14 — Competition Expansion + Polish 🟡 PARTIALLY DONE

| # | Task | Status | Notes |
|---|------|--------|-------|
| 1 | Israeli Premier League | 🟢 Done | 14 teams, FotMob IDs, Hebrew names |
| 2 | CL/EL teams | 🟢 Done | Main CL teams in registry |
| 3 | Euro/WC national teams | ⬜ Pending | Search lists added, no national teams in registry |
| 4 | FotMob IDs in registry | 🟢 Done | 104/107 teams have FotMob IDs |
| 5 | Full league coverage | 🟢 Done | 107 teams, all top-5 leagues with Hebrew names |
| 6 | Final documentation | ⬜ Pending | |
| 7 | Database backup to disk | ⬜ Pending | |

---

## Wave 15 — Testing Scheme ⬜ TBD

To be planned separately.

---

## Known Issues / Tech Debt

All tracked as GitHub issues: #44–#56. See `gh issue list --repo Omer-Pinto/SoccerSmartBet`.
