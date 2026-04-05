"""Live integration tests for fetch_daily_fixtures.

These tests hit the real football-data.org API. They are guarded by
``pytest.mark.integration`` and skipped automatically when
``FOOTBALL_DATA_API_KEY`` is absent.

NOTE: The free tier allows 10 requests/minute. This file makes at most
2 API calls across all tests combined to stay well within that limit.
"""

import os
from datetime import date, timedelta

import pytest
from dotenv import load_dotenv

load_dotenv()

pytestmark = pytest.mark.integration


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _has_api_key() -> bool:
    return bool(os.getenv("FOOTBALL_DATA_API_KEY"))


def _assert_fixture_shape(fixture: dict) -> None:
    """Assert that a single fixture dict has the required keys and types."""
    required_keys = [
        "match_id",
        "home_team",
        "away_team",
        "competition",
        "kickoff_time",
        "status",
        "home_team_id",
        "away_team_id",
    ]
    for key in required_keys:
        assert key in fixture, f"Missing key '{key}' in fixture: {fixture}"

    assert isinstance(fixture["match_id"], int), "match_id must be an int"
    assert isinstance(fixture["home_team"], str), "home_team must be a str"
    assert isinstance(fixture["away_team"], str), "away_team must be a str"
    assert isinstance(fixture["competition"], str), "competition must be a str"


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _has_api_key(), reason="FOOTBALL_DATA_API_KEY not set")
def test_fetch_today_structure():
    """Response for today's date has the correct top-level structure."""
    from soccersmartbet.pre_gambling_flow.tools.game import fetch_daily_fixtures

    today = str(date.today())
    result = fetch_daily_fixtures()  # default = today

    assert result["error"] is None, f"Unexpected error: {result['error']}"
    assert result["date"] == today
    assert isinstance(result["fixtures"], list)
    assert isinstance(result["total"], int)
    assert result["total"] == len(result["fixtures"])

    # Validate each fixture shape (even if the list is empty, this is valid)
    for fixture in result["fixtures"]:
        _assert_fixture_shape(fixture)


@pytest.mark.skipif(not _has_api_key(), reason="FOOTBALL_DATA_API_KEY not set")
def test_fetch_tomorrow_structure():
    """Response for tomorrow's date has the correct top-level structure.

    Tomorrow is more likely to have scheduled fixtures than today (which may
    already be in progress or finished). The test accepts an empty list
    because mid-week gaps are possible.
    """
    from soccersmartbet.pre_gambling_flow.tools.game import fetch_daily_fixtures

    tomorrow = str(date.today() + timedelta(days=1))
    result = fetch_daily_fixtures(date=tomorrow)

    assert result["error"] is None, f"Unexpected error: {result['error']}"
    assert result["date"] == tomorrow
    assert isinstance(result["fixtures"], list)
    assert result["total"] == len(result["fixtures"])

    for fixture in result["fixtures"]:
        _assert_fixture_shape(fixture)


def test_fetch_no_api_key(monkeypatch):
    """Returns a well-formed error dict when API key is missing."""
    monkeypatch.delenv("FOOTBALL_DATA_API_KEY", raising=False)

    # The module-level constant is cached at import time, so patch it directly.
    import sys
    # Ensure the module is already imported
    import soccersmartbet.pre_gambling_flow.tools.game.fetch_daily_fixtures  # noqa: F401
    mod = sys.modules["soccersmartbet.pre_gambling_flow.tools.game.fetch_daily_fixtures"]
    monkeypatch.setattr(mod, "FOOTBALL_DATA_API_KEY", None)

    result = mod.fetch_daily_fixtures()

    assert result["error"] is not None
    assert "FOOTBALL_DATA_API_KEY" in result["error"]
    assert result["fixtures"] == []
    assert result["total"] == 0
