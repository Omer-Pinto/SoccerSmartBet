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
SELECT h2h_insights, weather_risk
FROM game_reports
WHERE game_id = %(game_id)s
LIMIT 1
"""

_FETCH_TEAM_REPORTS_SQL = """
SELECT team_name, form_trend, injury_impact, league_position, team_news
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

_NOT_AVAILABLE = "Not available"


# ---------------------------------------------------------------------------
# Prompt
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = """\
You are an expert football betting AI. You analyze pre-match intelligence and
place bets on every game presented to you.

Rules:
- You MUST bet on EVERY game. No skipping.
- For each game, choose exactly one prediction: '1' (home win), 'x' (draw), or '2' (away win).
- Provide a brief justification for each bet.
- Base your decisions on the analysis data provided (form, injuries, H2H, expert analysis, odds).
- Consider value betting: look for predictions where the true probability exceeds what the odds imply.
"""


def _build_games_prompt(games_data: list[dict[str, Any]], ai_bankroll: float) -> str:
    """Build the human message content with all game analysis data."""
    lines: list[str] = [
        f"Your current bankroll: {ai_bankroll:.2f} NIS",
        f"Stake per game: {DEFAULT_STAKE:.0f} NIS",
        "",
        "=== GAMES TO BET ON ===",
        "",
    ]

    for g in games_data:
        lines.append(f"--- Game ID: {g['game_id']} ---")
        lines.append(f"{g['home_team']} vs {g['away_team']} ({g['league']})")
        lines.append(f"Odds: 1={g['home_win_odd']} / X={g['draw_odd']} / 2={g['away_win_odd']}")
        lines.append("")

        lines.append("H2H Insights:")
        lines.append(g.get("h2h_insights", _NOT_AVAILABLE))
        lines.append("")

        lines.append("Weather Risk:")
        lines.append(g.get("weather_risk", _NOT_AVAILABLE))
        lines.append("")

        # Home team report
        home_report = g.get("home_report")
        lines.append(f"{g['home_team']} (Home):")
        if home_report:
            lines.append(f"  Form: {home_report.get('form_trend', _NOT_AVAILABLE)}")
            lines.append(f"  Injuries: {home_report.get('injury_impact', _NOT_AVAILABLE)}")
            lines.append(f"  League Position: {home_report.get('league_position', _NOT_AVAILABLE)}")
            lines.append(f"  Team News: {home_report.get('team_news', _NOT_AVAILABLE)}")
        else:
            lines.append(f"  {_NOT_AVAILABLE}")
        lines.append("")

        # Away team report
        away_report = g.get("away_report")
        lines.append(f"{g['away_team']} (Away):")
        if away_report:
            lines.append(f"  Form: {away_report.get('form_trend', _NOT_AVAILABLE)}")
            lines.append(f"  Injuries: {away_report.get('injury_impact', _NOT_AVAILABLE)}")
            lines.append(f"  League Position: {away_report.get('league_position', _NOT_AVAILABLE)}")
            lines.append(f"  Team News: {away_report.get('team_news', _NOT_AVAILABLE)}")
        else:
            lines.append(f"  {_NOT_AVAILABLE}")
        lines.append("")

        # Expert analysis
        lines.append("Expert Analysis:")
        lines.append(g.get("expert_analysis", _NOT_AVAILABLE))
        lines.append("")
        lines.append("")

    lines.append("Place your bets on ALL games above. For each game provide game_id, prediction (1/x/2), and justification.")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Node function
# ---------------------------------------------------------------------------


def ai_betting_agent(state: GamblingState) -> dict:
    """LangGraph node: AI places bets on all games using pre-match analysis.

    Queries DB for game analysis (same data the user saw), makes a single
    LLM call with structured output, and returns AI bet selections.

    Args:
        state: Current Gambling Flow state with game_ids.

    Returns:
        State update dict with ``ai_bets`` list.
    """
    game_ids: list[int] = state["game_ids"]
    logger.info("ai_betting_agent: placing bets for %d game(s)", len(game_ids))

    if not game_ids:
        logger.info("ai_betting_agent: no games, returning empty bets")
        return {"ai_bets": []}

    # Fetch all analysis data from DB
    games_data: list[dict[str, Any]] = []
    ai_bankroll = 10000.0  # default

    conn = psycopg2.connect(DATABASE_URL)
    try:
        with conn:
            with conn.cursor() as cur:
                # Fetch AI bankroll
                cur.execute(_FETCH_AI_BANKROLL_SQL)
                row = cur.fetchone()
                if row:
                    ai_bankroll = float(row[0])

                for game_id in game_ids:
                    game_data: dict[str, Any] = {"game_id": game_id}

                    # Game basics
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

                    # Game report
                    cur.execute(_FETCH_GAME_REPORT_SQL, {"game_id": game_id})
                    report_row = cur.fetchone()
                    if report_row:
                        game_data["h2h_insights"] = report_row[0] or _NOT_AVAILABLE
                        game_data["weather_risk"] = report_row[1] or _NOT_AVAILABLE

                    # Team reports
                    cur.execute(_FETCH_TEAM_REPORTS_SQL, {"game_id": game_id})
                    team_rows = cur.fetchall()
                    team_map: dict[str, dict[str, Any]] = {}
                    for t_row in team_rows:
                        t_name, form_trend, injury_impact, league_position, team_news = t_row
                        team_map[t_name] = {
                            "form_trend": form_trend,
                            "injury_impact": injury_impact,
                            "league_position": league_position,
                            "team_news": team_news,
                        }
                    game_data["home_report"] = team_map.get(home_team)
                    game_data["away_report"] = team_map.get(away_team)

                    # Expert report
                    cur.execute(_FETCH_EXPERT_REPORT_SQL, {"game_id": game_id})
                    expert_row = cur.fetchone()
                    if expert_row:
                        game_data["expert_analysis"] = expert_row[0] or _NOT_AVAILABLE

                    games_data.append(game_data)
    finally:
        conn.close()

    if not games_data:
        logger.info("ai_betting_agent: no valid games found in DB")
        return {"ai_bets": []}

    # Build prompt and call LLM
    prompt_text = _build_games_prompt(games_data, ai_bankroll)

    model = ChatOpenAI(model=AI_BETTING_MODEL, temperature=0.3)
    structured_model = model.with_structured_output(AIBetsOutput)

    result: AIBetsOutput = structured_model.invoke([
        SystemMessage(content=_SYSTEM_PROMPT),
        HumanMessage(content=prompt_text),
    ])
    logger.info("ai_betting_agent: LLM returned %d bet(s)", len(result.bets))

    # Map LLM decisions to BetSelection dicts with correct odds
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

        ai_bets.append({
            "game_id": bet.game_id,
            "prediction": prediction,
            "odds": selected_odds,
            "stake": DEFAULT_STAKE,
            "justification": bet.justification,
        })

    logger.info("ai_betting_agent: returning %d AI bet(s)", len(ai_bets))
    return {"ai_bets": ai_bets}
