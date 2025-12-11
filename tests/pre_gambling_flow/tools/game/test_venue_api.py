"""Test TheSportsDB API availability for venue data."""

import os
import requests
from dotenv import load_dotenv

load_dotenv()


def test_venue_api_available():
    """Test that TheSportsDB search and lookup endpoints are accessible."""
    api_key = os.getenv("THESPORTSDB_API_KEY", "3")  # Default to free test key
    base_url = f"https://www.thesportsdb.com/api/v1/json/{api_key}"
    
    # Test 1: Search teams endpoint
    print("Testing TheSportsDB search endpoint...")
    response = requests.get(
        f"{base_url}/searchteams.php",
        params={"t": "Arsenal"},
        timeout=10
    )
    
    if response.status_code != 200:
        print(f"❌ Search API error: {response.status_code}")
        return False
    
    data = response.json()
    teams = data.get("teams")
    
    if not teams or len(teams) == 0:
        print("❌ No teams found in search")
        return False
    
    print(f"✅ Search endpoint working - found {len(teams)} team(s)")
    
    # Test 2: Lookup team endpoint (get venue)
    team_id = teams[0].get("idTeam")
    print(f"Testing TheSportsDB lookup endpoint with team ID {team_id}...")
    
    response = requests.get(
        f"{base_url}/lookupteam.php",
        params={"id": team_id},
        timeout=10
    )
    
    if response.status_code != 200:
        print(f"❌ Lookup API error: {response.status_code}")
        return False
    
    data = response.json()
    teams = data.get("teams")
    
    if not teams or len(teams) == 0:
        print("❌ No team data found in lookup")
        return False
    
    team = teams[0]
    venue = team.get("strStadium")
    
    if not venue:
        print("❌ No venue data in team response")
        return False
    
    print(f"✅ Lookup endpoint working - venue: {venue}")
    print(f"✅ TheSportsDB API fully accessible")
    return True


if __name__ == "__main__":
    success = test_venue_api_available()
    exit(0 if success else 1)
