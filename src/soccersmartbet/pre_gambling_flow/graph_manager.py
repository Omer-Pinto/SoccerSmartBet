"""
Pre-Gambling Flow Graph Manager

Wires the full Pre-Gambling Flow as a LangGraph StateGraph.

Flow phases: SELECTING → FILTERING → ANALYZING → COMPLETE

Graph structure:
    START → smart_game_picker → persist_games → [conditional]
          → parallel_orchestrator → combine_reports → persist_reports → END

The conditional edge at 'persist_games' maps 'analyze' to
'parallel_orchestrator', which runs game and team intelligence agents
sequentially before handing off to combine_reports.
"""

from langgraph.graph import StateGraph, START, END

from soccersmartbet.pre_gambling_flow.state import PreGamblingState, Phase
from soccersmartbet.pre_gambling_flow.nodes.smart_game_picker import smart_game_picker
from soccersmartbet.pre_gambling_flow.nodes.persist_games import persist_games
from soccersmartbet.pre_gambling_flow.agents.parallel_orchestrator import parallel_orchestrator
from soccersmartbet.pre_gambling_flow.nodes.combine_reports import combine_reports
from soccersmartbet.pre_gambling_flow.nodes.persist_reports import persist_reports


def route_after_persist(state: PreGamblingState) -> str:
    """Route after persist_games to the parallel orchestrator.

    Args:
        state: Current Pre-Gambling Flow state.

    Returns:
        Routing key string. Always 'analyze'.
    """
    return "analyze"


def build_pre_gambling_graph() -> StateGraph:
    """Build and return the compiled Pre-Gambling Flow graph.

    Graph structure:
        START → smart_game_picker → persist_games → [route_after_persist]
              → parallel_orchestrator → combine_reports → persist_reports → END

    The conditional edge at 'persist_games' maps 'analyze' to
    'parallel_orchestrator', which drives all intelligence agents before
    combine_reports assembles the final output.

    Returns:
        Compiled LangGraph Runnable ready to invoke.
    """
    graph = StateGraph(PreGamblingState)

    graph.add_node("smart_game_picker", smart_game_picker)
    graph.add_node("persist_games", persist_games)
    graph.add_node("parallel_orchestrator", parallel_orchestrator)
    graph.add_node("combine_reports", combine_reports)
    graph.add_node("persist_reports", persist_reports)

    graph.add_edge(START, "smart_game_picker")
    graph.add_edge("smart_game_picker", "persist_games")
    graph.add_conditional_edges(
        "persist_games",
        route_after_persist,
        {"analyze": "parallel_orchestrator"},
    )
    graph.add_edge("parallel_orchestrator", "combine_reports")
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
