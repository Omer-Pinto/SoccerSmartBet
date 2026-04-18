# SoccerSmartBet Revival — Progress Tracker

> **Last updated:** 2026-04-17 | **Branch:** major_report_refactor

## Summary

```
Progress: [🟩🟩🟩🟩🟩🟩🟩⬜⬜⬜⬜⬜] 7/12 waves done
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
| Offline Analysis Flow | **NOT BUILT** — deferred to Wave 9 |

---

## Wave Status

| Wave | Status | Notes |
|------|--------|-------|
| 0 | 🟢 Done | Setup, curation, schema, enrichment verification |
| 1 | 🟢 Done | FotMob client, team registry, winner client |
| 2 | 🟢 Done | All 11 tools working against live APIs |
| 3 | 🟢 Done | Web app works. Tests obsolete — deleted, deferred to Wave 11. |
| 4 | 🟢 Done | Subgraph architecture, E2E verified with expert summary |
| 5 | 🟢 Done | Telegram bot, triggers, game reports HTML, ISR timezone |
| 6 | 🟢 Done | Gambling (6A) + Post-Games (6B). E2E tested. |
| 7 | 🟢 Done | daily_runs table, wall-clock scheduler, full automation |
| 8 | 🔵 Scoped | Independent foundations — 5 parallel agents (8B–8F): prompts/outputs rewrite, missing-results alert, no-games day verify, startup recovery verify, Wave 9 contract investigation |
| 9 | 🔵 Scoped | Report overhaul consumers — 2 agents (9A H2H fix conditional, 9B HTML overhaul), blocked by Wave 8 |
| 10 | ⬜ Not Started | Offline analysis + cup-tie first-leg helper (deferred 2026-04-18 — no 2-legged cup ties on schedule to validate) |
| 11 | 🟡 Partial | Expansion: Israeli league + CL/EL done. Euro/WC + backup pending. |
| 12 | ⬜ TBD | Testing scheme — to be planned separately |

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

## Wave 8 — Independent Foundations 🔵 SCOPED (5 parallel agents)

All 5 agents touch disjoint files and are safe to dispatch in parallel. Original Wave 8 mixed producers and consumers — that was corrected by splitting into Wave 8 (foundations) + Wave 9 (consumers). Cup-tie helper (formerly 8A) moved to Wave 10 on 2026-04-18 — no 2-legged cup ties currently on schedule.

| # | Agent | Type | Status | Notes |
|---|-------|------|--------|-------|
| 8B | Tighten Agent Prompts + Structured Outputs | ai-engineer | ⬜ Pending | Split raw fields (streak, rank, points) from bullet commentary. H2H as first-class structured field. Length caps. No opening flourishes. |
| 8C | Post-Games Missing-Results Alert (#55) | python-pro | ⬜ Pending | Bot silently skips games with no FotMob match — must alert. |
| 8D | No-Games-Day Robustness Verification | python-pro | ⬜ Pending | Verify `daily_runs` closes cleanly, "No games today" message sent. |
| 8E | Startup Recovery Verification | python-pro | ⬜ Pending | Verify bot restart past 13:00 ISR fires pre-gambling flow immediately. |
| 8F | Wave 9 Contract Investigation | python-pro | ⬜ Pending | Read-only. Diagnose H2H empty bug; freeze Wave 9 contract in `wave9_contract.md`. (FotMob cup-tie metadata verification moved to Wave 10.) |
| 8G | H2H Rate-Limit Mitigation | python-pro | ⬜ Pending | Confirm rate-limit hypothesis (7-game run had empty H2H), evaluate pacing vs source-swap, implement. Budget: pre-gambling flow up to ~4 min OK. |

---

## Wave 9 — Report Overhaul Consumers 🔵 SCOPED (2 agents, blocked by Wave 8)

Consumes 8B's new Pydantic fields and 8F's contract doc. 9A and 9B touch disjoint files and render independent states — they are parallel once Wave 8 completes. Cup-tie first-leg rendering deferred to Wave 10 alongside the helper.

| # | Agent | Type | Status | Notes |
|---|-------|------|--------|-------|
| 9A | H2H Fix Application (conditional) | python-pro | ⬜ Pending | Scope depends on 8F's diagnosis. Skip entirely if 8B's rewrite already resolves the bug. |
| 9B | Report HTML Full Overhaul (5" mobile, table-comparison) | ui-designer + python-pro | ⬜ Pending | Mobile-first. Pills for form. Compact odds row + implied-prob bar. Fix venue dup bug. Remove crests / VS badge / emoji titles / home-green-away-red coding. Renders both present and absent states for H2H. Cup-tie inline rendering deferred to Wave 10. |

---

## Wave 10 — Offline Analysis Flow + Deferred Cup-Tie Context ⬜ NOT STARTED

### Agent 10A: Offline Analysis
| # | Task | Status |
|---|------|--------|
| 1 | Design analysis queries + HTML dashboard | ⬜ Pending |
| 2 | Create query_stats.py | ⬜ Pending |
| 3 | Create analysis HTML reports | ⬜ Pending |
| 4 | Create offline graph_manager.py | ⬜ Pending |

### Agent 10B: Cup-Tie First-Leg Context (moved from Wave 8 on 2026-04-18)
Trigger: pick up when an actual 2-legged cup tie appears on the schedule so the helper can be validated end-to-end.

| # | Task | Status |
|---|------|--------|
| 1 | Create fetch_cup_tie_context.py helper (FotMob roundInfo/aggregate) | ⬜ Pending |
| 2 | Pydantic output keyed by team identity (not home/away) | ⬜ Pending |
| 3 | Wire renderer — cup-tie inline in match header (html_report.py) | ⬜ Pending |
| 4 | Verify FotMob cup-tie metadata against a real 2-legged tie | ⬜ Pending |

---

## Wave 11 — Competition Expansion + Polish 🟡 PARTIALLY DONE

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

## Wave 12 — Testing Scheme ⬜ TBD

To be planned separately.

---

## Known Issues / Tech Debt

All tracked as GitHub issues: #44–#56. See `gh issue list --repo Omer-Pinto/SoccerSmartBet`.
