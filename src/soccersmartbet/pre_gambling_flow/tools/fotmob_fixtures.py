"""FotMob fixture-ID enrichment for today's games.

After games are inserted into the DB by persist_games, this module queries
FotMob's /api/data/leagues?id= endpoint per distinct league, fuzzy-matches
each game row by normalized team name + date, and writes the resolved
fotmob_match_id back to the games table.

Design decisions:
- Best-effort only: any FotMob failure is caught and logged; the flow continues.
- Uses FOTMOB_LEAGUES from fotmob_client so the league map is a single source
  of truth.
- Fuzzy match: normalize_team_name on both sides, then substring check before
  falling back to Levenshtein-like scoring (token overlap ratio).
- UTC match time from FotMob is converted to ISR date for the date filter;
  the endpoint returns matches across a ±few-day window so date gating is
  essential.
"""

from __future__ import annotations

import logging
from datetime import date
from typing import Optional

import requests

from soccersmartbet.db import get_conn
from soccersmartbet.pre_gambling_flow.tools.fotmob_client import (
    FOTMOB_LEAGUES,
    _generate_xmas_header,
)
from soccersmartbet.team_registry import normalize_team_name
from soccersmartbet.utils.timezone import utc_to_isr

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

_TIMEOUT = 10


def _fotmob_get(url: str) -> Optional[dict]:
    """GET a FotMob URL with the x-mas auth header.  Returns None on failure."""
    try:
        headers = {
            "x-mas": _generate_xmas_header(url),
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
            ),
        }
        resp = requests.get(url, headers=headers, timeout=_TIMEOUT)
        resp.raise_for_status()
        return resp.json()
    except Exception as exc:
        logger.warning("FotMob GET %s failed: %s", url, exc)
        return None


def _score_match(
    norm_home: str,
    norm_away: str,
    fotmob_home: str,
    fotmob_away: str,
) -> float:
    """Return a similarity score in [0, 1] for the team-name pair.

    Uses substring containment (cheap) then token overlap ratio (fallback).
    A score >= 0.5 is treated as a match; the caller picks the best candidate.
    """
    fh = normalize_team_name(fotmob_home)
    fa = normalize_team_name(fotmob_away)

    # Exact after normalization
    if norm_home == fh and norm_away == fa:
        return 1.0

    # Substring containment in both directions for each side
    def _substr_score(a: str, b: str) -> float:
        if not a or not b:
            return 0.0
        if a == b:
            return 1.0
        if a in b or b in a:
            return 0.8
        # Token overlap
        ta = set(a.split())
        tb = set(b.split())
        if not ta or not tb:
            return 0.0
        overlap = len(ta & tb)
        return overlap / max(len(ta), len(tb))

    home_sim = _substr_score(norm_home, fh)
    away_sim = _substr_score(norm_away, fa)
    return (home_sim + away_sim) / 2.0


def _fetch_league_matches(league_id: int) -> list[dict]:
    """Fetch allMatches[] for a FotMob league.

    Returns a flat list of dicts with keys:
        id, home_name, away_name, utc_time
    Returns [] on any failure.
    """
    url = f"https://www.fotmob.com/api/data/leagues?id={league_id}"
    data = _fotmob_get(url)
    if not data:
        return []

    # The allMatches array is at data["fixtures"]["allMatches"]
    try:
        raw: list[dict] = data["fixtures"]["allMatches"]
    except (KeyError, TypeError):
        logger.warning("FotMob league %d: unexpected shape — missing fixtures.allMatches", league_id)
        return []

    result = []
    for m in raw:
        try:
            result.append(
                {
                    "id": int(m["id"]),
                    "home_name": m.get("home", {}).get("name") or "",
                    "away_name": m.get("away", {}).get("name") or "",
                    "utc_time": m.get("status", {}).get("utcTime") or "",
                }
            )
        except Exception:
            continue
    return result


def _resolve_fotmob_id(
    home_team: str,
    away_team: str,
    match_date: date,
    league_name: str,
) -> Optional[int]:
    """Try to find a FotMob match ID for the given game.

    Looks up the FotMob league ID from FOTMOB_LEAGUES (case-insensitive),
    fetches all matches, then picks the best fuzzy match on the right date.

    Args:
        home_team: Home team name as stored in the games table.
        away_team: Away team name as stored in the games table.
        match_date: The game date (ISR).
        league_name: Canonical league name as stored in the games table.

    Returns:
        FotMob match ID (int) if a confident match is found, else None.
    """
    # Map league_name to FotMob league_id
    league_id: Optional[int] = None
    league_lower = league_name.strip().lower()
    for name, lid in FOTMOB_LEAGUES.items():
        if name.lower() == league_lower:
            league_id = lid
            break

    if league_id is None:
        logger.warning(
            "FotMob enrichment: no FOTMOB_LEAGUES entry for league '%s' — skipping",
            league_name,
        )
        return None

    candidates = _fetch_league_matches(league_id)
    if not candidates:
        logger.warning(
            "FotMob enrichment: no matches returned for league %s (id=%d)",
            league_name,
            league_id,
        )
        return None

    norm_home = normalize_team_name(home_team)
    norm_away = normalize_team_name(away_team)

    best_score = 0.0
    best_id: Optional[int] = None

    for m in candidates:
        # Gate by date: convert FotMob UTC time to ISR date
        if m["utc_time"]:
            try:
                match_date_fotmob = utc_to_isr(m["utc_time"]).date()
                if match_date_fotmob != match_date:
                    continue
            except Exception:
                pass  # If parse fails, don't filter out — try to match anyway

        score = _score_match(norm_home, norm_away, m["home_name"], m["away_name"])
        if score > best_score:
            best_score = score
            best_id = m["id"]

    # Only accept matches with at least moderate confidence
    if best_score >= 0.5 and best_id is not None:
        logger.info(
            "FotMob enrichment: matched %s vs %s → fotmob_id=%d (score=%.2f)",
            home_team,
            away_team,
            best_id,
            best_score,
        )
        return best_id

    logger.warning(
        "FotMob enrichment: no confident match for %s vs %s in league %s "
        "(best_score=%.2f on date %s)",
        home_team,
        away_team,
        league_name,
        best_score,
        match_date,
    )
    return None


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def enrich_games_with_fotmob_ids(game_ids: list[int]) -> None:
    """Best-effort: write fotmob_match_id for each game in game_ids.

    Fetches each game row from the DB, calls FotMob per distinct league,
    and UPDATEs fotmob_match_id where a match is found.  Unmatched games
    are left with fotmob_match_id = NULL.

    Exceptions inside any per-game lookup are caught and logged so the
    function never raises.  A top-level exception (e.g. DB failure) is also
    caught so the calling flow continues regardless.

    Args:
        game_ids: List of game_id primary keys to enrich.
    """
    if not game_ids:
        return

    logger.info("FotMob enrichment: starting for %d game(s)", len(game_ids))

    try:
        # Fetch the game rows we need to enrich
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT game_id, home_team, away_team, match_date, league
                    FROM games
                    WHERE game_id = ANY(%s)
                      AND fotmob_match_id IS NULL
                    """,
                    (game_ids,),
                )
                rows = cur.fetchall()

        if not rows:
            logger.info("FotMob enrichment: all games already have fotmob_match_id, skipping")
            return

        # Deduplicate FotMob calls per league: fetch each league once and
        # cache the result for all games in the same league.
        _league_cache: dict[int, list[dict]] = {}

        updates: list[tuple[int, int]] = []  # (fotmob_match_id, game_id)

        for game_id, home_team, away_team, match_date, league in rows:
            try:
                fotmob_id = _resolve_fotmob_id(home_team, away_team, match_date, league)
                if fotmob_id is not None:
                    updates.append((fotmob_id, game_id))
            except Exception as exc:
                logger.warning(
                    "FotMob enrichment: error resolving game_id=%d (%s vs %s): %s",
                    game_id,
                    home_team,
                    away_team,
                    exc,
                )

        if not updates:
            logger.info("FotMob enrichment: no IDs resolved for %d game(s)", len(rows))
            return

        # Write resolved IDs to DB
        with get_conn() as conn:
            with conn.cursor() as cur:
                for fotmob_match_id, game_id in updates:
                    cur.execute(
                        "UPDATE games SET fotmob_match_id = %s WHERE game_id = %s",
                        (fotmob_match_id, game_id),
                    )
            conn.commit()

        logger.info(
            "FotMob enrichment: wrote fotmob_match_id for %d/%d game(s)",
            len(updates),
            len(rows),
        )

    except Exception as exc:
        logger.exception("FotMob enrichment: unexpected error: %s", exc)
