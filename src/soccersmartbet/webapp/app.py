"""FastAPI application shell for SoccerSmartBet dashboard.

Binds to 127.0.0.1:8083.  Static files served from webapp/static/.
No auth, no SSE, no WebSocket — polling only.
"""
from __future__ import annotations

import asyncio
import logging
import time as _time
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from soccersmartbet.db import get_cursor
from soccersmartbet.utils.timezone import now_isr, today_isr

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Process start time — used by /api/health uptime_seconds
# ---------------------------------------------------------------------------
_PROCESS_START = now_isr()

from soccersmartbet.webapp.routes.insights import router as insights_router
from soccersmartbet.webapp.routes.stats import router as stats_router
from soccersmartbet.webapp.routes.today import router as today_router
from soccersmartbet.webapp.runtime_state import LAST_POLLER_TICK

# ---------------------------------------------------------------------------
# Status cache: key "today" → (payload_dict, cached_at_isr)
# ---------------------------------------------------------------------------
_STATUS_CACHE: dict[str, tuple[dict, Any]] = {}
_STATUS_LOCK = asyncio.Lock()

# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------

app = FastAPI(title="SoccerSmartBet Dashboard", docs_url=None, redoc_url=None)

# Mount static files (Wave 11 will populate; directory must exist)
_STATIC_DIR = Path(__file__).parent / "static"
_STATIC_DIR.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(_STATIC_DIR)), name="static")

# Wave 11A: Today tab routes
app.include_router(today_router)

# Wave 12A: History / P&L / Team / League stats routes
app.include_router(stats_router)

# Wave 12B: AI insights endpoint (async job manager + LLM call)
app.include_router(insights_router)


# ---------------------------------------------------------------------------
# Error-handler middleware
# ---------------------------------------------------------------------------


@app.middleware("http")
async def _unhandled_exception_middleware(request: Request, call_next: Any) -> Any:
    try:
        return await call_next(request)
    except Exception as exc:
        logger.exception("Unhandled exception in %s %s", request.method, request.url)
        return JSONResponse(
            status_code=500,
            content={"error": "internal", "detail": "An internal error occurred"},
        )


# ---------------------------------------------------------------------------
# GET /api/health
# ---------------------------------------------------------------------------


@app.get("/api/health")
async def health() -> dict:
    """Return liveness data: uptime, DB round-trip, last poller tick."""
    uptime = (now_isr() - _PROCESS_START).total_seconds()

    t0 = _time.perf_counter()
    with get_cursor(commit=False) as cur:
        cur.execute("SELECT 1")
    db_ping_ms = round((_time.perf_counter() - t0) * 1000, 2)

    return {
        "status": "ok",
        "uptime_seconds": round(uptime, 1),
        "db_ping_ms": db_ping_ms,
        "last_poller_tick_isr": LAST_POLLER_TICK[0] or None,
    }


# ---------------------------------------------------------------------------
# GET /api/status/today
# ---------------------------------------------------------------------------


def _fetch_status_from_db() -> dict:
    """Fetch daily_runs row + last 10 run_events for today. No cache logic."""
    today = today_isr()
    today_iso = today.isoformat()

    run_sql = """
        SELECT
            run_date,
            pre_gambling_started_at,
            pre_gambling_completed_at,
            gambling_completed_at,
            post_games_trigger_at,
            post_games_completed_at,
            games_found,
            game_ids,
            user_bet_completed,
            ai_bet_completed,
            no_games_user_confirmed,
            last_trigger_source,
            attempt_count,
            last_error,
            status
        FROM daily_runs
        WHERE run_date = %s
    """
    events_sql = """
        SELECT event_id, event_type, triggered_by, triggered_at, payload
        FROM run_events
        WHERE run_date = %s
        ORDER BY triggered_at DESC
        LIMIT 10
    """

    with get_cursor(commit=False) as cur:
        cur.execute(run_sql, (today,))
        run_row = cur.fetchone()
        cur.execute(events_sql, (today,))
        event_rows = cur.fetchall()

    events = [
        {
            "event_id": r[0],
            "event_type": r[1],
            "triggered_by": r[2],
            "triggered_at": r[3].isoformat() if r[3] is not None else None,
            "payload": r[4],
        }
        for r in event_rows
    ]

    if run_row is None:
        return {
            "run_date": today_iso,
            "today_date": today_iso,
            "status": "idle",
            "pre_gambling_started_at": None,
            "pre_gambling_completed_at": None,
            "gambling_completed_at": None,
            "post_games_trigger_at": None,
            "post_games_completed_at": None,
            "games_found": None,
            "game_ids": [],
            "user_bet_completed": False,
            "ai_bet_completed": False,
            "no_games_user_confirmed": None,
            "last_trigger_source": None,
            "attempt_count": 0,
            "last_error": None,
            "events": events,
        }

    def _iso(dt: Any) -> str | None:
        return dt.isoformat() if dt is not None else None

    return {
        "run_date": run_row[0].isoformat() if run_row[0] is not None else today_iso,
        "today_date": today_iso,
        "pre_gambling_started_at": _iso(run_row[1]),
        "pre_gambling_completed_at": _iso(run_row[2]),
        "gambling_completed_at": _iso(run_row[3]),
        "post_games_trigger_at": _iso(run_row[4]),
        "post_games_completed_at": _iso(run_row[5]),
        "games_found": run_row[6],
        "game_ids": list(run_row[7]) if run_row[7] is not None else [],
        "user_bet_completed": run_row[8],
        "ai_bet_completed": run_row[9],
        "no_games_user_confirmed": run_row[10],
        "last_trigger_source": run_row[11],
        "attempt_count": run_row[12],
        "last_error": run_row[13],
        "status": run_row[14],
        "events": events,
    }


async def _get_cached_status() -> dict:
    """Return status payload with 1-second server-side TTL cache.

    Uses _STATUS_LOCK to prevent concurrent DB fetches on cache miss
    (cache stampede / race condition guard).
    """
    now = now_isr()
    async with _STATUS_LOCK:
        if "today" in _STATUS_CACHE:
            payload, cached_at = _STATUS_CACHE["today"]
            if (now - cached_at).total_seconds() < 1.0:
                return payload
        payload = _fetch_status_from_db()
        _STATUS_CACHE["today"] = (payload, now)
        return payload


@app.get("/api/status/today")
async def status_today() -> dict:
    """Return daily_runs row + last 10 run_events for today (1s TTL cache)."""
    return await _get_cached_status()
