"""Shared DB insert/update helpers for Pre-Gambling Flow intelligence agents.

Each function is self-contained: it opens a connection, runs a single
transaction, and closes the connection in a finally block.
"""

from __future__ import annotations

import os

import psycopg2

from soccersmartbet.pre_gambling_flow.structured_outputs import ExpertGameReport, GameReport, TeamReport

DATABASE_URL = os.getenv("DATABASE_URL")

_INSERT_GAME_REPORT_SQL = """
INSERT INTO game_reports (game_id, h2h_insights, weather_risk, venue)
VALUES (%(game_id)s, %(h2h_insights)s, %(weather_risk)s, %(venue)s)
ON CONFLICT (game_id) DO UPDATE SET
    h2h_insights = EXCLUDED.h2h_insights,
    weather_risk = EXCLUDED.weather_risk,
    venue = EXCLUDED.venue
RETURNING report_id
"""

_INSERT_TEAM_REPORT_SQL = """
INSERT INTO team_reports (game_id, team_name, recovery_days, form_trend, injury_impact, league_position, team_news)
VALUES (%(game_id)s, %(team_name)s, %(recovery_days)s, %(form_trend)s, %(injury_impact)s, %(league_position)s, %(team_news)s)
ON CONFLICT (game_id, team_name) DO UPDATE SET
    recovery_days = EXCLUDED.recovery_days,
    form_trend = EXCLUDED.form_trend,
    injury_impact = EXCLUDED.injury_impact,
    league_position = EXCLUDED.league_position,
    team_news = EXCLUDED.team_news
RETURNING report_id
"""

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
    conn = psycopg2.connect(DATABASE_URL)
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    _INSERT_GAME_REPORT_SQL,
                    {
                        "game_id": game_id,
                        "h2h_insights": report.h2h_insights,
                        "weather_risk": report.weather_risk,
                        "venue": report.venue,
                    },
                )
                row = cur.fetchone()
                return str(row[0])
    finally:
        conn.close()


def insert_team_report(game_id: int, team_name: str, report: TeamReport) -> str:
    """Insert or upsert a team-level intelligence report into ``team_reports``.

    Args:
        game_id: Primary key of the game in the ``games`` table.
        team_name: Name of the team this report covers.
        report: LLM-generated team analysis produced by the Team Intelligence Agent.

    Returns:
        The ``report_id`` UUID assigned by the database, as a plain string.
    """
    conn = psycopg2.connect(DATABASE_URL)
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    _INSERT_TEAM_REPORT_SQL,
                    {
                        "game_id": game_id,
                        "team_name": team_name,
                        "recovery_days": report.recovery_days,
                        "form_trend": report.form_trend,
                        "injury_impact": report.injury_impact,
                        "league_position": report.league_position,
                        "team_news": report.team_news,
                    },
                )
                row = cur.fetchone()
                return str(row[0])
    finally:
        conn.close()


def insert_expert_report(game_id: int, report: ExpertGameReport) -> str:
    """Insert or upsert an expert analysis report into ``expert_game_reports``.

    Args:
        game_id: Primary key of the game in the ``games`` table.
        report: LLM-generated expert analysis produced by the Expert Report Agent.

    Returns:
        The ``report_id`` UUID assigned by the database, as a plain string.
    """
    conn = psycopg2.connect(DATABASE_URL)
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    _INSERT_EXPERT_REPORT_SQL,
                    {
                        "game_id": game_id,
                        "expert_analysis": report.expert_analysis,
                    },
                )
                row = cur.fetchone()
                return str(row[0])
    finally:
        conn.close()


def update_game_status(game_id: int, status: str) -> None:
    """Update the ``status`` column of a game row in the ``games`` table.

    Args:
        game_id: Primary key of the game to update.
        status: New status value (e.g., ``'analyzed'``, ``'ready'``).
    """
    conn = psycopg2.connect(DATABASE_URL)
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    _UPDATE_GAME_STATUS_SQL,
                    {
                        "status": status,
                        "game_id": game_id,
                    },
                )
    finally:
        conn.close()
