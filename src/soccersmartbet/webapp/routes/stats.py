"""Stats routes — History, P&L, Team, and League tabs.

Routes:
  GET  /history                       — Serve history.html
  GET  /pnl                           — Serve pnl.html
  GET  /team/{slug}                   — Serve team.html
  GET  /league/{slug}                 — Serve league.html
  GET  /api/bets                      — Filtered bet list (Query DSL)
  GET  /api/pnl                       — Cumulative P&L time-series
  GET  /api/teams/{slug}/stats        — Team rollup
  GET  /api/leagues/{slug}/stats      — League rollup

Design decision — team lookup:
  games.home_team / away_team are plain VARCHAR strings; there is no
  numeric team_id.  The slug path-param is a URL-encoded team name;
  the query uses ILIKE '%<slug>%' against both columns so partial or
  case-insensitive names resolve.  Alternative (team_registry) was
  rejected because team_registry is an in-memory bootstrap cache, not
  a DB-backed authoritative index — it would add a fragile dependency.

Design decision — notable games:
  Top-5 by absolute P&L magnitude (|pnl|).  Stake-based ordering would
  rank same-stake bets arbitrarily.  Upset-based ordering requires
  odds thresholds that are not in scope.  |pnl| surfaces the games
  that actually moved the needle.

Design decision — P&L zero baseline:
  The y-axis always includes zero.  If all values are positive, zero is
  the bottom of the range; if all negative, zero is the top.  This
  prevents the chart from visually amplifying small losses into apparent
  cliffs.  Observed min/max extend the range beyond zero when needed.
"""
from __future__ import annotations

import logging
import urllib.parse
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse

from soccersmartbet.db import get_cursor
from soccersmartbet.team_registry import resolve_team
from soccersmartbet.webapp.query.parser import ParseError
from soccersmartbet.webapp.query.service import run_filter

logger = logging.getLogger(__name__)

router = APIRouter()

_STATIC_DIR = Path(__file__).parent.parent / "static"

# ---------------------------------------------------------------------------
# HTML page endpoints
# ---------------------------------------------------------------------------


@router.get("/history")
async def serve_history_html() -> FileResponse:
    """Serve the History tab HTML page."""
    return FileResponse(str(_STATIC_DIR / "history.html"), media_type="text/html")


@router.get("/pnl")
async def serve_pnl_html() -> FileResponse:
    """Serve the P&L tab HTML page."""
    return FileResponse(str(_STATIC_DIR / "pnl.html"), media_type="text/html")


@router.get("/team/{slug}")
async def serve_team_html(slug: str) -> FileResponse:
    """Serve the Team tab HTML page (slug embedded in URL for JS to read)."""
    return FileResponse(str(_STATIC_DIR / "team.html"), media_type="text/html")


@router.get("/league/{slug}")
async def serve_league_html(slug: str) -> FileResponse:
    """Serve the League tab HTML page (slug embedded in URL for JS to read)."""
    return FileResponse(str(_STATIC_DIR / "league.html"), media_type="text/html")


# ---------------------------------------------------------------------------
# GET /api/bets
# ---------------------------------------------------------------------------


@router.get("/api/bets")
async def get_bets(
    filter: str = Query(default="", alias="filter"),
) -> dict:
    """Return bets matching the given DSL filter as JSON.

    Empty / missing ``filter`` param → all bets (no WHERE clause restriction
    beyond the 2000 row cap).  URL-shareable: dashboard sets ``?filter=`` in
    the address bar and reads it on page load.

    Args:
        filter: Raw DSL string (e.g. ``league:pl date:2026-04``).

    Returns:
        ``{rows, aggregates, row_cap_hit, dsl}`` — the ``FilterResult``
        serialised as JSON.

    Raises:
        HTTP 400 with ``{error, detail}`` on parse failure.
    """
    try:
        result = run_filter(filter.strip())
    except ParseError as exc:
        raise HTTPException(
            status_code=400,
            detail={"error": "parse_error", "detail": str(exc)},
        )

    def _row(b: Any) -> dict:
        return {
            "bet_id": b.bet_id,
            "bettor": b.bettor,
            "prediction": b.prediction,
            "stake": float(b.stake),
            "odds": float(b.odds),
            "result": b.result,
            "pnl": float(b.pnl) if b.pnl is not None else None,
            "game_id": b.game_id,
            "home_team": b.home_team,
            "away_team": b.away_team,
            "match_date": b.match_date.isoformat(),
            "kickoff_time": b.kickoff_time.strftime("%H:%M"),
            "league": b.league,
            "outcome": b.outcome,
            "home_score": b.home_score,
            "away_score": b.away_score,
        }

    agg = result.aggregates
    return {
        "rows": [_row(b) for b in result.rows],
        "aggregates": {
            "count": agg.count,
            "total_stake": float(agg.total_stake),
            "total_pnl": float(agg.total_pnl),
            "win_rate": agg.win_rate,
        },
        "row_cap_hit": result.row_cap_hit,
        "dsl": result.dsl,
    }


# ---------------------------------------------------------------------------
# GET /api/pnl
# ---------------------------------------------------------------------------


@router.get("/api/pnl")
async def get_pnl(
    filter: str = Query(default="", alias="filter"),
) -> dict:
    """Return cumulative P&L time-series for user and AI.

    Applies the same DSL filter as ``/api/bets`` and then aggregates
    daily P&L per bettor into a running cumulative series.

    Args:
        filter: Raw DSL string.

    Returns:
        ``{points: [{date, cumulative_user, cumulative_ai}, ...]}``

    Raises:
        HTTP 400 on parse failure.
    """
    try:
        result = run_filter(filter.strip())
    except ParseError as exc:
        raise HTTPException(
            status_code=400,
            detail={"error": "parse_error", "detail": str(exc)},
        )

    # Aggregate daily P&L per bettor from in-memory rows (no second DB hit)
    daily: dict[str, dict[str, float]] = {}
    for b in result.rows:
        if b.pnl is None:
            continue
        d = b.match_date.isoformat()
        if d not in daily:
            daily[d] = {"user": 0.0, "ai": 0.0}
        if b.bettor in ("user", "ai"):
            daily[d][b.bettor] += float(b.pnl)

    # Sort dates and compute cumulative sums
    sorted_dates = sorted(daily.keys())
    points = []
    user_cum = 0.0
    ai_cum = 0.0
    for d in sorted_dates:
        user_cum += daily[d].get("user", 0.0)
        ai_cum += daily[d].get("ai", 0.0)
        points.append({
            "date": d,
            "cumulative_user": round(user_cum, 2),
            "cumulative_ai": round(ai_cum, 2),
        })

    return {"points": points, "row_cap_hit": result.row_cap_hit, "dsl": result.dsl}


# ---------------------------------------------------------------------------
# GET /api/teams/{slug}/stats
# ---------------------------------------------------------------------------


@router.get("/api/teams/{slug}/stats")
async def get_team_stats(slug: str) -> dict:
    """Return rollup stats for a team identified by URL-encoded name slug.

    The slug is decoded and matched against both ``home_team`` and
    ``away_team`` using ILIKE.  Partial matches resolve (e.g. ``arsenal``
    matches ``Arsenal FC``).

    Args:
        slug: URL-encoded team name (e.g. ``Arsenal%20FC`` or ``arsenal``).

    Returns:
        ``{team_name, total_bets, win_rate, total_pnl, total_stake,
           notable_games}`` where ``notable_games`` is top-5 bets by
        ``|pnl|``.

    Raises:
        HTTP 404 when no bets match the slug.
    """
    raw_name = urllib.parse.unquote(slug)
    canonical = resolve_team(raw_name)
    if canonical is None:
        raise HTTPException(
            status_code=404,
            detail={"error": "unknown_team", "slug": slug},
        )
    # resolve_team returns a disambiguated canonical (e.g. "Arsenal") — substring
    # ILIKE only widens to storage variants ("Arsenal FC"), not to other teams.
    # Escape LIKE metacharacters so "_" / "%" in names are treated as literals.
    _safe = canonical.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    pattern = f"%{_safe}%"

    sql = """
        SELECT
            b.bet_id,
            b.bettor,
            b.prediction,
            b.stake,
            b.odds,
            b.result,
            b.pnl,
            g.game_id,
            g.home_team,
            g.away_team,
            g.match_date,
            g.kickoff_time,
            g.league,
            g.outcome,
            g.home_score,
            g.away_score
        FROM bets b
        JOIN games g ON g.game_id = b.game_id
        WHERE g.home_team ILIKE %(name)s ESCAPE '\\'
           OR g.away_team ILIKE %(name)s ESCAPE '\\'
        ORDER BY g.match_date DESC, g.kickoff_time DESC
        LIMIT 2000
    """

    with get_cursor(commit=False) as cur:
        cur.execute(sql, {"name": pattern})
        rows = cur.fetchall()

    if not rows:
        raise HTTPException(
            status_code=404,
            detail={"error": "not_found", "detail": f"No bets found for team '{canonical}'"},
        )

    total_stake = 0.0
    total_pnl = 0.0
    wins = 0
    settled = 0
    bet_list = []

    for r in rows:
        pnl_val = float(r[6]) if r[6] is not None else None
        stake_val = float(r[3])
        total_stake += stake_val
        if pnl_val is not None:
            total_pnl += pnl_val
            settled += 1
            if pnl_val > 0:
                wins += 1
        bet_list.append({
            "bet_id": r[0],
            "bettor": r[1],
            "prediction": r[2],
            "stake": stake_val,
            "odds": float(r[4]),
            "result": r[5],
            "pnl": pnl_val,
            "game_id": r[7],
            "home_team": r[8],
            "away_team": r[9],
            "match_date": r[10].isoformat(),
            "kickoff_time": r[11].strftime("%H:%M"),
            "league": r[12],
            "outcome": r[13],
            "home_score": r[14],
            "away_score": r[15],
        })

    win_rate = wins / settled if settled > 0 else None

    # Notable games: top-5 by |pnl| (only settled bets)
    notable = sorted(
        [b for b in bet_list if b["pnl"] is not None],
        key=lambda x: abs(x["pnl"]),
        reverse=True,
    )[:5]

    return {
        "team_name": canonical,
        "total_bets": len(bet_list),
        "total_stake": round(total_stake, 2),
        "total_pnl": round(total_pnl, 2),
        "win_rate": win_rate,
        "notable_games": notable,
        "bets": bet_list,
    }


# ---------------------------------------------------------------------------
# GET /api/leagues/{slug}/stats
# ---------------------------------------------------------------------------


@router.get("/api/leagues/{slug}/stats")
async def get_league_stats(slug: str) -> dict:
    """Return rollup stats for a league identified by URL-encoded name slug.

    The slug is decoded and matched against ``games.league`` using ILIKE.

    Args:
        slug: URL-encoded league name (e.g. ``Premier%20League`` or ``pl``).

    Returns:
        ``{league_name, total_bets, win_rate, total_pnl, total_stake,
           notable_games}`` — same shape as team stats.

    Raises:
        HTTP 404 when no bets match the slug.
    """
    league_name = urllib.parse.unquote(slug)
    # Prefix match (starts-with) so "pl" doesn't pull in "Italian Playoff" while
    # "Premier" still matches "Premier League". Escape LIKE metacharacters so
    # "_" / "%" in slugs are treated as literals.
    _safe_league = league_name.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    pattern = f"{_safe_league}%"

    sql = """
        SELECT
            b.bet_id,
            b.bettor,
            b.prediction,
            b.stake,
            b.odds,
            b.result,
            b.pnl,
            g.game_id,
            g.home_team,
            g.away_team,
            g.match_date,
            g.kickoff_time,
            g.league,
            g.outcome,
            g.home_score,
            g.away_score
        FROM bets b
        JOIN games g ON g.game_id = b.game_id
        WHERE g.league ILIKE %(name)s ESCAPE '\\'
        ORDER BY g.match_date DESC, g.kickoff_time DESC
        LIMIT 2000
    """

    with get_cursor(commit=False) as cur:
        cur.execute(sql, {"name": pattern})
        rows = cur.fetchall()

    if not rows:
        raise HTTPException(
            status_code=404,
            detail={"error": "not_found", "detail": f"No bets found for league matching '{league_name}'"},
        )

    total_stake = 0.0
    total_pnl = 0.0
    wins = 0
    settled = 0
    bet_list = []

    for r in rows:
        pnl_val = float(r[6]) if r[6] is not None else None
        stake_val = float(r[3])
        total_stake += stake_val
        if pnl_val is not None:
            total_pnl += pnl_val
            settled += 1
            if pnl_val > 0:
                wins += 1
        bet_list.append({
            "bet_id": r[0],
            "bettor": r[1],
            "prediction": r[2],
            "stake": stake_val,
            "odds": float(r[4]),
            "result": r[5],
            "pnl": pnl_val,
            "game_id": r[7],
            "home_team": r[8],
            "away_team": r[9],
            "match_date": r[10].isoformat(),
            "kickoff_time": r[11].strftime("%H:%M"),
            "league": r[12],
            "outcome": r[13],
            "home_score": r[14],
            "away_score": r[15],
        })

    win_rate = wins / settled if settled > 0 else None

    notable = sorted(
        [b for b in bet_list if b["pnl"] is not None],
        key=lambda x: abs(x["pnl"]),
        reverse=True,
    )[:5]

    return {
        "league_name": league_name,
        "total_bets": len(bet_list),
        "total_stake": round(total_stake, 2),
        "total_pnl": round(total_pnl, 2),
        "win_rate": win_rate,
        "notable_games": notable,
        "bets": bet_list,
    }
