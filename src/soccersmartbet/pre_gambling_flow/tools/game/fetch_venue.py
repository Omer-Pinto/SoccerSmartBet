"""
Fetch venue information for a match between two teams.

Clean interface: Accepts both team names, returns home team's venue.

Data source: TheSportsDB (free tier, 100 req/min)
API: https://www.thesportsdb.com/api/v1/json/{key}/searchteams.php
"""

import os
from typing import Dict, Any, Optional
import requests
from dotenv import load_dotenv

load_dotenv()

# API Configuration
THESPORTSDB_API_KEY = os.getenv("THESPORTSDB_API_KEY", "3")  # Default to free test key
BASE_URL = f"https://www.thesportsdb.com/api/v1/json/{THESPORTSDB_API_KEY}"
TIMEOUT = 10


def _search_team(team_name: str) -> Optional[str]:
    """
    Search for team by name and return team ID.
    
    Args:
        team_name: Team name to search for
    
    Returns:
        Team ID string or None if not found
    """
    try:
        response = requests.get(
            f"{BASE_URL}/searchteams.php",
            params={"t": team_name},
            timeout=TIMEOUT
        )
        
        if response.status_code != 200:
            return None
        
        data = response.json()
        teams = data.get("teams")
        
        if not teams or len(teams) == 0:
            return None
        
        # Return first match (TheSportsDB search is quite accurate)
        return teams[0].get("idTeam")
    
    except Exception:
        return None


def fetch_venue(home_team_name: str, away_team_name: str) -> Dict[str, Any]:
    """
    Fetch venue information for match between two teams.
    
    Returns the home team's venue details using TheSportsDB.
    
    Args:
        home_team_name: Home team name (e.g., "Manchester City")
        away_team_name: Away team name (e.g., "Tottenham")
    
    Returns:
        {
            "home_team": "Manchester City",
            "away_team": "Tottenham",
            "venue_name": "Etihad Stadium",
            "venue_city": "Manchester",
            "venue_capacity": "55097",
            "venue_address": None,  # Not available in TheSportsDB
            "venue_surface": None,  # Not available in TheSportsDB
            "error": None
        }
    """
    try:
        # Step 1: Search for home team
        team_id = _search_team(home_team_name)
        
        if not team_id:
            return {
                "home_team": home_team_name,
                "away_team": away_team_name,
                "venue_name": None,
                "venue_city": None,
                "venue_capacity": None,
                "venue_address": None,
                "venue_surface": None,
                "error": f"Team '{home_team_name}' not found"
            }
        
        # Step 2: Get full team data with venue
        response = requests.get(
            f"{BASE_URL}/lookupteam.php",
            params={"id": team_id},
            timeout=TIMEOUT
        )
        
        if response.status_code != 200:
            return {
                "home_team": home_team_name,
                "away_team": away_team_name,
                "venue_name": None,
                "venue_city": None,
                "venue_capacity": None,
                "venue_address": None,
                "venue_surface": None,
                "error": f"API error: {response.status_code}"
            }
        
        data = response.json()
        teams = data.get("teams")
        
        if not teams or len(teams) == 0:
            return {
                "home_team": home_team_name,
                "away_team": away_team_name,
                "venue_name": None,
                "venue_city": None,
                "venue_capacity": None,
                "venue_address": None,
                "venue_surface": None,
                "error": f"Team data not found for '{home_team_name}'"
            }
        
        team_data = teams[0]
        
        return {
            "home_team": team_data.get("strTeam", home_team_name),
            "away_team": away_team_name,
            "venue_name": team_data.get("strStadium"),
            "venue_city": team_data.get("strLocation"),
            "venue_capacity": team_data.get("intStadiumCapacity"),
            "venue_address": None,  # Not available in TheSportsDB
            "venue_surface": None,  # Not available in TheSportsDB
            "error": None
        }
    
    except requests.Timeout:
        return {
            "home_team": home_team_name,
            "away_team": away_team_name,
            "venue_name": None,
            "venue_city": None,
            "venue_capacity": None,
            "venue_address": None,
            "venue_surface": None,
            "error": f"Request timeout after {TIMEOUT}s"
        }
    except Exception as e:
        return {
            "home_team": home_team_name,
            "away_team": away_team_name,
            "venue_name": None,
            "venue_city": None,
            "venue_capacity": None,
            "venue_address": None,
            "venue_surface": None,
            "error": f"Unexpected error: {str(e)}"
        }
