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

    def test_get_current_soccer_odds(self, api_params):
        """Test retrieving CURRENT odds for upcoming matches (NOT 2021-2023 data)"""
        import requests
        from datetime import datetime, timedelta
        
        # Try Premier League
        response = requests.get(
            f"{BASE_URL}/sports/soccer_epl/odds",
            params=api_params,
            timeout=10
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Validate response is a list
        assert isinstance(data, list)
        
        if data:  # If there are matches with odds
            match = data[0]
            assert "id" in match
            assert "home_team" in match
            assert "away_team" in match
            assert "bookmakers" in match
            assert "commence_time" in match
            
            # CRITICAL: Verify odds are for current/upcoming matches, not 2021-2023
            # Allow matches from yesterday onwards (some might have started recently)
            yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
            match_time = match["commence_time"][:10]  # YYYY-MM-DD
            assert match_time >= yesterday, f"Got old match from {match_time}, expected >= {yesterday}"

    def test_odds_decimal_format(self, api_params):
        """Test that odds are returned in decimal format"""
        import requests
        
        response = requests.get(
            f"{BASE_URL}/sports/soccer_epl/odds",
            params=api_params,
            timeout=10
        )
        
        assert response.status_code == 200
        data = response.json()
        
        if data and data[0].get("bookmakers"):
            bookmaker = data[0]["bookmakers"][0]
            if bookmaker.get("markets"):
                market = bookmaker["markets"][0]
                if market.get("outcomes"):
                    price = market["outcomes"][0]["price"]
                    # Decimal odds should be > 1.0
                    assert isinstance(price, (int, float))
                    assert price >= 1.0

    def test_h2h_market(self, api_params):
        """Test retrieving head-to-head (1X2) market"""
        import requests
        
        response = requests.get(
            f"{BASE_URL}/sports/soccer_epl/odds",
            params=api_params,
            timeout=10
        )
        
        assert response.status_code == 200
        data = response.json()
        
        if data and data[0].get("bookmakers"):
            bookmaker = data[0]["bookmakers"][0]
            h2h_market = next(
                (m for m in bookmaker["markets"] if m["key"] == "h2h"),
                None
            )
            
            if h2h_market:
                outcomes = h2h_market["outcomes"]
                # H2H should have 3 outcomes (home/draw/away)
                assert len(outcomes) == 3
                outcome_names = [o["name"] for o in outcomes]
                # One should be "Draw"
                assert "Draw" in outcome_names


class TestSportsEndpoint:
    """Test available sports listing"""

    def test_get_soccer_sports(self, api_params):
        """Test retrieving available soccer leagues"""
        import requests
        
        # Note: /sports endpoint doesn't count against quota
        params = {"apiKey": api_params["apiKey"]}
        
        response = requests.get(
            f"{BASE_URL}/sports",
            params=params,
            timeout=10
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Should be a list of sports
        assert isinstance(data, list)
        
        # At least some sports should be returned
        assert len(data) > 0
        
        # Find soccer sports (may vary by season)
        soccer_sports = [s for s in data if "group" in s and s.get("group") == "soccer"]
        
        # Check for common leagues if soccer sports exist
        if soccer_sports:
            sport_keys = [s["key"] for s in soccer_sports]
            # At least one major league should be present
            assert any(key in sport_keys for key in ["soccer_epl", "soccer_spain_la_liga", "soccer_germany_bundesliga"])





class TestErrorHandling:
    """Test API error handling"""

    def test_invalid_api_key(self):
        """Test behavior with invalid API key"""
        import requests
        
        invalid_params = {
            "apiKey": "invalid_key_12345",
            "regions": "eu",
            "oddsFormat": "decimal"
        }
        
        response = requests.get(
            f"{BASE_URL}/sports/soccer_epl/odds",
            params=invalid_params,
            timeout=10
        )
        
        # Should return 401 for invalid key
        assert response.status_code == 401
