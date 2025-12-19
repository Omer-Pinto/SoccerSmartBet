"""Fetch and filter betting odds for selected games.

This module is pure-Python (no DB writes) so it can be wired into the Pre-Gambling
flow state later.
"""

from __future__ import annotations

from typing import Any

from soccersmartbet.pre_gambling_flow.structured_outputs import SelectedGame
from soccersmartbet.pre_gambling_flow.tools.game.fetch_odds import fetch_odds


def _coerce_decimal_odds(value: Any) -> float | None:
    """Return odds as float if valid decimal odds, else None."""
    if value is None:
        return None

    try:
        odds = float(value)
    except (TypeError, ValueError):
        return None

    # Decimal odds must be > 1.0.
    if odds <= 1.0:
        return None

    return odds


def _odds_payload_to_n1_n2_n3(odds_payload: dict[str, Any]) -> tuple[float, float, float] | None:
    """Map Odds API payload keys to Toto n1/n2/n3 (home/away/draw)."""
    odds_home = _coerce_decimal_odds(odds_payload.get("odds_home"))
    odds_draw = _coerce_decimal_odds(odds_payload.get("odds_draw"))
    odds_away = _coerce_decimal_odds(odds_payload.get("odds_away"))

    if odds_home is None or odds_draw is None or odds_away is None:
        return None

    # Project convention (see db/schema.sql comments):
    # n1 = home win, n2 = away win, n3 = draw.
    return odds_home, odds_away, odds_draw


def fetch_and_filter_odds(
    selected_games: list[SelectedGame],
    *,
    min_odds_threshold: float,
    max_daily_games: int,
) -> tuple[list[dict[str, Any]], list[int]]:
    """Fetch odds per selected game and filter by minimum odds threshold.

    Rules:
    - Include only games with complete odds (home/draw/away all present).
    - Include only games where max(home/draw/away) >= min_odds_threshold.
    - Cap results at max_daily_games, preserving input order.

    Returns:
        filtered_games: list of dicts containing the original game fields + n1/n2/n3.
        included_indexes: indexes in the original selected_games list for included games.
    """

    if max_daily_games <= 0:
        return [], []

    filtered_games: list[dict[str, Any]] = []
    included_indexes: list[int] = []

    for index, game in enumerate(selected_games):
        if len(filtered_games) >= max_daily_games:
            break

        try:
            odds_payload = fetch_odds(game.home_team, game.away_team)
        except Exception:
            # Tool implementations should return {"error": ...}, but we guard anyway.
            continue

        if not isinstance(odds_payload, dict):
            continue

        if odds_payload.get("error"):
            continue

        mapped = _odds_payload_to_n1_n2_n3(odds_payload)
        if mapped is None:
            continue

        n1, n2, n3 = mapped

        if max(n1, n2, n3) < float(min_odds_threshold):
            continue

        filtered_games.append(
            {
                "home_team": game.home_team,
                "away_team": game.away_team,
                "match_date": game.match_date,
                "kickoff_time": game.kickoff_time,
                "league": game.league,
                "venue": game.venue,
                "n1": n1,
                "n2": n2,
                "n3": n3,
            }
        )
        included_indexes.append(index)

    return filtered_games, included_indexes
