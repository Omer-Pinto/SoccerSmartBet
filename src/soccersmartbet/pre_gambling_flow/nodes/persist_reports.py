"""Persist Reports node for the Pre-Gambling Flow.

Updates the status of all analyzed games to ``ready_for_betting`` after
intelligence reports have been combined by the combine_reports node.
"""

from __future__ import annotations

import os

import psycopg2

from soccersmartbet.pre_gambling_flow.state import PreGamblingState

DATABASE_URL = os.getenv("DATABASE_URL")

_UPDATE_SQL = """
UPDATE games
SET status = 'ready_for_betting'
WHERE game_id = ANY(%(game_ids)s)
"""


def persist_reports(state: PreGamblingState) -> dict:
    """LangGraph node: mark analyzed games as ready for betting.

    Reads ``state["games_to_analyze"]`` and issues a single UPDATE against the
    ``games`` table, setting ``status = 'ready_for_betting'`` for every game in
    the list.  This is a DB side-effect only — combine_reports has already
    advanced the phase to ``Phase.COMPLETE``.

    Args:
        state: Current Pre-Gambling Flow state.  Must contain
            ``games_to_analyze``.

    Returns:
        Empty dict — no state changes required.
    """
    game_ids: list[int] = state["games_to_analyze"]

    if not game_ids:
        return {}

    conn = psycopg2.connect(DATABASE_URL)
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(_UPDATE_SQL, {"game_ids": game_ids})
    finally:
        conn.close()

    return {}
