"""Team Intelligence Agent for pre-gambling flow.

This is NOT an agentic tool-calling LLM. It is a Python function that:
1. Calls all five data-fetching tools programmatically.
2. Builds the structured portion of the report in Python (recovery_days,
   form_streak, last_5_games, league rank/points/played) directly from
   raw tool output — the LLM is NEVER asked to re-emit these numbers.
3. Makes a single LLM call that returns only the four bullet lists
   (``TeamReportBullets``: form/league/injury/news).
4. Merges Python-built structured fields with LLM bullet output into
   the final ``TeamReport`` and writes it to the database.

The LLM's only job is analysis and synthesis.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from soccersmartbet.pre_gambling_flow.agents.db_utils import insert_team_report
from soccersmartbet.pre_gambling_flow.prompts import TEAM_INTELLIGENCE_AGENT_PROMPT
from soccersmartbet.pre_gambling_flow.structured_outputs import (
    RecentMatch,
    TeamReport,
    TeamReportBullets,
)
from soccersmartbet.pre_gambling_flow.tools.team.calculate_recovery_time import (
    calculate_recovery_time,
)
from soccersmartbet.pre_gambling_flow.tools.team.fetch_form import fetch_form
from soccersmartbet.pre_gambling_flow.tools.team.fetch_injuries import fetch_injuries
from soccersmartbet.pre_gambling_flow.tools.team.fetch_league_position import (
    fetch_league_position,
)
from soccersmartbet.pre_gambling_flow.tools.team.fetch_team_news import fetch_team_news

INTELLIGENCE_MODEL = os.getenv("INTELLIGENCE_MODEL", "gpt-5.4")


# ---------------------------------------------------------------------------
# Structured-field builders (Python-only; no LLM involvement)
# ---------------------------------------------------------------------------


_VALID_RESULTS = {"W", "D", "L"}
_HOME_AWAY_MAP = {"home": "home", "away": "away", "HOME": "home", "AWAY": "away"}


def _build_last_5_games(form_data: Dict[str, Any]) -> List[RecentMatch]:
    """Map the raw fetch_form match list into ``RecentMatch`` rows.

    Order matches the tool's output — most recent FIRST, up to 5 entries.
    Rows with missing or invalid fields are skipped rather than fabricated.
    """
    if form_data.get("error"):
        return []

    matches = form_data.get("matches") or []
    rows: List[RecentMatch] = []
    for raw in matches[:5]:
        result = raw.get("result")
        goals_for = raw.get("goals_for")
        goals_against = raw.get("goals_against")
        opponent = raw.get("opponent")
        home_away_raw = raw.get("home_away")
        date = raw.get("date")

        if result not in _VALID_RESULTS:
            continue
        if goals_for is None or goals_against is None:
            continue
        if not opponent:
            continue
        home_or_away = _HOME_AWAY_MAP.get(home_away_raw) if home_away_raw else None
        if home_or_away is None:
            continue
        if not date or date == "Unknown":
            continue

        try:
            rows.append(
                RecentMatch(
                    result=result,
                    goals_for=int(goals_for),
                    goals_against=int(goals_against),
                    opponent=opponent,
                    home_or_away=home_or_away,
                    date=date,
                )
            )
        except (ValueError, TypeError):
            # Pydantic validation failure — skip this row rather than fabricate.
            continue

    return rows


def _build_form_streak(last_5_games: List[RecentMatch]) -> str:
    """Emit a 5-character streak string, most recent LAST.

    ``last_5_games`` is most-recent-first, so we reverse it. Missing slots
    (when fewer than 5 matches are available) are padded with ``'?'``.
    """
    results_most_recent_last = [m.result for m in reversed(last_5_games)]
    # Pad at the FRONT with '?' so that the most recent character stays at
    # the end and older (missing) matches are the unknown ones.
    padded = ["?"] * (5 - len(results_most_recent_last)) + results_most_recent_last
    return "".join(padded[:5])


def _extract_recovery_days(recovery_data: Dict[str, Any]) -> int:
    value = recovery_data.get("recovery_days")
    if isinstance(value, int) and value >= 0:
        return value
    return 0


def _extract_league_snapshot(
    league_data: Dict[str, Any],
) -> tuple[int | None, int | None, int | None]:
    """Return (rank, points, played) from fetch_league_position output."""
    if league_data.get("error"):
        return None, None, None
    position = league_data.get("position")
    points = league_data.get("points")
    played = league_data.get("played")

    def _int_or_none(v: Any) -> int | None:
        if isinstance(v, int):
            return v
        return None

    return _int_or_none(position), _int_or_none(points), _int_or_none(played)


# ---------------------------------------------------------------------------
# User-message assembly for the LLM
# ---------------------------------------------------------------------------


def _form_section(
    form_data: Dict[str, Any],
    form_streak: str,
    last_5_games: List[RecentMatch],
) -> str:
    """Line-level scoreline summary so the LLM can write form bullets."""
    if form_data.get("error"):
        return f"Form data unavailable. form_streak: {form_streak}"

    record = form_data.get("record", {}) or {}
    wins = record.get("wins", 0)
    draws = record.get("draws", 0)
    losses = record.get("losses", 0)

    if not last_5_games:
        return (
            f"form_streak (most recent LAST): {form_streak}\n"
            f"record: {wins}W - {draws}D - {losses}L\n"
            "No match rows available."
        )

    lines = [
        f"form_streak (most recent LAST): {form_streak}",
        f"record: {wins}W - {draws}D - {losses}L",
        "last 5 matches (most recent FIRST):",
    ]
    for idx, match in enumerate(last_5_games, start=1):
        lines.append(
            f"  [{idx}] {match.date} | vs {match.opponent} ({match.home_or_away}) | "
            f"{match.goals_for}-{match.goals_against} | {match.result}"
        )
    return "\n".join(lines)


def _league_section(
    league_data: Dict[str, Any],
    league_rank: int | None,
    league_points: int | None,
    league_matches_played: int | None,
) -> str:
    if league_data.get("error"):
        return "League position data unavailable."

    league_name = league_data.get("league_name") or "unknown"
    lines = [f"league_name: {league_name}"]
    lines.append(
        f"league_rank: {league_rank if league_rank is not None else 'unknown'}"
    )
    lines.append(
        f"league_points: {league_points if league_points is not None else 'unknown'}"
    )
    lines.append(
        f"league_matches_played: "
        f"{league_matches_played if league_matches_played is not None else 'unknown'}"
    )
    return "\n".join(lines)


def _injuries_section(injuries_data: Dict[str, Any]) -> str:
    if injuries_data.get("error"):
        return "Injury data unavailable."

    injuries = injuries_data.get("injuries") or []
    total = injuries_data.get("total_injuries", len(injuries))

    if not injuries:
        return "total_injured: 0"

    lines = [f"total_injured: {total}", "players:"]
    for player in injuries:
        name = player.get("player_name") or "unknown"
        position = player.get("position_group") or "unknown"
        injury_type = player.get("injury_type") or "unknown"
        expected_return = player.get("expected_return") or "unknown"
        lines.append(
            f"  - name={name} | position={position} | "
            f"injury_type={injury_type} | expected_return={expected_return}"
        )
    return "\n".join(lines)


def _news_section(news_data: Dict[str, Any]) -> str:
    if news_data.get("error"):
        return "News data unavailable."

    articles = news_data.get("articles") or []
    if not articles:
        return "No news articles available."

    lines = ["articles:"]
    for article in articles:
        title = article.get("title", "")
        source = article.get("source", "") or "unknown"
        published = article.get("published", "") or ""
        published_date = published[:10] if published else "unknown"
        lines.append(
            f"  - date={published_date} | source={source} | title={title}"
        )
    return "\n".join(lines)


def _build_user_message(
    team_name: str,
    match_date: str,
    form_data: Dict[str, Any],
    form_streak: str,
    last_5_games: List[RecentMatch],
    league_data: Dict[str, Any],
    league_rank: int | None,
    league_points: int | None,
    league_matches_played: int | None,
    injuries_data: Dict[str, Any],
    news_data: Dict[str, Any],
) -> str:
    """Assemble only what the LLM needs to produce the four bullet lists."""
    return "\n".join(
        [
            f"## Team: {team_name}",
            f"Upcoming Match Date: {match_date}",
            "",
            "## Form",
            _form_section(form_data, form_streak, last_5_games),
            "",
            "## League Standing",
            _league_section(
                league_data, league_rank, league_points, league_matches_played
            ),
            "",
            "## Injuries",
            _injuries_section(injuries_data),
            "",
            "## Team News",
            _news_section(news_data),
        ]
    )


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def run_team_intelligence(game_id: int, team_name: str, match_date: str) -> TeamReport:
    """Run the Team Intelligence Agent for a single team.

    Fetches data from all five tools, builds the structured portion of
    the report in Python, asks the LLM only for the four bullet lists,
    merges the two, persists the result, and returns it.

    Args:
        game_id: Primary key of the game row in the ``games`` table.
        team_name: Team name (e.g., "Arsenal", "Napoli").
        match_date: Date string in YYYY-MM-DD format.

    Returns:
        Merged ``TeamReport`` persisted to the database.
    """
    logger.info("run_team_intelligence: game_id=%d team=%s", game_id, team_name)

    # Step 1: Fetch raw data.
    form_data = fetch_form(team_name)
    logger.info(
        "run_team_intelligence: fetch_form done, error=%s", form_data.get("error")
    )

    injuries_data = fetch_injuries(team_name)
    logger.info(
        "run_team_intelligence: fetch_injuries done, error=%s",
        injuries_data.get("error"),
    )

    league_data = fetch_league_position(team_name)
    logger.info(
        "run_team_intelligence: fetch_league_position done, error=%s",
        league_data.get("error"),
    )

    recovery_data = calculate_recovery_time(team_name, match_date)
    logger.info(
        "run_team_intelligence: calculate_recovery_time done, error=%s",
        recovery_data.get("error"),
    )

    news_data = fetch_team_news(team_name)
    logger.info(
        "run_team_intelligence: fetch_team_news done, error=%s",
        news_data.get("error"),
    )

    # Step 2: Build the structured portion of the report in Python.
    last_5_games = _build_last_5_games(form_data)
    form_streak = _build_form_streak(last_5_games)
    recovery_days = _extract_recovery_days(recovery_data)
    league_rank, league_points, league_matches_played = _extract_league_snapshot(
        league_data
    )

    # Step 3: Build the user message containing only what the LLM needs.
    user_content = _build_user_message(
        team_name=team_name,
        match_date=match_date,
        form_data=form_data,
        form_streak=form_streak,
        last_5_games=last_5_games,
        league_data=league_data,
        league_rank=league_rank,
        league_points=league_points,
        league_matches_played=league_matches_played,
        injuries_data=injuries_data,
        news_data=news_data,
    )

    # Step 4: Single LLM call — bullet lists only.
    model = ChatOpenAI(model=INTELLIGENCE_MODEL, temperature=0.2)
    structured_model = model.with_structured_output(TeamReportBullets)

    system_msg = SystemMessage(content=TEAM_INTELLIGENCE_AGENT_PROMPT)
    human_msg = HumanMessage(content=user_content)

    llm_out: TeamReportBullets = structured_model.invoke([system_msg, human_msg])
    logger.info("run_team_intelligence: LLM call done for %s", team_name)

    # Step 5: Merge Python-built structured fields with LLM bullets.
    result = TeamReport(
        recovery_days=recovery_days,
        form_streak=form_streak,
        last_5_games=last_5_games,
        form_bullets=llm_out.form_bullets,
        league_rank=league_rank,
        league_points=league_points,
        league_matches_played=league_matches_played,
        league_bullets=llm_out.league_bullets,
        injury_bullets=llm_out.injury_bullets,
        news_bullets=llm_out.news_bullets,
    )

    # Step 6: Persist.
    insert_team_report(game_id, team_name, result)
    logger.info("run_team_intelligence: report saved to DB for %s", team_name)

    return result
