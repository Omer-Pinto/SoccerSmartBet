"""Smart Game Picker node for the Pre-Gambling Flow.

Selects today's interesting games from football-data.org fixtures cross-referenced
with winner.co.il odds, applies the Israeli Premier League top-6 filter, then
delegates final selection to an LLM with structured output.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from soccersmartbet.pre_gambling_flow.prompts import SMART_GAME_PICKER_PROMPT
from soccersmartbet.pre_gambling_flow.state import GameContext, Phase, PreGamblingState
from soccersmartbet.pre_gambling_flow.structured_outputs import SelectedGames
from soccersmartbet.pre_gambling_flow.tools.fotmob_client import get_fotmob_client
from soccersmartbet.pre_gambling_flow.tools.game.fetch_daily_fixtures import (
    fetch_daily_fixtures,
)
from soccersmartbet.pre_gambling_flow.tools.game.fetch_winner_odds import (
    fetch_all_winner_odds,
)
from soccersmartbet.team_registry import normalize_team_name, resolve_team

PICKER_MODEL = os.getenv("SMART_PICKER_MODEL", "gpt-5.4-mini")

_ISRAELI_LEAGUE_ID = 127


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _canonical(name: str) -> str:
    """Return canonical name if resolvable, else normalised fallback."""
    return resolve_team(name) or normalize_team_name(name)


def _parse_kickoff(iso_str: str | None) -> tuple[str, str]:
    """Parse an ISO-8601 UTC datetime into (YYYY-MM-DD, HH:MM)."""
    if not iso_str:
        return ("", "")
    try:
        dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        dt_utc = dt.astimezone(timezone.utc)
        return (dt_utc.strftime("%Y-%m-%d"), dt_utc.strftime("%H:%M"))
    except (ValueError, AttributeError):
        return ("", "")


def _extract_top6(league_table: Any) -> set[str]:
    """
    Extract the set of canonical names for the top-6 teams in the table.

    Expects the raw response from ``get_league_table(127)`` which is a list;
    the row path is ``table[0]["data"]["table"]["all"]`` with ``idx`` (1-based)
    and ``name`` per entry.
    """
    top6: set[str] = set()
    if not isinstance(league_table, list) or not league_table:
        return top6
    try:
        rows: list[dict[str, Any]] = league_table[0]["data"]["table"]["all"]
    except (IndexError, KeyError, TypeError):
        return top6
    for row in rows:
        idx = row.get("idx")
        name = row.get("name") or ""
        if isinstance(idx, int) and idx <= 6 and name:
            canonical = _canonical(name)
            top6.add(canonical)
    return top6


def _build_winner_index(
    events: list[dict[str, Any]],
) -> dict[tuple[str, str], dict[str, Any]]:
    """
    Build a lookup dict keyed by (canonical_home, canonical_away) for winner events.
    """
    index: dict[tuple[str, str], dict[str, Any]] = {}
    for event in events:
        key = (_canonical(event["home_team"]), _canonical(event["away_team"]))
        index[key] = event
    return index


def _is_israeli_league(competition: str) -> bool:
    lc = competition.lower()
    return "israel" in lc or "ligat" in lc


def _format_eligible_games(
    eligible: list[dict[str, Any]],
) -> str:
    """Format eligible games for the LLM user message."""
    lines: list[str] = []
    for g in eligible:
        odds_str = (
            f"1={g['odds_home']:.2f} / X={g['odds_draw']:.2f} / 2={g['odds_away']:.2f}"
        )
        lines.append(
            f"- {g['home_team']} vs {g['away_team']} "
            f"| {g['competition']} "
            f"| {g['match_date']} {g['kickoff_time']} UTC "
            f"| Odds: {odds_str}"
        )
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Node
# ---------------------------------------------------------------------------


def smart_game_picker(state: PreGamblingState) -> dict:  # noqa: ARG001
    """LangGraph node: select today's interesting games for betting analysis.

    Args:
        state: Current Pre-Gambling Flow state (unused directly; node is stateless).

    Returns:
        State update dict with ``all_games``, ``phase``, and ``messages``.
    """
    fixtures_result = fetch_daily_fixtures()
    fixtures: list[dict[str, Any]] = fixtures_result.get("fixtures") or []

    winner_result = fetch_all_winner_odds()
    winner_events: list[dict[str, Any]] = winner_result.get("events") or []

    winner_index = _build_winner_index(winner_events)

    # Fetch Israeli Premier League table for top-6 check
    client = get_fotmob_client()
    raw_table = client.get_league_table(_ISRAELI_LEAGUE_ID)
    top6_israeli = _extract_top6(raw_table)

    # Cross-reference fixtures with winner odds
    eligible: list[dict[str, Any]] = []
    israeli_count = 0

    for fixture in fixtures:
        home_canonical = _canonical(fixture["home_team"])
        away_canonical = _canonical(fixture["away_team"])
        key = (home_canonical, away_canonical)

        winner_event = winner_index.get(key)
        if winner_event is None:
            continue

        competition: str = fixture.get("competition") or ""
        match_date, kickoff_time = _parse_kickoff(fixture.get("kickoff_time"))

        if _is_israeli_league(competition):
            if israeli_count >= 1:
                continue
            if not (home_canonical in top6_israeli or away_canonical in top6_israeli):
                continue
            israeli_count += 1

        eligible.append(
            {
                "match_id": fixture.get("match_id"),
                "home_team": fixture["home_team"],
                "away_team": fixture["away_team"],
                "competition": competition,
                "match_date": match_date,
                "kickoff_time": kickoff_time,
                "venue": "",
                "odds_home": winner_event["odds_home"],
                "odds_draw": winner_event["odds_draw"],
                "odds_away": winner_event["odds_away"],
                "winner_event": winner_event,
            }
        )

    # Assemble top-6 names for the prompt
    top6_display = ", ".join(sorted(top6_israeli)) if top6_israeli else "unavailable"

    if len(eligible) < 3:
        return {
            "all_games": [],
            "phase": Phase.FILTERING,
            "messages": [
                AIMessage(
                    content=f"Insufficient eligible games ({len(eligible)} found, need 3). Skipping today."
                )
            ],
        }

    games_block = _format_eligible_games(eligible)

    user_message_text = f"""Today's eligible games (fixtures present on both football-data.org AND winner.co.il):

{games_block}

---
GAME SELECTION PREFERENCES:
1. Premier League and La Liga are ALWAYS preferred over other leagues. Then Bundesliga, Serie A, Ligue 1 in that order.
2. Israeli Premier League: maximum 1 game, and ONLY if at least one team is in the top 6 of the table. Top-6 teams: {top6_display}
3. No minimum odds threshold.
4. Within La Liga: prefer Barcelona and Real Madrid games over others.
5. Minimum 3 games per day.

Select the most interesting games for today's betting analysis."""

    system_msg = SystemMessage(content=SMART_GAME_PICKER_PROMPT)
    human_msg = HumanMessage(content=user_message_text)

    model = ChatOpenAI(model=PICKER_MODEL, temperature=0.3)
    structured_model = model.with_structured_output(SelectedGames)

    selected: SelectedGames = structured_model.invoke([system_msg, human_msg])

    # Build a map from (normalised_home, normalised_away) → eligible entry
    # so we can recover odds for each LLM-selected game
    eligible_map: dict[tuple[str, str], dict[str, Any]] = {
        (_canonical(g["home_team"]), _canonical(g["away_team"])): g
        for g in eligible
    }

    game_contexts: list[GameContext] = []
    for sg in selected.games:
        home_key = _canonical(sg.home_team)
        away_key = _canonical(sg.away_team)
        source = eligible_map.get((home_key, away_key))
        if source is None:
            continue

        game_contexts.append(
            GameContext(
                game_id=0,
                home_team=sg.home_team,
                away_team=sg.away_team,
                match_date=sg.match_date,
                kickoff_time=sg.kickoff_time,
                league=sg.league,
                venue=sg.venue or "",
                n1=source["odds_home"],
                n2=source["odds_away"],
                n3=source["odds_draw"],
            )
        )

    ai_message = AIMessage(
        content=(
            f"Selected {len(game_contexts)} games for today's betting analysis. "
            f"Reasoning: {selected.selection_reasoning}"
        )
    )

    return {
        "all_games": game_contexts,
        "phase": Phase.FILTERING,
        "messages": [ai_message],
    }
