"""
Gambling Flow Graph Manager

Wires the Gambling Flow as a LangGraph StateGraph.

Graph structure:
    START -> ai_betting_agent -> verify_and_persist_bets
          -> notify_gambling_result -> END

Entry point: run_gambling_flow(game_ids, user_bets) — invoked by Telegram
handlers after the user clicks SEND BET.
"""

from __future__ import annotations

import logging

from langgraph.graph import StateGraph, START, END

from soccersmartbet.gambling_flow.state import GamblingState
from soccersmartbet.gambling_flow.ai_betting_agent import ai_betting_agent
from soccersmartbet.gambling_flow.bet_verifier import verify_and_persist_bets
from soccersmartbet.gambling_flow.notify_result import notify_gambling_result

logger = logging.getLogger(__name__)


def build_gambling_graph() -> StateGraph:
    """Build and return the compiled Gambling Flow graph.

    Graph structure:
        START -> ai_betting_agent -> verify_and_persist_bets
              -> notify_gambling_result -> END

    Returns:
        Compiled LangGraph Runnable ready to invoke.
    """
    graph = StateGraph(GamblingState)

    graph.add_node("ai_betting_agent", ai_betting_agent)
    graph.add_node("verify_and_persist_bets", verify_and_persist_bets)
    graph.add_node("notify_gambling_result", notify_gambling_result)

    graph.add_edge(START, "ai_betting_agent")
    graph.add_edge("ai_betting_agent", "verify_and_persist_bets")
    graph.add_edge("verify_and_persist_bets", "notify_gambling_result")
    graph.add_edge("notify_gambling_result", END)

    return graph.compile()


def run_gambling_flow(game_ids: list[int], user_bets: list[dict]) -> dict:
    """Entry point invoked by Telegram handlers after user clicks SEND BET.

    Args:
        game_ids: List of game IDs the user is betting on.
        user_bets: List of BetSelection dicts from the Telegram UI, each with
            game_id, prediction, odds, and stake.

    Returns:
        Final GamblingState after the flow completes.
    """
    logger.info(
        "run_gambling_flow: starting for %d game(s) with %d user bet(s)",
        len(game_ids),
        len(user_bets),
    )

    graph = build_gambling_graph()

    initial_state: GamblingState = {
        "game_ids": game_ids,
        "user_bets": user_bets,
        "ai_bets": [],
        "verification_result": "",
        "rejection_reason": "",
    }

    result = graph.invoke(initial_state)

    logger.info(
        "run_gambling_flow: completed — verification=%s",
        result.get("verification_result", "unknown"),
    )

    return result
