"""Parallel Orchestrator for Pre-Gambling Flow intelligence agents.

Runs sequentially through each game selected for analysis, invoking
game intelligence and both team intelligence agents per game. Each
agent writes its report directly to the DB — no results are collected
here.
"""

from soccersmartbet.pre_gambling_flow.state import PreGamblingState
from soccersmartbet.pre_gambling_flow.agents.game_intelligence import run_game_intelligence
from soccersmartbet.pre_gambling_flow.agents.team_intelligence import run_team_intelligence
from soccersmartbet.pre_gambling_flow.agents.db_utils import update_game_status


def parallel_orchestrator(state: PreGamblingState) -> dict:
    """Run intelligence agents for every game selected for analysis.

    Iterates over ``games_to_analyze`` in order, running game intelligence
    and both team intelligence agents for each. Each agent persists its
    report to the DB independently. The orchestrator returns an empty dict
    because no state mutations are needed.

    Args:
        state: Current Pre-Gambling Flow state. Must contain ``all_games``
            and ``games_to_analyze`` in the same positional order as
            produced by ``smart_game_picker`` and preserved by
            ``persist_games``.

    Returns:
        Empty dict — all results are written directly to the DB by the
        intelligence agents.
    """
    games = state["all_games"]
    game_ids = state["games_to_analyze"]

    if not game_ids:
        return {}

    for i, game_id in enumerate(game_ids):
        game = games[i]
        home_team = game["home_team"]
        away_team = game["away_team"]
        match_date = game["match_date"]
        kickoff_time = game["kickoff_time"]

        update_game_status(game_id, "processing")

        run_game_intelligence(game_id, home_team, away_team, match_date, kickoff_time)

        run_team_intelligence(game_id, home_team, match_date)

        run_team_intelligence(game_id, away_team, match_date)

    return {}
