# SoccerSmartBet Revival — Progress Tracker

> **Last updated:** 2026-04-05 | **Branch:** `revive`

## Summary

```
Progress: [🟩🟩🟩⬜⬜⬜⬜⬜⬜⬜⬜⬜⬜⬜⬜⬜⬜⬜⬜⬜⬜⬜⬜⬜⬜] 7% (4/56)
```

| Status | Count | % |
|--------|-------|---|
| 🟢 Done | 4 / 56 | 7% |
| 🔵 In Progress | 0 | 0% |
| ⬜ Pending | 52 | 93% |

---

## Wave Status

| Wave | Status | Agents | Cherry-picked | Pending | Notes |
|------|--------|--------|---------------|---------|-------|
| 0 | Done | — | — | 0/4 | All 4 tasks complete |
| 1 | Not Started | 0/3 | 0/3 | 3/3 | FotMob client + team registry + winner client |
| 2 | Not Started | 0/3 | 0/3 | 3/3 | Fix existing tools + new tools |
| 3 | Not Started | 0/2 | 0/2 | 2/2 | Web app + tests + cleanup |
| 4 | Not Started | 0/2 | 0/2 | 2/2 | LangGraph Pre-Gambling Flow |
| 5 | Not Started | 0/3 | 0/3 | 3/3 | Gambling + Post-Games + Offline Analysis |
| 6 | Not Started | 0/1 | 0/1 | 1/1 | Competition expansion + polish |

**Wave status values:** `Not Started` → `In Progress` → `Cherry-picking` → `Verifying` → `Done`

---

## Wave 0 — Setup + Tools Curation

| # | Task | Status | Notes |
|---|------|--------|-------|
| 0.1 | Clean dead refs + deps | 🟢 Done | Removed APIFOOTBALL_API_KEY, pinned langgraph>=1.0.0, updated ORCHESTRATION_STATE |
| 0.2 | Tools curation session | 🟢 Done | 1-11 IN, 12-13 OUT (Cloudflare), 14-15 STRETCH, 16-18 NO |
| 0.3 | Schema update (teams table) | 🟢 Done | Added teams table to schema + deployment init |
| 0.4 | Verify enrichment sources | 🟢 Done | FBref=403, Sofascore=403, FotMob news=works, FotMob topPlayers=empty |

---

## Wave 1 — Core Infrastructure

### Agent 1A: FotMob Client Rewrite
| # | Task | Status | Notes |
|---|------|--------|-------|
| 1 | Rewrite fotmob_client.py | ⬜ Pending | |
| 2 | Implement x-mas signing | ⬜ Pending | |
| 3 | get_league_table | ⬜ Pending | |
| 4 | get_team_data | ⬜ Pending | |
| 5 | get_match_data | ⬜ Pending | |
| 6 | get_team_news | ⬜ Pending | |
| 7 | find_team with league search | ⬜ Pending | |

### Agent 1B: Team Name Registry
| # | Task | Status | Notes |
|---|------|--------|-------|
| 1 | Create team_registry.py | ⬜ Pending | |
| 2 | Fuzzy matching | ⬜ Pending | |
| 3 | teams_seed.py | ⬜ Pending | |
| 4 | winner.co.il Hebrew names | ⬜ Pending | |
| 5 | Israeli Premier League seed | ⬜ Pending | |

### Agent 1C: winner.co.il Odds Client
| # | Task | Status | Notes |
|---|------|--------|-------|
| 1 | Create fetch_winner_odds.py | ⬜ Pending | |
| 2 | Header generation | ⬜ Pending | |
| 3 | Market parsing | ⬜ Pending | |
| 4 | League filtering | ⬜ Pending | |
| 5 | Match fetch_odds interface | ⬜ Pending | |

---

## Wave 2 — Fix Existing + New Tools

### Agent 2A: Fix FotMob Game Tools
| # | Task | Status | Notes |
|---|------|--------|-------|
| 1 | Fix fetch_venue.py | ⬜ Pending | |
| 2 | Fix fetch_weather.py | ⬜ Pending | |

### Agent 2B: Fix FotMob Team Tools
| # | Task | Status | Notes |
|---|------|--------|-------|
| 1 | Fix fetch_form.py | ⬜ Pending | |
| 2 | Fix fetch_injuries.py | ⬜ Pending | |
| 3 | Fix fetch_league_position.py | ⬜ Pending | |
| 4 | Fix calculate_recovery_time.py | ⬜ Pending | |
| 5 | Create fetch_team_news.py | ⬜ Pending | |
| 6 | Update team __init__.py | ⬜ Pending | |

### Agent 2C: Daily Fixtures + Enrichment
| # | Task | Status | Notes |
|---|------|--------|-------|
| 1 | Create fetch_daily_fixtures.py | ⬜ Pending | |
| 2 | Create enrichment tools (from curation) | ⬜ Pending | |
| 3 | Update game __init__.py | ⬜ Pending | |

---

## Wave 3 — Web App + Tests

### Agent 3A: Fix Web App
| # | Task | Status | Notes |
|---|------|--------|-------|
| 1 | Update main.py imports | ⬜ Pending | |
| 2 | Winner odds display | ⬜ Pending | |
| 3 | Team news display | ⬜ Pending | |
| 4 | Enrichment data display | ⬜ Pending | |
| 5 | E2E verify | ⬜ Pending | |

### Agent 3B: Tests + Cleanup
| # | Task | Status | Notes |
|---|------|--------|-------|
| 1 | Update existing tool tests | ⬜ Pending | |
| 2 | Create new tool tests | ⬜ Pending | |
| 3 | Update test_all_tools.py | ⬜ Pending | |
| 4 | Clean .env.example | ⬜ Pending | |
| 5 | Update ORCHESTRATION_STATE.md | ⬜ Pending | |

---

## Wave 4 — LangGraph Pre-Gambling Flow

### Agent 4A: Core Flow + Pipeline Nodes
| # | Task | Status | Notes |
|---|------|--------|-------|
| 1 | Verify state.py for LangGraph 1.x | ⬜ Pending | |
| 2 | Update structured_outputs.py | ⬜ Pending | |
| 3 | Create smart_game_picker.py | ⬜ Pending | |
| 4 | Create persist_games.py | ⬜ Pending | |
| 5 | Create combine_reports.py | ⬜ Pending | |
| 6 | Create persist_reports.py | ⬜ Pending | |
| 7 | Create graph_manager.py | ⬜ Pending | |

### Agent 4B: Intelligence Agents + Orchestration
| # | Task | Status | Notes |
|---|------|--------|-------|
| 1 | Create game_intelligence.py | ⬜ Pending | |
| 2 | Create team_intelligence.py | ⬜ Pending | |
| 3 | Create parallel_orchestrator.py | ⬜ Pending | |
| 4 | Add DB write utilities | ⬜ Pending | |

---

## Wave 5 — Gambling + Post-Games + Offline Analysis

### Agent 5A: Telegram Bot + Gambling Flow
| # | Task | Status | Notes |
|---|------|--------|-------|
| 1 | Create telegram_bot.py | ⬜ Pending | |
| 2 | Create ai_betting_agent.py | ⬜ Pending | |
| 3 | Create bet_validator.py | ⬜ Pending | |
| 4 | Create gambling graph_manager.py | ⬜ Pending | |

### Agent 5B: Post-Games Flow
| # | Task | Status | Notes |
|---|------|--------|-------|
| 1 | Create fetch_results.py | ⬜ Pending | |
| 2 | Create pnl_calculator.py | ⬜ Pending | |
| 3 | Create daily_summary.py | ⬜ Pending | |
| 4 | Create post-games graph_manager.py | ⬜ Pending | |

### Agent 5C: Offline Analysis Flow
| # | Task | Status | Notes |
|---|------|--------|-------|
| 1 | Create query_stats.py | ⬜ Pending | |
| 2 | Create ai_insights.py | ⬜ Pending | |
| 3 | Create offline graph_manager.py | ⬜ Pending | |

---

## Wave 6 — Expansion

### Agent 6A: League Expansion + Polish
| # | Task | Status | Notes |
|---|------|--------|-------|
| 1 | Seed Israeli Premier League | ⬜ Pending | |
| 2 | Seed CL/EL teams | ⬜ Pending | |
| 3 | Add Euro/WC national teams | ⬜ Pending | |
| 4 | Add FotMob IDs to registry | ⬜ Pending | |
| 5 | Final documentation | ⬜ Pending | |
