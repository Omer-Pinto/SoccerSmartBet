"""Analyze Game subgraph for the Pre-Gambling Flow.

Builds a LangGraph StateGraph that runs three intelligence nodes in
parallel for a single game:

    START -> game_intelligence -----\
    START -> team_intel_home ---------> END
    START -> team_intel_away -------/

Each node calls the corresponding utility function (which fetches data,
invokes the LLM, and writes the report to the DB).  The subgraph is
compiled and registered as a node in the main Pre-Gambling Flow graph,
so LangGraph dispatches one subgraph invocation per game via Send().

The game_intelligence node also produces the ``analyzed_game_ids``
output so the parent graph's ``add`` reducer can track fan-in progress.
The team intelligence nodes return empty dicts since their only side
effect is the DB write.
"""

from __future__ import annotations

import logging

from langgraph.graph import StateGraph, START, END

logger = logging.getLogger(__name__)

from soccersmartbet.pre_gambling_flow.state import AnalyzeGameState
from soccersmartbet.pre_gambling_flow.agents.db_utils import update_game_status
from soccersmartbet.pre_gambling_flow.agents.game_intelligence import run_game_intelligence
from soccersmartbet.pre_gambling_flow.agents.team_intelligence import run_team_intelligence


def _game_intelligence_node(state: AnalyzeGameState) -> dict:
    """Subgraph node: run game-level intelligence (H2H, venue, weather, news).

    Marks the game as processing, calls the game intelligence utility
    function (which fetches data, calls LLM, and persists the GameReport),
    then returns the game_id for parent fan-in tracking.

    Args:
        state: AnalyzeGameState populated by the Send() payload.

    Returns:
        State update with ``analyzed_game_ids`` containing the processed
        game_id.  This is the only node that produces fan-in output.
    """
    game_id = state["game_id"]
    logger.info(
        "game_intelligence: starting for game_id=%d (%s vs %s)",
        game_id,
        state["home_team"],
        state["away_team"],
    )

    update_game_status(game_id, "processing")

    run_game_intelligence(
        game_id,
        state["home_team"],
        state["away_team"],
        state["match_date"],
        state["kickoff_time"],
    )

    logger.info("game_intelligence: completed for game_id=%d", game_id)
    return {"analyzed_game_ids": [game_id]}


def _team_intelligence_home_node(state: AnalyzeGameState) -> dict:
    """Subgraph node: run team intelligence for the home side.

    Calls the team intelligence utility function for the home team
    (form, injuries, league position, recovery).  The TeamReport is
    persisted to the DB by the utility function.

    Args:
        state: AnalyzeGameState populated by the Send() payload.

    Returns:
        Empty dict -- no state updates needed; DB write is the side effect.
    """
    logger.info(
        "team_intel_home: starting for game_id=%d (%s vs %s)",
        state["game_id"],
        state["home_team"],
        state["away_team"],
    )
    run_team_intelligence(
        state["game_id"],
        state["home_team"],
        state["match_date"],
    )
    logger.info("team_intel_home: completed for game_id=%d", state["game_id"])
    return {}


def _team_intelligence_away_node(state: AnalyzeGameState) -> dict:
    """Subgraph node: run team intelligence for the away side.

    Calls the team intelligence utility function for the away team
    (form, injuries, league position, recovery).  The TeamReport is
    persisted to the DB by the utility function.

    Args:
        state: AnalyzeGameState populated by the Send() payload.

    Returns:
        Empty dict -- no state updates needed; DB write is the side effect.
    """
    logger.info(
        "team_intel_away: starting for game_id=%d (%s vs %s)",
        state["game_id"],
        state["home_team"],
        state["away_team"],
    )
    run_team_intelligence(
        state["game_id"],
        state["away_team"],
        state["match_date"],
    )
    logger.info("team_intel_away: completed for game_id=%d", state["game_id"])
    return {}


def build_analyze_game_subgraph():
    """Build and compile the analyze_game subgraph.

    Graph topology (all three nodes run in parallel):

        START -> game_intelligence -----\\
        START -> team_intel_home ---------> END
        START -> team_intel_away -------/

    Returns:
        Compiled LangGraph Runnable whose input/output schema is
        AnalyzeGameState.  Intended to be registered as a node in the
        main Pre-Gambling Flow graph.
    """
    graph = StateGraph(AnalyzeGameState)

    graph.add_node("game_intelligence", _game_intelligence_node)
    graph.add_node("team_intel_home", _team_intelligence_home_node)
    graph.add_node("team_intel_away", _team_intelligence_away_node)

    graph.add_edge(START, "game_intelligence")
    graph.add_edge(START, "team_intel_home")
    graph.add_edge(START, "team_intel_away")

    graph.add_edge("game_intelligence", END)
    graph.add_edge("team_intel_home", END)
    graph.add_edge("team_intel_away", END)

    return graph.compile()
