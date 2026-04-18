"""Game Intelligence Agent for pre-gambling flow.

This is NOT an agentic tool-calling LLM. It is a Python function that:
1. Calls all three data-fetching tools programmatically.
2. Builds the structured portion of the report (``H2HAggregate``, venue
   name) directly in Python from raw tool output — the LLM is NEVER asked
   to re-emit these numbers.
3. Makes a single LLM call that returns only the synthesis fields
   (``GameReportBullets``: h2h/weather bullets + cancellation-risk
   classification).
4. Merges Python-built structured fields with the LLM bullet output into
   the final ``GameReport`` and writes it to the database.

The LLM's only job is analysis and synthesis. All data collection and all
structured fields happen in Python.
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
from soccersmartbet.pre_gambling_flow.structured_outputs import (
    GameReport,
    GameReportBullets,
    H2HAggregate,
)
from soccersmartbet.pre_gambling_flow.tools.game.fetch_h2h import fetch_h2h
from soccersmartbet.pre_gambling_flow.tools.game.fetch_venue import fetch_venue
from soccersmartbet.pre_gambling_flow.tools.game.fetch_weather import fetch_weather

INTELLIGENCE_MODEL = os.getenv("INTELLIGENCE_MODEL", "gpt-5.4")


# ---------------------------------------------------------------------------
# Structured-field builders (Python-only; no LLM involvement)
# ---------------------------------------------------------------------------


def _build_h2h_aggregate(
    h2h_data: Dict[str, Any],
    home_team: str,
    away_team: str,
) -> H2HAggregate | None:
    """Compute the aggregate W/D/L between today's two teams from the H2H match log.

    Returns ``None`` when the source data is unavailable or empty. The
    counts are keyed by team identity (not historical home/away role) —
    past meetings' home/away roles may not match today's fixture.
    """
    if h2h_data.get("error"):
        return None

    matches = h2h_data.get("h2h_matches") or []
    if not matches:
        return None

    # ``winner`` is populated by fetch_h2h using the user-supplied team names
    # (see fetch_h2h.py lines ~205-222). So we count against ``home_team`` /
    # ``away_team`` as passed into this function.
    home_wins = sum(1 for m in matches if m.get("winner") == home_team)
    away_wins = sum(1 for m in matches if m.get("winner") == away_team)
    draws = sum(1 for m in matches if m.get("winner") == "DRAW")
    total_meetings = home_wins + away_wins + draws

    if total_meetings == 0:
        return None

    return H2HAggregate(
        home_team=home_team,
        away_team=away_team,
        home_team_wins=home_wins,
        away_team_wins=away_wins,
        draws=draws,
        total_meetings=total_meetings,
    )


def _extract_venue_short(venue_data: Dict[str, Any]) -> str | None:
    """Pull just the short stadium name out of the venue tool's output."""
    if venue_data.get("error"):
        return None
    name = venue_data.get("venue_name")
    return name if name else None


# ---------------------------------------------------------------------------
# User-message assembly for the LLM
# ---------------------------------------------------------------------------


def _h2h_summary_line(aggregate: H2HAggregate | None) -> str:
    """One-line aggregate summary for the LLM, or an unavailable marker."""
    if aggregate is None:
        return "H2H data unavailable."
    return (
        f"H2H aggregate across {aggregate.total_meetings} all-time meetings "
        f"(any venue): {aggregate.home_team} {aggregate.home_team_wins}W, "
        f"{aggregate.away_team} {aggregate.away_team_wins}W, "
        f"{aggregate.draws}D. Today's home team is {aggregate.home_team}; "
        f"today's away team is {aggregate.away_team}."
    )


def _venue_section(venue_data: Dict[str, Any]) -> str:
    if venue_data.get("error"):
        return "Venue data unavailable."

    name = venue_data.get("venue_name") or "unknown"
    city = venue_data.get("venue_city") or "unknown"
    capacity = venue_data.get("venue_capacity")
    surface = venue_data.get("venue_surface")

    parts = [f"venue_name: {name}", f"venue_city: {city}"]
    if capacity is not None:
        parts.append(f"venue_capacity: {capacity}")
    if surface:
        parts.append(f"venue_surface: {surface}")
    return "\n".join(parts)


def _weather_section(weather_data: Dict[str, Any]) -> str:
    if weather_data.get("error"):
        return "Weather data unavailable."

    city = weather_data.get("venue_city") or "unknown"
    temp = weather_data.get("temperature_celsius")
    precip = weather_data.get("precipitation_mm")
    precip_prob = weather_data.get("precipitation_probability")
    wind = weather_data.get("wind_speed_kmh")
    conditions = weather_data.get("conditions")

    lines = [f"city: {city}"]
    if conditions:
        lines.append(f"conditions: {conditions}")
    if temp is not None:
        lines.append(f"temperature_celsius: {temp}")
    if precip_prob is not None:
        lines.append(f"precipitation_probability_pct: {precip_prob}")
    if precip is not None:
        lines.append(f"precipitation_mm: {precip}")
    if wind is not None:
        lines.append(f"wind_speed_kmh: {wind}")
    return "\n".join(lines)


def _build_user_message(
    home_team: str,
    away_team: str,
    match_date: str,
    kickoff_time: str,
    h2h_aggregate: H2HAggregate | None,
    venue_data: Dict[str, Any],
    weather_data: Dict[str, Any],
) -> str:
    """Assemble only what the LLM needs to produce bullets + cancellation risk.

    The H2H match list is intentionally NOT included — per Omer's rule,
    historical home/away roles are unreliable, so the LLM receives only
    the aggregate summary line.
    """
    return "\n".join(
        [
            f"## Match: {home_team} vs {away_team}",
            f"Date: {match_date} {kickoff_time}",
            "",
            "## H2H (aggregate only — no per-match history is provided)",
            _h2h_summary_line(h2h_aggregate),
            "",
            "## Venue",
            _venue_section(venue_data),
            "",
            "## Weather",
            _weather_section(weather_data),
        ]
    )


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

    Fetches data from all three tools, builds the structured portion of
    the report in Python, asks the LLM only for synthesis bullets + the
    cancellation-risk classification, merges the two, persists the
    result, and returns it.

    Args:
        game_id: Primary key of the game row in the ``games`` table.
        home_team: Home team name (e.g., "Arsenal").
        away_team: Away team name (e.g., "Chelsea").
        match_date: Date string in YYYY-MM-DD format.
        kickoff_time: Kickoff time in HH:MM format (24-hour).

    Returns:
        Merged ``GameReport`` persisted to the database.
    """
    logger.info(
        "run_game_intelligence: game_id=%d %s vs %s", game_id, home_team, away_team
    )

    # Step 1: Fetch raw data.
    h2h_data = fetch_h2h(home_team, away_team)
    logger.info("run_game_intelligence: fetch_h2h done, error=%s", h2h_data.get("error"))

    venue_data = fetch_venue(home_team, away_team)
    logger.info("run_game_intelligence: fetch_venue done, error=%s", venue_data.get("error"))

    match_datetime = f"{match_date}T{kickoff_time}:00"
    weather_data = fetch_weather(home_team, away_team, match_datetime)
    logger.info("run_game_intelligence: fetch_weather done, error=%s", weather_data.get("error"))

    # Step 2: Build the structured portion of the report in Python.
    h2h_aggregate = _build_h2h_aggregate(h2h_data, home_team, away_team)
    venue_short = _extract_venue_short(venue_data)

    # Step 3: Build the user message containing only what the LLM needs
    # (aggregate summary, raw venue + weather numbers).
    user_content = _build_user_message(
        home_team=home_team,
        away_team=away_team,
        match_date=match_date,
        kickoff_time=kickoff_time,
        h2h_aggregate=h2h_aggregate,
        venue_data=venue_data,
        weather_data=weather_data,
    )

    # Step 4: Single LLM call — bullets + cancellation-risk classification only.
    model = ChatOpenAI(model=INTELLIGENCE_MODEL, temperature=0.2)
    structured_model = model.with_structured_output(GameReportBullets)

    system_msg = SystemMessage(content=GAME_INTELLIGENCE_AGENT_PROMPT)
    human_msg = HumanMessage(content=user_content)

    llm_out: GameReportBullets = structured_model.invoke([system_msg, human_msg])
    logger.info("run_game_intelligence: LLM call done")

    # Step 5: Merge Python-built structured fields with LLM bullets.
    result = GameReport(
        h2h=h2h_aggregate,
        h2h_bullets=llm_out.h2h_bullets,
        weather_bullets=llm_out.weather_bullets,
        weather_cancellation_risk=llm_out.weather_cancellation_risk,
        venue=venue_short,
    )

    # Step 6: Persist.
    insert_game_report(game_id, result)
    logger.info("run_game_intelligence: report saved to DB")

    return result
