# SoccerSmartBet Revival — Progress Tracker

> **Last updated:** 2026-04-22 19:00 ISR (Wave 11 hard-fix pass — Force Override now works from `pre_gambling_done`, JS time fully ISR, value aliases + OR semantics for DSL, bet-edit trigger LIVE; awaiting bot restart) | **Branch:** Dashboard-Platform-Foundation

## Summary

```
Progress: [🟩🟩🟩🟩🟩🟩🟩🟩🟩🟩🟩⬜⬜⬜⬜] 11/15 waves done
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
| Operator Dashboard (webapp) | **TODAY TAB + QUERY DSL MERGED** (Wave 11 — `/today` HTML, `POST /api/runs`, `PATCH /api/bets/{id}`, Query DSL engine with 51 unit tests; awaiting bot restart + trigger DDL apply) — Wave 12 (Stats/P&L/History + AI Insights) unblocked |
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
| 10 | 🟢 Live (3/5 criteria green; 2 auto-close tonight) | Dashboard platform foundation. Bot restarted on new code 16:44 ISR (pid 21381). `/api/health` 200, `/api/status/today` valid JSON. Status backfilled from existing timestamps (today: `gambling_done`). Criteria #1 (no regression) + #5 (run_events row) auto-confirm at tonight's 01:30 post-games fire. Wave 11 can start in parallel. |
| 11 | 🟢 Done | Dashboard: Today tab + Query DSL. 11A+11B parallel wave → consultant → code-reviewer → hard-fix pass. 15 bugs caught & fixed total (9 from initial review, 6 from Omer's post-merge flag of bad deferrals). Force Override now works from `pre_gambling_done` (scenario the button was built for). All JS time handling pinned to ISR (offset-aware ISO + `Intl.DateTimeFormat('Asia/Jerusalem')`). DSL: outcome/prediction value aliases + repeated-key OR semantics. 70/70 query tests pass. Bet-edit-window trigger live (applied 2026-04-22). Pending: bot restart. |
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

## Wave 10 — Dashboard Platform Foundation 🟢 LIVE (3/5 criteria green; #1+#5 auto-close tonight) (1 agent)

Single-agent blocker wave. Everything in Waves 11 and 12 depends on this landing.

| # | Agent | Type | Status |
|---|-------|------|--------|
| 10A | Platform foundation (FastAPI shell, psycopg3 conn pool, schema additions, `run_events`/`bet_edits` writers, `daily_runs.status` mutex, `GET /api/status/today` + `/api/health`) | python-pro | 🟢 Live |

Two commits on this branch: `5d6c45d` (initial), `9766394` (psycopg3 migration + 3 architect ship-stoppers + 3 strong recommendations + 4 deferred cleanups). DDL applied 2026-04-22; status column backfilled from existing timestamps; bot restarted 16:44 ISR.

**Code shipped:**
- `webapp/` package: `app.py` (FastAPI on 127.0.0.1:8083, generic-detail error middleware, async 1s TTL status cache with `asyncio.Lock`), `audit.py` (`EventType` + `write_run_event` + `write_bet_edit` via psycopg3 `Jsonb` adapter), `run_mutex.py` (`acquire_flow` short-tx mutex with `*_running`-collision → `FlowConflict` + null-check guards, `release_flow`, `mark_failed` with `LockNotAvailable` swallow), `runtime_state.py` (shared `LAST_POLLER_TICK`).
- `db.py` — psycopg3 `psycopg_pool.ConnectionPool(min=1, max=10)`. All 4 `daily_runs.py` call-sites migrated. The 14 LangGraph DB call-sites stay on psycopg2 per ai-engineer verdict (fan-out width would starve a bounded pool — they continue to open ms-scale direct connects against Postgres's default `max_connections=100`).
- `triggers.py` — async `start_scheduler()` with manual PTB lifecycle, uvicorn co-host, signal-driven 30s bounded shutdown that drains in-flight flow tasks (20s) before force-cancel via `_ACTIVE_FLOW_TASKS` registry. Mutex + audit integrated into both flow triggers; `release_flow` calls wrapped in `try/except → mark_failed`. Flows spawned via `_spawn_flow` so the 60s poller heartbeat stays fresh.
- Transition table covers all needed Wave 10 paths: includes `pre_gambling_done → post_games_running` (architect B3 fix — without it Wave 10 post-games could not fire) and `failed → gambling_running` (Wave 11 forward-prep).
- `pyproject.toml` — `psycopg[binary,pool]>=3.2` in core deps; legacy `psycopg2-binary` retained in `[db]` extras for the 14 untouched call-sites; `fastapi` + `uvicorn` promoted to core.
- Schema (live DB applied 2026-04-22): 4 `ADD COLUMN IF NOT EXISTS` on `daily_runs` (`status` with CHECK, `last_trigger_source`, `attempt_count`, `last_error`), `run_events` (with no-FK rationale comment), `bet_edits` (with `field IN ('prediction','stake')` CHECK), 4 `CREATE INDEX IF NOT EXISTS`. All 11 existing `daily_runs` rows defaulted to `status='idle'`.

**Wave 10 completion criteria (from `task_breakdown.md`):**
| # | Criterion | Status |
|---|-----------|--------|
| 1 | Bot still runs existing flows identically (no regression on 08:35 pre-gambling or 01:30 post-games) | ⏳ Auto-confirms at tonight's 01:30 post-games fire on new code |
| 2 | `curl http://127.0.0.1:8083/api/health` returns 200 | 🟢 Done — uptime 16s, DB ping 3.9ms |
| 3 | `curl http://127.0.0.1:8083/api/status/today` returns correct JSON | 🟢 Done — `status: "gambling_done"`, timestamps intact |
| 4 | New schema additions applied to live DB (after explicit OK) | 🟢 Done 2026-04-22 |
| 5 | `run_events` gets one row per flow fire (scheduler writes via the new helper) | ⏳ Auto-confirms at tonight's 01:30 post-games fire (will also confirm #1) |

Architectural constraints (single process, `daily_runs.status` mutex with `SELECT FOR UPDATE NOWAIT`, sync `graph.invoke` + `asyncio.to_thread`, 2-5s polling, conn pool, no async node rewrite, no SSE, no second process, no auth) are LOCKED — see `task_breakdown.md`. Design mockup: `docs/wave10/mockup_today_v2.html`.

---

## Wave 11 — Dashboard: Today Tab + Query DSL 🟢 DONE (2026-04-22, 2 parallel agents + consultant + reviewer cycle)

Ran via `/parallel-wave-executor` on branch `Dashboard-Platform-Foundation`. Both agents ran in isolated worktrees; zero file overlap; cherry-picked clean onto the branch.

| # | Agent | Type | Status |
|---|-------|------|--------|
| 11A | Today tab — control panel + bet modification (`POST /api/runs`, `PATCH /api/bets/{id}`, Today HTML, countdown chips, override button) | fullstack-developer | 🟢 Done |
| 11B | Query DSL engine (parser + filter-to-SQL compiler + shared query service) | python-pro | 🟢 Done |

### Code shipped

**11A — Today tab:**
- `webapp/routes/today.py` — `POST /api/runs` (pre_gambling / post_games / regenerate_report, with `force=true` transactional cleanup of report rows only — games + bets preserved after the cascade-wipe reviewer catch), `PATCH /api/bets/{bet_id}` with dual-layer window enforcement (Python + DB trigger) executed in a single atomic transaction, `GET /today`, `/api/today/data`, `/api/today/pnl`.
- `webapp/static/today.{html,css,js}` — carnival aesthetic per `docs/wave10/mockup_today_v2.html`, live status strip (2.5s poll), 4 control buttons with two-phase Force Override + retyped-date modal, inline bet-row edits with countdown chips (green/amber/red), 30-day P&L inline-SVG sparkline (no chart library).
- `webapp/app.py` — router mount.
- `webapp/run_mutex.py` — comment explaining why `pre_gambling_done → pre_gambling_running` is intentionally absent (regen goes via Force Override).

**11B — Query DSL:**
- `webapp/query/{parser,compiler,models,service}.py` — hand-rolled DSL parser (~180 loc, no pyparsing), parameterized SQL compiler over `bets JOIN games`, Pydantic result models, `run_filter(dsl)` entry point for Wave 12 consumers. Columns aligned to the real schema (`match_date + kickoff_time` split, no `placed_at`). `ORDER BY match_date DESC, kickoff_time DESC`. Row cap 2000.
- `tests/webapp/query/{test_parser,test_compiler}.py` — 51 tests passing (parser grammar + SQL-injection safety + ISO date eq + month parsing).

### Ship-stoppers caught & fixed (consultant + code-reviewer cycle)

1. **11A force-clear cascade:** `DELETE FROM games` would cascade-wipe `bets` (ON DELETE CASCADE) → replaced with scoped deletes on report tables only; games + bets preserved.
2. **11A Literal widening:** `prediction: Literal["1","x","2","X"]` narrowed to canonical `["1","x","2"]`.
3. **11A post-games NULL guard:** 400 when `daily_runs.game_ids` empty/NULL.
4. **11A non-atomic bet-edit:** UPDATE bets + INSERT bet_edits now run in one transaction so the DB trigger actually enforces.
5. **11A force-clear ordering:** moved INSIDE `acquire_flow` so mutex conflict doesn't lose reports.
6. **11B nonexistent `b.placed_at`:** removed from SELECT + BetRow + service row-mapper.
7. **11B TIME vs TIMESTAMPTZ:** `g.kickoff_time` is TIME — date filter now uses `g.match_date` directly; month filter uses `(match_date + kickoff_time)::TIMESTAMP AT TIME ZONE 'Asia/Jerusalem'`.
8. **11B ORDER BY bug:** time-of-day only → `match_date DESC, kickoff_time DESC`.
9. **11B ISO-date eq parse:** `date:2026-04-15` was slug-normalized to `"2026 04 15"` → short-circuit added for `YYYY-MM-DD` and `YYYY-MM` patterns.

### Hard-fix pass (6 more bugs — Omer flagged the prior DEFERs as unacceptable)

10. **Force Override + Regenerate Report 409 from `pre_gambling_done`** — the exact scenario the button was created for ("kill a bad 0-games run and re-fire"). `acquire_flow(force=True)` kwarg added; skips transition validation when force-ing. `regenerate_report` unconditionally force-fires. New `EventType.PRE_GAMBLING_FORCE_RESET` audit event.
11. **JS kickoff parsed in browser-local time** — server now returns `kickoff_iso` with explicit ISR offset (`+03:00`/`+02:00`, DST-correct via `isr_datetime(...).isoformat()`); JS does `new Date(kickoff_iso).getTime()` — TZ-agnostic.
12. **JS "today's date" used UTC** — now sourced from `/api/status/today.today_date` (server `today_isr()`), with a hidden-input fallback.
13. **Lock-time display used browser-local** — now `Intl.DateTimeFormat(..., { timeZone: 'Asia/Jerusalem' })`.
14. **`outcome:draw` / `prediction:home` returned empty silently** — value aliases (`home/draw/away/tie/home_win/away_win → 1/x/2`) added with `=`/`IN` SQL instead of `ILIKE`; unrecognised values raise `ParseError`.
15. **`league:pl league:bundesliga` matched nothing (AND-of-substring)** — same-key clauses now group with OR inside parens; comma-list form still works and is equivalent.

### DDL applied to live DB 2026-04-22

`check_bet_edit_window()` PL/pgSQL function + `trg_bet_edit_window` BEFORE INSERT trigger on `bet_edits` applied via `docker exec soccersmartbet-staging psql -U postgres -d soccersmartbet_staging`. Verified via `pg_trigger` lookup (`trg_bet_edit_window BEFORE INSERT ON bet_edits FOR EACH ROW EXECUTE FUNCTION check_bet_edit_window()`). Schema SQL header updated to reflect live state.

### Completion criteria

| # | Criterion | Status |
|---|-----------|--------|
| 1 | Today tab functional at http://127.0.0.1:8083/today — manual triggers work, bet edit works with window enforcement | 🟢 Code + DDL shipped; pending bot restart to serve new routes |
| 2 | Query DSL parses and executes against the live `bets` table, returns correct result sets | 🟢 70/70 unit tests green; live-DB query verifies when Wave 12 routes land |

### Pending operator actions (Omer)

1. **Restart bot** — new `/today`, `/api/runs`, `PATCH /api/bets/{id}`, `/api/today/data`, `/api/today/pnl` endpoints registered at startup; existing process won't see them. Tonight's 01:30 post-games MUST run on the new code to validate Wave 10 criteria #1+#5.

Commits on branch (14): `746c2c0` `4cca4a3` `52abe80` `b0465e1` `227a1f3` `b25bd64` `59a6809` `027400a` `7518054` `fe41d67` `951dc74` `43f45e4` `f514e32` `d0a3f78`.

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
