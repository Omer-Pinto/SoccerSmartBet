"""
AI Betting Agent node for the Gambling Flow.

Queries all pre-gambling analysis from DB, makes a single LLM call with
structured output, and returns AI bet selections for every game.
"""

from __future__ import annotations

import logging
import os
from typing import Any

import psycopg2
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from soccersmartbet.gambling_flow.state import GamblingState

logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL")

AI_BETTING_MODEL = os.getenv("AI_BETTING_MODEL", "gpt-5.4-mini")

DEFAULT_STAKE = 100.0


# ---------------------------------------------------------------------------
# Structured output models
# ---------------------------------------------------------------------------


class AIBetDecision(BaseModel):
    """A single AI bet decision for one game."""

    game_id: int
    prediction: str = Field(description="'1' for home win, 'x' for draw, '2' for away win")
    stake: int = Field(description="Stake in NIS. Must be one of: 50, 100, 200, 500")
    justification: str = Field(description="Brief reasoning for this bet")


class AIBetsOutput(BaseModel):
    """Complete AI betting output for all games."""

    bets: list[AIBetDecision]


# ---------------------------------------------------------------------------
# SQL queries
# ---------------------------------------------------------------------------

_FETCH_GAME_SQL = """
SELECT home_team, away_team, league, home_win_odd, draw_odd, away_win_odd
FROM games
WHERE game_id = %(game_id)s
"""

_FETCH_GAME_REPORT_SQL = """
SELECT h2h_home_team, h2h_away_team, h2h_home_team_wins, h2h_away_team_wins,
       h2h_draws, h2h_total_meetings, h2h_bullets,
       weather_bullets, weather_cancellation_risk
FROM game_reports
WHERE game_id = %(game_id)s
LIMIT 1
"""

_FETCH_TEAM_REPORTS_SQL = """
SELECT team_name, recovery_days, form_streak, form_bullets,
       league_rank, league_points, league_matches_played, league_bullets,
       injury_bullets, news_bullets
FROM team_reports
WHERE game_id = %(game_id)s
ORDER BY team_name
"""

_FETCH_EXPERT_REPORT_SQL = """
SELECT expert_analysis
FROM expert_game_reports
WHERE game_id = %(game_id)s
LIMIT 1
"""

_FETCH_AI_BANKROLL_SQL = """
SELECT total_bankroll
FROM bankroll
WHERE bettor = 'ai'
"""

_EL_LEAGUES = {
    "Europa League",
    "UEFA Europa League",
    "UEFA Europa Conference League",
    "Conference League",
}


# ---------------------------------------------------------------------------
# Prompt
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = """\
You are an expert football betting AI. You analyze pre-match intelligence and
place bets on every game presented to you.

Rules:
- You MUST bet on EVERY game. No skipping.
- For each game, choose exactly one prediction: '1' (home win), 'x' (draw), or '2' (away win).
- For each game, choose a stake from: 50, 100, 200, or 500 NIS. Higher stakes for higher confidence.
- Provide a brief justification for each bet.
- Base your decisions on the analysis data provided (form, injuries, H2H, expert analysis, odds).
- Consider value betting: look for predictions where the true probability exceeds what the odds imply.
"""


def _fmt_bullets(items: list[str] | None, indent: str = "  ") -> str:
    if not items:
        return ""
    return "\n".join(f"{indent}- {b}" for b in items)


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


def _build_games_prompt(games_data: list[dict[str, Any]], ai_bankroll: float) -> str:
    lines: list[str] = [
        f"Your current bankroll: {ai_bankroll:.2f} NIS",
        "Available stakes: 50, 100, 200, or 500 NIS per game (choose based on confidence)",
        "",
        "=== GAMES TO BET ON ===",
        "",
    ]

    for g in games_data:
        league = g.get("league", "")
        lines.append(f"--- Game ID: {g['game_id']} ---")
        lines.append(f"{g['home_team']} vs {g['away_team']} ({league})")
        lines.append(f"Odds: 1={g['home_win_odd']} / X={g['draw_odd']} / 2={g['away_win_odd']}")
        lines.append("")

        h2h_text = _h2h_line(
            league,
            g.get("h2h_home_team"),
            g.get("h2h_away_team"),
            g.get("h2h_home_team_wins"),
            g.get("h2h_away_team_wins"),
            g.get("h2h_draws"),
            g.get("h2h_total_meetings"),
        )
        lines.append(f"H2H: {h2h_text}")
        h2h_b = _fmt_bullets(g.get("h2h_bullets"))
        if h2h_b:
            lines.append(h2h_b)
        lines.append("")

        weather_b = _fmt_bullets(g.get("weather_bullets"))
        if weather_b:
            lines.append("Weather:")
            lines.append(weather_b)
            cancel = g.get("weather_cancellation_risk")
            if cancel in ("medium", "high"):
                lines.append(f"  Cancellation risk: {cancel}")
            lines.append("")

        for side, key in (("Home", "home_report"), ("Away", "away_report")):
            report = g.get(key)
            team_name = g["home_team"] if side == "Home" else g["away_team"]
            lines.append(f"{team_name} ({side}):")
            if report:
                streak = report.get("form_streak") or "\u2014"
                rank = report.get("league_rank")
                pts = report.get("league_points")
                mp = report.get("league_matches_played")
                rank_s = str(rank) if rank is not None else "\u2014"
                pts_s = f"{pts} pts" if pts is not None else "\u2014"
                mp_s = f"{mp} MP" if mp is not None else "\u2014"
                recovery = report.get("recovery_days")
                recovery_s = f"{recovery} days" if recovery is not None else "\u2014"

                lines.append(f"  Form: {streak}")
                form_b = _fmt_bullets(report.get("form_bullets"))
                if form_b:
                    lines.append(form_b)
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
            lines.append("")

        expert_bullets: list[str] = g.get("expert_analysis") or []
        if expert_bullets:
            lines.append("Expert analysis:")
            lines.append(_fmt_bullets(expert_bullets))
        lines.append("")
        lines.append("")

    lines.append("Place your bets on ALL games above. For each game provide game_id, prediction (1/x/2), and justification.")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Node function
# ---------------------------------------------------------------------------


def ai_betting_agent(state: GamblingState) -> dict:
    """LangGraph node: AI places bets on all games using pre-match analysis."""
    game_ids: list[int] = state["game_ids"]
    logger.info("ai_betting_agent: placing bets for %d game(s)", len(game_ids))

    if not game_ids:
        logger.info("ai_betting_agent: no games, returning empty bets")
        return {"ai_bets": []}

    games_data: list[dict[str, Any]] = []
    ai_bankroll = 10000.0

    conn = psycopg2.connect(DATABASE_URL)
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(_FETCH_AI_BANKROLL_SQL)
                row = cur.fetchone()
                if row:
                    ai_bankroll = float(row[0])

                for game_id in game_ids:
                    game_data: dict[str, Any] = {"game_id": game_id}

                    cur.execute(_FETCH_GAME_SQL, {"game_id": game_id})
                    game_row = cur.fetchone()
                    if game_row is None:
                        logger.info("ai_betting_agent: game_id=%d not found, skipping", game_id)
                        continue
                    home_team, away_team, league, home_win_odd, draw_odd, away_win_odd = game_row
                    game_data.update({
                        "home_team": home_team,
                        "away_team": away_team,
                        "league": league,
                        "home_win_odd": home_win_odd,
                        "draw_odd": draw_odd,
                        "away_win_odd": away_win_odd,
                    })

                    cur.execute(_FETCH_GAME_REPORT_SQL, {"game_id": game_id})
                    report_row = cur.fetchone()
                    if report_row:
                        (
                            h2h_home, h2h_away, h2h_hw, h2h_aw, h2h_d, h2h_total,
                            h2h_bullets_raw, weather_bullets_raw, cancel_risk,
                        ) = report_row
                        game_data.update({
                            "h2h_home_team": h2h_home,
                            "h2h_away_team": h2h_away,
                            "h2h_home_team_wins": h2h_hw,
                            "h2h_away_team_wins": h2h_aw,
                            "h2h_draws": h2h_d,
                            "h2h_total_meetings": h2h_total,
                            "h2h_bullets": h2h_bullets_raw or [],
                            "weather_bullets": weather_bullets_raw or [],
                            "weather_cancellation_risk": cancel_risk,
                        })

                    cur.execute(_FETCH_TEAM_REPORTS_SQL, {"game_id": game_id})
                    team_rows = cur.fetchall()
                    team_map: dict[str, dict[str, Any]] = {}
                    for t_row in team_rows:
                        (
                            t_name, recovery_days, form_streak, form_bullets_raw,
                            league_rank, league_pts, league_mp, league_bullets_raw,
                            injury_bullets_raw, news_bullets_raw,
                        ) = t_row
                        team_map[t_name] = {
                            "recovery_days": recovery_days,
                            "form_streak": form_streak,
                            "form_bullets": form_bullets_raw or [],
                            "league_rank": league_rank,
                            "league_points": league_pts,
                            "league_matches_played": league_mp,
                            "league_bullets": league_bullets_raw or [],
                            "injury_bullets": injury_bullets_raw or [],
                            "news_bullets": news_bullets_raw or [],
                        }
                    game_data["home_report"] = team_map.get(home_team)
                    game_data["away_report"] = team_map.get(away_team)

                    cur.execute(_FETCH_EXPERT_REPORT_SQL, {"game_id": game_id})
                    expert_row = cur.fetchone()
                    if expert_row and expert_row[0]:
                        bullets = expert_row[0]
                        if not isinstance(bullets, list):
                            bullets = [str(bullets)]
                        game_data["expert_analysis"] = bullets

                    games_data.append(game_data)
    finally:
        conn.close()

    if not games_data:
        logger.info("ai_betting_agent: no valid games found in DB")
        return {"ai_bets": []}

    prompt_text = _build_games_prompt(games_data, ai_bankroll)

    model = ChatOpenAI(model=AI_BETTING_MODEL, temperature=0.3)
    structured_model = model.with_structured_output(AIBetsOutput)

    result: AIBetsOutput = structured_model.invoke([
        SystemMessage(content=_SYSTEM_PROMPT),
        HumanMessage(content=prompt_text),
    ])
    logger.info("ai_betting_agent: LLM returned %d bet(s)", len(result.bets))

    odds_map: dict[int, dict[str, float]] = {}
    for g in games_data:
        odds_map[g["game_id"]] = {
            "1": float(g["home_win_odd"]),
            "x": float(g["draw_odd"]),
            "2": float(g["away_win_odd"]),
        }

    ai_bets: list[dict] = []
    for bet in result.bets:
        prediction = bet.prediction.lower()
        game_odds = odds_map.get(bet.game_id, {})
        selected_odds = game_odds.get(prediction, 0.0)

        stake = bet.stake if bet.stake in (50, 100, 200, 500) else 100
        ai_bets.append({
            "game_id": bet.game_id,
            "prediction": prediction,
            "odds": selected_odds,
            "stake": float(stake),
            "justification": bet.justification,
        })

    logger.info("ai_betting_agent: returning %d AI bet(s)", len(ai_bets))
    return {"ai_bets": ai_bets}
