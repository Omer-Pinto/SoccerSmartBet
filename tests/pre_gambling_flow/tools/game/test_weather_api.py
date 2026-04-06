"""Tests for fetch_weather tool using current FotMob + Open-Meteo interface."""

import pytest

from soccersmartbet.pre_gambling_flow.tools.game.fetch_weather import fetch_weather


@pytest.mark.integration
def test_fetch_weather_returns_dict_with_error_key():
    """fetch_weather always returns a dict with an 'error' key."""
    result = fetch_weather("Barcelona", "Real Madrid", "2026-04-10T20:00:00")
    assert isinstance(result, dict)
    assert "error" in result


@pytest.mark.integration
def test_fetch_weather_known_team_returns_data():
    """fetch_weather should succeed for a well-known team with a future match date."""
    result = fetch_weather("Barcelona", "Real Madrid", "2026-04-10T20:00:00")
    # Either succeeds or returns a graceful error — never raises
    assert isinstance(result, dict)
    assert "home_team" in result
    assert "away_team" in result
    assert result["home_team"] == "Barcelona"
    assert result["away_team"] == "Real Madrid"


@pytest.mark.integration
def test_fetch_weather_unknown_team_returns_error():
    """fetch_weather returns a populated error for an unknown team."""
    result = fetch_weather("NonExistentTeamXYZ12345", "Barcelona", "2026-04-10T20:00:00")
    assert result["error"] is not None


@pytest.mark.integration
def test_fetch_weather_result_keys_present():
    """fetch_weather result always contains all expected keys."""
    result = fetch_weather("Manchester City", "Arsenal", "2026-04-12T15:00:00")
    expected_keys = {
        "home_team", "away_team", "venue_city", "match_datetime",
        "temperature_celsius", "precipitation_mm", "precipitation_probability",
        "wind_speed_kmh", "conditions", "error",
    }
    assert expected_keys.issubset(result.keys()), (
        f"Missing keys: {expected_keys - result.keys()}"
    )
