"""
P&L Calculator node for the Post-Games Flow.

Reads bets from DB, computes profit/loss per bet, and atomically updates
the bets and bankroll tables within a single transaction.
"""

from __future__ import annotations

import logging
from collections import defaultdict

from soccersmartbet.db import get_conn
from soccersmartbet.post_games_flow.state import PostGamesState

logger = logging.getLogger(__name__)

_FETCH_BETS_SQL = """
SELECT bet_id, game_id, bettor, prediction, odds, stake
FROM bets
WHERE game_id = ANY(%(game_ids)s)
"""

_UPDATE_BET_SQL = """
UPDATE bets
SET result = %(result)s,
    pnl    = %(pnl)s
WHERE bet_id = %(bet_id)s
"""

_UPDATE_BANKROLL_SQL = """
UPDATE bankroll
SET total_bankroll = total_bankroll + %(total_pnl)s,
    games_played   = games_played   + %(games_played)s,
    games_won      = games_won      + %(games_won)s,
    games_lost     = games_lost     + %(games_lost)s,
    last_updated   = CURRENT_TIMESTAMP
WHERE bettor = %(bettor)s
"""


def calculate_pnl(state: PostGamesState) -> dict:
    """LangGraph node: compute bet P&L and update DB atomically.

    Steps:
      1. Fetch all bets for the given game_ids.
      2. Compare each bet.prediction to the game outcome.
      3. UPDATE bets.result and bets.pnl for each bet.
      4. Aggregate and UPDATE bankroll per bettor.

    All writes run inside a single DB transaction for atomicity.

    Args:
        state: Current PostGamesState with game_ids and results populated.

    Returns:
        dict with key "pnl_summary" mapping game_id ->
        {"user_pnl": float, "ai_pnl": float}.
    """
    game_ids: list[int] = state["game_ids"]
    results: dict = state.get("results", {})
    logger.info("calculate_pnl: processing %d game(s)", len(game_ids))

    with get_conn() as conn:
        with conn.cursor() as cur:
            # 1. Fetch bets
            cur.execute(_FETCH_BETS_SQL, {"game_ids": game_ids})
            bets = cur.fetchall()

            # Accumulators keyed by bettor
            bettor_pnl: dict[str, float] = defaultdict(float)
            bettor_played: dict[str, int] = defaultdict(int)
            bettor_won: dict[str, int] = defaultdict(int)
            bettor_lost: dict[str, int] = defaultdict(int)

            # Per-game P&L keyed by (game_id, bettor)
            game_bettor_pnl: dict[tuple, float] = {}

            for row in bets:
                bet_id, game_id, bettor, prediction, odds, stake = row

                game_result = results.get(game_id)
                if game_result is None:
                    logger.warning(
                        "calculate_pnl: no result for game_id=%d, skipping bet_id=%d",
                        game_id,
                        bet_id,
                    )
                    continue

                outcome = game_result["outcome"]
                won = prediction == outcome
                pnl: float = float(stake) * (float(odds) - 1) if won else -float(stake)

                # 3. Update bet row
                cur.execute(
                    _UPDATE_BET_SQL,
                    {"result": outcome, "pnl": pnl, "bet_id": bet_id},
                )

                # Accumulate for bankroll update
                bettor_pnl[bettor] += pnl
                bettor_played[bettor] += 1
                if won:
                    bettor_won[bettor] += 1
                else:
                    bettor_lost[bettor] += 1

                game_bettor_pnl[(game_id, bettor)] = pnl
                logger.info(
                    "calculate_pnl: bet_id=%d game_id=%d bettor=%s prediction=%s "
                    "outcome=%s pnl=%.2f",
                    bet_id, game_id, bettor, prediction, outcome, pnl,
                )

            # 4. Update bankroll for each bettor
            for bettor in bettor_pnl:
                cur.execute(
                    _UPDATE_BANKROLL_SQL,
                    {
                        "total_pnl": bettor_pnl[bettor],
                        "games_played": bettor_played[bettor],
                        "games_won": bettor_won[bettor],
                        "games_lost": bettor_lost[bettor],
                        "bettor": bettor,
                    },
                )
                logger.info(
                    "calculate_pnl: bankroll updated bettor=%s pnl=%.2f "
                    "won=%d lost=%d",
                    bettor,
                    bettor_pnl[bettor],
                    bettor_won[bettor],
                    bettor_lost[bettor],
                )
        conn.commit()  # MANDATORY: bets result/pnl + bankroll totals in one atomic commit

    # Build pnl_summary keyed by game_id
    pnl_summary: dict[int, dict] = {}
    for game_id in game_ids:
        pnl_summary[game_id] = {
            "user_pnl": game_bettor_pnl.get((game_id, "user"), 0.0),
            "ai_pnl": game_bettor_pnl.get((game_id, "ai"), 0.0),
        }

    logger.info("calculate_pnl: completed for %d game(s)", len(game_ids))
    return {"pnl_summary": pnl_summary}
