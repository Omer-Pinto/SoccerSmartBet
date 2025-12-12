"""Test TheSportsDB API availability for league position data."""

import os
import requests
from dotenv import load_dotenv

load_dotenv()


def test_league_position_api_available():
    """Test that TheSportsDB league table endpoint is accessible."""
    api_key = os.getenv("THESPORTSDB_API_KEY", "3")  # Default to free test key
    base_url = f"https://www.thesportsdb.com/api/v1/json/{api_key}"
    
    # Test 1: Search for a team to get league ID
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
    
    team = teams[0]
    league_id = team.get("idLeague")
    team_id = team.get("idTeam")
    
    print(f"✅ Search working - team ID {team_id}, league ID {league_id}")
    
    # Test 2: Get league table
    print(f"Testing TheSportsDB lookuptable endpoint...")
    response = requests.get(
        f"{base_url}/lookuptable.php",
        params={"l": league_id},
        timeout=10
    )
    
    if response.status_code != 200:
        print(f"❌ Table API error: {response.status_code}")
        return False
    
    data = response.json()
    table = data.get("table")
    
    if not table or len(table) == 0:
        print("❌ No league table found (may not be available for this league)")
        return False
    
    # Find our team in the table
    team_row = None
    for row in table:
        if row.get("idTeam") == team_id:
            team_row = row
            break
    
    if not team_row:
        print(f"⚠️  Team not found in table")
        print(f"✅ API accessible but team not in current table")
        return True
    
    position = team_row.get("intRank")
    points = team_row.get("intPoints")
    team_name = team_row.get("strTeam")
    
    print(f"✅ Table endpoint working - {team_name} is {position} with {points} points")
    print(f"✅ TheSportsDB league position API fully accessible")
    return True


if __name__ == "__main__":
    success = test_league_position_api_available()
    exit(0 if success else 1)
