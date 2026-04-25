"""Live-score endpoint for today's games.

Route:
  GET /api/today/live

Returns real-time score, period, and minute for today's games that have a
fotmob_match_id.  Games without a fotmob_match_id are omitted from the
response.

Design decisions:

Period derivation (matches spec):
  - !started                                   → "pre"
  - started && reason.short == "HT"            → "HT"
  - started && ongoing && secondHalfStarted="" → "1H"
  - started && ongoing && secondHalfStarted!="" → "2H"
  - finished                                   → "FT"
  - anything else (parse error, unknown)       → "unknown"

Caching:
  - 30-second in-process cache per game, keyed by (game_id, fotmob_match_id).
  - Finished games are NOT evicted from cache (period "FT"); they will keep
    returning the cached final score without hitting FotMob again.
  - On FotMob failure for one game, last known cached value is returned if
    available, else period="unknown".
  - Cache does NOT persist across process restarts.

P&L estimates:
  - For games with period="FT", user_pnl_estimate and ai_pnl_estimate are
    computed from bets fetched with today's game data (already queried from
    DB for today_data).  They are ON-THE-FLY estimates only — the official
    P&L written by the post-gambling flow may differ if edge cases arise.
  - For in-play games (period in "1H", "HT", "2H") with non-null scores,
    estimates are also computed treating the current scoreline as final.
    These are flagged with pnl_estimate_is_live=true so the frontend can
    style them differently from settled FT values.
  - The endpoint fetches today's bets from the DB once per request (not
    cached separately) so estimates stay current after bet edits.
  - If no bet exists for a bettor on a finished or live game, that bettor's
    field is null in the response.
"""
from __future__ import annotations

import asyncio
import logging
import time
from typing import Any, Optional

import requests

from fastapi import APIRouter
from soccersmartbet.db import get_cursor
from soccersmartbet.post_games_flow.pnl_calculator import compute_bet_pnl_estimate
from soccersmartbet.pre_gambling_flow.tools.fotmob_client import _generate_xmas_header
from soccersmartbet.utils.timezone import now_isr, today_isr

logger = logging.getLogger(__name__)

router = APIRouter()

# ---------------------------------------------------------------------------
# In-process cache: (game_id, fotmob_match_id) → (payload_dict, cached_at_epoch)
# ---------------------------------------------------------------------------
_LIVE_CACHE: dict[tuple[int, int], tuple[dict, float]] = {}
_CACHE_TTL_SECONDS = 30.0

# ---------------------------------------------------------------------------
# FotMob helpers (sync, runs in asyncio.to_thread)
# ---------------------------------------------------------------------------

_FOTMOB_TIMEOUT = 8  # seconds per match fetch


def _fetch_match_raw(fotmob_match_id: int) -> Optional[dict]:
    """Synchronous FotMob match fetch.  Returns raw JSON or None on failure."""
    url = f"https://www.fotmob.com/api/data/match?id={fotmob_match_id}"
    try:
        headers = {
            "x-mas": _generate_xmas_header(url),
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
            ),
        }
        resp = requests.get(url, headers=headers, timeout=_FOTMOB_TIMEOUT)
        resp.raise_for_status()
        return resp.json()
    except Exception as exc:
        logger.warning("FotMob match fetch id=%d failed: %s", fotmob_match_id, exc)
        return None


def _derive_period(data: dict) -> str:
    """Derive the period string from a FotMob match response.

    Args:
        data: Parsed JSON from /api/data/match?id=.

    Returns:
        One of: "pre", "1H", "HT", "2H", "FT", "unknown".
    """
    try:
        status = data.get("status") or {}
        started: bool = bool(status.get("started"))
        finished: bool = bool(status.get("finished"))
        ongoing: bool = bool(status.get("ongoing"))
        reason_short: str = (status.get("reason") or {}).get("short") or ""
        halfs = data.get("halfs") or {}
        second_half_started: str = halfs.get("secondHalfStarted") or ""

        if not started:
            return "pre"
        if finished:
            return "FT"
        if reason_short == "HT":
            return "HT"
        if ongoing and second_half_started == "":
            return "1H"
        if ongoing and second_half_started != "":
            return "2H"
        # Started but not yet ongoing and not HT/FT — treat as pre
        return "pre"
    except Exception:
        return "unknown"


def _parse_game_entry(game_id: int, fotmob_match_id: int, data: dict) -> dict:
    """Build a single game entry dict from a FotMob match response."""
    period = _derive_period(data)
    finished = period == "FT"

    try:
        home_score: Optional[int] = data.get("home", {}).get("score")
        away_score: Optional[int] = data.get("away", {}).get("score")
    except Exception:
        home_score = None
        away_score = None

    # Coerce to int if possible (FotMob sometimes returns them as strings)
    if home_score is not None:
        try:
            home_score = int(home_score)
        except (ValueError, TypeError):
            home_score = None
    if away_score is not None:
        try:
            away_score = int(away_score)
        except (ValueError, TypeError):
            away_score = None

    try:
        minute: Optional[str] = (
            (data.get("status") or {}).get("liveTime") or {}
        ).get("short") or None
    except Exception:
        minute = None

    return {
        "game_id": game_id,
        "fotmob_match_id": fotmob_match_id,
        "home_score": home_score,
        "away_score": away_score,
        "period": period,
        "minute": minute if not finished else None,
        "finished": finished,
    }


async def _get_game_live(game_id: int, fotmob_match_id: int) -> dict:
    """Return a live entry for one game, with cache and graceful degradation.

    - Checks the 30-second cache first.
    - Finished games are served from cache indefinitely (no re-poll).
    - On FotMob failure, returns last known cache value or period="unknown".
    """
    cache_key = (game_id, fotmob_match_id)
    now_epoch = time.monotonic()

    # Cache hit
    if cache_key in _LIVE_CACHE:
        cached_entry, cached_at = _LIVE_CACHE[cache_key]
        # Serve from cache if: still within TTL, OR game is finished
        if cached_entry.get("finished") or (now_epoch - cached_at) < _CACHE_TTL_SECONDS:
            return cached_entry

    # Cache miss (or stale) — fetch from FotMob
    data = await asyncio.to_thread(_fetch_match_raw, fotmob_match_id)

    if data is None:
        # Degraded: return stale cache if available, else unknown
        if cache_key in _LIVE_CACHE:
            stale_entry, _ = _LIVE_CACHE[cache_key]
            logger.debug(
                "FotMob fetch failed for game_id=%d; returning stale cache", game_id
            )
            return stale_entry
        return {
            "game_id": game_id,
            "fotmob_match_id": fotmob_match_id,
            "home_score": None,
            "away_score": None,
            "period": "unknown",
            "minute": None,
            "finished": False,
        }

    entry = _parse_game_entry(game_id, fotmob_match_id, data)
    _LIVE_CACHE[cache_key] = (entry, now_epoch)
    return entry


# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------


def _fetch_today_games() -> list[dict]:
    """Return today's games that have a fotmob_match_id."""
    today = today_isr()
    with get_cursor(commit=False) as cur:
        cur.execute(
            """
            SELECT game_id, fotmob_match_id
            FROM games
            WHERE match_date = %s
              AND fotmob_match_id IS NOT NULL
            ORDER BY game_id
            """,
            (today,),
        )
        rows = cur.fetchall()
    return [{"game_id": r[0], "fotmob_match_id": r[1]} for r in rows]


def _fetch_today_bets() -> dict[tuple[int, str], dict]:
    """Return today's bets keyed by (game_id, bettor).

    Only bets for today's games are returned. Values contain the fields
    needed for on-the-fly P&L estimation.
    """
    today = today_isr()
    with get_cursor(commit=False) as cur:
        cur.execute(
            """
            SELECT b.game_id, b.bettor, b.prediction, b.stake, b.odds, b.pnl
            FROM bets b
            JOIN games g ON g.game_id = b.game_id
            WHERE g.match_date = %s
            """,
            (today,),
        )
        rows = cur.fetchall()

    result: dict[tuple[int, str], dict] = {}
    for game_id, bettor, prediction, stake, odds, pnl in rows:
        result[(game_id, bettor)] = {
            "prediction": prediction,
            "stake": float(stake),
            "odds": float(odds),
            "settled_pnl": float(pnl) if pnl is not None else None,
        }
    return result


# ---------------------------------------------------------------------------
# Route
# ---------------------------------------------------------------------------


@router.get("/api/today/live")
async def today_live() -> dict[str, Any]:
    """Return live scores for today's fotmob-mapped games.

    Each game entry includes:
      - game_id, fotmob_match_id, home_score, away_score
      - period: "pre" | "1H" | "HT" | "2H" | "FT" | "unknown"
      - minute: e.g. "59'" while in-play, null otherwise
      - finished: bool
      - user_pnl_estimate / ai_pnl_estimate: float or null
        (populated for finished games and for in-play games with known
        scores; for FT the settled value is used when bets.pnl is set)
      - pnl_estimate_is_live: bool — true when the estimate is based on
        a current in-play scoreline rather than a confirmed final result

    Games without fotmob_match_id are not included.
    """
    # Fetch today's mapped games and all today's bets in parallel
    today_games, bets_by_key = _fetch_today_games(), _fetch_today_bets()

    if not today_games:
        return {
            "as_of_isr": now_isr().isoformat(),
            "games": [],
        }

    # Fan-out: fetch live data for every game concurrently
    tasks = [
        _get_game_live(g["game_id"], g["fotmob_match_id"])
        for g in today_games
    ]
    entries: list[dict] = list(await asyncio.gather(*tasks))

    # Attach P&L estimates for finished games and in-play games with known scores
    _LIVE_PERIODS = frozenset({"1H", "HT", "2H"})
    for entry in entries:
        gid = entry["game_id"]
        entry["user_pnl_estimate"] = None
        entry["ai_pnl_estimate"] = None

        is_finished = entry["finished"]
        is_inplay = entry["period"] in _LIVE_PERIODS
        has_scores = (
            entry["home_score"] is not None and entry["away_score"] is not None
        )

        # Populate pnl_estimate_is_live: true for in-play, false for FT
        if is_finished:
            entry["pnl_estimate_is_live"] = False
        elif is_inplay and has_scores:
            entry["pnl_estimate_is_live"] = True
        else:
            entry["pnl_estimate_is_live"] = False

        if (is_finished or is_inplay) and has_scores:
            for bettor in ("user", "ai"):
                bet = bets_by_key.get((gid, bettor))
                if bet is None:
                    continue
                # For finished games: if post-gambling flow already settled
                # this bet, use that official value (not applicable to live).
                if is_finished and bet["settled_pnl"] is not None:
                    entry[f"{bettor}_pnl_estimate"] = bet["settled_pnl"]
                else:
                    estimate = compute_bet_pnl_estimate(
                        prediction=bet["prediction"],
                        stake=bet["stake"],
                        odds=bet["odds"],
                        home_score=entry["home_score"],
                        away_score=entry["away_score"],
                    )
                    entry[f"{bettor}_pnl_estimate"] = estimate

    return {
        "as_of_isr": now_isr().isoformat(),
        "games": entries,
    }
