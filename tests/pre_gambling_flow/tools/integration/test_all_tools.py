"""
Integration tests: verify every tool in the current suite returns a dict
with an 'error' key when called against real team names.

These tests make live network requests (FotMob, Open-Meteo, football-data.org,
The Odds API, winner.co.il). Run with:

    uv run pytest tests/pre_gambling_flow/tools/integration/test_all_tools.py -v -m integration

Team names used: "Barcelona" and "Real Madrid" — both well-known clubs
supported by all back-ends.
"""

import pytest

# Game tools
from soccersmartbet.pre_gambling_flow.tools.game.fetch_h2h import fetch_h2h
from soccersmartbet.pre_gambling_flow.tools.game.fetch_venue import fetch_venue
from soccersmartbet.pre_gambling_flow.tools.game.fetch_weather import fetch_weather
from soccersmartbet.pre_gambling_flow.tools.game.fetch_odds import fetch_odds
from soccersmartbet.pre_gambling_flow.tools.game.fetch_winner_odds import fetch_winner_odds
from soccersmartbet.pre_gambling_flow.tools.game.fetch_daily_fixtures import fetch_daily_fixtures

# Team tools
from soccersmartbet.pre_gambling_flow.tools.team.fetch_form import fetch_form
from soccersmartbet.pre_gambling_flow.tools.team.fetch_injuries import fetch_injuries
from soccersmartbet.pre_gambling_flow.tools.team.fetch_league_position import fetch_league_position
from soccersmartbet.pre_gambling_flow.tools.team.calculate_recovery_time import calculate_recovery_time
from soccersmartbet.pre_gambling_flow.tools.team.fetch_team_news import fetch_team_news

HOME_TEAM = "Barcelona"
AWAY_TEAM = "Real Madrid"
MATCH_DATETIME = "2026-04-10T20:00:00"
UPCOMING_DATE = "2026-04-10"


# ---------------------------------------------------------------------------
# Smoke test: all tools importable from their package __init__
# ---------------------------------------------------------------------------


def test_game_tools_importable():
    """All game tools should be importable from the game package __init__."""
    from soccersmartbet.pre_gambling_flow.tools.game import (
        fetch_h2h,
        fetch_venue,
        fetch_weather,
        fetch_odds,
        fetch_winner_odds,
        fetch_all_winner_odds,
        fetch_daily_fixtures,
    )
    assert callable(fetch_h2h)
    assert callable(fetch_venue)
    assert callable(fetch_weather)
    assert callable(fetch_odds)
    assert callable(fetch_winner_odds)
    assert callable(fetch_all_winner_odds)
    assert callable(fetch_daily_fixtures)


def test_team_tools_importable():
    """All team tools should be importable from the team package __init__."""
    from soccersmartbet.pre_gambling_flow.tools.team import (
        fetch_form,
        fetch_injuries,
        fetch_league_position,
        calculate_recovery_time,
        fetch_team_news,
    )
    assert callable(fetch_form)
    assert callable(fetch_injuries)
    assert callable(fetch_league_position)
    assert callable(calculate_recovery_time)
    assert callable(fetch_team_news)


# ---------------------------------------------------------------------------
# Game tools — each must return a dict with an 'error' key
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_fetch_h2h_returns_error_key():
    """fetch_h2h returns a dict with 'error' key."""
    result = fetch_h2h(HOME_TEAM, AWAY_TEAM)
    assert isinstance(result, dict)
    assert "error" in result
    assert result["home_team"] == HOME_TEAM
    assert result["away_team"] == AWAY_TEAM
    assert isinstance(result["h2h_matches"], list)


@pytest.mark.integration
def test_fetch_venue_returns_error_key():
    """fetch_venue returns a dict with 'error' key."""
    result = fetch_venue(HOME_TEAM, AWAY_TEAM)
    assert isinstance(result, dict)
    assert "error" in result
    assert result["error"] is None, f"Unexpected error: {result['error']}"
    assert result["home_team"] is not None
    assert result["away_team"] == AWAY_TEAM


@pytest.mark.integration
def test_fetch_weather_returns_error_key():
    """fetch_weather returns a dict with 'error' key."""
    result = fetch_weather(HOME_TEAM, AWAY_TEAM, MATCH_DATETIME)
    assert isinstance(result, dict)
    assert "error" in result
    assert result["error"] is None, f"Unexpected error: {result['error']}"
    assert result["home_team"] == HOME_TEAM
    assert result["away_team"] == AWAY_TEAM


@pytest.mark.integration
def test_fetch_odds_returns_error_key():
    """fetch_odds returns a dict with 'error' key."""
    result = fetch_odds(HOME_TEAM, AWAY_TEAM)
    assert isinstance(result, dict)
    assert "error" in result
    assert result["home_team"] == HOME_TEAM
    assert result["away_team"] == AWAY_TEAM


@pytest.mark.integration
def test_fetch_winner_odds_returns_error_key():
    """fetch_winner_odds returns a dict with 'error' key."""
    result = fetch_winner_odds(HOME_TEAM, AWAY_TEAM)
    assert isinstance(result, dict)
    assert "error" in result
    assert result["home_team"] == HOME_TEAM
    assert result["away_team"] == AWAY_TEAM


@pytest.mark.integration
def test_fetch_daily_fixtures_returns_error_key():
    """fetch_daily_fixtures returns a dict with 'error' key."""
    result = fetch_daily_fixtures(UPCOMING_DATE)
    assert isinstance(result, dict)
    assert "error" in result


# ---------------------------------------------------------------------------
# Team tools (home team) — each must return a dict with an 'error' key
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_fetch_form_home_returns_error_key():
    """fetch_form (home) returns a dict with 'error' key."""
    result = fetch_form(HOME_TEAM)
    assert isinstance(result, dict)
    assert "error" in result
    assert result["error"] is None, f"Unexpected error: {result['error']}"
    assert isinstance(result["matches"], list)


@pytest.mark.integration
def test_fetch_injuries_home_returns_error_key():
    """fetch_injuries (home) returns a dict with 'error' key."""
    result = fetch_injuries(HOME_TEAM)
    assert isinstance(result, dict)
    assert "error" in result
    assert result["error"] is None, f"Unexpected error: {result['error']}"
    assert isinstance(result["injuries"], list)


@pytest.mark.integration
def test_fetch_league_position_home_returns_error_key():
    """fetch_league_position (home) returns a dict with 'error' key."""
    result = fetch_league_position(HOME_TEAM)
    assert isinstance(result, dict)
    assert "error" in result
    assert result["error"] is None, f"Unexpected error: {result['error']}"


@pytest.mark.integration
def test_calculate_recovery_time_home_returns_error_key():
    """calculate_recovery_time (home) returns a dict with 'error' key."""
    result = calculate_recovery_time(HOME_TEAM, UPCOMING_DATE)
    assert isinstance(result, dict)
    assert "error" in result
    assert result["error"] is None, f"Unexpected error: {result['error']}"


@pytest.mark.integration
def test_fetch_team_news_home_returns_error_key():
    """fetch_team_news (home) returns a dict with 'error' key."""
    result = fetch_team_news(HOME_TEAM)
    assert isinstance(result, dict)
    assert "error" in result
    assert result["error"] is None, f"Unexpected error: {result['error']}"
    assert isinstance(result["articles"], list)


# ---------------------------------------------------------------------------
# Team tools (away team) — each must return a dict with an 'error' key
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_fetch_form_away_returns_error_key():
    """fetch_form (away) returns a dict with 'error' key."""
    result = fetch_form(AWAY_TEAM)
    assert isinstance(result, dict)
    assert "error" in result
    assert result["error"] is None, f"Unexpected error: {result['error']}"


@pytest.mark.integration
def test_fetch_injuries_away_returns_error_key():
    """fetch_injuries (away) returns a dict with 'error' key."""
    result = fetch_injuries(AWAY_TEAM)
    assert isinstance(result, dict)
    assert "error" in result
    assert result["error"] is None, f"Unexpected error: {result['error']}"


@pytest.mark.integration
def test_fetch_league_position_away_returns_error_key():
    """fetch_league_position (away) returns a dict with 'error' key."""
    result = fetch_league_position(AWAY_TEAM)
    assert isinstance(result, dict)
    assert "error" in result
    assert result["error"] is None, f"Unexpected error: {result['error']}"


@pytest.mark.integration
def test_calculate_recovery_time_away_returns_error_key():
    """calculate_recovery_time (away) returns a dict with 'error' key."""
    result = calculate_recovery_time(AWAY_TEAM, UPCOMING_DATE)
    assert isinstance(result, dict)
    assert "error" in result
    assert result["error"] is None, f"Unexpected error: {result['error']}"


@pytest.mark.integration
def test_fetch_team_news_away_returns_error_key():
    """fetch_team_news (away) returns a dict with 'error' key."""
    result = fetch_team_news(AWAY_TEAM)
    assert isinstance(result, dict)
    assert "error" in result
    assert result["error"] is None, f"Unexpected error: {result['error']}"
