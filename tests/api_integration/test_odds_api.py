"""
Integration tests for The Odds API

Tests betting lines retrieval for soccer matches.
Requires ODDS_API_KEY in .env file.

API Docs: https://the-odds-api.com/liveapi/guides/v4/
Rate Limit: 500 credits/month (free tier)
"""

import os
import pytest
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# API Configuration
API_KEY = os.getenv("ODDS_API_KEY")
BASE_URL = "https://api.the-odds-api.com/v4"


@pytest.fixture
def api_params():
    """Base parameters for The Odds API requests"""
    if not API_KEY:
        pytest.skip("ODDS_API_KEY not found in .env")
    return {
        "apiKey": API_KEY,
        "regions": "eu",  # European bookmakers
        "oddsFormat": "decimal",  # Israeli format
        "dateFormat": "iso",
    }


class TestOddsEndpoint:
    """Test odds retrieval for soccer matches"""

    def test_get_soccer_odds_success(self, api_params):
        """Test retrieving odds for soccer sport"""
        # TODO: Implement by ToolBuilderDroid
        # - Make request to /v4/sports/soccer_*/odds
        # - Validate response structure
        # - Check for required fields: id, home_team, away_team, bookmakers
        pytest.skip("To be implemented by ToolBuilderDroid")

    def test_odds_decimal_format(self, api_params):
        """Test that odds are returned in decimal format"""
        # TODO: Implement by ToolBuilderDroid
        # - Verify oddsFormat=decimal returns decimal odds
        # - Check bookmaker.markets.outcomes.price is decimal
        pytest.skip("To be implemented by ToolBuilderDroid")

    def test_h2h_market(self, api_params):
        """Test retrieving head-to-head (1X2) market"""
        # TODO: Implement by ToolBuilderDroid
        # - Request markets=h2h parameter
        # - Verify 3 outcomes: home win, draw, away win
        pytest.skip("To be implemented by ToolBuilderDroid")


class TestSportsEndpoint:
    """Test available sports listing"""

    def test_get_soccer_sports(self, api_params):
        """Test retrieving available soccer leagues"""
        # TODO: Implement by ToolBuilderDroid
        # - Make request to /v4/sports?group=soccer
        # - Validate soccer leagues are returned
        # - Check for common leagues (EPL, La Liga, etc.)
        pytest.skip("To be implemented by ToolBuilderDroid")


class TestRateLimits:
    """Test API rate limiting and quota tracking"""

    def test_quota_tracking(self, api_params):
        """Test API quota usage tracking via response headers"""
        # TODO: Implement by ToolBuilderDroid
        # - Make API request
        # - Check x-requests-remaining header
        # - Verify quota decreases after request
        pytest.skip("To be implemented by ToolBuilderDroid")

    def test_rate_limit_exceeded(self, api_params):
        """Test behavior when monthly quota exceeded"""
        # TODO: Implement by ToolBuilderDroid
        # - Simulate quota exceeded scenario (if possible)
        # - Verify appropriate error response
        pytest.skip("To be implemented by ToolBuilderDroid")


class TestErrorHandling:
    """Test API error handling"""

    def test_invalid_api_key(self):
        """Test behavior with invalid API key"""
        # TODO: Implement by ToolBuilderDroid
        # - Make request with invalid key
        # - Verify 401 status code
        pytest.skip("To be implemented by ToolBuilderDroid")

    def test_invalid_sport(self, api_params):
        """Test behavior with invalid sport key"""
        # TODO: Implement by ToolBuilderDroid
        # - Make request with non-existent sport
        # - Verify 404 status code
        pytest.skip("To be implemented by ToolBuilderDroid")
