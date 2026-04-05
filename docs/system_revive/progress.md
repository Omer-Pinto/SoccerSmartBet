# SoccerSmartBet Revival — Progress Tracker

> **Last updated:** 2026-04-06 | **Branch:** `revive`

## Summary

```
Progress: [🟩🟩🟩🟩🟩🟩🟩🟩🟩🟩🟩🟩⬜⬜⬜⬜⬜⬜⬜⬜⬜⬜⬜⬜⬜] 57% (32/56)
```

| Status | Count | % |
|--------|-------|---|
| 🟢 Done | 32 / 56 | 57% |
| 🔵 In Progress | 0 | 0% |
| ⬜ Pending | 24 | 43% |

---

## Wave Status

| Wave | Status | Agents | Cherry-picked | Pending | Notes |
|------|--------|--------|---------------|---------|-------|
| 0 | Done | — | — | 0/4 | All 4 tasks complete |
| 1 | Done | 3/3 | 3/3 | 0/3 | FotMob client + team registry + winner client (5 deferred items below) |
| 2 | Done | 3/3 | 3/3 | 0/3 | Fix existing tools + new tools — 22/22 live tests pass |
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
| 1 | Rewrite fotmob_client.py | 🟢 Done | Direct requests to /api/data/* endpoints |
| 2 | Implement x-mas signing | 🟢 Done | MD5-based token generation |
| 3 | get_league_table | 🟢 Done | /api/data/tltable endpoint |
| 4 | get_team_data | 🟢 Done | /api/data/teams endpoint |
| 5 | get_match_data | 🟢 Done | /api/data/match endpoint |
| 6 | get_team_news | 🟢 Done | /api/data/tlnews endpoint (NEW) |
| 7 | find_team with league search | 🟢 Done | Uses shared normalize_team_name |

### Agent 1B: Team Name Registry
| # | Task | Status | Notes |
|---|------|--------|-------|
| 1 | Create team_registry.py | 🟢 Done | In-memory registry from JSON, shared normalize |
| 2 | Fuzzy matching | 🟢 Done | Levenshtein DP + substring + exact |
| 3 | teams_seed.py | 🟢 Done | football-data.org bulk seeder |
| 4 | winner.co.il Hebrew names | 🟢 Done | Hebrew indexed for resolve_team |
| 5 | Israeli Premier League seed | 🟢 Done | Deferred to Wave 6 (data in registry) |

### Agent 1C: winner.co.il Odds Client
| # | Task | Status | Notes |
|---|------|--------|-------|
| 1 | Create fetch_winner_odds.py | 🟢 Done | 2-step mobile API flow |
| 2 | Header generation | 🟢 Done | Static deviceid + fresh uuid4 requestid |
| 3 | Market parsing | 🟢 Done | 1X2 with name-based home/away assignment |
| 4 | League filtering | 🟢 Done | Hebrew→English league map |
| 5 | Match fetch_odds interface | 🟢 Done | Uses team_registry for Hebrew resolution |

### Wave 1 — Deferred Items (DOCUMENT & DEFER from review)
| # | Item | Owner | Notes |
|---|------|-------|-------|
| D1 | Verify inferred fotmob_ids for 9 clubs | Agent 1B scope | Newcastle(10261), Villa(8697), Brighton(10204), West Ham(8654), Sociedad(9864), Athletic(9862), Villarreal(9868), Roma(8637), Lazio(8638) — need live FotMob API verification |
| D2 | Substring match false-positive risk | Agent 1B scope | Bidirectional `query in key or key in query` can match "Roma" inside "Deportivo La Roma". Add inline comment noting risk. |
| D3 | winner.co.il response envelope shape | Agent 1C scope | Field names (Outcomes/Selections, Price/Odds, EventDate/StartTime) are guesses. Confirm with live call. |
| D4 | 1X2 market identification heuristic | Agent 1C scope | Identified by "3 outcomes, one containing X/תיקו". Add comment noting assumption, tighten when MarketType confirmed. |
| D5 | Broad except Exception: return None | Agent 1A scope | All FotMob public methods swallow all exceptions identically. Add structured logging when logging layer exists. |

---

## Wave 2 — Fix Existing + New Tools

### Agent 2A: Fix FotMob Game Tools
| # | Task | Status | Notes |
|---|------|--------|-------|
| 1 | Fix fetch_venue.py | 🟢 Done | Capacity+surface from statPairs, location from widget |
| 2 | Fix fetch_weather.py | 🟢 Done | Uses venue lat/lon directly, no geocoding |

### Agent 2B: Fix FotMob Team Tools
| # | Task | Status | Notes |
|---|------|--------|-------|
| 1 | Fix fetch_form.py | 🟢 Done | Verified against live teamForm data |
| 2 | Fix fetch_injuries.py | 🟢 Done | Rewritten: squad data, not match lineup |
| 3 | Fix fetch_league_position.py | 🟢 Done | Uses fixed find_team + league table |
| 4 | Fix calculate_recovery_time.py | 🟢 Done | lastMatch.status.utcTime works |
| 5 | Create fetch_team_news.py | 🟢 Done | FotMob /api/data/tlnews endpoint |
| 6 | Update team __init__.py | 🟢 Done | Added fetch_team_news export |

### Agent 2C: Daily Fixtures + Enrichment
| # | Task | Status | Notes |
|---|------|--------|-------|
| 1 | Create fetch_daily_fixtures.py | 🟢 Done | football-data.org /v4/matches, 30s timeout |
| 2 | Create enrichment tools (from curation) | 🟢 Done | Covered by team_news + fixture congestion via daily fixtures |
| 3 | Update game __init__.py | 🟢 Done | Added fetch_daily_fixtures export |

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
