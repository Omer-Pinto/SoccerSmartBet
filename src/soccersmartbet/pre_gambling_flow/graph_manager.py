"""
Pre-Gambling Flow Graph Manager

Wires the full Pre-Gambling Flow as a LangGraph StateGraph using
Send() for parallel game analysis via the analyze_game subgraph.

Flow phases: SELECTING -> FILTERING -> ANALYZING -> COMPLETE

Graph structure:
    START -> smart_game_picker -> persist_games -> [fan_out_to_analysis]
          -> analyze_game subgraph (N parallel via Send()) -> combine_reports
          -> persist_reports -> END

The ``analyze_game`` node is a compiled subgraph with its own internal
parallel topology (game_intelligence, team_intel_home, team_intel_away).
Each Send() dispatches one subgraph invocation per game.  LangGraph
handles both the outer fan-out (per-game) and the inner parallelism
(per-intelligence-call within each game).

When no games need analysis, the fan-out sends directly to combine_reports
to gracefully skip the analysis phase.
"""

from __future__ import annotations

from langgraph.graph import StateGraph, START, END
from langgraph.types import Send

from soccersmartbet.pre_gambling_flow.state import PreGamblingState, Phase
from soccersmartbet.pre_gambling_flow.nodes.smart_game_picker import smart_game_picker
from soccersmartbet.pre_gambling_flow.nodes.persist_games import persist_games
from soccersmartbet.pre_gambling_flow.nodes.analyze_game import build_analyze_game_subgraph
from soccersmartbet.pre_gambling_flow.nodes.combine_reports import combine_reports
from soccersmartbet.pre_gambling_flow.nodes.persist_reports import persist_reports


def fan_out_to_analysis(state: PreGamblingState) -> list[Send]:
    """Fan-out router: dispatch one analyze_game subgraph invocation per game.

    For each game in ``games_to_analyze``, creates a ``Send()`` that
    dispatches to the ``analyze_game`` subgraph node with that game's
    specific payload (game_id, home_team, away_team, match_date,
    kickoff_time).  The payload matches the ``AnalyzeGameState`` schema
    so LangGraph can initialize the subgraph's state correctly.

    LangGraph runs all dispatched subgraph invocations in parallel.
    Within each subgraph, the three intelligence nodes also run in
    parallel.  Results are merged into the parent ``PreGamblingState``
    via the ``analyzed_game_ids`` ``add`` reducer before proceeding to
    ``combine_reports``.

    When there are no games to analyze (e.g. insufficient fixtures),
    sends directly to ``combine_reports`` to skip the analysis phase
    gracefully.

    Args:
        state: Current Pre-Gambling Flow state after persist_games.

    Returns:
        List of Send() objects -- one per game for analyze_game, or a
        single Send to combine_reports if the list is empty.
    """
    game_ids = state["games_to_analyze"]
    all_games = state["all_games"]

    if not game_ids:
        return [Send("combine_reports", state)]

    sends: list[Send] = []
    for i, game_id in enumerate(game_ids):
        game = all_games[i]
        sends.append(
            Send(
                "analyze_game",
                {
                    "game_id": game_id,
                    "home_team": game["home_team"],
                    "away_team": game["away_team"],
                    "match_date": game["match_date"],
                    "kickoff_time": game["kickoff_time"],
                    "analyzed_game_ids": [],
                },
            )
        )

    return sends


def build_pre_gambling_graph() -> StateGraph:
    """Build and return the compiled Pre-Gambling Flow graph.

    Graph structure:
        START -> smart_game_picker -> persist_games -> [fan_out_to_analysis]
              -> analyze_game subgraph (N parallel) -> combine_reports
              -> persist_reports -> END

    The analyze_game node is a compiled subgraph (not a plain function).
    Internally it runs game_intelligence, team_intel_home, and
    team_intel_away in parallel.  The fan-out at persist_games uses
    LangGraph's Send() API to dispatch one subgraph invocation per game.

    Returns:
        Compiled LangGraph Runnable ready to invoke.
    """
    graph = StateGraph(PreGamblingState)

    analyze_game_subgraph = build_analyze_game_subgraph()

    graph.add_node("smart_game_picker", smart_game_picker)
    graph.add_node("persist_games", persist_games)
    graph.add_node("analyze_game", analyze_game_subgraph)
    graph.add_node("combine_reports", combine_reports)
    graph.add_node("persist_reports", persist_reports)

    graph.add_edge(START, "smart_game_picker")
    graph.add_edge("smart_game_picker", "persist_games")

    graph.add_conditional_edges(
        "persist_games",
        fan_out_to_analysis,
        ["analyze_game", "combine_reports"],
    )

    graph.add_edge("analyze_game", "combine_reports")

    graph.add_edge("combine_reports", "persist_reports")
    graph.add_edge("persist_reports", END)

    return graph.compile()


def run_pre_gambling_flow():
    """Run the complete Pre-Gambling Flow with default initial state.

    Builds the graph and invokes it starting from Phase.SELECTING with
    empty message history and no games loaded yet.

    Returns:
        Final PreGamblingState after the full flow completes.
    """
    graph = build_pre_gambling_graph()
    initial_state = {
        "messages": [],
        "all_games": [],
        "games_to_analyze": [],
        "analyzed_game_ids": [],
        "phase": Phase.SELECTING,
    }
    return graph.invoke(initial_state)
