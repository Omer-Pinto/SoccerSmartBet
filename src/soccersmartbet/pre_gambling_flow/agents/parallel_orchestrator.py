"""DEPRECATED: Parallel Orchestrator — replaced by LangGraph Send() fan-out.

The Python for-loop orchestration previously in this module has been replaced
by proper LangGraph graph-level orchestration:

- Fan-out: ``graph_manager.fan_out_to_analysis()`` uses ``Send()`` to dispatch
  one ``analyze_game`` node invocation per game in parallel.
- Fan-in: LangGraph's ``analyzed_game_ids`` reducer (``add`` list concatenation)
  merges results from all parallel branches automatically.
- Node: ``nodes/analyze_game.py`` is the LangGraph node that wraps the
  intelligence agent calls for a single game.

The intelligence agent utility functions (``run_game_intelligence``,
``run_team_intelligence``) remain in ``agents/game_intelligence.py`` and
``agents/team_intelligence.py`` respectively — they are called by the
``analyze_game`` node.

This file is kept to avoid import errors from any stale references.
It should not be used in new code.
"""

from __future__ import annotations


def parallel_orchestrator(*args, **kwargs):
    """Deprecated stub — raises if accidentally called."""
    raise NotImplementedError(
        "parallel_orchestrator has been replaced by LangGraph Send() fan-out. "
        "Use graph_manager.build_pre_gambling_graph() which dispatches to "
        "nodes/analyze_game.py via Send(). See graph_manager.fan_out_to_analysis()."
    )
