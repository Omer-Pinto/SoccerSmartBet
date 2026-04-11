"""
Notify Result node for the Gambling Flow.

Sends a Telegram message summarising the placed bets (user vs AI side by
side) or the rejection reason.
"""

from __future__ import annotations

import asyncio
import logging
import os

import psycopg2

from soccersmartbet.gambling_flow.state import GamblingState
from soccersmartbet.telegram.bot import send_message

logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL")

_FETCH_GAME_NAMES_SQL = """
SELECT game_id, home_team, away_team
FROM games
WHERE game_id = ANY(%(game_ids)s)
"""

_PREDICTION_LABELS = {
    "1": "Home",
    "x": "Draw",
    "2": "Away",
}


def _team_for_prediction(prediction: str, home_team: str, away_team: str) -> str:
    """Return a human-readable label for a prediction."""
    if prediction == "1":
        return home_team
    if prediction == "2":
        return away_team
    return "Draw"


def _format_bet_line(
    label: str,
    prediction: str,
    odds: float,
    stake: float,
    home_team: str,
    away_team: str,
) -> str:
    """Format a single bet line for the Telegram message."""
    team_label = _team_for_prediction(prediction, home_team, away_team)
    returns = odds * stake
    profit = returns - stake
    return (
        f"  {label}: {team_label} ({prediction}) @ {odds:.2f} "
        f"-- {stake:.0f} NIS -> returns {returns:.0f} (profit {profit:.0f})"
    )


def notify_gambling_result(state: GamblingState) -> dict:
    """LangGraph node: send gambling result summary via Telegram.

    If bets were accepted, shows user and AI bets side by side per game.
    If rejected, shows the rejection reason.

    Args:
        state: Current Gambling Flow state after verification.

    Returns:
        Empty dict (terminal node).
    """
    verification = state.get("verification_result", "")

    if verification == "rejected":
        reason = state.get("rejection_reason", "Unknown reason")
        text = f"Bets rejected!\n\nReason: {reason}"
        asyncio.run(send_message(text))
        logger.info("notify_gambling_result: sent rejection notification")
        return {}

    # Build game_id -> team names map
    game_ids: list[int] = state.get("game_ids", [])
    game_names: dict[int, tuple[str, str]] = {}

    conn = psycopg2.connect(DATABASE_URL)
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(_FETCH_GAME_NAMES_SQL, {"game_ids": game_ids})
                for row in cur.fetchall():
                    game_names[row[0]] = (row[1], row[2])
    finally:
        conn.close()

    # Index bets by game_id
    user_bets_map: dict[int, dict] = {}
    for bet in state.get("user_bets", []):
        user_bets_map[bet["game_id"]] = bet

    ai_bets_map: dict[int, dict] = {}
    for bet in state.get("ai_bets", []):
        ai_bets_map[bet["game_id"]] = bet

    # Build message
    lines: list[str] = ["\u2705 All bets placed!", ""]

    for game_id in game_ids:
        home_team, away_team = game_names.get(game_id, ("Unknown", "Unknown"))
        lines.append(f"\u26bd {home_team} vs {away_team}")

        user_bet = user_bets_map.get(game_id)
        ai_bet = ai_bets_map.get(game_id)

        if user_bet and ai_bet and user_bet["prediction"] == ai_bet["prediction"]:
            pick = _team_for_prediction(user_bet["prediction"], home_team, away_team)
            lines.append(
                f"  Both picked {pick} ({user_bet['prediction']}) @ {user_bet['odds']:.2f}"
                f" \u2014 You: {user_bet['stake']:.0f} NIS / AI: {ai_bet['stake']:.0f} NIS"
            )
        else:
            if user_bet:
                lines.append(_format_bet_line(
                    "You", user_bet["prediction"], user_bet["odds"],
                    user_bet["stake"], home_team, away_team,
                ))
            if ai_bet:
                lines.append(_format_bet_line(
                    "AI", ai_bet["prediction"], ai_bet["odds"],
                    ai_bet["stake"], home_team, away_team,
                ))

        lines.append("")

    text = "\n".join(lines).rstrip()

    asyncio.run(send_message(text))
    logger.info("notify_gambling_result: sent summary for %d game(s)", len(game_ids))
    return {}
