"""Database connection pool for SoccerSmartBet.

Module-level psycopg_pool.ConnectionPool (min=1, max=75 — 75% of Postgres
default max_connections=100). All modules must import get_conn() /
get_cursor() from here instead of calling psycopg.connect() directly.
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
        pool_max = int(os.getenv("DATABASE_POOL_MAX", "75"))
        _pool = ConnectionPool(
            conninfo=DATABASE_URL,
            min_size=1,
            max_size=pool_max,
            open=True,
        )
    return _pool


def close_pool() -> None:
    """Close the module-level pool. Call from start_scheduler shutdown so
    psycopg3's pool worker threads stop and the process can exit cleanly.
    """
    global _pool
    if _pool is not None:
        _pool.close()
        _pool = None


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
