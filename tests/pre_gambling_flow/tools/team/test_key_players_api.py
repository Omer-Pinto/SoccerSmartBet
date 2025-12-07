"""Test apifootball.com API availability for player stats."""

import os
import requests
from dotenv import load_dotenv

load_dotenv()


def test_key_players_api_available():
    """Test that apifootball.com top scorers endpoint is accessible."""
    api_key = os.getenv("APIFOOTBALL_API_KEY")
    
    if not api_key:
        print("❌ APIFOOTBALL_API_KEY not found")
        return False
    
    response = requests.get(
        "https://apiv3.apifootball.com/",
        params={"action": "get_topscorers", "league_id": 152, "APIkey": api_key},
        timeout=10
    )
    
    if response.status_code != 200:
        print(f"❌ API error: {response.status_code}")
        return False
    
    scorers = response.json()
    
    print(f"✅ API accessible - {len(scorers)} top scorers")
    return True


if __name__ == "__main__":
    test_key_players_api_available()
