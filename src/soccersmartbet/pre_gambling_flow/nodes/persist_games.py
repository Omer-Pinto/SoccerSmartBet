"""Persist Games node for the Pre-Gambling Flow.

Inserts the games selected by smart_game_picker into the PostgreSQL ``games``
table and returns the DB-assigned game IDs so downstream nodes can reference
them by real primary keys.
"""

from __future__ import annotations

import os
from typing import Any

import psycopg2

from soccersmartbet.pre_gambling_flow.state import GameContext, Phase, PreGamblingState

DATABASE_URL = os.getenv("DATABASE_URL")

_INSERT_SQL = """
INSERT INTO games (
    match_date,
    kickoff_time,
    home_team,
    away_team,
    league,
    venue,
    n1,
    n2,
    n3,
    status
)
VALUES (
    %(match_date)s,
    %(kickoff_time)s,
    %(home_team)s,
    %(away_team)s,
    %(league)s,
    %(venue)s,
    %(n1)s,
    %(n2)s,
    %(n3)s,
    'selected'
)
RETURNING game_id
"""


def persist_games(state: PreGamblingState) -> dict[str, Any]:
    """LangGraph node: insert selected games into the DB and return real game IDs.

    Reads ``state["all_games"]`` (populated by smart_game_picker with
    ``game_id=0`` placeholders), inserts each row into the ``games`` table
    inside a single transaction, and returns the DB-assigned primary keys as
    ``games_to_analyze``.

    Args:
        state: Current Pre-Gambling Flow state.  Must contain ``all_games``.

    Returns:
        State update dict with ``games_to_analyze`` (list of real DB PKs) and
        ``phase`` set to ``Phase.ANALYZING``.
    """
    games: list[GameContext] = state["all_games"]

    if not games:
        return {
            "games_to_analyze": [],
            "phase": Phase.ANALYZING,
        }

    game_ids: list[int] = []

    conn = psycopg2.connect(DATABASE_URL)
    try:
        with conn:
            with conn.cursor() as cur:
                for game in games:
                    cur.execute(
                        _INSERT_SQL,
                        {
                            "match_date": game["match_date"],
                            "kickoff_time": game["kickoff_time"],
                            "home_team": game["home_team"],
                            "away_team": game["away_team"],
                            "league": game["league"],
                            "venue": game["venue"],
                            "n1": game["n1"],
                            "n2": game["n2"],
                            "n3": game["n3"],
                        },
                    )
                    row = cur.fetchone()
                    game_ids.append(row[0])
    finally:
        conn.close()

    return {
        "games_to_analyze": game_ids,
        "phase": Phase.ANALYZING,
    }
