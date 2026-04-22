"""Shared DB insert/update helpers for Pre-Gambling Flow intelligence agents.

Each function is self-contained: it opens a connection, runs a single
transaction, and closes the connection in a finally block.

Schema v2 — Wave 8B: structured fields plus JSONB bullet arrays.
"""

from __future__ import annotations

from psycopg.types.json import Jsonb

from soccersmartbet.db import get_cursor
from soccersmartbet.pre_gambling_flow.structured_outputs import (
    ExpertGameReport,
    GameReport,
    TeamReport,
)

# ---------------------------------------------------------------------------
# game_reports: H2H aggregate + weather + venue
# ---------------------------------------------------------------------------

_INSERT_GAME_REPORT_SQL = """
INSERT INTO game_reports (
    game_id,
    h2h_home_team,
    h2h_away_team,
    h2h_home_team_wins,
    h2h_away_team_wins,
    h2h_draws,
    h2h_total_meetings,
    h2h_bullets,
    weather_bullets,
    weather_cancellation_risk,
    venue
)
VALUES (
    %(game_id)s,
    %(h2h_home_team)s,
    %(h2h_away_team)s,
    %(h2h_home_team_wins)s,
    %(h2h_away_team_wins)s,
    %(h2h_draws)s,
    %(h2h_total_meetings)s,
    %(h2h_bullets)s,
    %(weather_bullets)s,
    %(weather_cancellation_risk)s,
    %(venue)s
)
ON CONFLICT (game_id) DO UPDATE SET
    h2h_home_team = EXCLUDED.h2h_home_team,
    h2h_away_team = EXCLUDED.h2h_away_team,
    h2h_home_team_wins = EXCLUDED.h2h_home_team_wins,
    h2h_away_team_wins = EXCLUDED.h2h_away_team_wins,
    h2h_draws = EXCLUDED.h2h_draws,
    h2h_total_meetings = EXCLUDED.h2h_total_meetings,
    h2h_bullets = EXCLUDED.h2h_bullets,
    weather_bullets = EXCLUDED.weather_bullets,
    weather_cancellation_risk = EXCLUDED.weather_cancellation_risk,
    venue = EXCLUDED.venue
RETURNING report_id
"""

# ---------------------------------------------------------------------------
# team_reports: structured facts + bullet arrays
# ---------------------------------------------------------------------------

_INSERT_TEAM_REPORT_SQL = """
INSERT INTO team_reports (
    game_id,
    team_name,
    recovery_days,
    form_streak,
    last_5_games,
    form_bullets,
    league_rank,
    league_points,
    league_matches_played,
    league_bullets,
    injury_bullets,
    news_bullets
)
VALUES (
    %(game_id)s,
    %(team_name)s,
    %(recovery_days)s,
    %(form_streak)s,
    %(last_5_games)s,
    %(form_bullets)s,
    %(league_rank)s,
    %(league_points)s,
    %(league_matches_played)s,
    %(league_bullets)s,
    %(injury_bullets)s,
    %(news_bullets)s
)
ON CONFLICT (game_id, team_name) DO UPDATE SET
    recovery_days = EXCLUDED.recovery_days,
    form_streak = EXCLUDED.form_streak,
    last_5_games = EXCLUDED.last_5_games,
    form_bullets = EXCLUDED.form_bullets,
    league_rank = EXCLUDED.league_rank,
    league_points = EXCLUDED.league_points,
    league_matches_played = EXCLUDED.league_matches_played,
    league_bullets = EXCLUDED.league_bullets,
    injury_bullets = EXCLUDED.injury_bullets,
    news_bullets = EXCLUDED.news_bullets
RETURNING report_id
"""

# ---------------------------------------------------------------------------
# expert_game_reports: bullet list stored as JSONB
# ---------------------------------------------------------------------------

_INSERT_EXPERT_REPORT_SQL = """
INSERT INTO expert_game_reports (game_id, expert_analysis)
VALUES (%(game_id)s, %(expert_analysis)s)
ON CONFLICT (game_id) DO UPDATE SET
    expert_analysis = EXCLUDED.expert_analysis
RETURNING report_id
"""

_UPDATE_GAME_STATUS_SQL = """
UPDATE games SET status = %(status)s WHERE game_id = %(game_id)s
"""


def insert_game_report(game_id: int, report: GameReport) -> str:
    """Insert or upsert a game-level intelligence report into ``game_reports``.

    Args:
        game_id: Primary key of the game in the ``games`` table.
        report: LLM-generated game analysis produced by the Game Intelligence Agent.

    Returns:
        The ``report_id`` UUID assigned by the database, as a plain string.
    """
    h2h = report.h2h
    if h2h is not None:
        h2h_home_team = h2h.home_team
        h2h_away_team = h2h.away_team
        h2h_home_team_wins = h2h.home_team_wins
        h2h_away_team_wins = h2h.away_team_wins
        h2h_draws = h2h.draws
        h2h_total_meetings = h2h.total_meetings
    else:
        h2h_home_team = None
        h2h_away_team = None
        h2h_home_team_wins = None
        h2h_away_team_wins = None
        h2h_draws = None
        h2h_total_meetings = None

    with get_cursor(commit=True) as cur:
        cur.execute(
            _INSERT_GAME_REPORT_SQL,
            {
                "game_id": game_id,
                "h2h_home_team": h2h_home_team,
                "h2h_away_team": h2h_away_team,
                "h2h_home_team_wins": h2h_home_team_wins,
                "h2h_away_team_wins": h2h_away_team_wins,
                "h2h_draws": h2h_draws,
                "h2h_total_meetings": h2h_total_meetings,
                "h2h_bullets": Jsonb(list(report.h2h_bullets)),
                "weather_bullets": Jsonb(list(report.weather_bullets)),
                "weather_cancellation_risk": report.weather_cancellation_risk,
                "venue": report.venue,
            },
        )
        row = cur.fetchone()
        return str(row[0])


def insert_team_report(game_id: int, team_name: str, report: TeamReport) -> str:
    """Insert or upsert a team-level intelligence report into ``team_reports``.

    Args:
        game_id: Primary key of the game in the ``games`` table.
        team_name: Name of the team this report covers.
        report: LLM-generated team analysis produced by the Team Intelligence Agent.

    Returns:
        The ``report_id`` UUID assigned by the database, as a plain string.
    """
    last_5_payload = [m.model_dump() for m in report.last_5_games]

    with get_cursor(commit=True) as cur:
        cur.execute(
            _INSERT_TEAM_REPORT_SQL,
            {
                "game_id": game_id,
                "team_name": team_name,
                "recovery_days": report.recovery_days,
                "form_streak": report.form_streak,
                "last_5_games": Jsonb(last_5_payload),
                "form_bullets": Jsonb(list(report.form_bullets)),
                "league_rank": report.league_rank,
                "league_points": report.league_points,
                "league_matches_played": report.league_matches_played,
                "league_bullets": Jsonb(list(report.league_bullets)),
                "injury_bullets": Jsonb(list(report.injury_bullets)),
                "news_bullets": Jsonb(list(report.news_bullets)),
            },
        )
        row = cur.fetchone()
        return str(row[0])


def insert_expert_report(game_id: int, report: ExpertGameReport) -> str:
    """Insert or upsert an expert analysis report into ``expert_game_reports``.

    Args:
        game_id: Primary key of the game in the ``games`` table.
        report: LLM-generated expert analysis produced by the Expert Report Agent.

    Returns:
        The ``report_id`` UUID assigned by the database, as a plain string.
    """
    with get_cursor(commit=True) as cur:
        cur.execute(
            _INSERT_EXPERT_REPORT_SQL,
            {
                "game_id": game_id,
                "expert_analysis": Jsonb(list(report.expert_analysis)),
            },
        )
        row = cur.fetchone()
        return str(row[0])


def update_game_status(game_id: int, status: str) -> None:
    """Update the ``status`` column of a game row in the ``games`` table.

    Args:
        game_id: Primary key of the game to update.
        status: New status value (e.g., ``'analyzed'``, ``'ready'``).
    """
    with get_cursor(commit=True) as cur:
        cur.execute(
            _UPDATE_GAME_STATUS_SQL,
            {
                "status": status,
                "game_id": game_id,
            },
        )
