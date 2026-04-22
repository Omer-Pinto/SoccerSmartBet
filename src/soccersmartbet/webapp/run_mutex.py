"""Flow mutex for SoccerSmartBet scheduler flows.

Uses daily_runs.status + SELECT ... FOR UPDATE NOWAIT as the concurrency
primitive — no asyncio.Lock, no in-memory flags.  DB is the sole system
of record for flow state.
"""
from __future__ import annotations

import logging
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import date
from typing import Generator

import psycopg
import psycopg.errors

from soccersmartbet.db import get_conn

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class FlowConflict(Exception):
    """Raised when the target transition is blocked by the current status."""

    def __init__(self, current_status: str) -> None:
        self.current_status = current_status
        super().__init__(f"Flow conflict: current status is '{current_status}'")

    def __str__(self) -> str:
        return self.current_status


class InvalidTransition(Exception):
    """Raised when the requested status transition is not in the allowed table."""


# ---------------------------------------------------------------------------
# Transition table
# ---------------------------------------------------------------------------

# Maps (from_status, to_status) → allowed.
# Wave 10 exercises pre_gambling_* and post_games_* paths.
# gambling_* rows are reserved for Wave 11A — kept here for completeness.
_RUNNING_STATUSES: tuple[str, ...] = (
    "pre_gambling_running",
    "gambling_running",
    "post_games_running",
)

_TRANSITIONS: frozenset[tuple[str, str]] = frozenset(
    [
        ("idle", "pre_gambling_running"),
        # Note: pre_gambling_done → pre_gambling_running is intentionally absent; regenerating after
        # a successful run must go through Force Override (which resets status first via _force_clear).
        ("pre_gambling_done", "gambling_running"),       # Wave 11 hook
        ("pre_gambling_done", "post_games_running"),     # B3: direct pre→post path (no gambling phase)
        ("gambling_done", "post_games_running"),
        ("post_games_done", "idle"),                     # close-of-day reset
        ("failed", "pre_gambling_running"),              # next-day retry / same-day re-fire
        ("failed", "gambling_running"),                  # B2: Wave 11 re-fire from failed state
        ("failed", "post_games_running"),                # post-games-only re-fire
        ("pre_gambling_running", "pre_gambling_done"),   # success terminal
        ("pre_gambling_running", "failed"),              # crash terminal
        ("gambling_running", "gambling_done"),
        ("gambling_running", "failed"),
        ("post_games_running", "post_games_done"),
        ("post_games_running", "failed"),
    ]
)


def _validate_transition(current: str, target: str) -> None:
    if (current, target) not in _TRANSITIONS:
        raise InvalidTransition(
            f"Transition '{current}' → '{target}' is not allowed"
        )


# ---------------------------------------------------------------------------
# RunContext
# ---------------------------------------------------------------------------


@dataclass
class RunContext:
    """Carries flow metadata yielded by acquire_flow()."""

    run_date: date
    previous_status: str
    target_status: str
    attempt_count: int


# ---------------------------------------------------------------------------
# acquire_flow — short transaction mutex
# ---------------------------------------------------------------------------


@contextmanager
def acquire_flow(
    run_date: date,
    target_status: str,
    triggered_by: str = "scheduler",
    force: bool = False,
) -> Generator[RunContext, None, None]:
    """Acquire the flow mutex for run_date.

    Opens a SHORT transaction:
      1. INSERT INTO daily_runs (run_date, status) VALUES (%s, 'idle')
         ON CONFLICT DO NOTHING
      2. SELECT status FROM daily_runs WHERE run_date = %s FOR UPDATE NOWAIT
      3. Validate current_status → target_status transition (skipped when force=True)
      4. UPDATE daily_runs SET status = target_status,
                               last_trigger_source = triggered_by,
                               attempt_count = attempt_count + 1,
                               last_error = NULL
         WHERE run_date = %s
      5. COMMIT

    The commit happens BEFORE yielding — the caller's long-running flow does
    not hold a row lock.  The mutex is the status column value, not the SQL
    lock.

    Args:
        run_date: Date for which the flow is being acquired.
        target_status: The status to transition into.
        triggered_by: One of 'scheduler', 'manual', 'recovery'.
        force: When True, skip _validate_transition entirely and set
            target_status regardless of current state.  Used by Force Override
            and Regenerate Report so operators can re-fire after pre_gambling_done
            without manually touching DB rows.

    Yields:
        RunContext with run_date, previous_status, target_status, attempt_count.

    Raises:
        FlowConflict: If the row is locked by another session (NOWAIT) or the
            current status is a running status (concurrent flow guard).
        InvalidTransition: If (current, target) is not in the transition table
            and force=False.
    """
    with get_conn() as conn:
        try:
            with conn.cursor() as cur:
                # Step 1 — ensure row exists
                cur.execute(
                    """
                    INSERT INTO daily_runs (run_date, status)
                    VALUES (%s, 'idle')
                    ON CONFLICT (run_date) DO NOTHING
                    """,
                    (run_date,),
                )

                # Step 2 — lock and read current status
                try:
                    cur.execute(
                        """
                        SELECT status, attempt_count
                        FROM daily_runs
                        WHERE run_date = %s
                        FOR UPDATE NOWAIT
                        """,
                        (run_date,),
                    )
                except psycopg.errors.LockNotAvailable:
                    conn.rollback()
                    raise FlowConflict("locked")

                row = cur.fetchone()
                if row is None:
                    conn.rollback()
                    raise RuntimeError(
                        f"daily_runs row for {run_date} disappeared after upsert — DB integrity violation"
                    )
                current_status: str = row[0]
                current_attempt: int = row[1]

                # Concurrency-collision detection — another fire is already in flight.
                # Translate to FlowConflict so callers handle this as "skip, already running"
                # rather than a programming error in the state machine.
                if current_status in _RUNNING_STATUSES:
                    conn.rollback()
                    raise FlowConflict(current_status)

                # Step 3 — validate transition (skipped when force=True)
                if not force:
                    _validate_transition(current_status, target_status)

                # Step 4 — write new status
                new_attempt = current_attempt + 1
                cur.execute(
                    """
                    UPDATE daily_runs
                    SET status = %s,
                        last_trigger_source = %s,
                        attempt_count = %s,
                        last_error = NULL
                    WHERE run_date = %s
                    """,
                    (target_status, triggered_by, new_attempt, run_date),
                )

            # Step 5 — COMMIT before yielding (release row lock)
            conn.commit()

        except (FlowConflict, InvalidTransition):
            # Already rolled back or never committed — re-raise clean
            raise
        except Exception:
            conn.rollback()
            raise

    ctx = RunContext(
        run_date=run_date,
        previous_status=current_status,
        target_status=target_status,
        attempt_count=new_attempt,
    )
    yield ctx


# ---------------------------------------------------------------------------
# release_flow — success terminal transition
# ---------------------------------------------------------------------------


def release_flow(run_date: date, target_status: str) -> None:
    """Transition the flow to a terminal success status.

    Validates the transition via the same table as acquire_flow.  Typically
    called after the long-running flow completes successfully.

    Args:
        run_date: Date of the flow.
        target_status: The success terminal status (e.g. 'pre_gambling_done').

    Raises:
        InvalidTransition: If the current → target transition is not allowed.
    """
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT status FROM daily_runs WHERE run_date = %s FOR UPDATE NOWAIT",
                (run_date,),
            )
            row = cur.fetchone()
            if row is None:
                conn.rollback()
                raise InvalidTransition(
                    f"No daily_runs row for {run_date} — cannot release flow"
                )
            current_status: str = row[0]
            _validate_transition(current_status, target_status)
            cur.execute(
                "UPDATE daily_runs SET status = %s WHERE run_date = %s",
                (target_status, run_date),
            )
        conn.commit()

    logger.debug(
        "release_flow: %s %s → %s", run_date, current_status, target_status
    )


# ---------------------------------------------------------------------------
# mark_failed — crash handler
# ---------------------------------------------------------------------------


def mark_failed(run_date: date, error: Exception) -> None:
    """Transition the current running status to 'failed' and record last_error.

    Idempotent: if the row is already 'failed', this is a no-op.

    Args:
        run_date: Date of the flow.
        error: The exception that caused the failure.
    """
    error_message = str(error)[:2000]

    with get_conn() as conn:
        with conn.cursor() as cur:
            try:
                cur.execute(
                    "SELECT status FROM daily_runs WHERE run_date = %s FOR UPDATE NOWAIT",
                    (run_date,),
                )
            except psycopg.errors.LockNotAvailable:
                conn.rollback()
                logger.warning(
                    "mark_failed: row for %s briefly locked by another session — skipping mark; original error: %s",
                    run_date, error_message[:200],
                )
                return
            row = cur.fetchone()
            if row is None:
                conn.rollback()
                logger.warning(
                    "mark_failed: no daily_runs row for %s — cannot mark failed",
                    run_date,
                )
                return

            current_status: str = row[0]

            if current_status == "failed":
                # Already failed — idempotent no-op
                conn.rollback()
                return

            try:
                _validate_transition(current_status, "failed")
            except InvalidTransition:
                conn.rollback()
                logger.warning(
                    "mark_failed: transition '%s' → 'failed' not allowed for %s; skipping",
                    current_status,
                    run_date,
                )
                return

            cur.execute(
                """
                UPDATE daily_runs
                SET status = 'failed', last_error = %s
                WHERE run_date = %s
                """,
                (error_message, run_date),
            )
        conn.commit()

    logger.warning(
        "mark_failed: %s transitioned from '%s' to 'failed' — %s",
        run_date,
        current_status,
        error_message[:120],
    )
