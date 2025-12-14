# Task Batch Plan - Pre-Gambling Flow

> **Source:** PRE_GAMBLING_OPTIMIZED_FLOW_TASKS.md (27 tasks)
> **Strategy:** Group tasks by dependencies, maximize parallelism within each batch
> **Note:** For task status, see ORCHESTRATION_STATE.md and PRE_GAMBLING_OPTIMIZED_FLOW_TASKS.md

---

## Batch 1: Research & Foundation

| Task | Droid | Description |
|------|-------|-------------|
| 0.1 | FootballResearchDroid | Research free football APIs and MCP servers |
| 0.2 | InfraDroid | LangSmith project setup and integration |
| 1.2 | InfraDroid | Configuration management (YAML/JSON) |

---

## Batch 2: API Registration & Testing

**Dependencies:** 0.1 research complete
**User-led task:** API key registration

| Task | Droid | Description | Depends On |
|------|-------|-------------|------------|
| 0.3 | **omer-me** | Register for API keys from research sources | 0.1 |
| 0.4 | ToolBuilderDroid | Simple integration tests for all APIs | 0.3 |

**Deliverables:**
- 0.3 → API keys in config
- 0.4 → `tests/api_integration/` test suite

---

## Batch 3: Schema & Docker

**Dependencies:** 
- 1.1 depends on 0.1 (needs data source understanding)
- 1.4 depends on 1.1 (needs schema)

| Task | Droid | Description | Depends On |
|------|-------|-------------|------------|
| 1.1 | InfraDroid | PostgreSQL schema (5 tables: games, game_reports, team_reports, bets, bankroll) | 0.1 |
| 1.4 | InfraDroid | docker-compose.yml with staging/prod DB | 1.1 |

**Deliverables:**
- 1.1 → `db/schema.sql`, `docs/db_schema.md`
- 1.4 → `docker-compose.yml`, `db/init/` scripts

---

## Batch 4: Core Architecture

**Dependencies:** All need schema (1.1) and config (1.2)

| Task | Droid | Description | Depends On |
|------|-------|-------------|------------|
| 1.3 | LangGraphArchitectDroid | State definition (Phase enum, GameContext, PreGamblingState with reducers) | 1.1, 1.2 |
| 2.3 | LangGraphArchitectDroid | LLM output schemas only (SelectedGames, GameReport, TeamReport) | 1.1, 1.2 |
| 2.4 | LangGraphArchitectDroid | System prompts for 3 agents (Smart Picker, Game/Team Intelligence) | 1.2 |

**Deliverables:**
- 1.3 → `src/pre_gambling_flow/state.py`
- 2.3 → `src/pre_gambling_flow/structured_outputs.py`
- 2.4 → `src/pre_gambling_flow/prompts.py`

---

## Batch 5: Tools Implementation ✅ COMPLETE (PR #33) - SUPERSEDED BY BATCH 6

**Dependencies:** Need state/schemas (Batch 3) for tool signatures

**Result:** 8 tools implemented (4 game + 4 team), organized in game/ and team/ folders

**⚠️ NOTE:** Batch 5 tools used apifootball.com which has since EXPIRED. See Batch 6 for current implementation.

---

## Batch 6: FotMob API Migration ✅ COMPLETE

**Dependencies:** Batch 5 tools (now replaced)
**Reason:** apifootball.com trial expired, football-data.org had 429 rate limit errors

**Result:** All 8 tools migrated to FotMob API (no rate limits, no API key required)

### Game Tools (4)
| Task | Tool | Source | File |
|------|------|--------|------|
| 2.5.1 | fetch_h2h | football-data.org | `src/pre_gambling_flow/tools/game/fetch_h2h.py` |
| 2.5.2 | fetch_venue | FotMob (mobfot) | `src/pre_gambling_flow/tools/game/fetch_venue.py` |
| 2.5.3 | fetch_weather | FotMob + Open-Meteo | `src/pre_gambling_flow/tools/game/fetch_weather.py` |
| 2.5.4 | fetch_odds | The Odds API | `src/pre_gambling_flow/tools/game/fetch_odds.py` |

### Team Tools (4)
| Task | Tool | Source | File |
|------|------|--------|------|
| 2.5.5 | fetch_form | FotMob (mobfot) | `src/pre_gambling_flow/tools/team/fetch_form.py` |
| 2.5.6 | fetch_injuries | FotMob (mobfot) | `src/pre_gambling_flow/tools/team/fetch_injuries.py` |
| 2.5.7 | fetch_league_position | FotMob (mobfot) | `src/pre_gambling_flow/tools/team/fetch_league_position.py` |
| 2.5.8 | calculate_recovery_time | FotMob (mobfot) | `src/pre_gambling_flow/tools/team/calculate_recovery_time.py` |

### New Architecture
- `fotmob_client.py` - Client wrapper with team name → FotMob ID resolution
- Supports 9 major leagues: Premier League, La Liga, Serie A, Bundesliga, Ligue 1, Champions League, Europa League, Eredivisie, Primeira Liga
- In-memory caching for league data
- Name normalization (handles accents, FC/CF prefixes)

### Replaced Tools
| Old Tool | New Tool | Reason |
|----------|----------|--------|
| fetch_key_players_form | fetch_league_position | No free API for player stats; league position more reliable |

### Cancelled Tools (2)
| Task | Tool | Reason |
|------|------|--------|
| ~~2.5.9~~ | ~~fetch_suspensions~~ | API limitation - returns empty data |
| ~~2.5.10~~ | ~~fetch_returning_players~~ | API limitation - cannot track status changes |

**Deliverables:**
- 8 tool files + fotmob_client.py
- Clean interfaces (accept team NAMES, not API-specific IDs)
- Integration test: 12 tool calls per match (all passing)
- Updated documentation with FotMob as primary source

---

## Batch 7: Main Flow Nodes

**Dependencies:** Need tools (Batch 6) and schemas (Batch 4)

| Task | Droid | Description | Depends On |
|------|-------|-------------|------------|
| 3.1 | InfraDroid | Pre-Gambling Trigger (APScheduler cron) | Config (1.2) |
| 3.2 | NodeBuilderDroid | Smart Game Picker Node | Tools, Schemas |
| 3.3 | NodeBuilderDroid | Fetch Lines from The Odds API | Tools, Schemas |
| 3.4 | NodeBuilderDroid | Persist Unfiltered Games | DB schema (1.1) |
| 3.5 | NodeBuilderDroid | Combine Results to Reports | DB schema, Schemas |
| 3.6 | NodeBuilderDroid | Persist Reports to DB | DB schema (1.1) |
| 3.7 | NodeBuilderDroid | Send Gambling Trigger | Schemas |

**Deliverables:** `src/pre_gambling_flow/nodes/` directory with 7 node files

---

## Batch 8: Subgraphs

**Dependencies:** Need tools (Batch 6) and schemas (Batch 4)

| Task | Droid | Description | Depends On |
|------|-------|-------------|------------|
| 4.1 | LangGraphArchitectDroid | Game Subgraph Manager | Tools, Schemas |
| 4.2 | NodeBuilderDroid | Game Intelligence Agent Node | Game tools, Schemas |
| 5.1 | LangGraphArchitectDroid | Team Subgraph Manager | Tools, Schemas |
| 5.2 | NodeBuilderDroid | Team Intelligence Agent Node | Team tools, Schemas |

**Deliverables:**
- `src/pre_gambling_flow/subgraphs/game_intelligence/` (manager + agent node)
- `src/pre_gambling_flow/subgraphs/team_intelligence/` (manager + agent node)

---

## Batch 9: Main Graph Manager

**Dependencies:** All nodes + subgraphs (Batch 7 + 8)

| Task | Droid | Description | Depends On |
|------|-------|-------------|------------|
| 2.1 | LangGraphArchitectDroid | Pre-Gambling Flow GraphManager | All nodes, subgraphs |

**Deliverables:** `src/pre_gambling_flow/graph_manager.py`

---

## Batch 10: Integration & Testing

**Dependencies:** Complete system (Batch 9)

| Task | Droid | Description |
|------|-------|-------------|
| 6.1 | NodeBuilderDroid | Parallel subgraph orchestration logic |
| 6.2 | NodeBuilderDroid | Error handling & partial data strategy |
| 6.3 | NodeBuilderDroid | End-to-end flow testing |
| 6.4 | ToolBuilderDroid | Tool integration testing |

**Deliverables:** `tests/` directory with integration tests

---

## Batch 11: Deployment

**Dependencies:** Working tested system (Batch 10)

| Task | Droid | Description |
|------|-------|-------------|
| 7.1 | InfraDroid | Cron job setup with error handling |
| 7.2 | InfraDroid | Logging & observability instrumentation |

**Deliverables:** Production deployment configuration

---

## Summary

- **Total Tasks:** 29
- **Total Batches:** 11
- **Critical Path:** Batch 1 → Batch 2 (user) → Batch 3 → Batch 4 → Batch 5 → Batch 6 (FotMob migration) → Batch 7-11

**Completed Batches:**
- ✅ Batch 1-5: Research, API setup, schema, architecture, initial tools
- ✅ Batch 6: FotMob API migration (all tools working, no rate limits)

---

