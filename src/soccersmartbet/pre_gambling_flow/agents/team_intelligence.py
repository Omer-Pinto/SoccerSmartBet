"""Team Intelligence Agent for pre-gambling flow.

This is NOT an agentic tool-calling LLM. It is a Python function that:
1. Calls all four data-fetching tools programmatically
2. Formats the raw results into a structured user message
3. Makes a single LLM call with structured output → TeamReport
4. Writes the TeamReport to the database

The LLM's only job is analysis and synthesis — all data collection
happens in Python before the model is invoked.
"""

from __future__ import annotations

import os
from typing import Any, Dict

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from soccersmartbet.pre_gambling_flow.agents.db_utils import insert_team_report
from soccersmartbet.pre_gambling_flow.prompts import TEAM_INTELLIGENCE_AGENT_PROMPT
from soccersmartbet.pre_gambling_flow.structured_outputs import TeamReport
from soccersmartbet.pre_gambling_flow.tools.team.calculate_recovery_time import calculate_recovery_time
from soccersmartbet.pre_gambling_flow.tools.team.fetch_form import fetch_form
from soccersmartbet.pre_gambling_flow.tools.team.fetch_injuries import fetch_injuries
from soccersmartbet.pre_gambling_flow.tools.team.fetch_league_position import fetch_league_position

INTELLIGENCE_MODEL = os.getenv("INTELLIGENCE_MODEL", "gpt-5.4")


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------


def _format_form(data: Dict[str, Any]) -> str:
    """Format form tool result into a readable section."""
    if data.get("error"):
        return f"Data unavailable: {data['error']}"

    matches = data.get("matches", [])
    record = data.get("record", {})

    if not matches:
        return "No recent matches found."

    lines = [
        f"Record: {record.get('wins', 0)}W - {record.get('draws', 0)}D - {record.get('losses', 0)}L",
        "",
        "Matches (most recent first):",
    ]

    for match in matches:
        date = match.get("date", "Unknown")
        opponent = match.get("opponent", "Unknown")
        home_away = match.get("home_away", "?")
        result = match.get("result", "?")
        goals_for = match.get("goals_for")
        goals_against = match.get("goals_against")

        if goals_for is not None and goals_against is not None:
            score_str = f"{goals_for}-{goals_against}"
        else:
            score_str = "?-?"

        lines.append(f"  {date}: vs {opponent} ({home_away}) {score_str} — {result}")

    return "\n".join(lines)


def _format_injuries(data: Dict[str, Any]) -> str:
    """Format injuries tool result into a readable section."""
    if data.get("error"):
        return f"Data unavailable: {data['error']}"

    injuries = data.get("injuries", [])
    total = data.get("total_injuries", 0)

    if not injuries:
        return "No injuries reported."

    lines = [f"Total injured: {total}", ""]

    for player in injuries:
        name = player.get("player_name", "Unknown")
        position = player.get("position_group", "Unknown")
        injury_type = player.get("injury_type", "Unknown")
        expected_return = player.get("expected_return", "Unknown")

        lines.append(
            f"  - {name} ({position}): {injury_type} — expected return: {expected_return}"
        )

    return "\n".join(lines)


def _format_league_position(data: Dict[str, Any]) -> str:
    """Format league position tool result into a readable section."""
    if data.get("error"):
        return f"Data unavailable: {data['error']}"

    league = data.get("league_name") or "Unknown league"
    position = data.get("position")
    points = data.get("points")
    played = data.get("played")
    won = data.get("won")
    draw = data.get("draw")
    lost = data.get("lost")
    form = data.get("form")

    lines = [f"League: {league}"]

    if position is not None:
        lines.append(f"Position: {position}")
    if points is not None:
        lines.append(f"Points: {points}")
    if played is not None:
        lines.append(f"Played: {played}")

    wdl_parts = []
    if won is not None:
        wdl_parts.append(f"{won}W")
    if draw is not None:
        wdl_parts.append(f"{draw}D")
    if lost is not None:
        wdl_parts.append(f"{lost}L")
    if wdl_parts:
        lines.append(f"Record: {' - '.join(wdl_parts)}")

    if form:
        lines.append(f"Form string: {form}")

    return "\n".join(lines)


def _format_recovery(data: Dict[str, Any]) -> str:
    """Format recovery time tool result into a readable section."""
    if data.get("error"):
        return f"Data unavailable: {data['error']}"

    last_date = data.get("last_match_date") or "Unknown"
    upcoming_date = data.get("upcoming_match_date") or "Unknown"
    recovery_days = data.get("recovery_days")
    recovery_status = data.get("recovery_status") or "Unknown"

    lines = [
        f"Last match: {last_date}",
        f"Upcoming match: {upcoming_date}",
    ]

    if recovery_days is not None:
        lines.append(f"Recovery days: {recovery_days}")
    lines.append(f"Recovery status: {recovery_status}")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# User message builder
# ---------------------------------------------------------------------------


def _build_user_message(
    team_name: str,
    match_date: str,
    form_data: Dict[str, Any],
    injuries_data: Dict[str, Any],
    league_data: Dict[str, Any],
    recovery_data: Dict[str, Any],
) -> str:
    """Build the structured text that delivers all raw tool data to the LLM."""
    sections = [
        f"## Team: {team_name}",
        f"Upcoming Match Date: {match_date}",
        "",
        "## Form Data (Last 5 Matches)",
        _format_form(form_data),
        "",
        "## Injury Data",
        _format_injuries(injuries_data),
        "",
        "## League Position",
        _format_league_position(league_data),
        "",
        "## Recovery Time",
        _format_recovery(recovery_data),
    ]
    return "\n".join(sections)


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def run_team_intelligence(game_id: int, team_name: str, match_date: str) -> TeamReport:
    """Run the Team Intelligence Agent for a single team.

    Fetches data from all four tools, formats it into a single user message,
    invokes the LLM once with structured output, persists the result, and
    returns the TeamReport.

    Args:
        game_id: Primary key of the game row in the ``games`` table.
        team_name: Team name (e.g., "Arsenal", "Napoli").
        match_date: Date string in YYYY-MM-DD format.

    Returns:
        LLM-generated TeamReport persisted to the database.
    """
    # Step 1: Call all four tools programmatically
    form_data = fetch_form(team_name)
    injuries_data = fetch_injuries(team_name)
    league_data = fetch_league_position(team_name)
    recovery_data = calculate_recovery_time(team_name, match_date)

    # Step 2: Format all raw results into a single user message
    user_content = _build_user_message(
        team_name=team_name,
        match_date=match_date,
        form_data=form_data,
        injuries_data=injuries_data,
        league_data=league_data,
        recovery_data=recovery_data,
    )

    # Step 3: Single LLM call with structured output
    model = ChatOpenAI(model=INTELLIGENCE_MODEL, temperature=0.2)
    structured_model = model.with_structured_output(TeamReport)

    system_msg = SystemMessage(content=TEAM_INTELLIGENCE_AGENT_PROMPT)
    human_msg = HumanMessage(content=user_content)

    result: TeamReport = structured_model.invoke([system_msg, human_msg])

    # Step 4: Persist to database
    insert_team_report(game_id, team_name, result)

    return result
