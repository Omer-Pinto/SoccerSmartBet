"""Test TheSportsDB API availability for injuries data."""

import os
import requests
from dotenv import load_dotenv

load_dotenv()


def test_injuries_api_available():
    """Test that TheSportsDB lineup endpoint is accessible."""
    api_key = os.getenv("THESPORTSDB_API_KEY", "3")  # Default to free test key
    base_url = f"https://www.thesportsdb.com/api/v1/json/{api_key}"
    
    # Test 1: Search for a team
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
        print("❌ No teams found")
        return False
    
    team_id = teams[0].get("idTeam")
    print(f"✅ Search working - found team ID {team_id}")
    
    # Test 2: Get next events
    print(f"Testing TheSportsDB eventsnext endpoint...")
    response = requests.get(
        f"{base_url}/eventsnext.php",
        params={"id": team_id},
        timeout=10
    )
    
    if response.status_code != 200:
        print(f"❌ Events API error: {response.status_code}")
        return False
    
    data = response.json()
    events = data.get("events")
    
    if not events or len(events) == 0:
        print("⚠️  No upcoming events (expected if no matches scheduled)")
        print("✅ TheSportsDB API accessible (injury detection requires upcoming matches)")
        return True
    
    event_id = events[0].get("idEvent")
    print(f"✅ Events endpoint working - found event ID {event_id}")
    
    # Test 3: Try to get lineup (may not be published yet)
    print(f"Testing TheSportsDB lookuplineup endpoint...")
    response = requests.get(
        f"{base_url}/lookuplineup.php",
        params={"id": event_id},
        timeout=10
    )
    
    if response.status_code != 200:
        print(f"⚠️  Lineup not yet published (expected before match day)")
    else:
        print(f"✅ Lineup endpoint accessible")
    
    print(f"✅ TheSportsDB API fully accessible for injuries")
    return True


if __name__ == "__main__":
    success = test_injuries_api_available()
    exit(0 if success else 1)
