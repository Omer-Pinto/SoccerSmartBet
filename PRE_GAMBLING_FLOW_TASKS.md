# Pre-Gambling Flow - Task Breakdown

> **Legend:** 
> - 🤖 Purple (Bot icon) = Smart agent using LangGraph/LangGraphWrappers
> - 🐍 Green (Python icon) = Code implementation  
> - 🗄️ Grey (DB icon) = Database/infrastructure code
> - ⏰ Blue (Clock icon) = Trigger/scheduler
> - 🔍 Research = Investigation/discovery task

---

## 0. Research & Setup (🔍 Pre-Implementation)

### 0.1 Football Data Sources Research
- [ ] Research and catalog free football APIs, MCPs (prioritize MCP browser, starred GitHub MCPs), and data sources for: fixtures, lines/odds, team news, injuries, weather, H2H stats. Document reliability, rate limits, and coverage.

### 0.2 LangSmith Integration Setup
- [ ] Create dedicated LangSmith project for SoccerSmartBet and configure environment variables: LANGSMITH_TRACING, LANGSMITH_ENDPOINT, LANGSMITH_API_KEY. Verify tracing works with test LangGraph run.

---

## 1. Infrastructure & Foundation (🗄️ Database/Config)

### 1.1 PostgreSQL Schema Design
- [ ] Design complete PostgreSQL schema with tables: games, teams, players, betting_lines, game_reports, team_reports, unfiltered_games, bets, results. Include foreign keys, indexes, and constraints for relational integrity and historical tracking.

### 1.2 Configuration Management
- [ ] Create config file (YAML/JSON) for: min odds threshold, max daily games, API keys, cron schedule, DB connections (staging/prod), LangSmith keys, and feature flags. Support environment-specific overrides.

### 1.3 State Class & Structured Outputs Foundation
- [ ] Define TypedDict state class with LangGraph reducers (`add_messages`, `add`) following StocksMarketRecommender pattern. Create base Pydantic models for GameInfo, TeamInfo, GameReport, FilterCriteria.

### 1.4 Docker Compose for Database Environments
- [ ] Create docker-compose.yml with two PostgreSQL containers (staging on port 5432, production on port 5433), volumes for persistence, and initialization scripts. Include .env files for credentials.

---

## 2. Graph Architecture (LangGraphWrappers)

### 2.1 Pre-Gambling Flow GraphManager
- [ ] Create `pre_gambling_flow/graph_manager.py` wiring all nodes, edges, and subgraphs using GraphWrapper. Expose `setup()`, `run_graph()`, `cleanup()` methods following StocksMarketRecommender skeleton.

### 2.2 State Definition
- [ ] Implement `pre_gambling_flow/state.py` with fields: messages, selected_games, filtered_games, game_reports, team_reports, combined_reports, phase enum. Use LangGraph reducers for list accumulation and message tracking.

### 2.3 Structured Outputs Schema
- [ ] Create `pre_gambling_flow/structured_outputs.py` with Pydantic models: SelectedGames, FilteredGame, GameData, TeamData, CombinedReport, TriggerPayload. Each model maps to a node's expected output format.

### 2.4 Prompts Repository
- [ ] Implement `pre_gambling_flow/prompts.py` containing system messages for Smart Game Picker, Game Data Fetchers, Team Data Fetchers. Prompts should guide agents on data prioritization and structured output format.

### 2.5 Routers (if needed)
- [ ] Create `pre_gambling_flow/routers.py` for conditional routing logic (e.g., skip fetching if no games filtered, handle partial data). Use `NodeWrapper.router` pattern from LangGraphWrappers.

### 2.6 Tools Setup
- [ ] Implement `pre_gambling_flow/tools_setup.py` centralizing toolkit instantiation (web scrapers, API clients, MCP tools for data sources). Manage lifecycle with `ToolsWrapper.setup()/cleanup()`.

---

## 3. Main Flow Nodes

### 3.1 Pre-Gambling Trigger (⏰ Scheduler)
- [ ] Implement cron/scheduler (Python APScheduler or system cron) that initiates Pre-Gambling Flow daily at configured time. Trigger should inject initial state and handle error recovery/retries.

### 3.2 Smart Game Picker Node (🤖 AI Agent)
- [ ] Create `NodeWrapper` with AI agent that analyzes today's soccer fixtures across leagues and selects interesting games based on criteria. Agent outputs SelectedGames structured model with game IDs, teams, kickoff times, leagues.

### 3.3 Fetch Lines & Filter Games Node (🐍 Code)
- [ ] Implement `PythonNodeWrapper` that fetches betting lines (n1, n2, n3) from API/scraper for selected games and filters by minimum odds threshold. Outputs FilteredGame list (min 3 games) and raw unfiltered data.

### 3.4 Persist Unfiltered Games Node (🗄️ DB Operation)
- [ ] Create `PythonNodeWrapper` executing DB insert for all games considered (even if filtered out). Stores snapshot for historical analysis and debugging of filter logic.

### 3.5 Combine Results to Reports Node (🐍 Code)
- [ ] Implement `PythonNodeWrapper` that merges game data and team data (from parallel subgraphs) into final CombinedReport per game. Handles missing data gracefully, generates markdown/JSON reports.

### 3.6 Persist Reports to DB Node (🗄️ DB Operation)
- [ ] Create `PythonNodeWrapper` inserting CombinedReport records into reports table keyed by game_id and date. Updates game status to 'ready_for_betting'.

### 3.7 Send Gambling Trigger Node (🐍 Code)
- [ ] Implement node that triggers Gambling Flow (via queue, webhook, or direct invocation). Passes list of game_ids and report references as TriggerPayload.

---

## 4. Game Data Fetchers Subgraph (🤖 Smart Agents)

### 4.1 Game Subgraph Manager
- [ ] Create `game_data_fetchers_subgraph/graph_manager.py` as reusable subgraph instantiated per filtered game (1:many parallelism). Orchestrates 5 fetcher nodes below and aggregates into GameData output.

### 4.2 Venue & Crowd Fetcher Node
- [ ] Implement `NodeWrapper` with AI/tools fetching venue name, capacity, expected attendance for the game. Uses web scraping or MCP tools; tolerates missing data.

### 4.3 Atmosphere News Fetcher Node
- [ ] Create `NodeWrapper` gathering fan sentiment, stadium atmosphere news, security concerns, or crowd-related incidents. AI summarizes findings into brief text.

### 4.4 Weather Fetcher Node
- [ ] Implement `ToolNodeWrapper` calling weather API for game location/time, extracting rain probability, wind, temperature. Critical for cancellation risk → influences draw ('x') odds.

### 4.5 Head-to-Head Results Fetcher Node
- [ ] Create `NodeWrapper` retrieving recent H2H match results (last 5 encounters) between the two teams. AI extracts patterns (home dominance, high-scoring, etc.).

---

## 5. Team Data Fetchers Subgraph (🤖 Smart Agents)

### 5.1 Team Subgraph Manager
- [ ] Create `team_data_fetchers_subgraph/graph_manager.py` as reusable subgraph instantiated per team (2 teams × N games parallelism). Orchestrates 11 fetcher nodes below and aggregates into TeamData output.

### 5.2 Recent Form Fetcher Node
- [ ] Implement `NodeWrapper` fetching last 5 games results for the team (W/D/L, goals scored/conceded). AI computes form trend (improving/declining).

### 5.3 Recovery Time Calculator Node
- [ ] Create `PythonNodeWrapper` calculating days since team's last match using fixture data. Outputs recovery_days integer; critical for fatigue assessment.

### 5.4 Injury List Fetcher Node
- [ ] Implement `NodeWrapper` with AI/scraper extracting current injuries with severity and expected return dates. Prioritizes key players; tolerates incomplete data.

### 5.5 Suspension List Fetcher Node
- [ ] Create `NodeWrapper` fetching suspended players (red cards, accumulated yellows) with suspension duration. AI flags impactful absences.

### 5.6 Returning Players Fetcher Node
- [ ] Implement `NodeWrapper` identifying players returning from injury/suspension for this game. AI assesses potential impact on team strength.

### 5.7 Rotation & Absence List Fetcher Node
- [ ] Create `NodeWrapper` gathering rotation policy news, coach/player absences (illness, personal, tactical). AI extracts likely lineup changes.

### 5.8 Near-Future Match Importance Analyzer Node
- [ ] Implement `NodeWrapper` analyzing team's upcoming fixtures (next 2-3 games) to infer rotation risk. AI determines if coach might rest players for current game.

### 5.9 Top Players Form Analyzer Node
- [ ] Create `NodeWrapper` fetching recent performance stats (goals, assists, GA conceded) for 3-5 key players. AI summarizes individual form trends.

### 5.10 Team Morale & Coach Stability Fetcher Node
- [ ] Implement `NodeWrapper` gathering news on team morale (recent controversies, winning streak, coach under pressure). AI extracts sentiment and stability indicators.

### 5.11 Preparation & Training News Fetcher Node
- [ ] Create `NodeWrapper` fetching training reports, coach press conference notes, tactical preparation insights. AI highlights relevant preparation quality signals.

### 5.12 Other Relevant News Fetcher Node
- [ ] Implement catch-all `NodeWrapper` for miscellaneous news (transfers, ownership changes, fan protests, etc.). AI filters for betting-relevant information only.

---

## 6. Integration & Testing

### 6.1 Parallel Subgraph Orchestration
- [ ] Implement logic in main graph to spawn game subgraphs (1:N) and team subgraphs (2N:1) in parallel using LangGraph subgraph execution. Collect results via DB writes for maximum parallelism.

### 6.2 Error Handling & Partial Data Strategy
- [ ] Define fallback behavior when fetchers fail (timeouts, missing data sources): continue with partial reports or abort game. Implement retry logic and data quality validation.

### 6.3 End-to-End Flow Testing
- [ ] Create integration test simulating full Pre-Gambling Flow with mock data sources. Verify: game selection → filtering → parallel fetching → report generation → DB persistence → trigger.

### 6.4 Data Source Configuration
- [ ] Document and configure actual APIs/scrapers for each fetcher node (weather API, sports data providers, news sources). Set up MCP servers if using sandboxed scraping.

### 6.5 Football MCPs Implementation in LangGraphWrappers
- [ ] Implement new MCP wrappers in LangGraphWrappers repo (under tools/mcps/) for football data sources discovered in task 0.1. Create ToolsWrapper classes exposing these MCPs to user graphs, following YahooFinanceMCPTools pattern.

---

## 7. Deployment & Monitoring

### 7.1 Cron Job Setup
- [ ] Configure production cron/scheduler with error notifications, timeout handling, and manual trigger capability. Ensure idempotency for same-day re-runs.

### 7.2 Logging & Observability
- [ ] Instrument all nodes with structured logging (game_id, node_name, duration, errors). Add metrics for: games filtered, fetch success rates, report generation time. Integrate with LangSmith tracing from task 0.2.

---

## Design Decisions - FINALIZED ✅

1. **Parallelism Strategy:** ✅ AGREED - DB writes from parallel subgraphs. State for coordination only.

2. **LangGraphWrappers vs. Raw LangGraph:** ✅ AGREED - Use LangGraphWrappers for structure and clarity. Flag immediately if limitations found. Implement additional tools/MCPs in LangGraphWrappers as needed.

3. **MCP Integration:** ✅ AGREED - Prioritize free MCPs (MCP browser, starred GitHub MCPs) over paid APIs. Avoid fragile web scrapers and expensive services like Tavily. See task 0.1 for research phase.

4. **Subgraph Results Collection:** ✅ AGREED - Direct DB writes for true parallelism, avoiding complex nested state management across 12-18 agents × games/teams.

5. **Structured Output Enforcement:** ✅ AGREED - Strict `method="json_schema"` for critical nodes (Game Picker, data aggregators), flexible for news fetchers.

6. **Database Choice:** ✅ PostgreSQL - Relational structure ideal for betting data (games↔teams↔players, odds, P&L), ACID compliance, excellent analytics support, free, easy Docker setup.

7. **Observability:** ✅ Structured logging + LangSmith tracing (dedicated project) for flow monitoring and debugging.

---

## Progress Tracking

**Total Tasks:** 43  
**Completed:** 0  
**In Progress:** 0  
**Remaining:** 43

**Breakdown by Category:**
- Research & Setup: 2 tasks
- Infrastructure: 4 tasks  
- Graph Architecture: 6 tasks
- Main Flow Nodes: 7 tasks
- Game Fetchers Subgraph: 5 tasks
- Team Fetchers Subgraph: 12 tasks
- Integration & Testing: 5 tasks
- Deployment & Monitoring: 2 tasks

**Parallelizable Work:** Game/team fetcher nodes (17 tasks) can be developed independently once subgraph managers are defined.
