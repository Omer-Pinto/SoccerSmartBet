# Smart AI Soccer Betting System

This project implements a **non-monetary, AI-assisted daily soccer game betting system**, built around four independent flows. The AI and user each place simulated bets on selected daily games, using rich real-time data and structured analysis. All logic runs in **Python 3.13**, powered by **LangGraph + LangGraphWrappers** (infrastructure) and follows the graph/style patterns demonstrated in **StocksMarketRecommender**.

This file gives a **high-level architectural overview** and defines guidelines and structure for code structure and generation.

---

## 1. System Architecture Overview

The system is organized around four main application flows, each responsible for a distinct stage of the daily 
soccer-betting lifecycle.
Refer to the architecture diagram as canonical. This md file must be read together with that visual:

![System Architecture Diagram](./resources/app_flows.png)

### Daily execution order and triggering
- **Pre-Gambling Flow** runs first each day on a fixed schedule (cron).  
  It selects the day’s games, fetches all required data, builds reports, and then triggers the next flow.

- **Gambling Flow** runs immediately after Pre-Gambling finishes.  
  It collects bets from both the user and the AI for the games of the day. It schedules the Post-Games Flow trigger for later.

- **Post-Games Flow** runs later, when all games for that day have completed.  
  Its trigger time is scheduled dynamically, e.g. *3 hours after the latest kickoff time*.

- **Offline Analysis Flow** runs on demand, any time a user requests statistics or insights from the UI.  
  It can execute multiple times per day and does not depend on the other flows.

---

## 2. Technology Stack (Concise)
- **Runtime:** Python **3.13**  
- **Graph engine:**  
  - **LangGraph** for orchestration  
  - **LangGraphWrappers** (my infra repo) for simplified, unified node/graph creation patterns  
- **Patterns Reference:**  
  - **StocksMarketRecommender** (my repo also) — demonstrates how to build multi-node, multi-toolgraphs using GraphManager, NodeActions, State, StructuredOutputs, ToolsSetup.
- **DB:** PostgreSQL or MySQL (TBD; relational expected).  
- **Frontend:** TBD (Telegram bot or app).  
- **Scraping / Data:** Prefer APIs when possible; fallback to scrapers. MCP integration may be used to sandbox scraping tasks.  
- **Parallelism:** Game-level and team-level subflows run in **parallel** using LangGraph subgraphs.

---

## 3. Purpose & Assumptions

**Goal:** Each day, pick meaningful games (main matches with minnimum lines above configurable threshold that allows substantial gain) , fetch structured data (game + team), produce AI-enriched reports, collect user & AI bets, compute P&L, and support offline analytics.

**Betting assumptions:**
1. Each game has **3 outcomes**: `'1'` = home win, `'x'` = draw, `'2'` = away win.  
2. Each game has **3 lines**: `n1`, `n2`, `n3` (float odds).  
3. Only **single bets per game** (no combos).  
4. Each day’s gambling is **per-game**, not tournaments.  
5. Both user & AI place **100 NIS** simulated stakes per game (win = stake × odds; loss = − stake).

---

## 4. Data Fetcher Logic (Pre-Gambling Flow)

The Pre-Gambling Flow contains **two extendible subflows**:

### A. Game Data Fetchers  
Fetch per-game information:
- Venue  
- Expected crowd  
- Atmosphere news  
- Weather (important: cancellations → `x`)  
- Head-to-head recent results  

### B. Team Data Fetchers  
Fetch for each team:
- Recent form (5 games)  
- Recovery time (days since last match)  
- Injury list  
- Suspension list  
- Returning players  
- Rotation/absence list (incl. coach)  
- Near-future match importance  
- Top players form (goals/assists/GA)  
- Team morale & coach stability  
- Preparation/training news  
- Any other relevant news

**Important:**  
- These subflows must be **modular & extendible**.  
- Some fetchers may return empty data; the system must tolerate partial information.  
- MCP tools *may* replace scrapers to reduce fragility.

---

## 5. Flow Overview (Short)

### 5.1 Pre-Gambling Flow
- Triggered daily.  
- Picks games, fetches lines, filters interesting matches.  
- Runs **game** and **team** subgraphs in parallel (configurable amount of games, min. 3, and 2 teams per game).  
- Combines + persists reports.  
- Triggers next flow.

### 5.2 Gambling Flow
- Fetches today's games and their reports from DB.  
- User places bet (UI/Bot).  
- AI places bet (ModelWrapper-driven agent).  
- Collector/verifier checks both arrived before deadline.  
- Either persist bets or cancel that day's run.  
- Schedules the Post-Games Flow trigger for later (e.g., several hours after the latest kickoff time). It does not directly start that flow.

### 5.3 Post-Games Flow
- Fetches results online.  
- Computes P&L for both sides.  
- Updates DB.  
- Sends summary to user.

### 5.4 Offline Analysis Flow
- On demand.  
- Queries DB for success rate, P&L slices, team/league stats.  
- AI generates additional insights/explanations.  
- Returns enhanced analytics to user.

---

## 6. How Claude/Droid Should Build Code (Very Important)

Claude/Droid must follow patterns from:

1. **[LangGraphWrappers](https://github.com/Omer-Pinto/LangGraphWrappers)**
   - Use `GraphWrapper`, `NodeWrapper`, `PythonNodeWrapper`, `ModelWrapper`.
   - Don’t write bare LangGraph nodes manually.
   - Use `EdgeType.EDGE` / `EdgeType.CONDITIONAL`.

2. **[StocksMarketRecommender](https://github.com/Omer-Pinto/StocksMarketRecommender)**
   - Each flow = `graph_manager.py`, with:  
     - List of models (ModelWrapper)  
     - List of nodes  
     - Edges  
     - `setup()` / `cleanup()`  
   - Node implementations in `node_actions.py`.  
   - State definitions in `state.py`.  
   - Output schemas in `structured_outputs.py`.  
   - External tools in `tools_setup.py`.  
   - Prompts kept in `prompts.py`.

3. **Subgraphs for teams/games**
   - Pre-Gambling Flow’s fetchers MUST be implemented as **subgraphs**, one per team/game, running in parallel.

4. **Minimal DB schemas at first**
   - Use placeholder ORM models with TODOs.  
   - DB design evolves later.

5. **Flexibility**
   - Everything should remain extendible.  
   - Avoid hard-coding fields.  
   - Prefer typing (Pydantic/TypedDict) over loose dicts.

**Note:**  
The information in Section 6 is an executive summary.  
For deeper analysis of the referenced repositories (LangGraphWrappers and StocksMarketRecommender), dedicated Markdown “skill” files will be created separately.  
Those documents will contain a full breakdown of patterns, abstractions, and implementation details that this overview intentionally does not cover.
---

## 7. TBD Areas (Explicit)
- Full DB schema  
- Full tool/scraper API sourcing  
- Frontend (Telegram vs App)  
- Authentication, deployment, notifications  
- Exact HTML/JSON of returned reports  

Keep code modular so these can be swapped later.

---

## 8. Extensions (Future)
- New data fetchers added via adding nodes to game/team subflows.  
- New competitions, leagues, or analytic flows plug into the same structure.  
- Additional AI agents can be added easily by defining new ModelWrappers + NodeWrappers.

---