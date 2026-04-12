from __future__ import annotations

import logging
import os
from datetime import date, datetime, time, timedelta

import psycopg2

from soccersmartbet.utils.timezone import ISR_TZ

logger = logging.getLogger(__name__)

DATABASE_URL: str | None = os.getenv("DATABASE_URL")


def get_daily_run(run_date: date) -> dict | None:
    """Read the daily_runs row for run_date.

    Returns the row as a dict, or None if no row exists for that date.
    """
    sql = """
        SELECT
            run_date,
            pre_gambling_started_at,
            pre_gambling_completed_at,
            gambling_completed_at,
            post_games_trigger_at,
            post_games_completed_at,
            game_ids,
            games_found,
            user_bet_completed,
            ai_bet_completed,
            no_games_user_confirmed
        FROM daily_runs
        WHERE run_date = %(run_date)s
    """
    conn = psycopg2.connect(DATABASE_URL)
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(sql, {"run_date": run_date})
                row = cur.fetchone()
    finally:
        conn.close()

    if row is None:
        return None

    return {
        "run_date": row[0],
        "pre_gambling_started_at": row[1],
        "pre_gambling_completed_at": row[2],
        "gambling_completed_at": row[3],
        "post_games_trigger_at": row[4],
        "post_games_completed_at": row[5],
        "game_ids": list(row[6]) if row[6] is not None else [],
        "games_found": row[7],
        "user_bet_completed": row[8],
        "ai_bet_completed": row[9],
        "no_games_user_confirmed": row[10],
    }


def upsert_daily_run(run_date: date, **fields: object) -> None:
    """Insert or update fields in daily_runs for run_date.

    Accepts keyword arguments matching daily_runs columns:
        pre_gambling_started_at, pre_gambling_completed_at,
        gambling_completed_at, post_games_completed_at,
        game_ids, user_bet_completed, ai_bet_completed.

    Unknown keys are silently ignored.
    """
    allowed = {
        "pre_gambling_started_at",
        "pre_gambling_completed_at",
        "gambling_completed_at",
        "post_games_trigger_at",
        "post_games_completed_at",
        "game_ids",
        "games_found",
        "user_bet_completed",
        "ai_bet_completed",
        "no_games_user_confirmed",
    }
    filtered = {k: v for k, v in fields.items() if k in allowed}
    if not filtered:
        return

    set_clauses = ", ".join(f"{col} = %({col})s" for col in filtered)
    col_list = ", ".join(filtered)
    val_placeholders = ", ".join(f"%({col})s" for col in filtered)

    sql = f"""
        INSERT INTO daily_runs (run_date, {col_list})
        VALUES (%(run_date)s, {val_placeholders})
        ON CONFLICT (run_date) DO UPDATE SET {set_clauses}
    """
    params = {"run_date": run_date, **filtered}

    conn = psycopg2.connect(DATABASE_URL)
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(sql, params)
    finally:
        conn.close()

    logger.debug("upsert_daily_run: %s → %s", run_date, list(filtered))


def get_pending_post_games() -> dict | None:
    """Find a daily_runs row with a pending post-games trigger.

    Returns the most recent row where post_games_trigger_at is set but
    post_games_completed_at is NULL. Handles midnight-crossing triggers
    (e.g. trigger at 01:00 on Apr 13 stored on the Apr 12 row).
    """
    sql = """
        SELECT
            run_date, post_games_trigger_at, game_ids
        FROM daily_runs
        WHERE post_games_trigger_at IS NOT NULL
          AND post_games_completed_at IS NULL
        ORDER BY run_date DESC
        LIMIT 1
    """
    conn = psycopg2.connect(DATABASE_URL)
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(sql)
                row = cur.fetchone()
    finally:
        conn.close()

    if row is None:
        return None

    return {
        "run_date": row[0],
        "post_games_trigger_at": row[1],
        "game_ids": list(row[2]) if row[2] is not None else [],
    }


def get_max_kickoff_for_games(game_ids: list[int]) -> datetime | None:
    """Return the latest kickoff as a timezone-aware ISR datetime, or None.

    Combines match_date + kickoff_time from the games table into a
    timezone-aware datetime in ISR_TZ so the caller can compare it
    directly against now_isr().
    """
    if not game_ids:
        return None

    sql = """
        SELECT match_date, kickoff_time
        FROM games
        WHERE game_id = ANY(%(game_ids)s)
        ORDER BY match_date DESC, kickoff_time DESC
        LIMIT 1
    """
    conn = psycopg2.connect(DATABASE_URL)
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(sql, {"game_ids": game_ids})
                row = cur.fetchone()
    finally:
        conn.close()

    if row is None:
        return None

    match_date: date = row[0]
    kickoff: time = row[1]
    return datetime(
        match_date.year,
        match_date.month,
        match_date.day,
        kickoff.hour,
        kickoff.minute,
        tzinfo=ISR_TZ,
    )
