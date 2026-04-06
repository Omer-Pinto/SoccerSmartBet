"""Tests for fetch_h2h tool using current football-data.org interface."""

import pytest

from soccersmartbet.pre_gambling_flow.tools.game.fetch_h2h import fetch_h2h


@pytest.mark.integration
def test_fetch_h2h_returns_dict_with_error_key():
    """fetch_h2h always returns a dict with an 'error' key."""
    result = fetch_h2h("Barcelona", "Real Madrid")
    assert isinstance(result, dict)
    assert "error" in result


@pytest.mark.integration
def test_fetch_h2h_result_keys_present():
    """fetch_h2h result always contains all expected keys."""
    result = fetch_h2h("Manchester City", "Arsenal")
    expected_keys = {
        "home_team", "away_team", "upcoming_match_id",
        "upcoming_match_date", "h2h_matches", "total_h2h", "error",
    }
    assert expected_keys.issubset(result.keys()), (
        f"Missing keys: {expected_keys - result.keys()}"
    )


@pytest.mark.integration
def test_fetch_h2h_team_names_preserved():
    """fetch_h2h echoes back input team names."""
    result = fetch_h2h("Barcelona", "Real Madrid")
    assert result["home_team"] == "Barcelona"
    assert result["away_team"] == "Real Madrid"


@pytest.mark.integration
def test_fetch_h2h_h2h_matches_is_list():
    """fetch_h2h always returns h2h_matches as a list."""
    result = fetch_h2h("Barcelona", "Real Madrid")
    assert isinstance(result["h2h_matches"], list)
    assert isinstance(result["total_h2h"], int)


@pytest.mark.integration
def test_fetch_h2h_unknown_team_returns_error():
    """fetch_h2h returns a populated error for an unknown team."""
    result = fetch_h2h("NonExistentTeamXYZ12345", "AnotherFakeTeamABC")
    assert isinstance(result, dict)
    assert "error" in result
    # Either no API key or no match found — error must be non-None
    assert result["error"] is not None
    assert result["h2h_matches"] == []
