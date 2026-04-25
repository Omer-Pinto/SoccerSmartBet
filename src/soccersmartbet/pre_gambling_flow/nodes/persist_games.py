"""Persist Games node for the Pre-Gambling Flow.

Inserts the games selected by smart_game_picker into the PostgreSQL ``games``
table and returns the DB-assigned game IDs so downstream nodes can reference
them by real primary keys.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

from soccersmartbet.db import get_conn
from soccersmartbet.pre_gambling_flow.state import GameContext, Phase, PreGamblingState

# ---------------------------------------------------------------------------
# League name normalisation
# ---------------------------------------------------------------------------
# Maps every known raw variant (lower-case) from football-data.org and the LLM
# to the canonical display name stored in the DB.  This prevents the DB from
# accumulating aliases like "Primera Division" alongside "La Liga" that are the
# same competition.  Add entries here whenever a new alias appears.
_LEAGUE_NAME_ALIASES: dict[str, str] = {
    "primera division": "La Liga",
    "primera división": "La Liga",
    "laliga": "La Liga",
    "la liga": "La Liga",
    "spanish la liga": "La Liga",
    "spain primera division": "La Liga",
}


def _normalise_league(name: str) -> str:
    """Return the canonical league name for *name*, or *name* unchanged if unknown."""
    return _LEAGUE_NAME_ALIASES.get(name.strip().lower(), name)

_INSERT_SQL = """
INSERT INTO games (
    match_date,
    kickoff_time,
    home_team,
    away_team,
    league,
    venue,
    home_win_odd,
    away_win_odd,
    draw_odd,
    status
)
VALUES (
    %(match_date)s,
    %(kickoff_time)s,
    %(home_team)s,
    %(away_team)s,
    %(league)s,
    %(venue)s,
    %(home_win_odd)s,
    %(away_win_odd)s,
    %(draw_odd)s,
    'selected'
)
RETURNING game_id
"""

# Deferred import so fotmob_fixtures is only loaded when this node runs,
# keeping the import graph clean and test mocking straightforward.
def _enrich_with_fotmob(game_ids: list[int]) -> None:
    """Best-effort FotMob enrichment — never raises."""
    try:
        from soccersmartbet.pre_gambling_flow.tools.fotmob_fixtures import (  # noqa: PLC0415
            enrich_games_with_fotmob_ids,
        )
        enrich_games_with_fotmob_ids(game_ids)
    except Exception as exc:
        logger.warning("persist_games: FotMob enrichment skipped due to error: %s", exc)


def persist_games(state: PreGamblingState) -> dict[str, Any]:
    """LangGraph node: insert selected games into the DB and return real game IDs.

    Reads ``state["all_games"]`` (populated by smart_game_picker with
    ``game_id=0`` placeholders), inserts each row into the ``games`` table
    inside a single transaction, and returns the DB-assigned primary keys as
    ``games_to_analyze``.

    Args:
        state: Current Pre-Gambling Flow state.  Must contain ``all_games``.

    Returns:
        State update dict with ``games_to_analyze`` (list of real DB PKs) and
        ``phase`` set to ``Phase.ANALYZING``.
    """
    games: list[GameContext] = state["all_games"]
    logger.info("persist_games: inserting %d games", len(games))

    if not games:
        return {
            "games_to_analyze": [],
            "phase": Phase.ANALYZING,
        }

    game_ids: list[int] = []

    with get_conn() as conn:
        with conn.cursor() as cur:
            for game in games:
                cur.execute(
                    _INSERT_SQL,
                    {
                        "match_date": game["match_date"],
                        "kickoff_time": game["kickoff_time"],
                        "home_team": game["home_team"],
                        "away_team": game["away_team"],
                        "league": _normalise_league(game["league"]),
                        "venue": game["venue"],
                        "home_win_odd": game["home_win_odd"],
                        "away_win_odd": game["away_win_odd"],
                        "draw_odd": game["draw_odd"],
                    },
                )
                row = cur.fetchone()
                game_ids.append(row[0])
        conn.commit()

    logger.info("persist_games: inserted game_ids=%s", game_ids)

    # Best-effort: write fotmob_match_id for live-score polling.
    # Never blocks the flow; any failure is caught inside _enrich_with_fotmob.
    _enrich_with_fotmob(game_ids)

    return {
        "games_to_analyze": game_ids,
        "phase": Phase.ANALYZING,
    }
