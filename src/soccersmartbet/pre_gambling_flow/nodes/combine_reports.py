"""Combine Reports node for the Pre-Gambling Flow.

Reads game_reports and team_reports from the DB for all analyzed games and
combines them into a single AIMessage for downstream consumption.
"""

from __future__ import annotations

import logging
import os
from typing import Any

import psycopg2

logger = logging.getLogger(__name__)
from langchain_core.messages import AIMessage

from soccersmartbet.pre_gambling_flow.state import Phase, PreGamblingState

DATABASE_URL = os.getenv("DATABASE_URL")

_FETCH_GAME_SQL = """
SELECT home_team, away_team, league, n1, n2, n3
FROM games
WHERE game_id = %(game_id)s
"""

_FETCH_GAME_REPORT_SQL = """
SELECT h2h_insights, weather_risk, venue, team_news
FROM game_reports
WHERE game_id = %(game_id)s
LIMIT 1
"""

_FETCH_TEAM_REPORTS_SQL = """
SELECT team_name, recovery_days, form_trend, injury_impact, league_position
FROM team_reports
WHERE game_id = %(game_id)s
ORDER BY team_name
"""

_NOT_AVAILABLE = "Not available"


def _format_game_block(
    home_team: str,
    away_team: str,
    league: str,
    n1: Any,
    n2: Any,
    n3: Any,
    h2h_insights: str,
    weather_risk: str,
    venue: str,
    team_news: str,
    home_report: dict[str, Any] | None,
    away_report: dict[str, Any] | None,
) -> str:
    """Build the formatted text block for a single game.

    Args:
        home_team: Home team name from the games table.
        away_team: Away team name from the games table.
        league: League name from the games table.
        n1: Home-win odds decimal value.
        n2: Away-win odds decimal value.
        n3: Draw odds decimal value.
        h2h_insights: Head-to-head insights text.
        weather_risk: Weather risk assessment text.
        venue: Venue description text.
        team_news: Team news text.
        home_report: Dict with keys recovery_days, form_trend, injury_impact,
            league_position for the home side, or None if unavailable.
        away_report: Dict with keys recovery_days, form_trend, injury_impact,
            league_position for the away side, or None if unavailable.

    Returns:
        Formatted multi-line string for this game.
    """
    lines: list[str] = [
        f"=== GAME REPORT: {home_team} vs {away_team} ({league}) ===",
        f"Odds: 1={n1} / X={n3} / 2={n2}",
        "",
        "--- H2H Insights ---",
        h2h_insights,
        "",
        "--- Weather Risk ---",
        weather_risk,
        "",
        "--- Venue ---",
        venue,
        "",
        "--- Team News ---",
        team_news,
    ]

    for label, report in ((f"{home_team} (Home)", home_report), (f"{away_team} (Away)", away_report)):
        lines.append("")
        lines.append(f"--- {label} ---")
        if report is None:
            lines.append(_NOT_AVAILABLE)
        else:
            lines.append(f"League Position: {report['league_position'] or _NOT_AVAILABLE}")
            lines.append(f"Form: {report['form_trend'] or _NOT_AVAILABLE}")
            recovery = report["recovery_days"]
            lines.append(f"Recovery: {recovery if recovery is not None else _NOT_AVAILABLE} days")
            lines.append(f"Injuries: {report['injury_impact'] or _NOT_AVAILABLE}")

    return "\n".join(lines)


def combine_reports(state: PreGamblingState) -> dict[str, Any]:
    """LangGraph node: combine game_reports and team_reports into a single message.

    Queries the DB for all analyzed games and assembles a structured text
    report per game.  All games are concatenated into a single AIMessage.

    Args:
        state: Current Pre-Gambling Flow state.  Must contain ``games_to_analyze``.

    Returns:
        State update dict with ``messages`` (list containing one AIMessage) and
        ``phase`` set to ``Phase.COMPLETE``.
    """
    game_ids: list[int] = state["games_to_analyze"]
    logger.info("combine_reports: querying reports for %d games", len(game_ids))

    if not game_ids:
        return {
            "messages": [],
            "phase": Phase.COMPLETE,
        }

    blocks: list[str] = []

    conn = psycopg2.connect(DATABASE_URL)
    try:
        with conn:
            with conn.cursor() as cur:
                for game_id in game_ids:
                    cur.execute(_FETCH_GAME_SQL, {"game_id": game_id})
                    game_row = cur.fetchone()
                    if game_row is None:
                        continue
                    home_team, away_team, league, n1, n2, n3 = game_row

                    cur.execute(_FETCH_GAME_REPORT_SQL, {"game_id": game_id})
                    report_row = cur.fetchone()
                    if report_row is not None:
                        h2h_insights, weather_risk, venue, team_news = (
                            v or _NOT_AVAILABLE for v in report_row
                        )
                    else:
                        h2h_insights = weather_risk = venue = team_news = _NOT_AVAILABLE

                    cur.execute(_FETCH_TEAM_REPORTS_SQL, {"game_id": game_id})
                    team_rows = cur.fetchall()

                    team_map: dict[str, dict[str, Any]] = {}
                    for row in team_rows:
                        t_name, recovery_days, form_trend, injury_impact, league_position = row
                        team_map[t_name] = {
                            "recovery_days": recovery_days,
                            "form_trend": form_trend,
                            "injury_impact": injury_impact,
                            "league_position": league_position,
                        }

                    home_report = team_map.get(home_team)
                    away_report = team_map.get(away_team)

                    blocks.append(
                        _format_game_block(
                            home_team=home_team,
                            away_team=away_team,
                            league=league,
                            n1=n1,
                            n2=n2,
                            n3=n3,
                            h2h_insights=h2h_insights,
                            weather_risk=weather_risk,
                            venue=venue,
                            team_news=team_news,
                            home_report=home_report,
                            away_report=away_report,
                        )
                    )
    finally:
        conn.close()

    combined_text = "\n\n".join(blocks)
    logger.info("combine_reports: combined %d game reports", len(blocks))

    return {
        "messages": [AIMessage(content=combined_text)],
        "phase": Phase.COMPLETE,
    }
