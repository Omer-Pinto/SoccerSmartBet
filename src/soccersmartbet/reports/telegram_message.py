from __future__ import annotations

import os
from typing import Any

import psycopg2

DATABASE_URL = os.getenv("DATABASE_URL")

_FETCH_GAME_SQL = """
SELECT game_id, match_date, kickoff_time, home_team, away_team, league, venue
FROM games WHERE game_id = %(game_id)s
"""


def format_gambling_time_message(game_ids: list[int], base_url: str) -> str:
    """Generate the 'gambling time' Telegram message with game bullets and report links."""
    if not game_ids:
        return "No games today."

    lines: list[str] = ["Gambling Time!", ""]

    conn = psycopg2.connect(DATABASE_URL)
    try:
        with conn:
            with conn.cursor() as cur:
                for game_id in game_ids:
                    cur.execute(_FETCH_GAME_SQL, {"game_id": game_id})
                    row = cur.fetchone()
                    if row is None:
                        continue

                    _gid, match_date, kickoff_time, home_team, away_team, league, venue = row

                    date_str = str(match_date) if match_date else "TBD"
                    time_str = str(kickoff_time) if kickoff_time else "TBD"
                    venue_str = venue or "TBD"
                    league_str = league or "Unknown League"

                    lines.append(
                        f"- {home_team} vs {away_team} - {date_str} {time_str} ISR"
                        f" - {venue_str} - {league_str}"
                    )
                    lines.append(f"  Report: {base_url}/reports/{game_id}")
                    lines.append("")
    finally:
        conn.close()

    return "\n".join(lines).rstrip()
