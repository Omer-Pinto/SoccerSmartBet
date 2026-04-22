"""Today tab — control panel + bet modification endpoints.

Routes:
  GET  /today            — Serve today.html
  POST /api/runs         — Manual flow trigger (pre_gambling / post_games / regenerate_report)
  PATCH /api/bets/{bet_id} — Edit prediction and/or stake within the allowed window
"""
from __future__ import annotations

import asyncio
import logging
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from soccersmartbet.db import get_conn, get_cursor
from soccersmartbet.utils.timezone import format_isr_time, isr_datetime, now_isr, today_isr
from soccersmartbet.webapp.audit import EventType, write_run_event
from soccersmartbet.webapp.run_mutex import (
    FlowConflict,
    InvalidTransition,
    acquire_flow,
    mark_failed,
    release_flow,
)

logger = logging.getLogger(__name__)

router = APIRouter()

_STATIC_DIR = Path(__file__).parent.parent / "static"

# ---------------------------------------------------------------------------
# In-flight task registry (mirrors triggers.py pattern)
# ---------------------------------------------------------------------------

_ACTIVE_FLOW_TASKS: set[asyncio.Task] = set()


def _spawn_flow(coro) -> asyncio.Task:
    """Create a task, register it, and auto-remove on completion."""
    task = asyncio.create_task(coro)
    _ACTIVE_FLOW_TASKS.add(task)
    task.add_done_callback(_ACTIVE_FLOW_TASKS.discard)
    return task


# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------

FlowType = Literal["pre_gambling", "post_games", "regenerate_report"]

_FLOW_TARGET_STATUS: dict[str, str] = {
    "pre_gambling": "pre_gambling_running",
    "regenerate_report": "pre_gambling_running",
    "post_games": "post_games_running",
}

_FLOW_SUCCESS_STATUS: dict[str, str] = {
    "pre_gambling_running": "pre_gambling_done",
    "post_games_running": "post_games_done",
}


class RunRequest(BaseModel):
    run_date: str = Field(..., description="YYYY-MM-DD")
    flow_type: FlowType
    force: bool = False
    params: dict | None = None


class BetPatchRequest(BaseModel):
    prediction: Literal["1", "x", "2"] | None = None
    stake: float | None = None


# ---------------------------------------------------------------------------
# GET /today
# ---------------------------------------------------------------------------


@router.get("/today")
async def serve_today_html():
    """Serve the Today tab HTML page."""
    path = _STATIC_DIR / "today.html"
    return FileResponse(str(path), media_type="text/html")


# ---------------------------------------------------------------------------
# POST /api/runs
# ---------------------------------------------------------------------------


@router.post("/api/runs", status_code=202)
async def trigger_run(body: RunRequest):
    """Manually trigger a flow run.

    Returns 202 immediately and spawns a background task.
    Returns 409 on mutex conflict.
    """
    try:
        run_date = date.fromisoformat(body.run_date)
    except ValueError:
        raise HTTPException(status_code=400, detail="run_date must be YYYY-MM-DD")

    flow_type = body.flow_type
    target_status = _FLOW_TARGET_STATUS[flow_type]

    # Guard: post_games requires existing game_ids from a completed pre-gambling run
    if flow_type == "post_games":
        game_ids_check = _resolve_game_ids(run_date)
        if not game_ids_check:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "no_games",
                    "detail": "No game_ids from pre-gambling run — run pre-gambling first",
                },
            )

    # Determine whether to bypass the transition guard.
    # regenerate_report: always force (the whole point is "redo no matter what").
    # pre_gambling / post_games: force only if the operator explicitly toggled it.
    use_force = flow_type == "regenerate_report" or body.force

    try:
        with acquire_flow(run_date, target_status, triggered_by="manual", force=use_force) as ctx:
            # Force: write an audit event so the override is visible in run_events,
            # then clear derived report rows AFTER acquiring the mutex slot.
            if use_force:
                write_run_event(
                    run_date,
                    EventType.PRE_GAMBLING_FORCE_RESET,
                    "manual",
                    {
                        "flow_type": flow_type,
                        "previous_status": ctx.previous_status,
                        "triggered_at_isr": now_isr().isoformat(),
                    },
                )
                # Only wipe reports for pre-gambling side; post_games doesn't produce them.
                if flow_type in ("pre_gambling", "regenerate_report"):
                    _force_clear(run_date)
            event_id = write_run_event(
                run_date,
                _start_event_type(flow_type),
                "manual",
                {
                    "flow_type": flow_type,
                    "triggered_at_isr": now_isr().isoformat(),
                    "attempt_count": ctx.attempt_count,
                    "force": use_force,
                },
            )
    except FlowConflict as exc:
        raise HTTPException(
            status_code=409,
            detail={"error": "flow_conflict", "current_status": exc.current_status},
        )
    except InvalidTransition as exc:
        raise HTTPException(
            status_code=409,
            detail={"error": "invalid_transition", "detail": str(exc)},
        )

    _spawn_flow(_wrap_flow(run_date, flow_type, target_status, body.params or {}))

    return {"event_id": event_id, "status": "starting"}


def _force_clear(run_date: date) -> None:
    """Delete only the LLM-derived report rows so a force re-run starts clean.

    Deliberately does NOT touch games or bets.  bets.game_id has ON DELETE CASCADE
    from games — deleting games would wipe user bets, which is data loss.

    Design decision: persist_games uses plain INSERT (no ON CONFLICT), so games rows
    survive and the next pre-gambling run will re-select and re-insert new game rows.
    The force-override path is intended to regenerate REPORTS from a fresh game
    selection; the old game rows are left in place and the new run inserts new ones.
    This means a force-override on a day with existing games accumulates rows — that
    is an accepted trade-off documented here.  Operator can inspect via DB directly.

    Called AFTER acquire_flow so the delete is conditional on taking the mutex slot.
    """
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                DELETE FROM expert_game_reports
                WHERE game_id IN (SELECT game_id FROM games WHERE match_date = %s)
                """,
                (run_date,),
            )
            cur.execute(
                """
                DELETE FROM game_reports
                WHERE game_id IN (SELECT game_id FROM games WHERE match_date = %s)
                """,
                (run_date,),
            )
            cur.execute(
                """
                DELETE FROM team_reports
                WHERE game_id IN (SELECT game_id FROM games WHERE match_date = %s)
                """,
                (run_date,),
            )
        conn.commit()
    logger.info("force_clear: deleted report rows for %s (games + bets preserved)", run_date)


def _start_event_type(flow_type: str) -> str:
    if flow_type in ("pre_gambling", "regenerate_report"):
        return EventType.PRE_GAMBLING_STARTED
    return EventType.POST_GAMES_STARTED


def _fail_event_type(flow_type: str) -> str:
    if flow_type in ("pre_gambling", "regenerate_report"):
        return EventType.PRE_GAMBLING_FAILED
    return EventType.POST_GAMES_FAILED


def _complete_event_type(flow_type: str) -> str:
    if flow_type in ("pre_gambling", "regenerate_report"):
        return EventType.PRE_GAMBLING_COMPLETED
    return EventType.POST_GAMES_COMPLETED


async def _wrap_flow(
    run_date: date,
    flow_type: str,
    target_status: str,
    params: dict,
) -> None:
    """Background task: run the sync flow in a thread, then release the mutex."""
    started = now_isr()
    try:
        if flow_type in ("pre_gambling", "regenerate_report"):
            from soccersmartbet.pre_gambling_flow.graph_manager import run_pre_gambling_flow  # noqa: PLC0415

            result = await asyncio.to_thread(run_pre_gambling_flow)
            game_ids: list[int] = result.get("games_to_analyze", [])
        else:
            # post_games — game_ids must be resolved from daily_runs
            game_ids = _resolve_game_ids(run_date)
            from soccersmartbet.post_games_flow.graph_manager import run_post_games_flow  # noqa: PLC0415

            result = await asyncio.to_thread(run_post_games_flow, game_ids)
            game_ids = list(result.get("game_ids", game_ids))

    except Exception as exc:
        mark_failed(run_date, exc)
        write_run_event(
            run_date,
            _fail_event_type(flow_type),
            "manual",
            {
                "flow_type": flow_type,
                "error_type": type(exc).__name__,
                "error_message": str(exc)[:2000],
            },
        )
        logger.exception("Manual flow %s failed for %s", flow_type, run_date)
        return

    success_status = _FLOW_SUCCESS_STATUS.get(target_status, "pre_gambling_done")
    try:
        release_flow(run_date, success_status)
    except Exception as exc:
        logger.exception("release_flow failed for manual %s — marking failed", flow_type)
        mark_failed(run_date, exc)
        return

    elapsed = (now_isr() - started).total_seconds()
    write_run_event(
        run_date,
        _complete_event_type(flow_type),
        "manual",
        {
            "flow_type": flow_type,
            "game_ids": game_ids,
            "games_found": len(game_ids),
            "elapsed_seconds": round(elapsed, 2),
        },
    )
    logger.info("Manual flow %s completed for %s in %.1fs", flow_type, run_date, elapsed)


def _resolve_game_ids(run_date: date) -> list[int]:
    """Fetch game_ids from daily_runs for a post_games trigger."""
    with get_cursor(commit=False) as cur:
        cur.execute(
            "SELECT game_ids FROM daily_runs WHERE run_date = %s",
            (run_date,),
        )
        row = cur.fetchone()
    if row is None or row[0] is None:
        return []
    return list(row[0])


# ---------------------------------------------------------------------------
# PATCH /api/bets/{bet_id}
# ---------------------------------------------------------------------------


@router.patch("/api/bets/{bet_id}")
async def patch_bet(bet_id: int, body: BetPatchRequest):
    """Edit prediction and/or stake for a bet.

    Guards:
    - gambling_completed_at must be set (betting phase done)
    - kickoff_time - now_isr() must be > 30 minutes

    Returns 200 with updated bet, 403 if window is closed, 404 if not found.
    """
    if body.prediction is None and body.stake is None:
        raise HTTPException(status_code=400, detail="Provide at least one of: prediction, stake")

    # --- fetch current bet + game + daily_runs row ---
    with get_cursor(commit=False) as cur:
        cur.execute(
            """
            SELECT
                b.bet_id,
                b.game_id,
                b.bettor,
                b.prediction,
                b.stake,
                b.odds,
                b.justification,
                b.result,
                b.pnl,
                g.kickoff_time,
                g.match_date,
                g.home_team,
                g.away_team,
                g.league,
                g.home_win_odd,
                g.draw_odd,
                g.away_win_odd,
                g.status AS game_status,
                dr.gambling_completed_at,
                dr.status AS run_status
            FROM bets b
            JOIN games g ON g.game_id = b.game_id
            LEFT JOIN daily_runs dr ON dr.run_date = g.match_date
            WHERE b.bet_id = %s
            """,
            (bet_id,),
        )
        row = cur.fetchone()

    if row is None:
        raise HTTPException(status_code=404, detail=f"bet_id {bet_id} not found")

    (
        _bet_id, game_id, bettor, old_prediction, old_stake, odds, justification,
        result, pnl, kickoff_time, match_date, home_team, away_team, league,
        home_win_odd, draw_odd, away_win_odd, game_status, gambling_completed_at, run_status,
    ) = row

    # Guard A: gambling phase must have completed
    if gambling_completed_at is None:
        raise HTTPException(
            status_code=403,
            detail="Bet edits are only allowed after the gambling phase has completed (bets not yet placed).",
        )

    # Guard B: must be > 30 minutes before kickoff
    kickoff_dt = isr_datetime(
        match_date.year,
        match_date.month,
        match_date.day,
        kickoff_time.hour,
        kickoff_time.minute,
        kickoff_time.second,
    )
    now = now_isr()
    minutes_to_kickoff = (kickoff_dt - now).total_seconds() / 60.0

    if minutes_to_kickoff <= 30:
        lock_time_str = format_isr_time(kickoff_dt)
        raise HTTPException(
            status_code=403,
            detail=(
                f"Edits close 30 minutes before kickoff. "
                f"This game kicks off at {lock_time_str} ISR — edit window is now closed."
            ),
        )

    # Apply changes
    new_prediction = body.prediction if body.prediction is not None else old_prediction
    new_stake = Decimal(str(body.stake)) if body.stake is not None else old_stake

    if new_stake <= 0:
        raise HTTPException(status_code=400, detail="stake must be positive")

    # Atomic transaction: UPDATE bets + INSERT INTO bet_edits in one commit.
    # This ensures trg_bet_edit_window trigger (which fires on bet_edits INSERT)
    # can roll back BOTH mutations together if the window is already closed.
    # If UPDATE committed first and trigger rejected only the audit INSERT, the
    # forbidden bet mutation would remain live — hence the single transaction.
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE bets
                SET prediction = %s,
                    stake = %s
                WHERE bet_id = %s
                """,
                (new_prediction, new_stake, bet_id),
            )
            if body.prediction is not None and body.prediction != old_prediction:
                cur.execute(
                    """
                    INSERT INTO bet_edits (bet_id, field, old_value, new_value, source)
                    VALUES (%(bet_id)s, %(field)s, %(old_value)s, %(new_value)s, %(source)s)
                    """,
                    {
                        "bet_id": bet_id,
                        "field": "prediction",
                        "old_value": str(old_prediction) if old_prediction is not None else None,
                        "new_value": str(new_prediction),
                        "source": "dashboard",
                    },
                )
            if body.stake is not None and abs(body.stake - float(old_stake)) > 1e-9:
                cur.execute(
                    """
                    INSERT INTO bet_edits (bet_id, field, old_value, new_value, source)
                    VALUES (%(bet_id)s, %(field)s, %(old_value)s, %(new_value)s, %(source)s)
                    """,
                    {
                        "bet_id": bet_id,
                        "field": "stake",
                        "old_value": str(old_stake),
                        "new_value": str(new_stake),
                        "source": "dashboard",
                    },
                )
        conn.commit()

    return {
        "bet_id": bet_id,
        "game_id": game_id,
        "bettor": bettor,
        "prediction": new_prediction,
        "stake": new_stake,
        "odds": float(odds),
        "justification": justification,
        "result": result,
        "pnl": float(pnl) if pnl is not None else None,
        "game": {
            "game_id": game_id,
            "kickoff_time": kickoff_time.strftime("%H:%M"),
            "match_date": match_date.isoformat(),
            "home_team": home_team,
            "away_team": away_team,
            "league": league,
            "home_win_odd": float(home_win_odd),
            "draw_odd": float(draw_odd),
            "away_win_odd": float(away_win_odd),
            "status": game_status,
        },
    }


# ---------------------------------------------------------------------------
# GET /api/today/data — today's bets + games + bankroll for the JS frontend
# ---------------------------------------------------------------------------


@router.get("/api/today/data")
async def today_data() -> dict:
    """Return today's bets (joined with games) and bankroll totals."""
    today = today_isr()

    bets_sql = """
        SELECT
            b.bet_id,
            b.game_id,
            b.bettor,
            b.prediction,
            b.stake,
            b.odds,
            b.justification,
            b.result,
            b.pnl,
            g.kickoff_time,
            g.match_date,
            g.home_team,
            g.away_team,
            g.league,
            g.home_win_odd,
            g.draw_odd,
            g.away_win_odd,
            g.status AS game_status
        FROM bets b
        JOIN games g ON g.game_id = b.game_id
        WHERE g.match_date = %s
        ORDER BY g.kickoff_time, b.bettor
    """
    bankroll_sql = """
        SELECT bettor, total_bankroll
        FROM bankroll
    """
    today_pnl_sql = """
        SELECT b.bettor, COALESCE(SUM(b.pnl), 0) AS today_pnl
        FROM bets b
        JOIN games g ON g.game_id = b.game_id
        WHERE g.match_date = %s AND b.pnl IS NOT NULL
        GROUP BY b.bettor
    """

    with get_cursor(commit=False) as cur:
        cur.execute(bets_sql, (today,))
        bet_rows = cur.fetchall()
        cur.execute(bankroll_sql)
        bankroll_rows = cur.fetchall()
        cur.execute(today_pnl_sql, (today,))
        pnl_rows = cur.fetchall()

    bets = [
        {
            "bet_id": r[0],
            "game_id": r[1],
            "bettor": r[2],
            "prediction": r[3],
            "stake": float(r[4]),
            "odds": float(r[5]),
            "justification": r[6],
            "result": r[7],
            "pnl": float(r[8]) if r[8] is not None else None,
            "game": {
                "game_id": r[1],
                "kickoff_time": r[9].strftime("%H:%M"),
                "match_date": r[10].isoformat(),
                "home_team": r[11],
                "away_team": r[12],
                "league": r[13],
                "home_win_odd": float(r[14]),
                "draw_odd": float(r[15]),
                "away_win_odd": float(r[16]),
                "status": r[17],
            },
        }
        for r in bet_rows
    ]

    bankroll_by_bettor = {r[0]: float(r[1]) for r in bankroll_rows}
    pnl_by_bettor = {r[0]: float(r[1]) for r in pnl_rows}

    return {
        "bets": bets,
        "bankroll": {
            "user": {
                "balance": bankroll_by_bettor.get("user"),
                "today_pnl": pnl_by_bettor.get("user"),
            },
            "ai": {
                "balance": bankroll_by_bettor.get("ai"),
                "today_pnl": pnl_by_bettor.get("ai"),
            },
        },
    }


# ---------------------------------------------------------------------------
# GET /api/today/pnl — 30-day cumulative P&L history for sparkline
# ---------------------------------------------------------------------------


@router.get("/api/today/pnl")
async def today_pnl() -> dict:
    """Return 30-day cumulative P&L series for user and AI sparkline."""
    today = today_isr()
    start = today - timedelta(days=29)

    sql = """
        SELECT
            g.match_date,
            b.bettor,
            SUM(b.pnl) AS daily_pnl
        FROM bets b
        JOIN games g ON g.game_id = b.game_id
        WHERE g.match_date BETWEEN %s AND %s
          AND b.pnl IS NOT NULL
        GROUP BY g.match_date, b.bettor
        ORDER BY g.match_date
    """

    with get_cursor(commit=False) as cur:
        cur.execute(sql, (start, today))
        rows = cur.fetchall()

    # Build date → {user, ai} daily P&L map
    daily: dict[str, dict[str, float]] = {}
    for row in rows:
        d = row[0].isoformat()
        bettor: str = row[1]
        pnl_val = float(row[2]) if row[2] is not None else 0.0
        if d not in daily:
            daily[d] = {"user": 0.0, "ai": 0.0}
        daily[d][bettor] = pnl_val

    # Walk 30 days and accumulate cumulative totals
    history = []
    user_cum = 0.0
    ai_cum = 0.0
    current = start
    while current <= today:
        d = current.isoformat()
        user_cum += daily.get(d, {}).get("user", 0.0)
        ai_cum += daily.get(d, {}).get("ai", 0.0)
        history.append({
            "date": d,
            "user_cumulative": round(user_cum, 2),
            "ai_cumulative": round(ai_cum, 2),
        })
        current = current + timedelta(days=1)

    return {"history": history}
