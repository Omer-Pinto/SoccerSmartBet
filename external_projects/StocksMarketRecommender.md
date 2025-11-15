## Overview
StocksMarketRecommender is a reference application that exercises LangGraphWrappers to build multi-node financial research agents. It hosts three graphs under `src/`:
1. `market_analyst_graph` – a single-loop analyst + MCP summarizer workflow.
2. `stocks_market_recommender_graph` – extends (1) with reporting/push notifications.
3. `agentic_stock_analyzer_graph` – a hierarchical manager that orchestrates iterative querying, subgraph execution, and investment decisions.

## Graph Pattern
Each graph bundles the same artifacts:
- `graph_manager.py` wires models, node wrappers, and `(START, EdgeType, targets)` tuples into a `GraphWrapper`, exposing `setup()`, `run_graph(...)`, and `cleanup()`.
- `state.py` defines a TypedDict with LangGraph reducers (`add_messages`, `add`) and domain enums (e.g., `Phase.QUERY` vs. `Phase.DECIDE`).
- `node_actions.py` holds async actions that read/write state slices and call their injected models (`action.__model__`).
- `structured_outputs.py` defines Pydantic schemas for structured responses (`AnalysisOutput`, `McpCall`, `InvestmentDecision`, `ManagerDecision`, etc.).
- `prompts.py` contains the system messages referenced by each node.
- `routers.py` decides the next node name based on state (tool calls present, query/decide phase, etc.).
- `tools_setup.py` centralizes toolkit instantiation via LangGraphWrappers’ `ToolsWrapper` API (Push notifications, Yahoo Finance MCP, file toolkit) and tears them down post-run.

## Notable Implementations
- **Market analyst loop** – `market_analyst_graph` routes between the analyst LLM node, a MCP tool node backed by `YahooFinanceMCPTools`, and a summarizer node that emits `AnalysisOutput`. Tool calls stay in `state["messages"]` so routers can examine `tool_calls` metadata.
- **Reporting workflow** – `stocks_market_recommender_graph` adds `report_file_writer`, which consumes the summarizer output, writes `report_[ticker]_DDMMYYYY.md`, and sends push notifications via the toolkit wrappers. Conditional edges let the writer call filesystem tools before terminating.
- **Hierarchical agent** – `agentic_stock_analyzer_graph` demonstrates orchestrating subgraphs: `market_research_manager` decides whether more data is needed, spawns the analyst subgraph via `market_analyst_subgraph_executer` (a `PythonNodeWrapper` that instantiates and runs the market analyst graph per query), aggregates results into `FinalQueryResult`, and hands them to `hedge_fund_manager` for scoring. The final `file_writer` dumps user input, query transcripts, and investment decisions into timestamped directories.
- **Control messages** – All graphs use `ControlMessage` events to signal orchestration milestones without fabricating LLM outputs.

## Extension Opportunities
- Plug additional MCP or LangChain toolkits into `tools_setup.py` and expose them via `ToolNodeWrapper` edges.
- Add more routers (e.g., risk checks) by enriching `state` with new fields and EdgeType.CONDITIONAL transitions.
- Reuse `market_analyst_graph` as a subgraph template for other domains (soccer match data fetchers) by swapping prompts and structured outputs but keeping the same GraphManager skeleton.
- Enhance state persistence by replacing or augmenting the `MemorySaver` checkpointer through LangGraphWrappers once advanced checkpointing requirements surface.
