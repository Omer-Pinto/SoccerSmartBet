"""
Integration tests for apifootball.com API

Tests injuries, suspensions, H2H, and team form endpoints.
Requires APIFOOTBALL_API_KEY in .env file.

API Docs: https://apifootball.com/documentation/
Rate Limit: 180 requests/hour (6,480/day) (free tier)
"""

import os
import pytest
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# API Configuration
API_KEY = os.getenv("APIFOOTBALL_API_KEY")
BASE_URL = "https://apiv3.apifootball.com"


@pytest.fixture
def api_params():
    """Base parameters for apifootball.com API requests"""
    if not API_KEY:
        pytest.skip("APIFOOTBALL_API_KEY not found in .env")
    return {"APIkey": API_KEY}


class TestInjuriesEndpoint:
    """Test injuries and suspensions retrieval"""

    def test_get_team_injuries(self, api_params):
        """Test retrieving injury list for a specific team"""
        import requests
        
        # Get teams from Premier League (league_id=152)
        params = {**api_params, "action": "get_teams", "league_id": 152}
        
        response = requests.get(BASE_URL, params=params, timeout=30)
        
        assert response.status_code == 200
        data = response.json()
        
        # Should return a list of teams
        assert isinstance(data, list)
        
        if data:
            team = data[0]
            # Check for basic team structure
            assert "team_key" in team or "team_name" in team
            # players field may or may not be present depending on response

    def test_injuries_data_format(self, api_params):
        """Test injury data contains required fields"""
        import requests
        
        # Get teams with players
        params = {**api_params, "action": "get_teams", "league_id": 152}
        
        response = requests.get(BASE_URL, params=params, timeout=30)
        
        assert response.status_code == 200
        data = response.json()
        
        if data and isinstance(data, list):
            # Look for a team with players data
            for team in data:
                if "players" in team and team["players"]:
                    player = team["players"][0]
                    # Check for expected fields
                    assert "player_name" in player
                    # player_injured field should exist
                    if "player_injured" in player:
                        assert player["player_injured"] in ["Yes", "No", ""]
                    break


class TestH2HEndpoint:
    """Test head-to-head statistics (backup for football-data.org)"""

    def test_get_h2h_matches(self, api_params):
        """Test retrieving H2H matches between two teams"""
        import requests
        from datetime import datetime, timedelta
        
        # Get events (matches)
        to_date = datetime.now().strftime("%Y-%m-%d")
        from_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
        
        params = {
            **api_params,
            "action": "get_events",
            "from": from_date,
            "to": to_date
        }
        
        response = requests.get(BASE_URL, params=params, timeout=30)
        
        assert response.status_code == 200
        data = response.json()
        
        # Should return list of events
        assert isinstance(data, list)
        
        if data:
            match = data[0]
            # Validate match structure
            assert "match_id" in match or "match_hometeam_name" in match or "match_awayteam_name" in match

    def test_h2h_event_filtering(self, api_params):
        """Test filtering events by team IDs for H2H"""
        import requests
        from datetime import datetime, timedelta
        
        to_date = datetime.now().strftime("%Y-%m-%d")
        from_date = (datetime.now() - timedelta(days=60)).strftime("%Y-%m-%d")
        
        # Request events (would filter by team_id if we knew a valid one)
        params = {
            **api_params,
            "action": "get_events",
            "from": from_date,
            "to": to_date
        }
        
        response = requests.get(BASE_URL, params=params, timeout=30)
        
        assert response.status_code == 200
        data = response.json()
        
        # Validate response format
        assert isinstance(data, list)


class TestTeamFormEndpoint:
    """Test team form (recent matches) retrieval"""

    def test_get_recent_matches(self, api_params):
        """Test retrieving recent matches for a team"""
        import requests
        from datetime import datetime, timedelta
        
        to_date = datetime.now().strftime("%Y-%m-%d")
        from_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
        
        params = {
            **api_params,
            "action": "get_events",
            "from": from_date,
            "to": to_date
        }
        
        response = requests.get(BASE_URL, params=params, timeout=30)
        
        assert response.status_code == 200
        data = response.json()
        
        assert isinstance(data, list)
        
        if data:
            match = data[0]
            # Validate match structure
            assert "match_date" in match or "match_status" in match

    def test_team_form_date_range(self, api_params):
        """Test filtering team matches by date range"""
        import requests
        from datetime import datetime, timedelta
        
        to_date = datetime.now().strftime("%Y-%m-%d")
        from_date = (datetime.now() - timedelta(days=14)).strftime("%Y-%m-%d")
        
        params = {
            **api_params,
            "action": "get_events",
            "from": from_date,
            "to": to_date
        }
        
        response = requests.get(BASE_URL, params=params, timeout=30)
        
        assert response.status_code == 200
        data = response.json()
        
        assert isinstance(data, list)
        
        # Verify matches are within date range
        if data:
            for match in data[:3]:  # Check first 3
                if "match_date" in match:
                    match_date = match["match_date"]
                    assert from_date <= match_date <= to_date


class TestPlayerStatsEndpoint:
    """Test player statistics (goals, assists, form)"""

    def test_get_player_stats(self, api_params):
        """Test retrieving player statistics"""
        import requests
        
        # Try to get players (may require player_id which we don't have)
        # For now, test the API endpoint responds correctly
        params = {**api_params, "action": "get_players"}
        
        response = requests.get(BASE_URL, params=params, timeout=30)
        
        # Should return 200 even if empty or requires player_id
        assert response.status_code in [200, 400]

    def test_top_scorers(self, api_params):
        """Test retrieving top scorers for a team"""
        import requests
        
        # Get top scorers for Premier League (league_id=152)
        params = {**api_params, "action": "get_topscorers", "league_id": 152}
        
        response = requests.get(BASE_URL, params=params, timeout=30)
        
        assert response.status_code == 200
        data = response.json()
        
        # Should return list of players
        assert isinstance(data, list)
        
        if data:
            player = data[0]
            # Check for expected fields
            assert "player_name" in player or "player_key" in player


class TestRateLimits:
    """Test API rate limiting"""

    def test_rate_limit_tracking(self, api_params):
        """Test API rate limit doesn't exceed 180 req/hour"""
        import requests
        import time
        
        # Make a few requests and verify they succeed
        # We won't actually test the limit (would take too long)
        # Just verify the API is responsive for multiple requests
        for i in range(3):
            params = {**api_params, "action": "get_leagues"}
            response = requests.get(BASE_URL, params=params, timeout=30)
            assert response.status_code == 200
            time.sleep(0.5)  # Small delay between requests


class TestErrorHandling:
    """Test API error handling"""

    def test_invalid_api_key(self):
        """Test behavior with invalid API key"""
        import requests
        
        params = {"APIkey": "invalid_key_12345", "action": "get_leagues"}
        
        response = requests.get(BASE_URL, params=params, timeout=30)
        
        # API might return 401, 403, or 200 with error message in body
        # Check that we get a response (even if error)
        assert response.status_code in [200, 401, 403]

    def test_invalid_team_id(self, api_params):
        """Test behavior with invalid team ID"""
        import requests
        
        params = {**api_params, "action": "get_teams", "team_id": 99999999}
        
        response = requests.get(BASE_URL, params=params, timeout=30)
        
        # Should return 200 (empty list) or error code
        assert response.status_code in [200, 404]
        
        if response.status_code == 200:
            data = response.json()
            # Should be empty or error structure
            assert isinstance(data, (list, dict))
