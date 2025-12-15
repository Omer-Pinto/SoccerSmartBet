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

## Batch 5: Tools Implementation ✅ COMPLETE

**Dependencies:** Need state/schemas (Batch 3) for tool signatures

**Result:** 8 tools implemented (4 game + 4 team), organized in game/ and team/ folders

### Current Sources (after FotMob migration)
| Tool | Source |
|------|--------|
| fetch_h2h | football-data.org |
| fetch_venue | FotMob (mobfot) |
| fetch_weather | FotMob + Open-Meteo |
| fetch_odds | The Odds API |
| fetch_form | FotMob (mobfot) |
| fetch_injuries | FotMob (mobfot) |
| fetch_league_position | FotMob (mobfot) |
| calculate_recovery_time | FotMob (mobfot) |

**Note:** Originally used apifootball.com (trial expired). Migrated to FotMob - no rate limits, no API key.

---

## Batch 6: Main Flow Nodes

**Dependencies:** Need tools (Batch 5) and schemas (Batch 4)

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

## Batch 7: Subgraphs

**Dependencies:** Need tools (Batch 5) and schemas (Batch 4)

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

## Batch 8: Main Graph Manager

**Dependencies:** All nodes + subgraphs (Batch 6 + 7)

| Task | Droid | Description | Depends On |
|------|-------|-------------|------------|
| 2.1 | LangGraphArchitectDroid | Pre-Gambling Flow GraphManager | All nodes, subgraphs |

**Deliverables:** `src/pre_gambling_flow/graph_manager.py`

---

## Batch 9: Integration & Testing

**Dependencies:** Complete system (Batch 8)

| Task | Droid | Description |
|------|-------|-------------|
| 6.1 | NodeBuilderDroid | Parallel subgraph orchestration logic |
| 6.2 | NodeBuilderDroid | Error handling & partial data strategy |
| 6.3 | NodeBuilderDroid | End-to-end flow testing |
| 6.4 | ToolBuilderDroid | Tool integration testing |
| 6.5 | ToolBuilderDroid | Add structured logging to tools |

**Deliverables:** `tests/` directory with integration tests

---

## Batch 10: Deployment

**Dependencies:** Working tested system (Batch 9)

| Task | Droid | Description |
|------|-------|-------------|
| 7.1 | InfraDroid | Cron job setup with error handling |
| 7.2 | InfraDroid | Logging & observability instrumentation |

**Deliverables:** Production deployment configuration

---

## Summary

- **Total Tasks:** 30
- **Total Batches:** 10
- **Critical Path:** Batch 1 → Batch 2 (user) → Batch 3 → Batch 4 → Batch 5 → Batch 6/7 → Batch 8 → Batch 9 → Batch 10

---
