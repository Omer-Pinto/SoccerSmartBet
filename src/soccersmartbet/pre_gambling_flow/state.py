"""
Pre-Gambling Flow State Definition

This module defines the state schema for the Pre-Gambling Flow orchestration graph,
following the StocksMarketRecommender reference architecture pattern.

State Design Philosophy (per LangGraphWrappers + StocksMarketRecommender):
----------------------------------------------------------------------
- State is for COORDINATION ONLY, not data accumulation
- Game/team report data goes directly to DB from parallel subgraphs
- State tracks: flow phase, message history, game IDs for orchestration
- Uses simple LangGraph reducers: add_messages for messages, add for lists

References:
-----------
- Pattern: external_projects/StocksMarketRecommender.md (state.py)
- DB Schema: db/schema.sql (games.game_id as SERIAL PRIMARY KEY)
- Wrapper DSL: external_projects/LangGraphWrappers.md
"""

from enum import Enum
from typing import Annotated, TypedDict

from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage


# Custom reducer for list accumulation (mimics StocksMarketRecommender pattern)
def add(left: list, right: list) -> list:
    """
    Simple list concatenation reducer for LangGraph state fields.
    
    Args:
        left: Existing list in state
        right: New list to append
        
    Returns:
        Concatenated list
    """
    return left + right


class Phase(Enum):
    """
    Pre-Gambling Flow execution phases for conditional routing.
    
    Flow progression:
    SELECTING → FILTERING → ANALYZING → COMPLETE
    
    Phase purposes:
    - SELECTING: Smart Picker choosing interesting games from football-data.org
    - FILTERING: Fetching odds from The Odds API + applying min-odds threshold
    - ANALYZING: Parallel subgraphs running (Game + Team Intelligence Agents)
    - COMPLETE: Flow finished, reports in DB, ready to trigger Gambling Flow
    """
    SELECTING = "selecting"
    FILTERING = "filtering"
    ANALYZING = "analyzing"
    COMPLETE = "complete"


class AnalyzeGameState(TypedDict):
    """
    State schema for the analyze_game subgraph.

    This subgraph is invoked once per game via Send() from the main
    Pre-Gambling Flow graph.  The Send payload populates the input fields
    (game_id through kickoff_time).  The subgraph's three internal nodes
    (game_intelligence, team_intelligence_home, team_intelligence_away)
    run in parallel, each writing reports directly to the DB.

    After all three complete, the subgraph output includes
    ``analyzed_game_ids`` which the parent graph's ``add`` reducer
    merges into ``PreGamblingState.analyzed_game_ids`` for fan-in
    tracking.

    Input fields (set by Send payload):
        game_id: DB primary key from the games table.
        home_team: Home team name.
        away_team: Away team name.
        match_date: YYYY-MM-DD format.
        kickoff_time: HH:MM format (24-hour).

    Output field (returned to parent):
        analyzed_game_ids: Single-element list ``[game_id]`` produced
            by the game_intelligence node upon completion.
    """
    game_id: int
    home_team: str
    away_team: str
    match_date: str
    kickoff_time: str
    analyzed_game_ids: Annotated[list[int], add]


class GameContext(TypedDict):
    """
    Minimal game context stored in state for debugging/logging.

    This is NOT the full game report - detailed analysis goes to DB tables
    (game_reports, team_reports). This lightweight context enables graph nodes
    to log/debug without DB calls.

    Why TypedDict not Pydantic:
    ---------------------------
    State fields should be simple typed dicts per LangGraph conventions.
    Pydantic models are reserved for structured_outputs.py (node responses).

    Field Sources:
    --------------
    - game_id: DB primary key from games.game_id (SERIAL)
    - home_team, away_team, league, venue: football-data.org API
    - match_date, kickoff_time: football-data.org API
    - n1, n2, n3: The Odds API (Israeli Toto notation: 1=home, 2=away, x=draw)

    DB Schema Reference:
    --------------------
    Maps to `games` table columns (db/schema.sql):
    - game_id → games.game_id (SERIAL PRIMARY KEY)
    - All other fields → direct column matches
    """
    game_id: int  # DB PK from games.game_id (SERIAL PRIMARY KEY)
    home_team: str
    away_team: str
    match_date: str  # Format: YYYY-MM-DD
    kickoff_time: str  # Format: HH:MM
    league: str
    venue: str  # Stadium name from football-data.org
    n1: float  # Home win odds (The Odds API)
    n2: float  # Away win odds
    n3: float  # Draw odds


class PreGamblingState(TypedDict):
    """
    Main state schema for Pre-Gambling Flow graph orchestration.

    Design Principles:
    ------------------
    1. COORDINATION ONLY - No accumulated game/team analysis data
    2. Parallel intelligence nodes write reports directly to DB
       (game_reports, team_reports)
    3. State tracks: message history, game contexts, filtered IDs, flow phase,
       and analyzed-game IDs (for fan-in synchronisation)
    4. Uses standard LangGraph reducers (add_messages, add)

    Field Purposes:
    ---------------
    messages:
        LLM conversation history required for agent nodes.
        Reducer: add_messages (LangGraph built-in for BaseMessage merging)

    all_games:
        Full context for ALL games inserted to DB by Smart Picker + Filter nodes.
        Used for debugging, logging, and orchestration decisions.
        Reducer: add (custom list concatenation)

    games_to_analyze:
        Filtered game IDs (DB PKs) that passed odds threshold.
        These are fanned-out via LangGraph Send() to the ``analyze_game``
        node — one invocation per game running in parallel.
        Reducer: add (custom list concatenation)

    analyzed_game_ids:
        Game IDs whose intelligence analysis has completed.  Each
        ``analyze_game`` fan-out invocation appends its game_id here.
        The ``add`` reducer merges results from all parallel branches
        so downstream nodes (combine_reports) can verify completeness.
        Reducer: add (custom list concatenation)

    phase:
        Current flow phase enum for conditional routing.
        No reducer (single-value field, last write wins).

    Graph Flow (LangGraph Send() pattern):
    ---------------------------------------
    1. START -> smart_game_picker (phase=SELECTING)
       - Queries football-data.org for today's games
       - Inserts selected games to DB
       - Populates state.all_games with GameContext objects
       - Sets phase=FILTERING

    2. smart_game_picker -> persist_games (phase=ANALYZING)
       - Inserts games to DB, gets real PKs
       - Sets state.games_to_analyze with DB PKs

    3. persist_games -> [fan_out_to_analysis via Send()]
       - For each game_id: Send("analyze_game", {game payload})
       - LangGraph dispatches N parallel analyze_game invocations

    4. analyze_game (N parallel invocations)
       - Runs game intelligence + 2x team intelligence per game
       - Writes reports to DB
       - Returns {analyzed_game_ids: [game_id]} for fan-in

    5. analyze_game -> combine_reports -> persist_reports -> END

    References:
    -----------
    - Pattern: StocksMarketRecommender state.py (Phase enum + TypedDict + reducers)
    - DB Schema: db/schema.sql (games, game_reports, team_reports tables)
    - Architecture: README.md (Pre-Gambling Flow)
    """
    messages: Annotated[list[BaseMessage], add_messages]
    all_games: Annotated[list[GameContext], add]
    games_to_analyze: Annotated[list[int], add]
    analyzed_game_ids: Annotated[list[int], add]
    phase: Phase
