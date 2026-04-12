from __future__ import annotations

import logging
import os

import psycopg2

DATABASE_URL = os.getenv("DATABASE_URL")

logger = logging.getLogger(__name__)

_FETCH_GAME_SQL = """
SELECT g.game_id, g.match_date, g.kickoff_time, g.home_team, g.away_team, g.league,
       COALESCE(NULLIF(g.venue, ''), gr.venue) AS venue
FROM games g
LEFT JOIN game_reports gr ON gr.game_id = g.game_id
WHERE g.game_id = %(game_id)s
"""


def _extract_venue_name(venue_text: str) -> str:
    """Extract just the stadium name from a potentially long AI venue analysis."""
    if not venue_text:
        return ""
    for sep in (" is a ", " is an ", " \u2014 a ", " - a ", ", a "):
        idx = venue_text.lower().find(sep)
        if idx != -1:
            return venue_text[:idx].strip()
    return venue_text[:60].rstrip(". ,") if len(venue_text) > 60 else venue_text


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
                            "kickoff_time": kickoff_time.strftime("%H:%M") if kickoff_time else "TBD",
                            "league": league or "Unknown League",
                            "venue": _extract_venue_name(venue or ""),
                        }
                    )
    finally:
        conn.close()

    return games


def format_gambling_time_message(game_ids: list[int]) -> str:
    """Generate the 'Gambling Time!' Telegram message with HTML formatting.

    Args:
        game_ids: List of game IDs to include in the message.

    Returns:
        HTML-formatted multi-line string ready to send with parse_mode="HTML".
    """
    if not game_ids:
        return "No games today."

    games = get_games_info(game_ids)
    if not games:
        return "No games today."

    lines: list[str] = ["\U0001f3c6 <b>Gambling Time!</b>", ""]

    for game in games:
        lines.append(
            f"\u26bd <b>{game['home_team']}</b> vs <b>{game['away_team']}</b>"
            f" \u2014 {game['kickoff_time']} ISR"
            f" \u2014 <i>{game['league']}</i>"
        )

    return "\n".join(lines)
