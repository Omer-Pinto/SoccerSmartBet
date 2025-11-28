"""
Integration tests for football-data.org API

Tests fixtures and H2H statistics endpoints.
Requires FOOTBALL_DATA_API_KEY in .env file.

API Docs: https://www.football-data.org/documentation/quickstart
Rate Limit: 10 requests/minute (free tier)
"""

import os
import pytest
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# API Configuration
API_KEY = os.getenv("FOOTBALL_DATA_API_KEY")
BASE_URL = "https://api.football-data.org/v4"


@pytest.fixture
def api_headers():
    """Headers for football-data.org API requests"""
    if not API_KEY:
        pytest.skip("FOOTBALL_DATA_API_KEY not found in .env")
    return {"X-Auth-Token": API_KEY}


class TestFixturesEndpoint:
    """Test fixtures retrieval from football-data.org"""

    def test_get_upcoming_fixtures(self, api_headers):
        """Test retrieving upcoming fixtures (NOT old 2021-2023 data)"""
        import requests
        from datetime import datetime, timedelta
        
        # Get upcoming matches (next 30 days)
        today = datetime.now().strftime("%Y-%m-%d")
        future = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
        
        response = requests.get(
            f"{BASE_URL}/competitions/PL/matches",
            headers=api_headers,
            params={"dateFrom": today, "dateTo": future},
            timeout=10
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "matches" in data
        
        # Verify we got upcoming matches, not old data
        if data["matches"]:
            match = data["matches"][0]
            assert "id" in match
            assert "utcDate" in match
            assert "homeTeam" in match
            assert "awayTeam" in match
            
            # CRITICAL: Verify match date is current/upcoming, not 2021-2023
            match_date = match["utcDate"][:10]
            assert match_date >= today, f"Got old match from {match_date}, expected >= {today}"


class TestH2HEndpoint:
    """Test head-to-head statistics endpoint"""

    def test_get_h2h_last_5_matches_only(self, api_headers):
        """Test retrieving ONLY last 3-5 H2H matches (NOT years of data)"""
        import requests
        from datetime import datetime
        
        # First, get an upcoming match ID
        today = datetime.now().strftime("%Y-%m-%d")
        
        fixtures_response = requests.get(
            f"{BASE_URL}/competitions/PL/matches",
            headers=api_headers,
            params={"dateFrom": today},
            timeout=10
        )
        
        if fixtures_response.status_code == 200:
            fixtures_data = fixtures_response.json()
            if fixtures_data.get("matches"):
                match_id = fixtures_data["matches"][0]["id"]
                
                # Get H2H with limit=5 (ONLY last 5 matches between these teams)
                h2h_response = requests.get(
                    f"{BASE_URL}/matches/{match_id}/head2head",
                    headers=api_headers,
                    params={"limit": 5},
                    timeout=10
                )
                
                assert h2h_response.status_code == 200
                h2h_data = h2h_response.json()
                
                # Validate response structure
                assert "matches" in h2h_data or "aggregates" in h2h_data
                
                # CRITICAL: Verify we got ONLY 5 or fewer matches, not years of data
                if h2h_data.get("matches"):
                    assert len(h2h_data["matches"]) <= 5, f"Got {len(h2h_data['matches'])} matches, expected max 5"


class TestErrorHandling:
    """Test API error handling"""

    def test_invalid_api_key(self):
        """Test behavior with invalid API key"""
        import requests
        
        invalid_headers = {"X-Auth-Token": "invalid_key_12345"}
        
        response = requests.get(
            f"{BASE_URL}/matches",
            headers=invalid_headers,
            timeout=10
        )
        
        # Should return 400 or 403 for invalid key
        assert response.status_code in [400, 403]
