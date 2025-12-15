# Pre-Gambling Flow - Optimized Task Breakdown

> **Changes from original:** Consolidated 16 fetcher nodes into 2 smart agents with tool access (Game Intelligence Agent + Team Intelligence Agent). Kept parallelism, sophisticated game picker, The Odds API as odds source. Estimated ~20-30 LLM calls total using gpt-4o-mini.

---

## 0. Research & Setup (🔍 Pre-Implementation)

### 0.1 Football Data Sources Research
- [x] Research and catalog free football APIs and existing MCP servers for: fixtures, team news, injuries, weather, H2H stats. Check existing MCPs (MCP browser for scraping, GitHub for football MCPs). **Do not plan to develop custom MCPs** - we'll write Python functions instead. Document reliability and coverage.

### 0.2 LangSmith Integration Setup
- [x] Create dedicated LangSmith project for SoccerSmartBet and configure environment variables. Verify tracing works with test LangGraph run.

### 0.3 Update Football API Keys (👤 Omer-led)
- [x] Register for API keys from sources identified in research (football-data.org, apifootball.com, the-odds-api, open-meteo). Store in config. **Assigned: omer-me** ✅ **COMPLETE** - All 3 API keys registered and added to `.env` file.

### 0.4 Test All APIs
- [x] Simple integration test for each API from executive_summary.md: verify connectivity, response format, rate limits. Create `tests/api_integration/` with one test per source. ✅ **COMPLETE** - 24 passing tests across 4 APIs (football-data.org, The Odds API, apifootball.com, Open-Meteo). All tests verify current/upcoming data with dynamic date validation.

---

## 1. Infrastructure & Foundation (🗄️ Database/Config)

### 1.1 PostgreSQL Schema Design
- [x] Design complete PostgreSQL schema with 5 tables: games (odds + results merged), game_reports, team_reports, bets, bankroll. Simplified from original 9-table design. No teams/players/betting_lines/results tables needed.

### 1.2 Configuration Management
- [x] Create config file (YAML/JSON) for: min odds threshold, max daily games, API keys, cron schedule, DB connections (staging/prod), LangSmith keys, model selection (default: gpt-4o-mini), and feature flags. ✅ **COMPLETE** - Minimal MVP config.yaml (29 lines) with betting params, DB config, model selection. Database credentials in .env at project root.

### 1.3 State Definition
- [x] Define TypedDict state class (PreGamblingState) with LangGraph reducers following StocksMarketRecommender pattern. Include Phase enum, GameContext TypedDict, and custom reducers. State for coordination only - game/team data goes to DB. **See DETAILED_TASK_BREAKDOWN.md for specifications.** ✅ **COMPLETE** - PR #13

### 1.4 Docker Compose for Database Environments
- [x] Create docker-compose.yml with two PostgreSQL containers (staging on port 5432, production on port 5433), volumes for persistence, and initialization scripts. ✅ **COMPLETE** - Docker Compose setup in deployment/ folder with staging (5432) and production (5433) PostgreSQL 16 containers, persistent volumes, health checks, and schema auto-initialization.

---

## 2. Graph Architecture (LangGraphWrappers)

### 2.1 Pre-Gambling Flow GraphManager
- [ ] Create `pre_gambling_flow/graph_manager.py` wiring all nodes, edges, and parallel subgraphs using GraphWrapper. Expose `setup()`, `run_graph()`, `cleanup()` methods.

### 2.3 Structured Outputs (LLM Outputs Only)
- [x] Create `pre_gambling_flow/structured_outputs.py` with Pydantic models for LLM outputs ONLY: SelectedGames, GameReport, TeamReport. Match enabled data sources from docs/research/data_sources/executive_summary.md. **See DETAILED_TASK_BREAKDOWN.md for field specifications.** ✅ **COMPLETE** - PR #14

### 2.4 Prompts Repository
- [x] Implement `pre_gambling_flow/prompts.py` containing system messages for Smart Game Picker, Game Intelligence Agent, Team Intelligence Agent. Emphasize sophisticated AI analysis over raw stats dumping. **See DETAILED_TASK_BREAKDOWN.md for prompt requirements and agent goals.** ✅ **COMPLETE** - PR #15

### 2.5 Tools Implementation ✅ COMPLETE (Batch 6 - FotMob Migration)
- [x] Implement 8 data fetching tools (4 game + 4 team) as Python functions wrapped as LangGraph tools. Tools are "dumb fetchers" returning raw data without AI analysis. Agents (Game Intelligence, Team Intelligence) will use these tools and perform sophisticated analysis. ✅ **COMPLETE** - Migrated to FotMob API (no rate limits, no API key)

**Tools implemented:**

**Game Tools (4):**
- ✅ `fetch_h2h()` - H2H match history (football-data.org)
- ✅ `fetch_venue()` - Venue information (FotMob via mobfot)
- ✅ `fetch_weather()` - Weather forecast (FotMob + Open-Meteo)
- ✅ `fetch_odds()` - Betting lines 1/X/2 decimal odds (The Odds API)

**Team Tools (4):**
- ✅ `fetch_form()` - Recent team form W/D/L (FotMob via mobfot)
- ✅ `fetch_injuries()` - Current injury list (FotMob via mobfot)
- ✅ `fetch_league_position()` - League standings for ALL teams (FotMob via mobfot)
- ✅ `calculate_recovery_time()` - Days since last match (FotMob via mobfot)

**Replaced Tools:**
- `fetch_key_players_form` → `fetch_league_position` (no free API provides individual player stats)

**Cancelled Tools (API limitations):**
- ❌ `fetch_suspensions()` - **CANCELLED** (PR #26, removed in PR #32) - Returns empty, API has no suspension data
- ❌ `fetch_returning_players()` - **CANCELLED** (PR #29) - API cannot track status changes over time

**Architecture:**
- `fotmob_client.py` - Client wrapper with team name → FotMob ID resolution
- Supports 9 leagues: Premier League, La Liga, Serie A, Bundesliga, Ligue 1, Champions League, Europa League, Eredivisie, Primeira Liga
- Tools accept team NAMES (not API-specific IDs)

Tools are bound directly to agent NodeWrappers via LangGraph's tool-calling mechanism. No separate tools_setup.py file needed.

---

## 3. Main Flow Nodes

### 3.1 Pre-Gambling Trigger (⏰ Scheduler)
- [ ] Implement cron/scheduler (Python APScheduler) that initiates Pre-Gambling Flow daily at configured time (e.g., 14:00). Handle error recovery/retries.

### 3.2 Smart Game Picker Node (🤖 AI Agent)
- [ ] Create `NodeWrapper` with AI agent that analyzes today's fixtures and selects **interesting games** based on rivalry, importance, playoff implications, derby status, league prestige. Not a simple odds filter. Outputs SelectedGames structured model with justifications.

### 3.3 Fetch Lines from The Odds API Node (🐍 Code/API Integration)
- [ ] Implement fetcher for betting lines (n1, n2, n3) from **The Odds API**. Apply minimum odds threshold filter. Outputs FilteredGame list (min 3 games).

### 3.4 Persist Unfiltered Games Node (🗄️ DB Operation)
- [ ] Create `PythonNodeWrapper` executing DB insert for all games considered (even if filtered out). Stores snapshot for historical analysis.

### 3.5 Combine Results to Reports Node (🐍 Code)
- [ ] Implement `PythonNodeWrapper` that queries DB for game_reports and team_reports (from parallel subgraphs) and merges into final CombinedReport per game. Handles missing data gracefully, generates structured reports.

### 3.6 Persist Reports to DB Node (🗄️ DB Operation)
- [ ] Create `PythonNodeWrapper` inserting CombinedReport records into reports table. Updates game status to 'ready_for_betting'.

### 3.7 Send Gambling Trigger Node (🐍 Code)
- [ ] Implement node that triggers Gambling Flow (via queue, webhook, or direct invocation). Passes game_ids and report references as TriggerPayload.

---

## 4. Game Intelligence Agent Subgraph (🤖 Smart Agent with Tools)

### 4.1 Game Subgraph Manager
- [ ] Create `game_intelligence_subgraph/graph_manager.py` as reusable subgraph instantiated per filtered game (parallel execution). Orchestrates single Game Intelligence Agent node.

### 4.2 Game Intelligence Agent Node
- [ ] Implement `NodeWrapper` with AI agent (following StocksMarketRecommender pattern) equipped with tools:
  
  **Tools** (dumb fetchers):
  - fetch_h2h() - Recent head-to-head results (raw data)
  - fetch_venue() - Venue name, capacity, expected attendance
  - fetch_weather() - Weather conditions (temperature, rain, wind)
  
  **AI Analysis** (what the agent actually does):
  - **H2H Pattern Extraction:** Analyzes recent encounters to identify home dominance, high-scoring trends, defensive patterns
  - **Weather Impact Analysis:** Evaluates cancellation risk and draw probability impact based on conditions
  
  **Output:** GameReport Pydantic model (from structured_outputs.py):
  - h2h_insights: str (patterns extracted by AI)
  - weather_risk: str (AI assessment)
  - venue: str (simple venue name from fixtures API)
  
  Agent makes **2-3 LLM calls:** initial tool orchestration call, then analysis synthesis call(s).

---

## 5. Team Intelligence Agent Subgraph (🤖 Smart Agent with Tools)

### 5.1 Team Subgraph Manager
- [ ] Create `team_intelligence_subgraph/graph_manager.py` as reusable subgraph instantiated per team (2 teams × N games parallelism). Orchestrates Team Intelligence Agent.

### 5.2 Team Intelligence Agent Node
- [ ] Implement `NodeWrapper` with AI agent (following StocksMarketRecommender pattern) equipped with tools:

  **Tools** (dumb fetchers via FotMob):
  - calculate_recovery_time() - Days since team's last match
  - fetch_form() - Last 5 games results (W/D/L with scores)
  - fetch_injuries() - Current injury list with player names
  - fetch_league_position() - Team's position, points, form in league standings

  **AI Analysis** (what the agent actually does):
  1. **Form Trend Analysis:** Computes improving/declining trajectory from last 5 games (not just W/D/L count)
  2. **Injury Impact Assessment:** **Critical** - Flags whether injured players are starters vs bench warmers. For teams user doesn't know (e.g., Napoli), AI must use context clues from injury data.
  3. **League Context:** Uses league position to assess team quality, motivation (title race, relegation battle, mid-table comfort).

  **Output:** TeamReport Pydantic model (from structured_outputs.py):
  - recovery_days: int (from calculate_recovery_time tool)
  - form_trend: str (AI-computed: "improving", "declining", "stable" + reasoning)
  - injury_impact: str (AI assessment: "critical starters missing" vs "minor depth issues")
  - league_context: str (AI summary of team's league position and implications)

  Agent makes **3-5 LLM calls:**
  - 1 initial orchestration call (decide which tools to use)
  - 1-2 analysis calls for complex categories (form trend + injury impact)
  - 1-2 synthesis calls for final report assembly

---

## 6. Integration & Testing

### 6.1 Parallel Subgraph Orchestration
- [ ] Implement parallel execution of game subgraphs (1:N) and team subgraphs (2N:1) using LangGraph. Collect results via DB writes for maximum parallelism.

### 6.2 Error Handling & Partial Data Strategy
- [ ] Define fallback behavior when tools fail: continue with partial reports flagging data quality. Implement retry logic and logging for debugging.

### 6.3 End-to-End Flow Testing
- [ ] Create integration test simulating full Pre-Gambling Flow with mock data sources. Verify: game selection → The Odds API odds → parallel fetching → report generation → DB persistence → trigger.

### 6.4 Tool Integration Testing
- [ ] Verify all tools work correctly: existing MCPs (browser), Python API clients, Python utility functions wrapped as LangGraph tools. **No custom MCP development** - MCPs are for external consumers, we use Python tools internally.

### 6.5 Add Structured Logging to Tools
- [ ] Add logging to all tool exception handlers and key operations. Currently tools catch exceptions but don't log them, making production debugging difficult. Use Python's `logging` module with structured context (tool_name, team_name, error_type).

---

## 7. Deployment & Monitoring

### 7.1 Cron Job Setup
- [ ] Configure production cron/scheduler with error notifications and manual trigger capability. Ensure idempotency for same-day re-runs.

### 7.2 Logging & Observability
- [ ] Instrument all nodes with structured logging (game_id, node_name, duration, errors). Integrate with LangSmith tracing for full visibility into agent decisions and tool usage.

---

## Key Design Decisions

1. **Agent Architecture:** 2 smart agents (Game + Team Intelligence) with rich tool access vs. 16 specialized fetcher agents. Follows **StocksMarketRecommender pattern**. Tools are dumb fetchers, agents do sophisticated analysis.

2. **State vs DB:** State for coordination only (game IDs, phase, messages). Game/team data written **directly to DB** from parallel subgraphs, not accumulated in state.

3. **LLM Budget:** ~20-30 calls total per run (3 games × [2-3 game calls + 2×(3-5 team calls)] ≈ 24-33 calls). Using gpt-4o-mini for cost efficiency. Each agent makes multiple purposeful calls: orchestration, analysis, synthesis.

4. **Parallelism:** Full parallel execution of subgraphs via LangGraph. Essential for performance and learning complex orchestration.

5. **Odds Source:** The Odds API as primary/only odds source. Free tier with 500 credits/month provides decimal odds matching Israeli Toto format.

6. **Game Selection:** Sophisticated AI picker based on rivalry/importance/context, NOT simple odds threshold filter.

7. **Data Quality:** Tolerate partial data with quality flags. Don't abort on missing non-critical information.

8. **MCP Strategy:** Use existing MCPs where available (browser, any football MCPs found). Don't develop custom MCPs - write Python functions wrapped as LangGraph tools instead.

---
