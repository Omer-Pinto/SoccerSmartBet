"""Audit write helpers for SoccerSmartBet dashboard.

Provides EventType constants and functions to write audit rows to
run_events and bet_edits tables. All timestamps default to DB-side
CURRENT_TIMESTAMP (TIMESTAMPTZ, Asia/Jerusalem).
"""
from __future__ import annotations

from datetime import date

from psycopg.types.json import Jsonb

from soccersmartbet.db import get_cursor


class EventType:
    """Vocabulary of valid run_events.event_type values.

    No SQL CHECK constraint (per Q4 design decision).
    """

    PRE_GAMBLING_STARTED: str = "pre_gambling_started"
    PRE_GAMBLING_COMPLETED: str = "pre_gambling_completed"
    PRE_GAMBLING_FAILED: str = "pre_gambling_failed"
    PRE_GAMBLING_FORCE_RESET: str = "pre_gambling_force_reset"
    POST_GAMES_STARTED: str = "post_games_started"
    POST_GAMES_COMPLETED: str = "post_games_completed"
    POST_GAMES_FAILED: str = "post_games_failed"


def write_run_event(
    run_date: date,
    event_type: str,
    triggered_by: str,
    payload: dict | None = None,
) -> int:
    """Insert one row into run_events.

    Args:
        run_date: The date this event belongs to.
        event_type: One of the EventType constants.
        triggered_by: One of 'scheduler', 'manual', 'recovery'.
        payload: Optional JSONB payload dict. Serialised via psycopg3 Jsonb adapter.

    Returns:
        The new event_id (SERIAL).
    """
    sql = """
        INSERT INTO run_events (run_date, event_type, triggered_by, payload)
        VALUES (%(run_date)s, %(event_type)s, %(triggered_by)s, %(payload)s)
        RETURNING event_id
    """
    params: dict = {
        "run_date": run_date,
        "event_type": event_type,
        "triggered_by": triggered_by,
        "payload": Jsonb(payload) if payload is not None else None,
    }
    with get_cursor(commit=True) as cur:
        cur.execute(sql, params)
        row = cur.fetchone()
    return row[0]  # type: ignore[index]


def write_bet_edit(
    bet_id: int,
    field: str,
    old_value: object,
    new_value: object,
    source: str = "dashboard",
) -> int:
    """Insert one row into bet_edits.

    Args:
        bet_id: FK to bets.bet_id.
        field: Column name that was changed (e.g. 'prediction', 'stake').
        old_value: Previous value — stored as TEXT.
        new_value: New value — stored as TEXT.
        source: Origin of the edit; defaults to 'dashboard'.

    Returns:
        The new edit_id (SERIAL).
    """
    sql = """
        INSERT INTO bet_edits (bet_id, field, old_value, new_value, source)
        VALUES (%(bet_id)s, %(field)s, %(old_value)s, %(new_value)s, %(source)s)
        RETURNING edit_id
    """
    params: dict = {
        "bet_id": bet_id,
        "field": field,
        "old_value": str(old_value) if old_value is not None else None,
        "new_value": str(new_value) if new_value is not None else None,
        "source": source,
    }
    with get_cursor(commit=True) as cur:
        cur.execute(sql, params)
        row = cur.fetchone()
    return row[0]  # type: ignore[index]
