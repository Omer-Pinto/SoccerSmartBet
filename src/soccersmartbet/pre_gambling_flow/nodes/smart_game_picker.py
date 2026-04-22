"""Smart Game Picker node for the Pre-Gambling Flow.

Selects today's interesting games from football-data.org fixtures cross-referenced
with winner.co.il odds, applies the Israeli Premier League top-6 filter, then
delegates final selection to an LLM with structured output.
"""

from __future__ import annotations

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from soccersmartbet.pre_gambling_flow.prompts import SMART_GAME_PICKER_PROMPT
from soccersmartbet.utils.timezone import utc_to_isr
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

# Hebrew league names on winner.co.il that correspond to UEFA competitions not
# covered by the football-data.org free tier.
_WINNER_EUROPEAN_LEAGUES = {"הליגה האירופית", "ליגת הועידה"}  # Europa League, Conference League


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _canonical(name: str) -> str:
    """Return canonical name if resolvable, else normalised fallback."""
    return resolve_team(name) or normalize_team_name(name)


def _parse_kickoff(iso_str: str | None) -> tuple[str, str]:
    """Parse an ISO-8601 UTC datetime into (YYYY-MM-DD, HH:MM) in ISR time."""
    if not iso_str:
        return ("", "")
    try:
        dt_isr = utc_to_isr(iso_str)
        return (dt_isr.strftime("%Y-%m-%d"), dt_isr.strftime("%H:%M"))
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


def _parse_winner_kickoff(commence_str: str) -> tuple[str, str]:
    """Parse winner.co.il commence_time (ISO with +03:00 offset) into (YYYY-MM-DD, HH:MM).

    Args:
        commence_str: ISO-8601 string, e.g. ``"2026-04-16T19:44:00+03:00"``.

    Returns:
        A ``(date, time)`` tuple in ISR wall-clock time, or ``("", "")`` on failure.
    """
    if not commence_str:
        return ("", "")
    try:
        dt = utc_to_isr(commence_str)
        return (dt.strftime("%Y-%m-%d"), dt.strftime("%H:%M"))
    except (ValueError, AttributeError):
        return ("", "")


def _fallback_winner_european(
    winner_events: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Extract EL/ECL games directly from winner events when cross-ref yields nothing.

    Only includes events where both team names resolve to English canonical names
    via :func:`resolve_team`, so downstream LLM prompts receive consistent names.

    Args:
        winner_events: Raw event dicts from :func:`fetch_all_winner_odds`.

    Returns:
        List of eligible-game dicts in the same shape produced by the normal
        cross-reference loop, with ``match_id`` set to ``None``.
    """
    eligible: list[dict[str, Any]] = []
    for event in winner_events:
        league_he: str = event.get("league", "")
        if league_he not in _WINNER_EUROPEAN_LEAGUES:
            continue

        home_canonical = resolve_team(event["home_team"])
        away_canonical = resolve_team(event["away_team"])

        if not home_canonical or not away_canonical:
            logger.info(
                "smart_game_picker: EL/ECL skip — unresolved team(s): %s [%s] vs %s [%s]",
                event["home_team"],
                home_canonical,
                event["away_team"],
                away_canonical,
            )
            continue

        match_date, kickoff_time = _parse_winner_kickoff(event.get("commence_time", ""))
        league_en = (
            "Europa League" if league_he == "הליגה האירופית" else "Conference League"
        )

        eligible.append(
            {
                "match_id": None,
                "home_team": home_canonical,
                "away_team": away_canonical,
                "competition": league_en,
                "match_date": match_date,
                "kickoff_time": kickoff_time,
                "venue": "",
                "odds_home": event["odds_home"],
                "odds_draw": event["odds_draw"],
                "odds_away": event["odds_away"],
                "winner_event": event,
            }
        )

    return eligible


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
            f"| {g['match_date']} {g['kickoff_time']} ISR "
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
    logger.info("smart_game_picker: starting")

    fixtures_result = fetch_daily_fixtures()
    fixtures_error = fixtures_result.get("error")
    if fixtures_error:
        # A fetch failure is NOT a genuine no-games day.  Raise so the flow
        # fails loudly and daily_runs is left with pre_gambling_started_at set
        # but no completed_at — the wall-clock poller will log this as a crash
        # requiring manual intervention (avoids silent data loss).
        raise RuntimeError(f"smart_game_picker: fixtures fetch failed — {fixtures_error}")
    fixtures: list[dict[str, Any]] = fixtures_result.get("fixtures") or []
    logger.info("smart_game_picker: %d fixtures fetched", len(fixtures))

    winner_result = fetch_all_winner_odds()
    winner_error = winner_result.get("error")
    if winner_error:
        raise RuntimeError(f"smart_game_picker: winner odds fetch failed — {winner_error}")
    winner_events: list[dict[str, Any]] = winner_result.get("events") or []
    logger.info("smart_game_picker: %d winner events fetched", len(winner_events))

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

    logger.info("smart_game_picker: %d eligible games", len(eligible))

    # Fallback: football-data.org free tier excludes EL/ECL; on those days
    # the cross-ref loop produces nothing even though winner has the events.
    if not eligible:
        eligible = _fallback_winner_european(winner_events)
        if eligible:
            logger.info(
                "smart_game_picker: %d eligible games from winner EL/ECL fallback",
                len(eligible),
            )

    # Assemble top-6 names for the prompt
    top6_display = ", ".join(sorted(top6_israeli)) if top6_israeli else "unavailable"

    if not eligible:
        return {
            "all_games": [],
            "phase": Phase.FILTERING,
            "messages": [
                AIMessage(content="No eligible games found today (no fixture/odds overlap).")
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
    logger.info("smart_game_picker: LLM selected %d games", len(selected.games))

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
                home_win_odd=source["odds_home"],
                away_win_odd=source["odds_away"],
                draw_odd=source["odds_draw"],
            )
        )

    logger.info("smart_game_picker: returning %d games", len(game_contexts))

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
