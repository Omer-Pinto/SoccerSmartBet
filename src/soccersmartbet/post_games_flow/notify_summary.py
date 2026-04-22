"""
Notify Daily Summary node for the Post-Games Flow.

Sends a Telegram HTML message with per-game results, bet outcomes,
and final bankroll balances for both user and AI.
"""

from __future__ import annotations

import asyncio
import logging
import os

import psycopg2

from soccersmartbet.post_games_flow.state import PostGamesState
from soccersmartbet.telegram.bot import send_message

logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL")

_FETCH_GAMES_SQL = """
SELECT game_id, home_team, away_team, home_score, away_score, outcome
FROM games
WHERE game_id = ANY(%(game_ids)s)
ORDER BY kickoff_time
"""

_FETCH_BETS_SQL = """
SELECT game_id, bettor, prediction, odds, stake, pnl
FROM bets
WHERE game_id = ANY(%(game_ids)s)
"""

_FETCH_BANKROLL_SQL = """
SELECT bettor, total_bankroll, games_won, games_lost
FROM bankroll
WHERE bettor IN ('user', 'ai')
"""

_PREDICTION_ICONS = {
    "1": "1\ufe0f\u20e3",
    "x": "\U0001D54F",
    "2": "2\ufe0f\u20e3",
}

_OUTCOME_LABELS = {
    "1": "1\ufe0f\u20e3 Home win",
    "x": "\U0001D54F Draw",
    "2": "2\ufe0f\u20e3 Away win",
}


def _pnl_str(pnl: float) -> str:
    """Format P&L with sign and suffix."""
    sign = "+" if pnl >= 0 else ""
    return f"{sign}{pnl:.0f} NIS"


def notify_daily_summary(state: PostGamesState) -> dict:
    """LangGraph node: send daily results summary via Telegram.

    Builds an HTML message showing each game's score, both bets, and the
    final bankroll state for user and AI.

    Args:
        state: Fully populated PostGamesState after fetch_results and
            calculate_pnl have run.

    Returns:
        Empty dict (terminal node).
    """
    game_ids: list[int] = state["game_ids"]
    pnl_summary: dict = state.get("pnl_summary", {})

    conn = psycopg2.connect(DATABASE_URL)
    try:
        with conn:
            with conn.cursor() as cur:
                # Game metadata + results
                cur.execute(_FETCH_GAMES_SQL, {"game_ids": game_ids})
                games = {
                    row[0]: {
                        "home_team": row[1],
                        "away_team": row[2],
                        "home_score": row[3],
                        "away_score": row[4],
                        "outcome": row[5],
                    }
                    for row in cur.fetchall()
                }

                # Bets indexed by (game_id, bettor)
                cur.execute(_FETCH_BETS_SQL, {"game_ids": game_ids})
                bets: dict[tuple, dict] = {}
                for row in cur.fetchall():
                    bets[(row[0], row[1])] = {
                        "prediction": row[2],
                        "odds": float(row[3]),
                        "stake": float(row[4]),
                        "pnl": float(row[5]) if row[5] is not None else 0.0,
                    }

                # Bankroll totals
                cur.execute(_FETCH_BANKROLL_SQL)
                bankroll: dict[str, dict] = {
                    row[0]: {
                        "total": float(row[1]),
                        "won": row[2],
                        "lost": row[3],
                    }
                    for row in cur.fetchall()
                }
    finally:
        conn.close()

    lines: list[str] = ["\U0001f4ca <b>Daily Results</b>", ""]

    for game_id in game_ids:
        game = games.get(game_id)
        if game is None:
            continue

        home = game["home_team"]
        away = game["away_team"]
        hs = game["home_score"] if game["home_score"] is not None else "?"
        as_ = game["away_score"] if game["away_score"] is not None else "?"
        outcome = game.get("outcome", "")
        outcome_label = _OUTCOME_LABELS.get(outcome, outcome)

        lines.append(f"\u26bd <b>{home}</b> {hs} - {as_} <b>{away}</b> ({outcome_label})")

        for bettor, label in (("user", "You"), ("ai", "AI")):
            bet = bets.get((game_id, bettor))
            if bet is None:
                continue
            pred_icon = _PREDICTION_ICONS.get(bet["prediction"], bet["prediction"])
            pnl = bet["pnl"]
            won = pnl > 0
            status_icon = "\u2705" if won else "\u274c"
            pnl_formatted = _pnl_str(pnl)

            if bet["prediction"] == "1":
                team_label = home
            elif bet["prediction"] == "2":
                team_label = away
            else:
                team_label = "Draw"

            lines.append(
                f"  <b>{label}</b>: {team_label} {pred_icon} @ {bet['odds']:.2f}"
                f" \u2014 {status_icon} {pnl_formatted}"
            )

        lines.append("")

    lines.append("\u2501" * 16)
    lines.append("\U0001f4b0 <b>Bankroll</b>")

    for bettor, label in (("user", "You"), ("ai", "AI")):
        br = bankroll.get(bettor)
        if br is None:
            continue
        total_fmt = f"{br['total']:,.0f}"
        lines.append(f"  {label}: {total_fmt} NIS ({br['won']}W / {br['lost']}L)")

    skipped_games: list = state.get("skipped_games", [])
    if skipped_games:
        lines.append("")
        lines.append("━" * 16)
        lines.append("⚠️ <b>Missing Results</b>")
        lines.append(f"<i>{len(skipped_games)} game(s) could not be resolved — no PnL recorded.</i>")
        for skip in skipped_games:
            lines.append(
                f"  • <b>{skip['home_team']} vs {skip['away_team']}</b>"
                f" ({skip['match_date']}) — {skip['reason']}"
            )

    text = "\n".join(lines)

    asyncio.run(send_message(text, parse_mode="HTML"))
    logger.info(
        "notify_daily_summary: sent summary for %d game(s), %d skipped",
        len(game_ids), len(skipped_games),
    )
    return {}
