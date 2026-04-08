# SoccerSmartBet Revival — Progress Tracker

> **Last updated:** 2026-04-08 | **Branch:** main

## Summary

```
Progress: [🟩🟩🟩🟩🟩🟩🟩🟩🟩🟩🟩🟩🟩🟩🟩🟩🟩🟡⬜⬜⬜⬜⬜⬜⬜] 68%
```

| What | Status |
|------|--------|
| 11 data tools (FotMob, football-data.org, The Odds API, winner.co.il) | Working |
| Team registry (83 teams, Hebrew, fuzzy match, Israeli league) | Working |
| Web app tool tester (SSE streaming, concurrent, dual odds) | Working |
| DB schema (6 tables) | Running on PostgreSQL (docker-compose, port 5433), pgweb on 8082 |
| State + prompts + structured outputs | Updated and wired into graph |
| Pre-Gambling LangGraph flow | **Working E2E** — verified on 2 CL games, subgraph architecture + expert summary |
| Telegram bot + triggers + ISR time + game reports | **NOT BUILT** — new Wave 5 |
| Gambling Flow (AI bets + validation) | **NOT BUILT** — directory doesn't exist |
| Post-Games Flow (results + P&L) | **NOT BUILT** — directory doesn't exist |
| Offline Analysis Flow | **NOT BUILT** — directory doesn't exist |

---

## Wave Status

| Wave | Status | Notes |
|------|--------|-------|
| 0 | 🟢 Done | Setup, curation, schema, enrichment verification |
| 1 | 🟢 Done | FotMob client, team registry, winner client. Heavy post-wave bug fixes. |
| 2 | 🟢 Done | All 11 tools working against live APIs |
| 3 | 🟡 Partial | Web app works (streaming, concurrent). Tests mostly deleted (4 kept of 10). |
| 4 | 🟢 Done | Subgraph architecture, E2E verified on 2 CL games with expert summary |
| 5 | ⬜ Not Started | Telegram bot, triggers, game reports HTML, ISR timezone |
| 6 | ⬜ Not Started | Gambling + Post-Games + Offline — no code exists |
| 7 | 🟡 Partial | Israeli league done. 83 teams. Euro/WC search lists added. Final docs pending. |

---

## Wave 0 — Setup + Tools Curation ✅

| # | Task | Status |
|---|------|--------|
| 0.1 | Clean dead refs + deps | 🟢 Done |
| 0.2 | Tools curation session | 🟢 Done |
| 0.3 | Schema update (teams table) | 🟢 Done |
| 0.4 | Verify enrichment sources | 🟢 Done |

---

## Wave 1 — Core Infrastructure ✅ (with major post-wave fixes)

### Agent 1A: FotMob Client
| # | Task | Status | Notes |
|---|------|--------|-------|
| 1 | Rewrite fotmob_client.py | 🟢 Done | x-mas signing, direct requests |
| 2 | get_league_table | 🟢 Done | Fixed post-wave: response is list not dict |
| 3 | get_team_data / get_match_data | 🟢 Done | |
| 4 | get_team_news | 🟢 Done | |
| 5 | find_team | 🟢 Done | Fixed post-wave: registry lookup for Bayern/PSG |

### Agent 1B: Team Name Registry
| # | Task | Status | Notes |
|---|------|--------|-------|
| 1 | team_registry.py + fuzzy matching | 🟢 Done | Levenshtein + substring + exact |
| 2 | teams_registry.json | 🟢 Done | 83 teams (was 29, expanded during bug fixes) |
| 3 | teams_seed.py | 🟢 Done | football-data.org bulk seeder |
| 4 | Israeli Premier League (14 teams) | 🟢 Done | Originally Wave 6, done during bug fixes |
| 5 | Hebrew name corrections | 🟢 Done | AC Milan=מילאן, Inter=אינטר, 38 teams added |
| 6 | Hyphen/accent normalization | 🟢 Done | Saint-Germain vs Saint Germain etc. |

### Agent 1C: winner.co.il Odds Client
| # | Task | Status | Notes |
|---|------|--------|-------|
| 1 | fetch_winner_odds.py | 🟢 Done | **Fully rewritten** post-wave |
| 2 | API endpoint | 🟢 Done | www.winner.co.il/api/v2/publicapi/ (GET, session cookies) |
| 3 | Market parsing | 🟢 Done | Flat markets list, 1X2 by mp field |
| 4 | League filtering | 🟢 Done | Hebrew→English league map |
| 5 | fetch_all_winner_odds | 🟢 Done | Bulk fetch with optional league filter |

**Post-wave lessons**: winner.co.il API was built without testing (Incapsula WAF blocked original endpoint). Entire client was rewritten after live investigation found the real API at www.winner.co.il/api/v2/publicapi/.

---

## Wave 2 — Fix Existing + New Tools ✅

### Agent 2A: Fix FotMob Game Tools
| # | Task | Status | Notes |
|---|------|--------|-------|
| 1 | Fix fetch_venue.py | 🟢 Done | Capacity from statPairs, lat/lon from widget |
| 2 | Fix fetch_weather.py | 🟢 Done | Direct lat/lon, no geocoding needed |

### Agent 2B: Fix FotMob Team Tools
| # | Task | Status | Notes |
|---|------|--------|-------|
| 1 | Fix fetch_form.py | 🟢 Done | teamForm data verified |
| 2 | Fix fetch_injuries.py | 🟢 Done | Rewritten: uses squad data not match lineup |
| 3 | Fix fetch_league_position.py | 🟢 Done | |
| 4 | Fix calculate_recovery_time.py | 🟢 Done | |
| 5 | Create fetch_team_news.py | 🟢 Done | FotMob news (empty for Israeli clubs) |

### Agent 2C: Daily Fixtures
| # | Task | Status | Notes |
|---|------|--------|-------|
| 1 | Create fetch_daily_fixtures.py | 🟢 Done | football-data.org, 30s timeout |

**Post-wave fixes**: H2H crash on None names, accent matching (Atlético), CL-first search order, 429 rate limit handling, earliest match selection, win attribution relative to queried teams.

---

## Wave 3 — Web App + Tests 🟡

### Agent 3A: Web App
| # | Task | Status | Notes |
|---|------|--------|-------|
| 1 | Wire new tools | 🟢 Done | winner_odds, team_news added |
| 2 | Winner odds display | 🟢 Done | Israeli Toto section |
| 3 | Team news display | 🟢 Done | News cards in team columns |
| 4 | SSE streaming | 🟢 Done | Results appear as tools complete (post-wave fix) |
| 5 | Concurrent execution | 🟢 Done | ThreadPoolExecutor + cache pre-warm (post-wave fix) |
| 6 | E2E verify | 🟡 Partial | Works but bugs found by manual QA, not automated tests |

### Agent 3B: Tests + Cleanup
| # | Task | Status | Notes |
|---|------|--------|-------|
| 1 | Tests | 🔴 Failed | 6/10 test files deleted as worthless (only checked dict keys) |
| 2 | 4 surviving tests | 🟢 Done | venue_live, weather_live, fixtures_live, team_tools_live |
| 3 | ORCHESTRATION_STATE.md | 🟢 Done | |

---

## Wave 4 — LangGraph Pre-Gambling Flow ✅

**All code written.** Architecture: main graph fans out via Send() to analyze_game subgraph per game. Two-level parallelism (outer=games, inner=3 intelligence calls).

### Agent 4A: Core Flow + Pipeline Nodes
| # | Task | Status | Notes |
|---|------|--------|-------|
| 1 | Verify state.py for LangGraph 1.x | 🟢 Done | LangGraph 1.0.3 — all imports, reducers, StateGraph compile OK |
| 2 | Update structured_outputs.py | 🟢 Done | Added team_news to GameReport, league_position to TeamReport, removed key_players_status, fixed FotMob refs |
| 3 | Create smart_game_picker.py | 🟢 Done | Cross-refs fixtures×winner odds, Israeli top-6 filter, gpt-5.4-mini LLM, review fixes applied |
| 4 | Create persist_games.py | 🟢 Done | psycopg2, single transaction, RETURNING game_id, tested against real DB |
| 5 | Create combine_reports.py | 🟢 Done | Queries game_reports + team_reports, formats combined text per game |
| 6 | Create persist_reports.py | 🟢 Done | Single UPDATE with ANY(), marks games ready_for_betting |
| 7 | Create graph_manager.py | 🟢 Done | StateGraph compiled, conditional edge for 4B intelligence agents insertion |

### Agent 4B: Intelligence Agents + Subgraph Orchestration
| # | Task | Status | Notes |
|---|------|--------|-------|
| 1 | Create game_intelligence.py | 🟢 Done | 4 tools pre-called, 1 LLM call (gpt-5.4), writes GameReport to DB, prompt updated |
| 2 | Create team_intelligence.py | 🟢 Done | 4 tools pre-called, 1 LLM call (gpt-5.4), writes TeamReport to DB, prompt updated |
| 3 | Create analyze_game.py subgraph | 🟢 Done | Replaced parallel_orchestrator with proper LangGraph subgraph. 3 parallel nodes (game_intelligence, team_intel_home, team_intel_away). Main graph uses Send() fan-out. |
| 4 | Add DB write utilities | 🟢 Done | insert_game_report, insert_team_report, update_game_status — upsert, tested against real DB |

### Infrastructure
- PostgreSQL staging DB on port 5433 (docker-compose project: soccer-smart-bet)
- pgweb UI on port 8082
- DB schema updated for new structured outputs (team_news, league_position)
- psycopg2-binary + langchain-openai installed

### Remaining before Wave 4 complete ✅
- 🟢 Test smart_game_picker standalone against real APIs
- 🟢 Test game_intelligence + team_intelligence standalone with real FotMob + LLM
- 🟢 Run end-to-end Pre-Gambling Flow (2 CL games, with expert summary LLM call)
- 🟢 Check LangSmith traces

---

## Wave 5 — Telegram Bot + Triggers + Game Reports + ISR Time ⬜ NOT STARTED

### Agent 5A: ISR Timezone Utility ✅
| # | Task | Status | Notes |
|---|------|--------|-------|
| 1 | Create timezone utility (UTC → Israel time) | 🟢 Done | `utils/timezone.py` — ISR_TZ, utc_to_isr, now_isr, format helpers |
| 2 | Apply to game picker selected games | 🟢 Done | `_parse_kickoff()` converts UTC→ISR, label changed to ISR |
| 3 | Apply to all existing time references | 🟢 Done | fotmob cache, winner odds tagged ISR, DB schema → TIMESTAMPTZ |

### Agent 5B: Telegram Bot + Flow Triggers ✅
**Prerequisite:** Omer creates bot via @BotFather → provides bot token in `.env`

| # | Task | Status | Notes |
|---|------|--------|-------|
| 0 | **[USER]** Create bot via @BotFather | 🟢 Done | `@soccer_smart_bet_bot`, token + chat_id in `.env` |
| 1 | Create Telegram bot client code | 🟢 Done | `telegram/bot.py` — async send, chat ID guard, owner-only |
| 2 | Create Pre-Gambling daily trigger | 🟢 Done | `telegram/triggers.py` — daily job at 13:00 ISR via JobQueue |
| 3 | Create Gambling trigger | 🟢 Done | `trigger_pre_gambling_and_notify()` — runs flow then sends gambling time message |

### Agent 5C: HTML Game Report Pages + Telegram Message Design ✅
| # | Task | Status | Notes |
|---|------|--------|-------|
| 1 | Static HTML report page per game | 🟢 Done | `reports/html_report.py` — self-contained HTML, dark theme, 3-column grid, responsive |
| 2 | Design Telegram "gambling time" message | 🟢 Done | `reports/telegram_message.py` — bullets with teams, ISR time, venue, league + report link |
| 3 | Serve HTML pages accessible from Telegram links | 🟢 Done | `reports/serve.py` — FastAPI router `GET /reports/{game_id}`, generates on-the-fly |

---

## Wave 6 — Gambling + Post-Games + Offline Analysis ⬜ NOT STARTED

### Agent 6A: Gambling Flow
| # | Task | Status | Notes |
|---|------|--------|-------|
| 1 | Create ai_betting_agent.py | ⬜ Pending | AI places bets using reports |
| 2 | Create bet_validator.py | ⬜ Pending | Verify both bets before deadline |
| 3 | Create gambling graph_manager.py | ⬜ Pending | Uses Telegram bot from Wave 5 |

### Agent 6B: Post-Games Flow
| # | Task | Status | Notes |
|---|------|--------|-------|
| 1 | Create fetch_results.py | ⬜ Pending | |
| 2 | Create pnl_calculator.py | ⬜ Pending | |
| 3 | Create daily_summary.py | ⬜ Pending | |
| 4 | Create post-games graph_manager.py | ⬜ Pending | |

### Agent 6C: Offline Analysis Flow
| # | Task | Status | Notes |
|---|------|--------|-------|
| 1 | Create query_stats.py | ⬜ Pending | |
| 2 | Create ai_insights.py | ⬜ Pending | |
| 3 | Create offline graph_manager.py | ⬜ Pending | |

---

## Wave 7 — Expansion 🟡 PARTIALLY DONE

| # | Task | Status | Notes |
|---|------|--------|-------|
| 1 | Israeli Premier League | 🟢 Done | 14 teams, FotMob IDs, Hebrew names — done during bug fixes |
| 2 | CL/EL teams | 🟢 Done | Sporting CP + main CL teams in registry |
| 3 | Euro/WC support | 🟡 Partial | Search lists added (EC, WC), no national teams in registry |
| 4 | FotMob IDs in registry | 🟢 Done | All 83 teams have FotMob IDs where known |
| 5 | Full league coverage | 🟡 Partial | 83 teams. ~62 winner.co.il teams in major leagues still unresolved. |
| 6 | Final documentation | ⬜ Pending | |

---

## Known Issues / Tech Debt

All tracked as GitHub issues: #45–#52, #44. See `gh issue list --repo Omer-Pinto/SoccerSmartBet`.
