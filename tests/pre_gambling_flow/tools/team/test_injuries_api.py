"""Test apifootball.com API availability for injury data."""

import os
import requests
from dotenv import load_dotenv

load_dotenv()


def test_injuries_api_available():
    """Test that apifootball.com teams endpoint returns injury data."""
    api_key = os.getenv("APIFOOTBALL_API_KEY")
    
    if not api_key:
        print("❌ APIFOOTBALL_API_KEY not found")
        return False
    
    response = requests.get(
        "https://apiv3.apifootball.com/",
        params={"action": "get_teams", "league_id": 152, "APIkey": api_key},
        timeout=10
    )
    
    if response.status_code != 200:
        print(f"❌ API error: {response.status_code}")
        return False
    
    teams = response.json()
    
    # Check if player injury data exists
    has_injury_data = False
    for team in teams:
        if "players" in team and team["players"]:
            if "player_injured" in team["players"][0]:
                has_injury_data = True
                break
    
    if has_injury_data:
        print(f"✅ API accessible - Injury data available")
        return True
    else:
        print("⚠️  API accessible but no injury fields found")
        return False


if __name__ == "__main__":
    test_injuries_api_available()
