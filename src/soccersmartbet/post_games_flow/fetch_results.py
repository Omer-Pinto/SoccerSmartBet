"""
Fetch Results node for the Post-Games Flow.

Uses FotMob match data (preferred, via fotmob_match_id) or falls back to
overviewFixtures (team-data search by opponent + date) to find match results.

Retry policy
------------
Each FotMob call is wrapped by ``_call_with_retry``:
  - 3 attempts total (configurable via FOTMOB_MAX_RETRIES).
  - Exponential backoff: 1 s → 3 s → 8 s between attempts.
  - Backoff lives here, not in fotmob_client, so only the post-games flow
    carries its own SLA without affecting other callers.
  - If all attempts return None the flow falls back to the team-fixtures path
    (when a fotmob_match_id exists).  Only when both paths exhaust does the
    game count as a transient_failure and trigger a loud WARNING.
"""

from __future__ import annotations

import logging
import time
from typing import Callable, TypeVar

from soccersmartbet.db import get_conn, get_cursor
from soccersmartbet.post_games_flow.state import PostGamesState, SkippedGame
from soccersmartbet.pre_gambling_flow.tools.fotmob_client import get_fotmob_client
from soccersmartbet.team_registry import resolve_team

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Retry configuration
# ---------------------------------------------------------------------------

FOTMOB_MAX_RETRIES: int = 3
# Delays in seconds between successive attempts: [1, 3, 8]
_RETRY_DELAYS: list[float] = [1.0, 3.0, 8.0]

T = TypeVar("T")


def _sleep(seconds: float) -> None:  # pragma: no cover — patched in tests
    """Thin wrapper around time.sleep so tests can swap it out."""
    time.sleep(seconds)


def _call_with_retry(fn: Callable[[], T | None], label: str) -> tuple[T | None, bool]:
    """Call ``fn`` up to FOTMOB_MAX_RETRIES times, returning on first non-None result.

    Args:
        fn: Zero-argument callable that returns a value or None on failure.
        label: Human-readable label for log messages (e.g. "game_id=5 match_id=123").

    Returns:
        A tuple (result, exhausted) where:
          - result is the first non-None return value, or None if all attempts failed.
          - exhausted is True only when all attempts returned None (transient failure).
    """
    last_exc: Exception | None = None
    for attempt in range(1, FOTMOB_MAX_RETRIES + 1):
        try:
            result = fn()
        except Exception as exc:  # fotmob_client already swallows, but belt-and-suspenders
            last_exc = exc
            result = None

        if result is not None:
            if attempt > 1:
                logger.info("fetch_results: %s succeeded on attempt %d", label, attempt)
            return result, False

        if attempt < FOTMOB_MAX_RETRIES:
            delay = _RETRY_DELAYS[attempt - 1]
            logger.debug(
                "fetch_results: %s attempt %d/%d returned None, retrying in %.0fs",
                label,
                attempt,
                FOTMOB_MAX_RETRIES,
                delay,
            )
            _sleep(delay)

    err_str = str(last_exc) if last_exc else "returned None"
    logger.warning(
        "fetch_results: %s exhausted FotMob retries — last error=%s",
        label,
        err_str,
    )
    return None, True


# ---------------------------------------------------------------------------
# SQL
# ---------------------------------------------------------------------------

_FETCH_GAMES_SQL = """
SELECT game_id, home_team, away_team, match_date, fotmob_match_id
FROM games
WHERE game_id = ANY(%(game_ids)s)
ORDER BY game_id
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


# ---------------------------------------------------------------------------
# Pure helpers
# ---------------------------------------------------------------------------


def _determine_outcome(home_score: int, away_score: int) -> str:
    if home_score > away_score:
        return "1"
    if away_score > home_score:
        return "2"
    return "x"


def _parse_score(raw: object) -> int | None:
    """Coerce a raw FotMob score value to int, or None when not representable.

    Matches the semantics used in ``webapp/routes/live.py``:
      - Numeric / string-numeric → int.
      - None / non-numeric → None (signals "data not yet available").
    """
    if raw is None:
        return None
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


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


# ---------------------------------------------------------------------------
# Per-game fetch strategies
# ---------------------------------------------------------------------------


def _fetch_via_match_id(
    client,
    game_id: int,
    game: dict,
    fotmob_match_id: int,
    cur,
) -> tuple[bool, bool, int | None, int | None, str | None]:
    """Attempt to fetch and settle a game using its fotmob_match_id.

    Args:
        client: FotMobClient instance.
        game_id: DB primary key.
        game: Dict with home_team/away_team/match_date.
        fotmob_match_id: The FotMob match ID.
        cur: Open DB cursor (for the UPDATE).

    Returns:
        (settled, transient_failure, home_score, away_score, outcome):
          - settled=True → game was finished and updated; scores/outcome populated.
          - settled=False, transient_failure=False → game not finished yet (normal).
          - settled=False, transient_failure=True → all retries exhausted;
            caller MUST fall back to team-fixtures before marking as failure.
          - scores/outcome are None when settled=False.
    """
    label = f"game_id={game_id} match_id={fotmob_match_id}"
    data, exhausted = _call_with_retry(
        lambda: client.get_match_data(fotmob_match_id),
        label,
    )

    if exhausted:
        # Signal the caller to try the team-fixtures fallback.
        return False, True, None, None, None

    if data is None:
        # Unreachable in normal operation (exhausted covers None), but be safe.
        return False, True, None, None, None

    status = data.get("status") or {}
    if not status.get("finished", False):
        logger.info("fetch_results: game_id=%d not finished yet (match_id path)", game_id)
        return False, False, None, None, None

    home_score = _parse_score(data.get("home", {}).get("score"))
    away_score = _parse_score(data.get("away", {}).get("score"))

    # FotMob returned finished=true but score is None — abandoned / awarded match.
    # Treat as transient_failure so the operator notices rather than settling 0-0.
    if home_score is None or away_score is None:
        logger.warning(
            "fetch_results: game_id=%d (match_id path) finished=true but score is null"
            " — treating as transient_failure",
            game_id,
        )
        return False, True, None, None, None

    outcome = _determine_outcome(home_score, away_score)
    cur.execute(_UPDATE_GAME_SQL, {
        "home_score": home_score,
        "away_score": away_score,
        "outcome": outcome,
        "game_id": game_id,
    })
    logger.info(
        "fetch_results: game_id=%d (match_id path) %s %d-%d %s outcome=%s",
        game_id, game["home_team"], home_score, away_score, game["away_team"], outcome,
    )
    return True, False, home_score, away_score, outcome


def _fetch_via_team_fixtures(
    client,
    game_id: int,
    game: dict,
    cur,
) -> tuple[bool, bool, int | None, int | None, str | None]:
    """Fallback: fetch via home-team overviewFixtures search.

    Returns:
        (settled, transient_failure, home_score, away_score, outcome) — same
        semantics as ``_fetch_via_match_id``.
    """
    team_label = f"game_id={game_id} team={game['home_team']}"

    fotmob_id = _get_fotmob_id(cur, client, game["home_team"])
    if not fotmob_id:
        logger.warning("fetch_results: no FotMob ID for %s", game["home_team"])
        return False, False, None, None, None  # permanent skip — not a transient failure

    data, exhausted = _call_with_retry(
        lambda: client.get_team_data(fotmob_id),
        team_label,
    )

    if exhausted:
        return False, True, None, None, None

    if data is None:
        return False, True, None, None, None

    fixtures = data.get("overview", {}).get("overviewFixtures", [])
    match = _find_match_in_fixtures(fixtures, game["away_team"], game["match_date"])

    if not match:
        logger.warning(
            "fetch_results: game_id=%d no fixture found for %s vs %s on %s",
            game_id, game["home_team"], game["away_team"], game["match_date"],
        )
        return False, False, None, None, None  # fixture not found — not a transient failure

    if not match.get("status", {}).get("finished", False):
        logger.info("fetch_results: game_id=%d not finished yet (team-fixtures path)", game_id)
        return False, False, None, None, None

    home_score = _parse_score(match.get("home", {}).get("score"))
    away_score = _parse_score(match.get("away", {}).get("score"))

    # Finished but null scores — treat as transient_failure (same logic as match_id path).
    if home_score is None or away_score is None:
        logger.warning(
            "fetch_results: game_id=%d (team-fixtures path) finished=true but score is null"
            " — treating as transient_failure",
            game_id,
        )
        return False, True, None, None, None

    outcome = _determine_outcome(home_score, away_score)

    cur.execute(_UPDATE_GAME_SQL, {
        "home_score": home_score,
        "away_score": away_score,
        "outcome": outcome,
        "game_id": game_id,
    })
    logger.info(
        "fetch_results: game_id=%d (team-fixtures path) %s %d-%d %s outcome=%s",
        game_id, game["home_team"], home_score, away_score, game["away_team"], outcome,
    )
    return True, False, home_score, away_score, outcome


# ---------------------------------------------------------------------------
# LangGraph node
# ---------------------------------------------------------------------------


def fetch_results(state: PostGamesState) -> dict:
    """LangGraph node: fetch match results via FotMob and persist to DB.

    For each game with a non-null fotmob_match_id the direct match endpoint is
    tried first (preferred).  When that path exhausts its retries *or* returns
    a broken response shape the function falls through to the team-fixtures
    fallback (same path that worked for 20+ days before fotmob_match_id was
    added).  Only when BOTH paths exhaust does the game count as a
    transient_failure.

    When fotmob_match_id IS NULL, the team-fixtures path is used directly.

    When the match-id path returns finished=false authoritatively, no fallback
    is attempted — the game is genuinely ongoing.

    Each FotMob call is retried up to FOTMOB_MAX_RETRIES times with
    exponential backoff (_RETRY_DELAYS).  Exhausted retries are counted
    separately from games that genuinely have not finished yet, so callers
    (and operators) can distinguish "transient FotMob failure" from "game
    not done".
    """
    game_ids: list[int] = state["game_ids"]
    logger.info("fetch_results: processing %d game(s)", len(game_ids))

    with get_cursor(commit=False) as cur:
        cur.execute(_FETCH_GAMES_SQL, {"game_ids": game_ids})
        rows = cur.fetchall()

    db_games: dict[int, dict] = {
        row[0]: {
            "home_team": row[1],
            "away_team": row[2],
            "match_date": str(row[3]),
            "fotmob_match_id": row[4],  # may be None
        }
        for row in rows
    }

    client = get_fotmob_client()
    results: dict[int, dict] = {}
    skipped_games: list[SkippedGame] = []
    transient_failure_count: int = 0

    with get_conn() as conn:
        with conn.cursor() as cur:
            for game_id, game in db_games.items():
                fotmob_match_id: int | None = game["fotmob_match_id"]
                settled = False
                transient = False
                home_score: int | None = None
                away_score: int | None = None
                outcome: str | None = None

                if fotmob_match_id is not None:
                    settled, transient, home_score, away_score, outcome = _fetch_via_match_id(
                        client, game_id, game, fotmob_match_id, cur
                    )
                    # transient here means retries exhausted OR score=null — fall through
                    # to team-fixtures.  NOT-finished (transient=False, settled=False) is
                    # authoritative: do NOT fall back.
                    if transient:
                        logger.info(
                            "fetch_results: game_id=%d match_id path failed — falling back"
                            " to team-fixtures",
                            game_id,
                        )
                        settled, transient, home_score, away_score, outcome = _fetch_via_team_fixtures(
                            client, game_id, game, cur
                        )

                else:
                    # No fotmob_match_id: go straight to team-fixtures.
                    settled, transient, home_score, away_score, outcome = _fetch_via_team_fixtures(
                        client, game_id, game, cur
                    )

                if transient:
                    transient_failure_count += 1
                    skipped_games.append(SkippedGame(
                        game_id=game_id,
                        home_team=game["home_team"],
                        away_team=game["away_team"],
                        match_date=game["match_date"],
                        reason="FotMob retries exhausted (transient failure)",
                        transient=True,
                    ))
                    continue

                if not settled:
                    # Game not finished or no fixture found — normal skip
                    skipped_games.append(SkippedGame(
                        game_id=game_id,
                        home_team=game["home_team"],
                        away_team=game["away_team"],
                        match_date=game["match_date"],
                        reason="not finished or no FotMob fixture found",
                        transient=False,
                    ))
                    continue

                # settled=True — use the locally captured scores; no extra SELECT needed.
                results[game_id] = {
                    "home_score": home_score,
                    "away_score": away_score,
                    "outcome": outcome,
                }

        conn.commit()  # MANDATORY: persist game scores/outcomes

    matched = len(results)
    total = len(game_ids)
    not_finished = total - matched - transient_failure_count
    summary_msg = (
        "fetch_results: matched %d/%d game(s) | not_finished=%d | transient_failures=%d"
    )
    summary_args = (matched, total, not_finished, transient_failure_count)
    if transient_failure_count > 0:
        logger.warning(summary_msg, *summary_args)
    else:
        logger.info(summary_msg, *summary_args)

    return {"results": results, "skipped_games": skipped_games}
