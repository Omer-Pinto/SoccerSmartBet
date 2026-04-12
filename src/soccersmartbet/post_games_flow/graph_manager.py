"""
Post-Games Flow Graph Manager

Wires the Post-Games Flow as a LangGraph StateGraph.

Graph structure:
    START -> fetch_results -> calculate_pnl -> notify_daily_summary -> END

Entry point: run_post_games_flow(game_ids) — invoked after games finish.
"""

from __future__ import annotations

import logging

from langgraph.graph import END, START, StateGraph

from soccersmartbet.post_games_flow.fetch_results import fetch_results
from soccersmartbet.post_games_flow.pnl_calculator import calculate_pnl
from soccersmartbet.post_games_flow.notify_summary import notify_daily_summary
from soccersmartbet.post_games_flow.state import PostGamesState

logger = logging.getLogger(__name__)


def build_post_games_graph() -> StateGraph:
    """Build and return the compiled Post-Games Flow graph.

    Graph structure:
        START -> fetch_results -> calculate_pnl -> notify_daily_summary -> END

    Returns:
        Compiled LangGraph Runnable ready to invoke.
    """
    graph = StateGraph(PostGamesState)

    graph.add_node("fetch_results", fetch_results)
    graph.add_node("calculate_pnl", calculate_pnl)
    graph.add_node("notify_daily_summary", notify_daily_summary)

    graph.add_edge(START, "fetch_results")
    graph.add_edge("fetch_results", "calculate_pnl")
    graph.add_edge("calculate_pnl", "notify_daily_summary")
    graph.add_edge("notify_daily_summary", END)

    return graph.compile()


def run_post_games_flow(game_ids: list[int]) -> dict:
    """Entry point: run post-games flow for the given game IDs.

    Fetches final scores from football-data.org, calculates P&L for all bets,
    updates the DB, and sends a Telegram summary.

    Args:
        game_ids: List of DB game IDs for games that have finished.

    Returns:
        Final PostGamesState after the flow completes.
    """
    logger.info("run_post_games_flow: starting for %d game(s)", len(game_ids))

    graph = build_post_games_graph()

    initial_state: PostGamesState = {
        "game_ids": game_ids,
        "results": {},
        "pnl_summary": {},
    }

    result = graph.invoke(initial_state)

    logger.info(
        "run_post_games_flow: completed — processed %d result(s)",
        len(result.get("results", {})),
    )

    return result
