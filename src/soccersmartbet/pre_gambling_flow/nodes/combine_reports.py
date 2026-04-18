"""Combine Reports node for the Pre-Gambling Flow.

Reads game_reports and team_reports from the DB for all analyzed games and
combines them into a single AIMessage for downstream consumption.
"""

from __future__ import annotations

import logging
import os
from typing import Any

import psycopg2
from langchain_core.messages import AIMessage

from soccersmartbet.pre_gambling_flow.state import Phase, PreGamblingState

logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL")

_EL_LEAGUES = {
    "Europa League",
    "UEFA Europa League",
    "UEFA Europa Conference League",
    "Conference League",
}

_FETCH_GAME_SQL = """
SELECT home_team, away_team, league, home_win_odd, away_win_odd, draw_odd
FROM games
WHERE game_id = %(game_id)s
"""

_FETCH_GAME_REPORT_SQL = """
SELECT h2h_home_team, h2h_away_team, h2h_home_team_wins, h2h_away_team_wins,
       h2h_draws, h2h_total_meetings, h2h_bullets,
       weather_bullets, weather_cancellation_risk, venue
FROM game_reports
WHERE game_id = %(game_id)s
LIMIT 1
"""

_FETCH_TEAM_REPORTS_SQL = """
SELECT team_name, recovery_days, form_streak, last_5_games, form_bullets,
       league_rank, league_points, league_matches_played, league_bullets,
       injury_bullets, news_bullets
FROM team_reports
WHERE game_id = %(game_id)s
ORDER BY team_name
"""


def _fmt_bullets(items: list[str] | None) -> str:
    if not items:
        return ""
    return "\n".join(f"  - {b}" for b in items)


def _h2h_line(
    league: str,
    home: str | None,
    away: str | None,
    hw: int | None,
    aw: int | None,
    draws: int | None,
    total: int | None,
) -> str:
    if league in _EL_LEAGUES:
        return "H2H not tracked for this competition"
    if total and total > 0 and home and away:
        return f"{home} {hw or 0} \u2013 {draws or 0} draws \u2013 {aw or 0} {away}"
    return "H2H: No data available."


def _format_team_block(label: str, report: dict[str, Any] | None) -> list[str]:
    lines: list[str] = [f"  [{label}]"]
    if report is None:
        return lines

    streak = report.get("form_streak") or "\u2014"
    rank = report.get("league_rank")
    pts = report.get("league_points")
    mp = report.get("league_matches_played")
    rank_s = str(rank) if rank is not None else "\u2014"
    pts_s = f"{pts} pts" if pts is not None else "\u2014"
    mp_s = f"{mp} MP" if mp is not None else "\u2014"
    recovery = report.get("recovery_days")
    recovery_s = f"{recovery} days" if recovery is not None else "\u2014"

    lines.append(f"  Form streak: {streak}")
    form_b = _fmt_bullets(report.get("form_bullets"))
    if form_b:
        lines.append(form_b)

    last5: list[dict] = report.get("last_5_games") or []
    if last5:
        lines.append("  Last 5 (most recent first):")
        for m in last5[:5]:
            lines.append(
                f"    {m.get('result','?')} {m.get('goals_for','?')}:{m.get('goals_against','?')}"
                f" vs {m.get('opponent','')} ({m.get('home_or_away','')})"
            )

    lines.append(f"  League: {rank_s} \u00b7 {pts_s} \u00b7 {mp_s}")
    league_b = _fmt_bullets(report.get("league_bullets"))
    if league_b:
        lines.append(league_b)

    lines.append(f"  Recovery: {recovery_s}")

    injury_b = _fmt_bullets(report.get("injury_bullets"))
    if injury_b:
        lines.append("  Injuries:")
        lines.append(injury_b)

    news_b = _fmt_bullets(report.get("news_bullets"))
    if news_b:
        lines.append("  News:")
        lines.append(news_b)

    return lines


def _format_game_block(
    home_team: str,
    away_team: str,
    league: str,
    home_win_odd: Any,
    away_win_odd: Any,
    draw_odd: Any,
    h2h_home: str | None,
    h2h_away: str | None,
    h2h_hw: int | None,
    h2h_aw: int | None,
    h2h_draws: int | None,
    h2h_total: int | None,
    h2h_bullets: list[str] | None,
    weather_bullets: list[str] | None,
    cancel_risk: str | None,
    venue: str | None,
    home_report: dict[str, Any] | None,
    away_report: dict[str, Any] | None,
) -> str:
    lines: list[str] = [
        f"=== {home_team} vs {away_team} ({league}) ===",
        f"Odds: 1={home_win_odd} / X={draw_odd} / 2={away_win_odd}",
        "",
        "--- H2H ---",
        _h2h_line(league, h2h_home, h2h_away, h2h_hw, h2h_aw, h2h_draws, h2h_total),
    ]
    h2h_b = _fmt_bullets(h2h_bullets)
    if h2h_b:
        lines.append(h2h_b)

    if weather_bullets:
        lines.append("")
        lines.append("--- Weather ---")
        lines.append(_fmt_bullets(weather_bullets))
        if cancel_risk in ("medium", "high"):
            lines.append(f"  Cancellation risk: {cancel_risk}")

    if venue:
        lines.extend(["", "--- Venue ---", venue])

    lines.append("")
    lines.extend(_format_team_block(f"{home_team} (Home)", home_report))
    lines.append("")
    lines.extend(_format_team_block(f"{away_team} (Away)", away_report))

    return "\n".join(lines)


def combine_reports(state: PreGamblingState) -> dict[str, Any]:
    """LangGraph node: combine game_reports and team_reports into a single message."""
    game_ids: list[int] = state["games_to_analyze"]
    logger.info("combine_reports: querying reports for %d games", len(game_ids))

    if not game_ids:
        return {"messages": [], "phase": Phase.COMPLETE}

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
                    home_team, away_team, league, home_win_odd, away_win_odd, draw_odd = game_row

                    h2h_home = h2h_away = None
                    h2h_hw = h2h_aw = h2h_d = h2h_total = None
                    h2h_bullets: list[str] = []
                    weather_bullets: list[str] = []
                    cancel_risk: str | None = None
                    venue: str | None = None

                    cur.execute(_FETCH_GAME_REPORT_SQL, {"game_id": game_id})
                    report_row = cur.fetchone()
                    if report_row is not None:
                        (
                            h2h_home, h2h_away, h2h_hw, h2h_aw, h2h_d, h2h_total,
                            h2h_bullets_raw, weather_bullets_raw, cancel_risk, venue,
                        ) = report_row
                        h2h_bullets = h2h_bullets_raw or []
                        weather_bullets = weather_bullets_raw or []

                    cur.execute(_FETCH_TEAM_REPORTS_SQL, {"game_id": game_id})
                    team_rows = cur.fetchall()

                    team_map: dict[str, dict[str, Any]] = {}
                    for row in team_rows:
                        (
                            t_name, recovery_days, form_streak, last5_raw, form_bullets_raw,
                            league_rank, league_points, league_mp, league_bullets_raw,
                            injury_bullets_raw, news_bullets_raw,
                        ) = row
                        team_map[t_name] = {
                            "recovery_days": recovery_days,
                            "form_streak": form_streak,
                            "last_5_games": last5_raw or [],
                            "form_bullets": form_bullets_raw or [],
                            "league_rank": league_rank,
                            "league_points": league_points,
                            "league_matches_played": league_mp,
                            "league_bullets": league_bullets_raw or [],
                            "injury_bullets": injury_bullets_raw or [],
                            "news_bullets": news_bullets_raw or [],
                        }

                    home_report = team_map.get(home_team)
                    away_report = team_map.get(away_team)

                    blocks.append(
                        _format_game_block(
                            home_team=home_team,
                            away_team=away_team,
                            league=league,
                            home_win_odd=home_win_odd,
                            away_win_odd=away_win_odd,
                            draw_odd=draw_odd,
                            h2h_home=h2h_home,
                            h2h_away=h2h_away,
                            h2h_hw=h2h_hw,
                            h2h_aw=h2h_aw,
                            h2h_draws=h2h_d,
                            h2h_total=h2h_total,
                            h2h_bullets=h2h_bullets,
                            weather_bullets=weather_bullets,
                            cancel_risk=cancel_risk,
                            venue=venue,
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
