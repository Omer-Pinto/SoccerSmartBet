"""
Fetch Results node for the Post-Games Flow.

Queries football-data.org for finished matches on the relevant date,
matches them to our DB games via team name resolution, and persists
scores and outcome back to the games table.
"""

from __future__ import annotations

import logging
import os
from typing import Any

import psycopg2
import requests

from soccersmartbet.post_games_flow.state import PostGamesState
from soccersmartbet.team_registry import resolve_team

logger = logging.getLogger(__name__)

FOOTBALL_DATA_API_KEY = os.getenv("FOOTBALL_DATA_API_KEY")
DATABASE_URL = os.getenv("DATABASE_URL")
BASE_URL = "https://api.football-data.org/v4"
TIMEOUT = 30

_FETCH_GAMES_SQL = """
SELECT game_id, home_team, away_team, match_date
FROM games
WHERE game_id = ANY(%(game_ids)s)
"""

_UPDATE_GAME_SQL = """
UPDATE games
SET home_score = %(home_score)s,
    away_score = %(away_score)s,
    outcome    = %(outcome)s,
    status     = 'completed'
WHERE game_id = %(game_id)s
"""


def _determine_outcome(home_score: int, away_score: int) -> str:
    if home_score > away_score:
        return "1"
    if away_score > home_score:
        return "2"
    return "x"


def _fetch_finished_matches(date_str: str) -> list[dict[str, Any]]:
    """Call football-data.org for finished matches on date_str."""
    if not FOOTBALL_DATA_API_KEY:
        raise RuntimeError("FOOTBALL_DATA_API_KEY not set in environment")

    response = requests.get(
        f"{BASE_URL}/matches",
        headers={"X-Auth-Token": FOOTBALL_DATA_API_KEY},
        params={"dateFrom": date_str, "dateTo": date_str, "status": "FINISHED"},
        timeout=TIMEOUT,
    )
    response.raise_for_status()
    return response.json().get("matches", [])


def fetch_results(state: PostGamesState) -> dict:
    """LangGraph node: fetch finished match scores and persist to DB.

    Steps:
      1. Load game rows (home_team, away_team, match_date) from games table.
      2. Call football-data.org FINISHED matches for each unique date.
      3. Match API entries to DB games via resolve_team normalization.
      4. Compute outcome and UPDATE games table (scores + status='completed').

    Args:
        state: Current PostGamesState with populated game_ids.

    Returns:
        dict with key "results" mapping game_id -> {home_score, away_score, outcome}.
    """
    game_ids: list[int] = state["game_ids"]
    logger.info("fetch_results: processing %d game(s)", len(game_ids))

    # --- 1. Load game rows from DB ---
    conn = psycopg2.connect(DATABASE_URL)
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(_FETCH_GAMES_SQL, {"game_ids": game_ids})
                rows = cur.fetchall()
    finally:
        conn.close()

    # {game_id: {"home_team": str, "away_team": str, "match_date": date}}
    db_games: dict[int, dict] = {
        row[0]: {"home_team": row[1], "away_team": row[2], "match_date": str(row[3])}
        for row in rows
    }

    # --- 2. Fetch API results grouped by date (one request per unique date) ---
    dates: set[str] = {g["match_date"] for g in db_games.values()}
    api_matches: list[dict[str, Any]] = []
    for date_str in dates:
        logger.info("fetch_results: fetching finished matches for %s", date_str)
        api_matches.extend(_fetch_finished_matches(date_str))

    # Build resolved index: canonical_name -> match dict
    # Key on both home and away resolved names for fast lookup
    resolved_api: list[tuple[str | None, str | None, dict]] = [
        (
            resolve_team(m.get("homeTeam", {}).get("name", "")),
            resolve_team(m.get("awayTeam", {}).get("name", "")),
            m,
        )
        for m in api_matches
    ]

    # --- 3. Match API entries to our DB games ---
    results: dict[int, dict] = {}

    conn = psycopg2.connect(DATABASE_URL)
    try:
        with conn:
            with conn.cursor() as cur:
                for game_id, game in db_games.items():
                    db_home_resolved = resolve_team(game["home_team"])
                    db_away_resolved = resolve_team(game["away_team"])

                    matched_match: dict | None = None
                    for api_home, api_away, match in resolved_api:
                        if api_home == db_home_resolved and api_away == db_away_resolved:
                            matched_match = match
                            break

                    if matched_match is None:
                        logger.warning(
                            "fetch_results: no API match found for game_id=%d (%s vs %s)",
                            game_id,
                            game["home_team"],
                            game["away_team"],
                        )
                        continue

                    score_info = matched_match.get("score", {})
                    full_time = score_info.get("fullTime", {})
                    home_score: int = full_time.get("home", 0) or 0
                    away_score: int = full_time.get("away", 0) or 0
                    outcome = _determine_outcome(home_score, away_score)

                    cur.execute(
                        _UPDATE_GAME_SQL,
                        {
                            "home_score": home_score,
                            "away_score": away_score,
                            "outcome": outcome,
                            "game_id": game_id,
                        },
                    )
                    results[game_id] = {
                        "home_score": home_score,
                        "away_score": away_score,
                        "outcome": outcome,
                    }
                    logger.info(
                        "fetch_results: game_id=%d %s %d-%d %s outcome=%s",
                        game_id,
                        game["home_team"],
                        home_score,
                        away_score,
                        game["away_team"],
                        outcome,
                    )
    finally:
        conn.close()

    logger.info("fetch_results: matched and updated %d/%d game(s)", len(results), len(game_ids))
    return {"results": results}
