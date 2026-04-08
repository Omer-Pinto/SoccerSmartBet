from __future__ import annotations

import logging
import os

import psycopg2

DATABASE_URL = os.getenv("DATABASE_URL")

logger = logging.getLogger(__name__)

_FETCH_GAME_SQL = """
SELECT game_id, match_date, kickoff_time, home_team, away_team, league, venue
FROM games WHERE game_id = %(game_id)s
"""


def get_games_info(game_ids: list[int]) -> list[dict]:
    """Return metadata for each game ID from the database.

    Args:
        game_ids: Ordered list of game IDs to fetch.

    Returns:
        List of dicts with keys: game_id, home_team, away_team, match_date,
        kickoff_time, league, venue.  Games not found in the DB are skipped.
    """
    if not game_ids:
        return []

    games: list[dict] = []
    conn = psycopg2.connect(DATABASE_URL)
    try:
        with conn:
            with conn.cursor() as cur:
                for game_id in game_ids:
                    cur.execute(_FETCH_GAME_SQL, {"game_id": game_id})
                    row = cur.fetchone()
                    if row is None:
                        logger.warning("game_id=%s not found in DB, skipping", game_id)
                        continue
                    gid, match_date, kickoff_time, home_team, away_team, league, venue = row
                    games.append(
                        {
                            "game_id": gid,
                            "home_team": home_team,
                            "away_team": away_team,
                            "match_date": str(match_date) if match_date else "TBD",
                            "kickoff_time": str(kickoff_time) if kickoff_time else "TBD",
                            "league": league or "Unknown League",
                            "venue": venue or "TBD",
                        }
                    )
    finally:
        conn.close()

    return games


def format_gambling_time_message(game_ids: list[int]) -> str:
    """Generate the 'Gambling Time!' Telegram message with game bullets.

    Args:
        game_ids: List of game IDs to include in the message.

    Returns:
        Formatted multi-line string ready to send as a Telegram message.
    """
    if not game_ids:
        return "No games today."

    games = get_games_info(game_ids)
    if not games:
        return "No games today."

    lines: list[str] = ["Gambling Time!", ""]

    for game in games:
        lines.append(
            f"\u2022 {game['home_team']} vs {game['away_team']}"
            f" \u2014 {game['kickoff_time']} ISR"
            f" \u2014 {game['venue']}"
            f" \u2014 {game['league']}"
        )

    return "\n".join(lines)
