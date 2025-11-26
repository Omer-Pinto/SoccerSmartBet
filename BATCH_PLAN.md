# Task Batch Plan - Pre-Gambling Flow

> **Source:** PRE_GAMBLING_OPTIMIZED_FLOW_TASKS.md (27 tasks)
> **Strategy:** Group tasks by dependencies, maximize parallelism within each batch

---

## Batch 1: Research & Foundation

**Status:** All merged to main

| Task | Droid | Status |
|------|-------|--------|
| 0.1 | FootballResearchDroid | ✅ MERGED (#2) |
| 0.2 | InfraDroid | ✅ MERGED (#1) |
| 1.2 | InfraDroid | Pending CR (#3) |

---

## Batch 2: API Registration & Testing

**Dependencies:** 0.1 research complete
**User-led task:** API key registration

| Task | Owner | Description | Depends On |
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
| 1.1 | InfraDroid | PostgreSQL schema design (games, teams, reports, bets) | 0.1 |
| 1.4 | InfraDroid | docker-compose.yml with staging/prod DB | 1.1 |

**Deliverables:**
- 1.1 → `db/schema.sql`, `docs/db_schema.md`
- 1.4 → `docker-compose.yml`, `db/init/` scripts

---

## Batch 4: Core Architecture

**Dependencies:** All need schema (1.1) and config (1.2)

| Task | Droid | Description | Depends On |
|------|-------|-------------|------------|
| 1.3 | LangGraphArchitectDroid | State class, base Pydantic models | 1.1, 1.2 |
| 2.3 | LangGraphArchitectDroid | Structured outputs (GameReport, TeamReport, etc.) | 1.1, 1.2 |
| 2.4 | LangGraphArchitectDroid | Prompts for Smart Picker, Intelligence Agents | 1.2 |

**Deliverables:**
- 1.3 → `src/pre_gambling_flow/state.py`
- 2.3 → `src/pre_gambling_flow/structured_outputs.py`
- 2.4 → `src/pre_gambling_flow/prompts.py`

---

## Batch 5: Tools Implementation

**Dependencies:** Need state/schemas (Batch 3) for tool signatures

**Can be split across multiple ToolBuilderDroid instances:**

| Tool | Droid | File |
|------|-------|------|
| fetch_h2h | ToolBuilderDroid-1 | `src/pre_gambling_flow/tools/fetch_h2h.py` |
| fetch_venue | ToolBuilderDroid-1 | `src/pre_gambling_flow/tools/fetch_venue.py` |
| fetch_weather | ToolBuilderDroid-2 | `src/pre_gambling_flow/tools/fetch_weather.py` |
| fetch_form | ToolBuilderDroid-2 | `src/pre_gambling_flow/tools/fetch_form.py` |
| fetch_injuries | ToolBuilderDroid-3 | `src/pre_gambling_flow/tools/fetch_injuries.py` |
| fetch_suspensions | ToolBuilderDroid-3 | `src/pre_gambling_flow/tools/fetch_suspensions.py` |
| fetch_returning_players | ToolBuilderDroid-4 | `src/pre_gambling_flow/tools/fetch_returning_players.py` |
| fetch_rotation_news | ToolBuilderDroid-4 | `src/pre_gambling_flow/tools/fetch_rotation_news.py` |
| fetch_key_players_form | ToolBuilderDroid-5 | `src/pre_gambling_flow/tools/fetch_key_players_form.py` |
| fetch_team_morale | ToolBuilderDroid-5 | `src/pre_gambling_flow/tools/fetch_team_morale.py` |
| calculate_recovery_time | ToolBuilderDroid-1 | `src/pre_gambling_flow/tools/calculate_recovery_time.py` |

**Plus:**
| Task | Droid | Description |
|------|-------|-------------|
| 2.5 | ToolBuilderDroid-1 | Tools setup/registry (`tools_setup.py`) |

**Deliverables:** 11 tool files + `tools_setup.py` + `tools/__init__.py`

---

## Batch 6: Main Flow Nodes

**Dependencies:** Need tools (Batch 4) and schemas (Batch 3)

| Task | Droid | Description | Depends On |
|------|-------|-------------|------------|
| 3.1 | InfraDroid | Pre-Gambling Trigger (APScheduler cron) | Config (1.2) |
| 3.2 | NodeBuilderDroid | Smart Game Picker Node | Tools, Schemas |
| 3.3 | NodeBuilderDroid | Fetch Lines from winner.co.il | Tools, Schemas |
| 3.4 | NodeBuilderDroid | Persist Unfiltered Games | DB schema (1.1) |
| 3.5 | NodeBuilderDroid | Combine Results to Reports | DB schema, Schemas |
| 3.6 | NodeBuilderDroid | Persist Reports to DB | DB schema (1.1) |
| 3.7 | NodeBuilderDroid | Send Gambling Trigger | Schemas |

**Deliverables:** `src/pre_gambling_flow/nodes/` directory with 7 node files

---

## Batch 7: Subgraphs

**Dependencies:** Need tools (Batch 4) and schemas (Batch 3)

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

**Dependencies:** All nodes + subgraphs (Batch 5 + 6)

| Task | Droid | Description | Depends On |
|------|-------|-------------|------------|
| 2.1 | LangGraphArchitectDroid | Pre-Gambling Flow GraphManager | All nodes, subgraphs |

**Deliverables:** `src/pre_gambling_flow/graph_manager.py`

---

## Batch 9: Integration & Testing

**Dependencies:** Complete system (Batch 7)

| Task | Droid | Description |
|------|-------|-------------|
| 6.1 | NodeBuilderDroid | Parallel subgraph orchestration logic |
| 6.2 | NodeBuilderDroid | Error handling & partial data strategy |
| 6.3 | NodeBuilderDroid | End-to-end flow testing |
| 6.4 | ToolBuilderDroid | Tool integration testing |

**Deliverables:** `tests/` directory with integration tests

---

## Batch 10: Deployment

**Dependencies:** Working tested system (Batch 8)

| Task | Droid | Description |
|------|-------|-------------|
| 7.1 | InfraDroid | Cron job setup with error handling |
| 7.2 | InfraDroid | Logging & observability instrumentation |

**Deliverables:** Production deployment configuration

---

## Summary

- **Total Tasks:** 29
- **Total Batches:** 10
- **Batch 1:** ✅ 2/3 tasks complete (0.1, 0.2 merged; 1.2 in CR)
- **Critical Path:** Batch 1 → Batch 2 (user) → Batch 3 → Batch 4 → Batch 5 → Batch 6/7 → Batch 8 → Batch 9 → Batch 10

---

## Execution Strategy

1. **Batch 1:** Start with 2-3 droids (FootballResearchDroid + 2x InfraDroid)
2. **User reviews PRs** between each batch
3. **Batch 4:** Maximum parallelism (5 ToolBuilderDroid instances)
4. **Adapt:** Based on user feedback and issues found
5. **One batch at a time** - full stop for review between batches
