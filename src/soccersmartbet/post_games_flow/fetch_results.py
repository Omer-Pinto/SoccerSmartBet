"""
Fetch Results node for the Post-Games Flow.

Uses FotMob overviewFixtures to find specific match results by opponent + date.
"""

from __future__ import annotations

import logging
import os

import psycopg2

from soccersmartbet.post_games_flow.state import PostGamesState, SkippedGame
from soccersmartbet.pre_gambling_flow.tools.fotmob_client import get_fotmob_client
from soccersmartbet.team_registry import resolve_team

logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL")

_FETCH_GAMES_SQL = """
SELECT game_id, home_team, away_team, match_date
FROM games
WHERE game_id = ANY(%(game_ids)s)
"""

_FETCH_FOTMOB_ID_SQL = """
SELECT fotmob_id FROM teams WHERE canonical_name = %(name)s AND fotmob_id IS NOT NULL
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


def _get_fotmob_id(cur, client, team_name: str) -> int | None:
    canonical = resolve_team(team_name)
    if canonical:
        cur.execute(_FETCH_FOTMOB_ID_SQL, {"name": canonical})
        row = cur.fetchone()
        if row:
            return row[0]
    found = client.find_team(team_name)
    return found["id"] if found else None


def _find_match_in_fixtures(fixtures: list[dict], opponent_name: str, match_date: str) -> dict | None:
    """Find a specific match by opponent and date in overviewFixtures."""
    opp_resolved = resolve_team(opponent_name)
    for f in fixtures:
        utc_time = f.get("status", {}).get("utcTime", "")
        if match_date not in utc_time:
            continue
        fixture_opp = resolve_team(f.get("opponent", {}).get("name", ""))
        if fixture_opp == opp_resolved:
            return f
    return None


def fetch_results(state: PostGamesState) -> dict:
    """LangGraph node: fetch match results via FotMob and persist to DB.

    For each game, looks up the home team's overviewFixtures, finds the
    specific match by opponent + date, and reads the score.
    """
    game_ids: list[int] = state["game_ids"]
    logger.info("fetch_results: processing %d game(s)", len(game_ids))

    conn = psycopg2.connect(DATABASE_URL)
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(_FETCH_GAMES_SQL, {"game_ids": game_ids})
                rows = cur.fetchall()
    finally:
        conn.close()

    db_games: dict[int, dict] = {
        row[0]: {"home_team": row[1], "away_team": row[2], "match_date": str(row[3])}
        for row in rows
    }

    client = get_fotmob_client()
    results: dict[int, dict] = {}
    skipped_games: list[SkippedGame] = []

    conn = psycopg2.connect(DATABASE_URL)
    try:
        with conn:
            with conn.cursor() as cur:
                for game_id, game in db_games.items():
                    fotmob_id = _get_fotmob_id(cur, client, game["home_team"])
                    if not fotmob_id:
                        logger.warning("fetch_results: no FotMob ID for %s", game["home_team"])
                        skipped_games.append(SkippedGame(
                            game_id=game_id,
                            home_team=game["home_team"],
                            away_team=game["away_team"],
                            match_date=game["match_date"],
                            reason="no FotMob team ID for home team",
                        ))
                        continue

                    team_data = client.get_team_data(fotmob_id)
                    if not team_data:
                        logger.warning("fetch_results: no FotMob data for %s", game["home_team"])
                        skipped_games.append(SkippedGame(
                            game_id=game_id,
                            home_team=game["home_team"],
                            away_team=game["away_team"],
                            match_date=game["match_date"],
                            reason="FotMob returned no team data",
                        ))
                        continue

                    fixtures = team_data.get("overview", {}).get("overviewFixtures", [])
                    match = _find_match_in_fixtures(fixtures, game["away_team"], game["match_date"])

                    if not match:
                        logger.warning(
                            "fetch_results: game_id=%d no fixture found for %s vs %s on %s",
                            game_id, game["home_team"], game["away_team"], game["match_date"],
                        )
                        skipped_games.append(SkippedGame(
                            game_id=game_id,
                            home_team=game["home_team"],
                            away_team=game["away_team"],
                            match_date=game["match_date"],
                            reason="no FotMob fixture match",
                        ))
                        continue

                    if not match.get("status", {}).get("finished", False):
                        logger.info("fetch_results: game_id=%d not finished yet", game_id)
                        continue

                    home_score = match.get("home", {}).get("score", 0)
                    away_score = match.get("away", {}).get("score", 0)
                    outcome = _determine_outcome(home_score, away_score)

                    cur.execute(_UPDATE_GAME_SQL, {
                        "home_score": home_score,
                        "away_score": away_score,
                        "outcome": outcome,
                        "game_id": game_id,
                    })

                    results[game_id] = {
                        "home_score": home_score,
                        "away_score": away_score,
                        "outcome": outcome,
                    }
                    logger.info(
                        "fetch_results: game_id=%d %s %d-%d %s outcome=%s",
                        game_id, game["home_team"], home_score, away_score, game["away_team"], outcome,
                    )
    finally:
        conn.close()

    logger.info(
        "fetch_results: matched and updated %d/%d game(s), skipped %d",
        len(results), len(game_ids), len(skipped_games),
    )
    return {"results": results, "skipped_games": skipped_games}
