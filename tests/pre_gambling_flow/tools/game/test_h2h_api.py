"""Test football-data.org API availability for H2H."""

import os
import requests
from dotenv import load_dotenv

load_dotenv()


def test_h2h_api_available():
    """Test that football-data.org H2H endpoint is accessible."""
    api_key = os.getenv("FOOTBALL_DATA_API_KEY")
    
    if not api_key:
        print("❌ FOOTBALL_DATA_API_KEY not found")
        return False
    
    # Test getting PL matches
    response = requests.get(
        "https://api.football-data.org/v4/competitions/PL/matches",
        headers={"X-Auth-Token": api_key},
        params={"status": "SCHEDULED"},
        timeout=10
    )
    
    if response.status_code != 200:
        print(f"❌ API error: {response.status_code}")
        return False
    
    data = response.json()
    matches = data.get("matches", [])
    
    print(f"✅ API accessible - {len(matches)} scheduled matches")
    return True


if __name__ == "__main__":
    test_h2h_api_available()
