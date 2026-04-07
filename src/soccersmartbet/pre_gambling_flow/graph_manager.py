"""
Pre-Gambling Flow Graph Manager

Wires the full Pre-Gambling Flow as a LangGraph StateGraph.

Flow phases: SELECTING → FILTERING → ANALYZING → COMPLETE

Current graph structure (Agent 4B intelligence agents not yet built):
    START → smart_game_picker → persist_games → [conditional] → combine_reports → persist_reports → END

The conditional edge at 'persist_games' uses the 'analyze' routing key.
Agent 4B will insert parallel_orchestrator at that key without restructuring
the graph.
"""

from langgraph.graph import StateGraph, START, END

from soccersmartbet.pre_gambling_flow.state import PreGamblingState, Phase
from soccersmartbet.pre_gambling_flow.nodes.smart_game_picker import smart_game_picker
from soccersmartbet.pre_gambling_flow.nodes.persist_games import persist_games
from soccersmartbet.pre_gambling_flow.nodes.combine_reports import combine_reports
from soccersmartbet.pre_gambling_flow.nodes.persist_reports import persist_reports


def route_after_persist(state: PreGamblingState) -> str:
    """Route after persist_games. Currently skips to combine_reports.

    Agent 4B will add intelligence agents at the 'analyze' routing key.

    Args:
        state: Current Pre-Gambling Flow state.

    Returns:
        Routing key string. Currently always 'analyze'.
    """
    return "analyze"


def build_pre_gambling_graph() -> StateGraph:
    """Build and return the compiled Pre-Gambling Flow graph.

    Graph structure:
        START → smart_game_picker → persist_games → [route_after_persist]
              → combine_reports → persist_reports → END

    The conditional edge at 'persist_games' maps 'analyze' to 'combine_reports'
    today. Agent 4B will remap 'analyze' to 'parallel_orchestrator' once
    intelligence agents are built.

    Returns:
        Compiled LangGraph Runnable ready to invoke.
    """
    graph = StateGraph(PreGamblingState)

    graph.add_node("smart_game_picker", smart_game_picker)
    graph.add_node("persist_games", persist_games)
    graph.add_node("combine_reports", combine_reports)
    graph.add_node("persist_reports", persist_reports)

    graph.add_edge(START, "smart_game_picker")
    graph.add_edge("smart_game_picker", "persist_games")
    graph.add_conditional_edges(
        "persist_games",
        route_after_persist,
        {"analyze": "combine_reports"},  # Will become: {"analyze": "parallel_orchestrator"} in 4B
    )
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
        "phase": Phase.SELECTING,
    }
    return graph.invoke(initial_state)
