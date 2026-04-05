"""Live integration tests for all team tools using real FotMob API calls.

Run with:
    uv run pytest tests/pre_gambling_flow/tools/team/test_team_tools_live.py -v

These tests make real network requests to FotMob and verify actual Barcelona
data which has known injured players, a known league position, and recent
match history.
"""

import pytest

from soccersmartbet.pre_gambling_flow.tools.team.fetch_form import fetch_form
from soccersmartbet.pre_gambling_flow.tools.team.fetch_injuries import fetch_injuries
from soccersmartbet.pre_gambling_flow.tools.team.fetch_league_position import fetch_league_position
from soccersmartbet.pre_gambling_flow.tools.team.calculate_recovery_time import calculate_recovery_time
from soccersmartbet.pre_gambling_flow.tools.team.fetch_team_news import fetch_team_news

TEAM = "Barcelona"
UPCOMING_DATE = "2026-04-08"


@pytest.mark.integration
def test_fetch_form_returns_matches():
    """fetch_form should return recent match history with no error."""
    result = fetch_form(TEAM)

    assert result["error"] is None, f"Unexpected error: {result['error']}"
    assert result["team_name"] != "", "team_name should be non-empty"
    assert isinstance(result["matches"], list), "matches should be a list"
    assert len(result["matches"]) > 0, "Barcelona should have recent matches"

    match = result["matches"][0]
    assert "date" in match
    assert "opponent" in match
    assert "home_away" in match
    assert match["home_away"] in ("HOME", "AWAY")
    assert "result" in match
    assert match["result"] in ("W", "D", "L", "?")
    assert "goals_for" in match
    assert "goals_against" in match

    record = result["record"]
    assert "wins" in record and "draws" in record and "losses" in record
    total = record["wins"] + record["draws"] + record["losses"]
    assert total == len(result["matches"]), "record totals should equal match count"


@pytest.mark.integration
def test_fetch_form_unknown_team_returns_error():
    """fetch_form should return a populated error for an unknown team."""
    result = fetch_form("NonExistentTeamXYZ12345")

    assert result["error"] is not None
    assert result["matches"] == []


@pytest.mark.integration
def test_fetch_injuries_returns_players():
    """fetch_injuries should return known injured Barcelona players via squad data."""
    result = fetch_injuries(TEAM)

    assert result["error"] is None, f"Unexpected error: {result['error']}"
    assert result["team_name"] != ""
    assert result["source"] == "squad", "source must be 'squad' (not match lineup)"
    assert isinstance(result["injuries"], list)
    assert result["total_injuries"] == len(result["injuries"])

    # Barcelona has known injuries — assert at least one injured player
    assert result["total_injuries"] > 0, (
        "Barcelona has known injured players; list should not be empty"
    )

    injury = result["injuries"][0]
    assert "player_name" in injury
    assert "position_group" in injury
    assert injury["position_group"] in ("keepers", "defenders", "midfielders", "attackers")
    assert "injury_type" in injury
    assert "expected_return" in injury

    # Known injured players from live data
    injured_names = {i["player_name"] for i in result["injuries"]}
    known_injured = {"Frenkie de Jong", "Andreas Christensen"}
    assert known_injured & injured_names, (
        f"Expected at least one of {known_injured} in injury list, got {injured_names}"
    )


@pytest.mark.integration
def test_fetch_injuries_unknown_team_returns_error():
    """fetch_injuries should return an error for an unknown team."""
    result = fetch_injuries("NonExistentTeamXYZ12345")

    assert result["error"] is not None
    assert result["injuries"] == []
    assert result["total_injuries"] == 0


@pytest.mark.integration
def test_fetch_league_position_returns_position():
    """fetch_league_position should return Barcelona's La Liga standing."""
    result = fetch_league_position(TEAM)

    assert result["error"] is None, f"Unexpected error: {result['error']}"
    assert result["team_name"] != ""
    assert result["league_name"] is not None
    assert isinstance(result["position"], int), "position should be an integer"
    assert result["position"] >= 1, "position should be at least 1"
    assert isinstance(result["played"], int), "played should be an integer"
    assert result["played"] > 0
    assert result["points"] is not None and result["points"] >= 0
    assert result["form"] is not None
    assert len(result["form"]) > 0, "form string should not be empty"
    assert all(c in "WDL?" for c in result["form"]), "form chars must be W/D/L/?"


@pytest.mark.integration
def test_fetch_league_position_unknown_team_returns_error():
    """fetch_league_position should return an error for an unknown team."""
    result = fetch_league_position("NonExistentTeamXYZ12345")

    assert result["error"] is not None
    assert result["position"] is None


@pytest.mark.integration
def test_calculate_recovery_time_returns_days():
    """calculate_recovery_time should compute numeric recovery days."""
    result = calculate_recovery_time(TEAM, UPCOMING_DATE)

    assert result["error"] is None, f"Unexpected error: {result['error']}"
    assert result["team_name"] != ""
    assert result["last_match_date"] is not None
    assert isinstance(result["recovery_days"], int), "recovery_days should be an integer"
    assert result["recovery_days"] >= 0, "recovery_days should be non-negative"
    assert result["recovery_status"] in ("Short", "Normal", "Extended")
    assert result["upcoming_match_date"] == UPCOMING_DATE


@pytest.mark.integration
def test_calculate_recovery_time_unknown_team_returns_error():
    """calculate_recovery_time should return an error for an unknown team."""
    result = calculate_recovery_time("NonExistentTeamXYZ12345", UPCOMING_DATE)

    assert result["error"] is not None
    assert result["recovery_days"] is None


@pytest.mark.integration
def test_fetch_team_news_returns_articles():
    """fetch_team_news should return a list of news articles for Barcelona."""
    result = fetch_team_news(TEAM, limit=5)

    assert result["error"] is None, f"Unexpected error: {result['error']}"
    assert result["team_name"] != ""
    assert isinstance(result["articles"], list)
    assert len(result["articles"]) > 0, "Barcelona should have news articles"
    assert len(result["articles"]) <= 5, "Should respect the limit parameter"
    assert isinstance(result["total_available"], int)
    assert result["total_available"] >= len(result["articles"])

    article = result["articles"][0]
    assert "title" in article
    assert article["title"] != "", "Article title should not be empty"
    assert "source" in article
    assert "published" in article
    assert "language" in article


@pytest.mark.integration
def test_fetch_team_news_unknown_team_returns_error():
    """fetch_team_news should return an error for an unknown team."""
    result = fetch_team_news("NonExistentTeamXYZ12345")

    assert result["error"] is not None
    assert result["articles"] == []
    assert result["total_available"] == 0


@pytest.mark.integration
def test_team_tools_package_imports():
    """All team tools should be importable from the team package."""
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
