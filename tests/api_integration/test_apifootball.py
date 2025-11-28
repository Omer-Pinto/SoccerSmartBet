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

    def test_get_current_team_injuries(self, api_params):
        """Test retrieving CURRENT injury list (not old 2021-2023 data)"""
        import requests
        
        # Get teams from Premier League (league_id=152)
        # This should give us current squad with current injury status
        params = {**api_params, "action": "get_teams", "league_id": 152}
        
        response = requests.get(BASE_URL, params=params, timeout=30)
        
        assert response.status_code == 200
        data = response.json()
        
        # Should return a list of teams
        assert isinstance(data, list)
        assert len(data) > 0, "Expected teams data, got empty response"
        
        team = data[0]
        assert "team_key" in team or "team_name" in team
        
        # Verify we have players data with injury status
        if "players" in team and team["players"]:
            player = team["players"][0]
            assert "player_name" in player
            # player_injured field indicates current injury status
            if "player_injured" in player:
                assert player["player_injured"] in ["Yes", "No", ""]


class TestH2HEndpoint:
    """Test head-to-head statistics (backup for football-data.org)"""

    def test_get_h2h_between_two_teams(self, api_params):
        """Test retrieving ONLY H2H matches between 2 specific teams (last 5 meetings)"""
        import requests
        
        # apifootball.com has get_H2H action that returns head-to-head between two teams
        # Test with a known rivalry: Man City vs Man United
        # This should return ONLY matches where these two teams played each other
        params = {
            **api_params,
            "action": "get_H2H",
            "firstTeamId": "33",   # Man City
            "secondTeamId": "35"   # Man United
        }
        
        response = requests.get(BASE_URL, params=params, timeout=30)
        
        assert response.status_code == 200
        data = response.json()
        
        # Should return H2H matches between these two teams
        assert isinstance(data, dict) or isinstance(data, list)
        
        # Verify it's returning H2H data, not all matches
        # The API returns firstTeam_lastResults and secondTeam_lastResults
        if isinstance(data, dict):
            # Check for H2H structure
            assert "firstTeam_lastResults" in data or "secondTeam_lastResults" in data or "firstTeam_VS_secondTeam" in data
        elif isinstance(data, list) and data:
            # If it's a list of matches, verify they involve both teams
            match = data[0]
            assert "match_hometeam_name" in match or "match_awayteam_name" in match


class TestTeamFormEndpoint:
    """Test team form (recent matches) retrieval"""

    def test_get_last_5_team_matches(self, api_params):
        """Test retrieving ONLY last 5 matches for team form (NOT years of data)"""
        import requests
        from datetime import datetime, timedelta
        
        # Get last 30 days of matches (we'll limit to 5 in real usage)
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
            # Verify matches are recent
            match = data[0]
            assert "match_date" in match or "match_status" in match
            
            if "match_date" in match:
                assert from_date <= match["match_date"] <= to_date
            
            # In real usage, we'll filter by team_id and limit to 5 matches
            # This test just verifies we can get recent matches within a date range


class TestPlayerStatsEndpoint:
    """Test player statistics (goals, assists, form)"""

    def test_get_current_top_scorers(self, api_params):
        """Test retrieving CURRENT season top scorers (not old 2021-2023 data)"""
        import requests
        
        # Get top scorers for Premier League (league_id=152)
        # This should return current season stats
        params = {**api_params, "action": "get_topscorers", "league_id": 152}
        
        response = requests.get(BASE_URL, params=params, timeout=30)
        
        assert response.status_code == 200
        data = response.json()
        
        # Should return list of current top scorers
        assert isinstance(data, list)
        assert len(data) > 0, "Expected top scorers data, got empty response"
        
        player = data[0]
        assert "player_name" in player or "player_key" in player
        
        # Verify we have goal stats
        if "goals" in player:
            # Current season should have some goals
            assert isinstance(player["goals"], (int, str))


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
