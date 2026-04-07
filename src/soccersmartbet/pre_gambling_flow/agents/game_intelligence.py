"""Game Intelligence Agent for pre-gambling flow.

This is NOT an agentic tool-calling LLM. It is a Python function that:
1. Calls all four data-fetching tools programmatically
2. Formats the raw results into a structured user message
3. Makes a single LLM call with structured output → GameReport
4. Writes the GameReport to the database

The LLM's only job is analysis and synthesis — all data collection
happens in Python before the model is invoked.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict

logger = logging.getLogger(__name__)

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from soccersmartbet.pre_gambling_flow.agents.db_utils import insert_game_report
from soccersmartbet.pre_gambling_flow.prompts import GAME_INTELLIGENCE_AGENT_PROMPT
from soccersmartbet.pre_gambling_flow.structured_outputs import GameReport
from soccersmartbet.pre_gambling_flow.tools.game.fetch_h2h import fetch_h2h
from soccersmartbet.pre_gambling_flow.tools.game.fetch_venue import fetch_venue
from soccersmartbet.pre_gambling_flow.tools.game.fetch_weather import fetch_weather
from soccersmartbet.pre_gambling_flow.tools.team.fetch_team_news import fetch_team_news

INTELLIGENCE_MODEL = os.getenv("INTELLIGENCE_MODEL", "gpt-5.4")


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------


def _format_h2h(data: Dict[str, Any]) -> str:
    """Format H2H tool result into a readable section."""
    if data.get("error"):
        return f"Data unavailable: {data['error']}"

    matches = data.get("h2h_matches", [])
    total = data.get("total_h2h", 0)

    if not matches:
        return "No historical meetings found."

    home_wins = sum(1 for m in matches if m.get("winner") == data.get("home_team"))
    away_wins = sum(1 for m in matches if m.get("winner") == data.get("away_team"))
    draws = sum(1 for m in matches if m.get("winner") == "DRAW")

    lines = [
        f"Total meetings shown: {total}",
        f"Results: {data.get('home_team')} {home_wins}W - {draws}D - {away_wins}W {data.get('away_team')}",
        "",
        "Individual matches (most recent first):",
    ]

    for match in matches:
        date = match.get("date", "Unknown")
        home = match.get("home_team", "?")
        away = match.get("away_team", "?")
        score_h = match.get("score_home")
        score_a = match.get("score_away")

        if score_h is not None and score_a is not None:
            score_str = f"{score_h}-{score_a}"
        else:
            score_str = "?-?"

        winner = match.get("winner", "DRAW")
        lines.append(f"  {date}: {home} {score_str} {away} (Winner: {winner})")

    return "\n".join(lines)


def _format_venue(data: Dict[str, Any]) -> str:
    """Format venue tool result into a readable section."""
    if data.get("error"):
        return f"Data unavailable: {data['error']}"

    name = data.get("venue_name") or "Unknown stadium"
    city = data.get("venue_city") or "Unknown city"
    capacity = data.get("venue_capacity")
    surface = data.get("venue_surface")

    parts = [f"Stadium: {name}", f"City: {city}"]
    if capacity:
        parts.append(f"Capacity: {capacity}")
    if surface:
        parts.append(f"Surface: {surface}")

    return "\n".join(parts)


def _format_weather(data: Dict[str, Any]) -> str:
    """Format weather tool result into a readable section."""
    if data.get("error"):
        return f"Data unavailable: {data['error']}"

    city = data.get("venue_city") or "Unknown"
    temp = data.get("temperature_celsius")
    precip = data.get("precipitation_mm")
    precip_prob = data.get("precipitation_probability")
    wind = data.get("wind_speed_kmh")
    conditions = data.get("conditions") or "Unknown"

    lines = [f"Location: {city}", f"Conditions: {conditions}"]

    if temp is not None:
        lines.append(f"Temperature: {temp}°C")
    if precip_prob is not None:
        lines.append(f"Precipitation probability: {precip_prob}%")
    if precip is not None:
        lines.append(f"Precipitation: {precip} mm")
    if wind is not None:
        lines.append(f"Wind speed: {wind} km/h")

    return "\n".join(lines)


def _format_team_news(data: Dict[str, Any]) -> str:
    """Format team news tool result into a readable section."""
    if data.get("error"):
        return f"Data unavailable: {data['error']}"

    articles = data.get("articles", [])
    if not articles:
        return "No news articles available."

    lines = []
    for article in articles:
        title = article.get("title", "")
        source = article.get("source", "")
        published = article.get("published", "")

        parts = []
        if published:
            parts.append(f"[{published[:10]}]")
        if source:
            parts.append(f"({source})")
        parts.append(title)

        lines.append("  - " + " ".join(parts))

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# User message builder
# ---------------------------------------------------------------------------


def _build_user_message(
    home_team: str,
    away_team: str,
    match_date: str,
    kickoff_time: str,
    h2h_data: Dict[str, Any],
    venue_data: Dict[str, Any],
    weather_data: Dict[str, Any],
    home_news: Dict[str, Any],
    away_news: Dict[str, Any],
) -> str:
    """Build the structured text that delivers all raw tool data to the LLM."""
    sections = [
        f"## Match: {home_team} vs {away_team}",
        f"Date: {match_date} {kickoff_time}",
        "",
        "## H2H Data",
        _format_h2h(h2h_data),
        "",
        "## Venue Data",
        _format_venue(venue_data),
        "",
        "## Weather Data",
        _format_weather(weather_data),
        "",
        f"## Team News - {home_team}",
        _format_team_news(home_news),
        "",
        f"## Team News - {away_team}",
        _format_team_news(away_news),
    ]
    return "\n".join(sections)


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def run_game_intelligence(
    game_id: int,
    home_team: str,
    away_team: str,
    match_date: str,
    kickoff_time: str,
) -> GameReport:
    """Run the Game Intelligence Agent for a single match.

    Fetches data from all four tools, formats it into a single user message,
    invokes the LLM once with structured output, persists the result, and
    returns the GameReport.

    Args:
        game_id: Primary key of the game row in the ``games`` table.
        home_team: Home team name (e.g., "Arsenal").
        away_team: Away team name (e.g., "Chelsea").
        match_date: Date string in YYYY-MM-DD format.
        kickoff_time: Kickoff time in HH:MM format (24-hour).

    Returns:
        LLM-generated GameReport persisted to the database.
    """
    logger.info("run_game_intelligence: game_id=%d %s vs %s", game_id, home_team, away_team)

    # Step 1: Call all four tools programmatically
    h2h_data = fetch_h2h(home_team, away_team)
    logger.info("run_game_intelligence: fetch_h2h done, error=%s", h2h_data.get("error"))

    venue_data = fetch_venue(home_team, away_team)
    logger.info("run_game_intelligence: fetch_venue done, error=%s", venue_data.get("error"))

    match_datetime = f"{match_date}T{kickoff_time}:00"
    weather_data = fetch_weather(home_team, away_team, match_datetime)
    logger.info("run_game_intelligence: fetch_weather done, error=%s", weather_data.get("error"))

    home_news = fetch_team_news(home_team)
    logger.info("run_game_intelligence: fetch_team_news (home) done, error=%s", home_news.get("error"))

    away_news = fetch_team_news(away_team)
    logger.info("run_game_intelligence: fetch_team_news (away) done, error=%s", away_news.get("error"))

    # Step 2: Format all raw results into a single user message
    user_content = _build_user_message(
        home_team=home_team,
        away_team=away_team,
        match_date=match_date,
        kickoff_time=kickoff_time,
        h2h_data=h2h_data,
        venue_data=venue_data,
        weather_data=weather_data,
        home_news=home_news,
        away_news=away_news,
    )

    # Step 3: Single LLM call with structured output
    model = ChatOpenAI(model=INTELLIGENCE_MODEL, temperature=0.2)
    structured_model = model.with_structured_output(GameReport)

    system_msg = SystemMessage(content=GAME_INTELLIGENCE_AGENT_PROMPT)
    human_msg = HumanMessage(content=user_content)

    result: GameReport = structured_model.invoke([system_msg, human_msg])
    logger.info("run_game_intelligence: LLM call done")

    # Step 4: Persist to database
    insert_game_report(game_id, result)
    logger.info("run_game_intelligence: report saved to DB")

    return result
