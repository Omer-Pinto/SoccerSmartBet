# SoccerSmartBet Revival — Progress Tracker

> **Last updated:** 2026-04-19 | **Branch:** major_report_refactor

## Summary

```
Progress: [🟩🟩🟩🟩🟩🟩🟩⬜⬜⬜⬜⬜⬜] 7/13 waves done
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
| Offline Analysis Flow | **NOT BUILT** — Wave 10 |
| Cup-Tie 2-leg support | **NOT BUILT** — Wave 11 |

---

## Wave Status

| Wave | Status | Notes |
|------|--------|-------|
| 0 | 🟢 Done | Setup, curation, schema, enrichment verification |
| 1 | 🟢 Done | FotMob client, team registry, winner client |
| 2 | 🟢 Done | All 11 tools working against live APIs |
| 3 | 🟢 Done | Web app works. Tests obsolete — deleted, deferred to Wave 13. |
| 4 | 🟢 Done | Subgraph architecture, E2E verified with expert summary |
| 5 | 🟢 Done | Telegram bot, triggers, game reports HTML, ISR timezone |
| 6 | 🟢 Done | Gambling (6A) + Post-Games (6B). E2E tested. |
| 7 | 🟢 Done | daily_runs table, wall-clock scheduler, full automation |
| 8 | 🔵 In Progress | Report refactor track (sequential): 8A → 8B → 8C → 8D → 8E. 8A + 8B + 8C done. |
| 9 | ⬜ Not Started | Robustness carryovers: 9A missing-results alert, 9B no-games verify, 9C startup-recovery verify. Independent of Wave 8. |
| 10 | ⬜ Not Started | Offline Analysis Flow — multi-day gambling view. Deferred until enough betting data accumulated. |
| 11 | ⬜ Not Started | Cup-Tie 2-leg Match Support — pick up when an actual 2nd leg appears on schedule. |
| 12 | 🟡 Partial | Competition expansion + polish: Israeli league + CL/EL done. Euro/WC + backup pending. |
| 13 | ⬜ TBD | Testing scheme — to be planned separately |

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

> Tests (former Agent 3B) were obsolete — hardcoded dates, brittle assertions, zero coverage of Waves 4-7. Deleted. Testing redesign deferred to Wave 11.

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

## Wave 8 — Report Refactor Track 🔵 IN PROGRESS (sequential)

Execution order: **8A → 8B → 8C → 8D → 8E.**

| # | Agent | Type | Status |
|---|-------|------|--------|
| 8A | Contract Investigation + H2H Diagnosis | python-pro | 🟢 Done |
| 8B | Tighten Agent Prompts + Structured Outputs | ai-engineer | 🟢 Done |
| 8C | H2H Rate-Limit Mitigation | python-pro | 🟢 Done | League hint threaded end-to-end (state → Send → game_intelligence → fetch_h2h). 1 competition scan + 1 H2H per game. Per-call exponential backoff `[5,10,20,40,80]`. Unsupported league or retry exhaustion → `"couldn't retrieve h2h due to API issues"`. Zero shared state — no buckets, no locks, no caches. LangGraph `Send()` owns parallelism. |
| 8D | H2H Fix Application (conditional) | python-pro | ⬜ Pending | Likely skippable: 8B built `_build_h2h_aggregate`; 8C populates H2H reliably for supported leagues. Confirm on a real pre-gambling run once 8E migration lands. |
| 8E | Report HTML Full Overhaul | ui-designer + python-pro | ⬜ Pending |

---

## Wave 9 — Robustness Carryovers ⬜ NOT STARTED (independent of Wave 8)

| # | Agent | Type | Status |
|---|-------|------|--------|
| 9A | Post-Games Missing-Results Alert (#55) | python-pro | ⬜ Pending |
| 9B | No-Games-Day Robustness Verification | python-pro | ⬜ Pending |
| 9C | Startup Recovery Verification | python-pro | ⬜ Pending |

---

## Wave 10 — Offline Analysis Flow ⬜ NOT STARTED

Multi-day gambling analytics. Deferred until enough betting data accumulated.

### Agent 10A: Offline Analysis
| # | Task | Status |
|---|------|--------|
| 1 | Design analysis queries + multi-day HTML dashboard | ⬜ Pending |
| 2 | Create query_stats.py | ⬜ Pending |
| 3 | Create analysis HTML reports | ⬜ Pending |
| 4 | Create offline graph_manager.py | ⬜ Pending |

---

## Wave 11 — Cup-Tie 2-Leg Match Support ⬜ NOT STARTED

Trigger: pick up when an actual 2-legged cup tie appears on the schedule so the helper can be validated end-to-end.

### Agent 11A: Cup-Tie First-Leg Context
| # | Task | Status |
|---|------|--------|
| 1 | Create fetch_cup_tie_context.py helper (FotMob roundInfo/aggregate) | ⬜ Pending |
| 2 | Pydantic output keyed by team identity (not home/away) | ⬜ Pending |
| 3 | Wire renderer — cup-tie inline in match header (html_report.py) | ⬜ Pending |
| 4 | Verify FotMob cup-tie metadata against a real 2-legged tie | ⬜ Pending |

---

## Wave 12 — Competition Expansion + Polish 🟡 PARTIALLY DONE

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

## Wave 13 — Testing Scheme ⬜ TBD

To be planned separately.

---

## Known Issues / Tech Debt

All tracked as GitHub issues: #44–#56. See `gh issue list --repo Omer-Pinto/SoccerSmartBet`.
