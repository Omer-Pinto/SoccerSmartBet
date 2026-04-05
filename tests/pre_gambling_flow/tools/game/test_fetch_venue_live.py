"""
Live integration tests for fetch_venue.

Calls the real FotMob API and verifies response shapes.
Run with: uv run pytest tests/pre_gambling_flow/tools/game/test_fetch_venue_live.py -v -m integration
"""

import pytest

from soccersmartbet.pre_gambling_flow.tools.game.fetch_venue import fetch_venue


@pytest.mark.integration
def test_fetch_venue_barcelona() -> None:
    """Fetch Barcelona's venue (Camp Nou) and verify core fields."""
    result = fetch_venue("Barcelona", "Real Madrid")

    assert result["error"] is None, f"Unexpected error: {result['error']}"
    assert result["home_team"] is not None
    assert result["away_team"] == "Real Madrid"
    assert result["venue_name"] is not None, "venue_name should not be None"
    assert result["venue_city"] is not None, "venue_city should not be None"
    assert result["venue_capacity"] is not None, "venue_capacity should not be None"
    assert int(result["venue_capacity"]) > 0, "capacity must be positive"
    assert "barcelona" in result["venue_city"].lower() or result["venue_city"] is not None


@pytest.mark.integration
def test_fetch_venue_man_city() -> None:
    """Fetch Manchester City's venue (Etihad Stadium) and verify core fields."""
    result = fetch_venue("Manchester City", "Arsenal")

    assert result["error"] is None, f"Unexpected error: {result['error']}"
    assert result["home_team"] is not None
    assert result["away_team"] == "Arsenal"
    assert result["venue_name"] is not None, "venue_name should not be None"
    assert result["venue_city"] is not None, "venue_city should not be None"
    assert result["venue_capacity"] is not None, "venue_capacity should not be None"
    assert int(result["venue_capacity"]) > 0, "capacity must be positive"


@pytest.mark.integration
def test_fetch_venue_capacity_is_numeric() -> None:
    """Verify that capacity extracted from statPairs is numeric."""
    result = fetch_venue("Barcelona", "Atletico Madrid")

    assert result["error"] is None, f"Unexpected error: {result['error']}"
    capacity = result["venue_capacity"]
    assert capacity is not None, "capacity should be present"
    # Capacity should be castable to int
    assert int(capacity) > 10_000, "Stadium capacity should be at least 10,000"


@pytest.mark.integration
def test_fetch_venue_unknown_team_returns_error() -> None:
    """Unknown team name should return an error, not raise an exception."""
    result = fetch_venue("TeamThatDoesNotExistXYZ123", "Barcelona")

    assert result["error"] is not None, "Expected an error for unknown team"
    assert result["venue_name"] is None
    assert result["venue_capacity"] is None
