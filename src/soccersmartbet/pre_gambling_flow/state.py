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
    2. Parallel subgraphs write reports directly to DB (game_reports, team_reports)
    3. State tracks: message history, game contexts, filtered IDs, flow phase
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
        These spawn parallel subgraphs (Game + Team Intelligence Agents).
        Reducer: add (custom list concatenation)
        
    phase:
        Current flow phase enum for conditional routing.
        No reducer (single-value field, last write wins).
        
    Graph Flow Example:
    -------------------
    1. START → Smart Picker (phase=SELECTING)
       - Queries football-data.org for today's games
       - Inserts selected games to DB
       - Populates state.all_games with GameContext objects
       - Sets phase=FILTERING
       
    2. Router → Filter Node (phase=FILTERING)
       - Fetches odds from The Odds API for games in state.all_games
       - Applies min-odds threshold (configurable)
       - Updates state.games_to_analyze with filtered game IDs (DB PKs)
       - Sets phase=ANALYZING
       
    3. Router → Parallel Subgraph Orchestrator (phase=ANALYZING)
       - For each game_id in state.games_to_analyze:
           - Spawn Game Intelligence subgraph (writes to game_reports table)
           - Spawn 2x Team Intelligence subgraphs (writes to team_reports table)
       - Wait for all parallel subgraphs to complete
       - Sets phase=COMPLETE
       
    4. Router → Trigger Gambling Flow (phase=COMPLETE)
       - Publishes event to trigger next flow
       - END
    
    References:
    -----------
    - Pattern: StocksMarketRecommender state.py (Phase enum + TypedDict + reducers)
    - DB Schema: db/schema.sql (games, game_reports, team_reports tables)
    - Architecture: agents.md (Section 5.1 - Pre-Gambling Flow)
    """
    messages: Annotated[list[BaseMessage], add_messages]
    all_games: Annotated[list[GameContext], add]
    games_to_analyze: Annotated[list[int], add]
    phase: Phase
