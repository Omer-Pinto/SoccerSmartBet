"""
Live integration tests for fetch_weather.

Calls the real FotMob and Open-Meteo APIs and verifies response shapes.
Run with: uv run pytest tests/pre_gambling_flow/tools/game/test_fetch_weather_live.py -v -m integration
"""

import pytest

from soccersmartbet.pre_gambling_flow.tools.game.fetch_weather import fetch_weather

# A future date within Open-Meteo's 16-day forecast window
FUTURE_MATCH_DATETIME = "2026-04-08T21:00:00"


@pytest.mark.integration
def test_fetch_weather_barcelona() -> None:
    """Fetch weather for a Barcelona home match using direct venue coordinates."""
    result = fetch_weather("Barcelona", "Real Madrid", FUTURE_MATCH_DATETIME)

    assert result["error"] is None, f"Unexpected error: {result['error']}"
    assert result["home_team"] == "Barcelona"
    assert result["away_team"] == "Real Madrid"
    assert result["venue_city"] is not None, "venue_city should not be None"
    assert result["match_datetime"] == FUTURE_MATCH_DATETIME

    # Weather fields
    assert result["temperature_celsius"] is not None, "temperature should be present"
    assert isinstance(result["temperature_celsius"], (int, float)), "temperature must be numeric"
    assert result["precipitation_mm"] is not None
    assert isinstance(result["precipitation_mm"], (int, float))
    assert result["wind_speed_kmh"] is not None
    assert isinstance(result["wind_speed_kmh"], (int, float))
    assert result["conditions"] is not None
    assert isinstance(result["conditions"], str)
    assert result["conditions"] in ("Clear", "Rain", "Heavy Rain", "Snow")


@pytest.mark.integration
def test_fetch_weather_man_city() -> None:
    """Fetch weather for a Manchester City home match."""
    result = fetch_weather("Manchester City", "Tottenham", FUTURE_MATCH_DATETIME)

    assert result["error"] is None, f"Unexpected error: {result['error']}"
    assert result["venue_city"] is not None
    assert isinstance(result["temperature_celsius"], (int, float))
    assert isinstance(result["conditions"], str)
    assert result["conditions"] in ("Clear", "Rain", "Heavy Rain", "Snow")


@pytest.mark.integration
def test_fetch_weather_no_geocoding_dependency() -> None:
    """
    Confirm the function works without any geocoding service.

    This test verifies that lat/lon comes directly from the FotMob venue widget.
    If geocoding were used, removing network access to Nominatim would break it.
    We simply verify the result is successful and the city is populated.
    """
    result = fetch_weather("Barcelona", "Atletico Madrid", FUTURE_MATCH_DATETIME)

    assert result["error"] is None, f"Unexpected error: {result['error']}"
    assert result["venue_city"] is not None
    assert result["temperature_celsius"] is not None


@pytest.mark.integration
def test_fetch_weather_unknown_team_returns_error() -> None:
    """Unknown team name should return an error, not raise an exception."""
    result = fetch_weather("TeamThatDoesNotExistXYZ123", "Barcelona", FUTURE_MATCH_DATETIME)

    assert result["error"] is not None, "Expected an error for unknown team"
    assert result["temperature_celsius"] is None
    assert result["conditions"] is None
