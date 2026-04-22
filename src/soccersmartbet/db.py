"""Database connection pool for SoccerSmartBet.

Module-level ThreadedConnectionPool (size 5). All new modules must import
get_conn() / get_cursor() from here instead of calling psycopg2.connect()
directly.
"""
from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Generator

import psycopg2
import psycopg2.pool

DATABASE_URL: str | None = os.getenv("DATABASE_URL")

_pool: psycopg2.pool.ThreadedConnectionPool | None = None


def _get_pool() -> psycopg2.pool.ThreadedConnectionPool:
    """Return the module-level connection pool, creating it on first call."""
    global _pool
    if _pool is None:
        _pool = psycopg2.pool.ThreadedConnectionPool(
            minconn=1,
            maxconn=5,
            dsn=DATABASE_URL,
        )
    return _pool


@contextmanager
def get_conn() -> Generator[psycopg2.extensions.connection, None, None]:
    """Yield a connection from the pool, returning it in a finally block.

    Thread-safe: psycopg2.ThreadedConnectionPool serialises getconn/putconn.

    Yields:
        An open psycopg2 connection.
    """
    pool = _get_pool()
    conn = pool.getconn()
    try:
        yield conn
    finally:
        pool.putconn(conn)


@contextmanager
def get_cursor(
    commit: bool = True,
) -> Generator[psycopg2.extensions.cursor, None, None]:
    """Yield a cursor, committing on clean exit or rolling back on exception.

    Args:
        commit: If True (default), commit the transaction on clean exit.

    Yields:
        An open psycopg2 cursor.
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
