"""Tests for fetch_odds tool using current The Odds API interface."""

import pytest

from soccersmartbet.pre_gambling_flow.tools.game.fetch_odds import fetch_odds


@pytest.mark.integration
def test_fetch_odds_returns_dict_with_error_key():
    """fetch_odds always returns a dict with an 'error' key."""
    result = fetch_odds("Barcelona", "Real Madrid")
    assert isinstance(result, dict)
    assert "error" in result


@pytest.mark.integration
def test_fetch_odds_result_keys_present():
    """fetch_odds result always contains all expected keys."""
    result = fetch_odds("Chelsea", "Arsenal")
    expected_keys = {
        "home_team", "away_team", "match_id", "commence_time",
        "odds_home", "odds_draw", "odds_away", "bookmaker", "error",
    }
    assert expected_keys.issubset(result.keys()), (
        f"Missing keys: {expected_keys - result.keys()}"
    )


@pytest.mark.integration
def test_fetch_odds_team_names_preserved():
    """fetch_odds always echoes back the input team names."""
    result = fetch_odds("Barcelona", "Real Madrid")
    assert result["home_team"] == "Barcelona"
    assert result["away_team"] == "Real Madrid"


@pytest.mark.integration
def test_fetch_odds_unknown_team_returns_graceful_error():
    """fetch_odds returns a dict (not an exception) for teams with no odds."""
    result = fetch_odds("NonExistentTeamXYZ12345", "AnotherFakeTeamABC")
    assert isinstance(result, dict)
    assert "error" in result
    # error should be a string, not None, since no match will be found
    assert result["error"] is not None
