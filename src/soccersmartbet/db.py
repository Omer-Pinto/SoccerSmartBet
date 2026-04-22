"""Database connection pool for SoccerSmartBet.

Module-level psycopg_pool.ConnectionPool (min=1, max=10). All Wave 10+
modules must import get_conn() / get_cursor() from here instead of calling
psycopg.connect() directly.

NOTE: The 14 direct-connect call-sites in gambling_flow/, pre_gambling_flow/,
post_games_flow/, team_registry.py, and reports/ are intentionally excluded
from this pool (fan-out isolation; see ai-engineer decision).
This pool is for Wave 10 dashboard / webapp code only.
"""
from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Generator

import psycopg
from psycopg_pool import ConnectionPool

DATABASE_URL: str | None = os.getenv("DATABASE_URL")

_pool: ConnectionPool | None = None


def _get_pool() -> ConnectionPool:
    """Return the module-level connection pool, creating it on first call."""
    global _pool
    if _pool is None:
        _pool = ConnectionPool(
            conninfo=DATABASE_URL,
            min_size=1,
            max_size=10,
            open=True,
        )
    return _pool


@contextmanager
def get_conn() -> Generator[psycopg.Connection, None, None]:
    """Yield a connection from the pool, returning it on exit.

    psycopg3: pool.connection() is a context manager that checks the
    connection back in automatically.  The caller is responsible for
    committing or rolling back.

    Yields:
        An open psycopg3 Connection.
    """
    pool = _get_pool()
    with pool.connection() as conn:
        yield conn


@contextmanager
def get_cursor(
    commit: bool = True,
) -> Generator[psycopg.Cursor, None, None]:
    """Yield a cursor, committing on clean exit or rolling back on exception.

    Args:
        commit: If True (default), commit the transaction on clean exit.

    Yields:
        An open psycopg3 cursor.
    """
    with get_conn() as conn:
        with conn.cursor() as cur:
            try:
                yield cur
                if commit:
                    conn.commit()
            except Exception:
                conn.rollback()
                raise
