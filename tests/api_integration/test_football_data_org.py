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

    def test_get_fixtures_success(self, api_headers):
        """Test retrieving fixtures for a specific competition"""
        import requests
        
        # Test Premier League (PL = 2021)
        response = requests.get(
            f"{BASE_URL}/competitions/PL/matches",
            headers=api_headers,
            timeout=10
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Validate response structure
        assert "matches" in data
        
        if data["matches"]:  # If there are matches
            match = data["matches"][0]
            assert "id" in match
            assert "utcDate" in match
            assert "homeTeam" in match
            assert "awayTeam" in match
            assert "score" in match

    def test_fixtures_date_filter(self, api_headers):
        """Test filtering fixtures by date range"""
        import requests
        from datetime import datetime, timedelta
        
        # Get fixtures for a specific date
        today = datetime.now()
        date_str = today.strftime("%Y-%m-%d")
        
        response = requests.get(
            f"{BASE_URL}/matches",
            headers=api_headers,
            params={"date": date_str},
            timeout=10
        )
        
        # Should return 200 or 404 if no matches on this date
        assert response.status_code in [200, 404]
        
        if response.status_code == 200:
            data = response.json()
            assert "matches" in data

    def test_fixtures_rate_limit(self, api_headers):
        """Test API rate limiting behavior"""
        import requests
        import time
        
        # Make multiple requests rapidly (11 requests in quick succession)
        # Free tier limit: 10 requests/minute
        responses = []
        for i in range(11):
            response = requests.get(
                f"{BASE_URL}/matches",
                headers=api_headers,
                timeout=10
            )
            responses.append(response.status_code)
            time.sleep(0.1)  # Small delay between requests
        
        # At least one should succeed
        assert 200 in responses
        # Note: May or may not hit 429 depending on current quota


class TestH2HEndpoint:
    """Test head-to-head statistics endpoint"""

    def test_get_h2h_success(self, api_headers):
        """Test retrieving H2H data for a specific match"""
        import requests
        
        # First, get a match ID from recent fixtures
        fixtures_response = requests.get(
            f"{BASE_URL}/competitions/PL/matches",
            headers=api_headers,
            timeout=10
        )
        
        if fixtures_response.status_code == 200:
            fixtures_data = fixtures_response.json()
            if fixtures_data.get("matches"):
                match_id = fixtures_data["matches"][0]["id"]
                
                # Now get H2H for that match
                h2h_response = requests.get(
                    f"{BASE_URL}/matches/{match_id}/head2head",
                    headers=api_headers,
                    params={"limit": 5},
                    timeout=10
                )
                
                assert h2h_response.status_code == 200
                h2h_data = h2h_response.json()
                
                # Validate response structure (may be empty if no H2H history)
                assert "matches" in h2h_data or "aggregates" in h2h_data

    def test_h2h_limit_parameter(self, api_headers):
        """Test limiting number of H2H results"""
        import requests
        
        # Get a match ID
        fixtures_response = requests.get(
            f"{BASE_URL}/competitions/PL/matches",
            headers=api_headers,
            timeout=10
        )
        
        if fixtures_response.status_code == 200:
            fixtures_data = fixtures_response.json()
            if fixtures_data.get("matches"):
                match_id = fixtures_data["matches"][0]["id"]
                
                # Test limit parameter
                h2h_response = requests.get(
                    f"{BASE_URL}/matches/{match_id}/head2head",
                    headers=api_headers,
                    params={"limit": 3},
                    timeout=10
                )
                
                assert h2h_response.status_code == 200
                h2h_data = h2h_response.json()
                
                # If there are matches, verify limit is respected
                if h2h_data.get("matches"):
                    assert len(h2h_data["matches"]) <= 3


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

    def test_invalid_competition_id(self, api_headers):
        """Test behavior with invalid competition ID"""
        import requests
        
        response = requests.get(
            f"{BASE_URL}/competitions/INVALID999/matches",
            headers=api_headers,
            timeout=10
        )
        
        # Should return 404 for non-existent competition (or 429 if rate limited)
        assert response.status_code in [404, 429]
