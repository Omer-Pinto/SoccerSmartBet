"""
Fetch team's current injuries.

Clean interface: Accepts team name, returns injured players.
"""

import os
from typing import Dict, Any, Optional, Tuple
import requests
from dotenv import load_dotenv

load_dotenv()

APIFOOTBALL_API_KEY = os.getenv("APIFOOTBALL_API_KEY")
BASE_URL = "https://apiv3.apifootball.com"
TIMEOUT = 10

# Major European leagues
MAJOR_LEAGUES = [152, 302, 207, 175, 168]  # PL, La Liga, Serie A, Bundesliga, Ligue 1


def _find_team_league(team_name: str) -> Tuple[Optional[str], Optional[int], Optional[str]]:
    """
    Search for team across all major leagues.
    
    Args:
        team_name: Team name to search for
    
    Returns:
        Tuple of (team_id, league_id, actual_team_name) or (None, None, None) if not found
    """
    if not APIFOOTBALL_API_KEY:
        return (None, None, None)
    
    for league_id in MAJOR_LEAGUES:
        try:
            response = requests.get(
                BASE_URL,
                params={"action": "get_teams", "league_id": league_id, "APIkey": APIFOOTBALL_API_KEY},
                timeout=TIMEOUT
            )
            
            if response.status_code != 200:
                continue
            
            teams = response.json()
            for team in teams:
                if team_name.lower() in team.get("team_name", "").lower():
                    return (team["team_key"], league_id, team["team_name"])
        except Exception:
            continue
    
    return (None, None, None)


def fetch_injuries(team_name: str) -> Dict[str, Any]:
    """
    Fetch team's current injury list.
    
    Searches across all major European leagues to find the team.
    
    Args:
        team_name: Team name (e.g., "Manchester City")
    
    Returns:
        {
            "team_name": "Manchester City",
            "injuries": [
                {
                    "player_name": "Mateo Kovacic",
                    "player_type": "Midfielders",
                    "injury_type": "Not specified",
                    "matches_played": "1"
                },
                ...
            ],
            "total_injuries": 2,
            "error": None
        }
    """
    if not APIFOOTBALL_API_KEY:
        return {
            "team_name": team_name,
            "injuries": [],
            "total_injuries": 0,
            "error": "APIFOOTBALL_API_KEY not found"
        }
    
    try:
        # Find team across all major leagues
        team_id, league_id, actual_name = _find_team_league(team_name)
        
        if not team_id:
            return {
                "team_name": team_name,
                "injuries": [],
                "total_injuries": 0,
                "error": f"Team '{team_name}' not found in any major league"
            }
        
        # Get full team data with players
        response = requests.get(
            BASE_URL,
            params={"action": "get_teams", "league_id": league_id, "APIkey": APIFOOTBALL_API_KEY},
            timeout=TIMEOUT
        )
        
        if response.status_code != 200:
            return {
                "team_name": team_name,
                "injuries": [],
                "total_injuries": 0,
                "error": f"API error: {response.status_code}"
            }
        
        teams = response.json()
        team_data = None
        
        for team in teams:
            if team["team_key"] == team_id:
                team_data = team
                break
        
        if not team_data:
            return {
                "team_name": team_name,
                "injuries": [],
                "total_injuries": 0,
                "error": f"Team '{team_name}' not found"
            }
        
        players = team_data.get("players", [])
        injured = []
        
        for player in players:
            if player.get("player_injured") == "Yes":
                injured.append({
                    "player_name": player.get("player_name", "Unknown"),
                    "player_type": player.get("player_type", "Unknown"),
                    "injury_type": player.get("player_injury_type", "Not specified"),
                    "matches_played": player.get("player_match_played", "0")
                })
        
        return {
            "team_name": team_data.get("team_name"),
            "injuries": injured,
            "total_injuries": len(injured),
            "error": None
        }
    
    except requests.Timeout:
        return {
            "team_name": team_name,
            "injuries": [],
            "total_injuries": 0,
            "error": f"Request timeout after {TIMEOUT}s"
        }
    except Exception as e:
        return {
            "team_name": team_name,
            "injuries": [],
            "total_injuries": 0,
            "error": f"Unexpected error: {str(e)}"
        }
