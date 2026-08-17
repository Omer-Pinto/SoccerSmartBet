"""Unit tests for _fallback_winner_european in smart_game_picker.

Verifies that EL/ECL events from winner.co.il are filtered to today's ISR
date only, since winner.co.il lists events days ahead.
"""
from __future__ import annotations

from datetime import datetime
from unittest.mock import patch

from soccersmartbet.pre_gambling_flow.nodes.smart_game_picker import (
    _fallback_winner_european,
)
from soccersmartbet.utils.timezone import ISR_TZ


def _make_event(home: str, away: str, commence_time: str) -> dict:
    return {
        "league": "Europa League",
        "home_team": home,
        "away_team": away,
        "commence_time": commence_time,
        "odds_home": 1.5,
        "odds_draw": 3.5,
        "odds_away": 5.0,
    }


def test_fallback_winner_european_filters_non_today_events() -> None:
    fixed_now = datetime(2026, 4, 16, 12, 0, tzinfo=ISR_TZ)
    events = [
        _make_event("Team A", "Team B", "2026-04-16T19:44:00+03:00"),
        _make_event("Team C", "Team D", "2026-04-19T19:44:00+03:00"),
    ]

    def fake_resolve_team(name: str) -> str:
        return name

    with (
        patch(
            "soccersmartbet.pre_gambling_flow.nodes.smart_game_picker.now_isr",
            return_value=fixed_now,
        ),
        patch(
            "soccersmartbet.pre_gambling_flow.nodes.smart_game_picker.resolve_team",
            side_effect=fake_resolve_team,
        ),
    ):
        result = _fallback_winner_european(events)

    assert len(result) == 1
    assert result[0]["home_team"] == "Team A"
    assert result[0]["away_team"] == "Team B"
    assert result[0]["match_date"] == "2026-04-16"


def test_fallback_winner_european_skips_unparseable_date() -> None:
    fixed_now = datetime(2026, 4, 16, 12, 0, tzinfo=ISR_TZ)
    events = [_make_event("Team A", "Team B", "")]

    def fake_resolve_team(name: str) -> str:
        return name

    with (
        patch(
            "soccersmartbet.pre_gambling_flow.nodes.smart_game_picker.now_isr",
            return_value=fixed_now,
        ),
        patch(
            "soccersmartbet.pre_gambling_flow.nodes.smart_game_picker.resolve_team",
            side_effect=fake_resolve_team,
        ),
    ):
        result = _fallback_winner_european(events)

    assert result == []
