"""
Fetch team's current league position and standings.

Clean interface: Accepts team name, returns league position + record.

Data source: TheSportsDB (free tier, 100 req/min)
API: https://www.thesportsdb.com/api/v1/json/{key}/lookuptable.php
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


def _search_team(team_name: str) -> Optional[Dict[str, Any]]:
    """
    Search for team by name and return team data including league ID.
    
    Args:
        team_name: Team name to search for
    
    Returns:
        Dict with team_id, league_id, team_name or None if not found
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
        
        team = teams[0]
        return {
            "team_id": team.get("idTeam"),
            "league_id": team.get("idLeague"),
            "team_name": team.get("strTeam")
        }
    
    except Exception:
        return None


def fetch_league_position(team_name: str) -> Dict[str, Any]:
    """
    Fetch team's current league position and standing.
    
    Returns full league table and extracts the team's row.
    Uses current season (no season parameter needed for current standings).
    
    Args:
        team_name: Team name (e.g., "Manchester City")
    
    Returns:
        {
            "team_name": "Manchester City",
            "league_name": "English Premier League",
            "position": 1,
            "played": 20,
            "won": 15,
            "draw": 3,
            "lost": 2,
            "goals_for": 45,
            "goals_against": 18,
            "goal_difference": 27,
            "points": 48,
            "form": "WWDWW",  # Last 5 matches
            "error": None
        }
    """
    try:
        # Step 1: Search for team to get league ID
        team_data = _search_team(team_name)
        
        if not team_data:
            return {
                "team_name": team_name,
                "league_name": None,
                "position": None,
                "played": None,
                "won": None,
                "draw": None,
                "lost": None,
                "goals_for": None,
                "goals_against": None,
                "goal_difference": None,
                "points": None,
                "form": None,
                "error": f"Team '{team_name}' not found"
            }
        
        league_id = team_data["league_id"]
        actual_team_name = team_data["team_name"]
        
        # Step 2: Get league table (current season by default)
        response = requests.get(
            f"{BASE_URL}/lookuptable.php",
            params={"l": league_id},  # No season = current season
            timeout=TIMEOUT
        )
        
        if response.status_code != 200:
            return {
                "team_name": team_name,
                "league_name": None,
                "position": None,
                "played": None,
                "won": None,
                "draw": None,
                "lost": None,
                "goals_for": None,
                "goals_against": None,
                "goal_difference": None,
                "points": None,
                "form": None,
                "error": f"API error: {response.status_code}"
            }
        
        data = response.json()
        table = data.get("table")
        
        if not table or len(table) == 0:
            return {
                "team_name": team_name,
                "league_name": None,
                "position": None,
                "played": None,
                "won": None,
                "draw": None,
                "lost": None,
                "goals_for": None,
                "goals_against": None,
                "goal_difference": None,
                "points": None,
                "form": None,
                "error": "League table not found (may not be available for this league)"
            }
        
        # Step 3: Find team in table
        team_row = None
        league_name = None
        
        for row in table:
            if row.get("idTeam") == team_data["team_id"]:
                team_row = row
                league_name = row.get("strLeague")  # League name from table row
                break
        
        if not team_row:
            return {
                "team_name": team_name,
                "league_name": None,
                "position": None,
                "played": None,
                "won": None,
                "draw": None,
                "lost": None,
                "goals_for": None,
                "goals_against": None,
                "goal_difference": None,
                "points": None,
                "form": None,
                "error": f"Team '{actual_team_name}' not found in league table"
            }
        
        # Parse data with proper type conversions
        def safe_int(value):
            try:
                return int(value) if value is not None else None
            except (ValueError, TypeError):
                return None
        
        return {
            "team_name": team_row.get("strTeam", actual_team_name),
            "league_name": league_name,
            "position": safe_int(team_row.get("intRank")),
            "played": safe_int(team_row.get("intPlayed")),
            "won": safe_int(team_row.get("intWin")),
            "draw": safe_int(team_row.get("intDraw")),
            "lost": safe_int(team_row.get("intLoss")),
            "goals_for": safe_int(team_row.get("intGoalsFor")),
            "goals_against": safe_int(team_row.get("intGoalsAgainst")),
            "goal_difference": safe_int(team_row.get("intGoalDifference")),
            "points": safe_int(team_row.get("intPoints")),
            "form": team_row.get("strForm"),  # e.g., "WWDLW"
            "error": None
        }
    
    except requests.Timeout:
        return {
            "team_name": team_name,
            "league_name": None,
            "position": None,
            "played": None,
            "won": None,
            "draw": None,
            "lost": None,
            "goals_for": None,
            "goals_against": None,
            "goal_difference": None,
            "points": None,
            "form": None,
            "error": f"Request timeout after {TIMEOUT}s"
        }
    except Exception as e:
        return {
            "team_name": team_name,
            "league_name": None,
            "position": None,
            "played": None,
            "won": None,
            "draw": None,
            "lost": None,
            "goals_for": None,
            "goals_against": None,
            "goal_difference": None,
            "points": None,
            "form": None,
            "error": f"Unexpected error: {str(e)}"
        }
