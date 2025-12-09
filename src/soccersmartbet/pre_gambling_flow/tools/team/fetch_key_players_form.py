"""
Fetch team's key players and their form.

Clean interface: Accepts team name, returns top performers.
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


def fetch_key_players_form(team_name: str, top_n: int = 5) -> Dict[str, Any]:
    """
    Fetch team's top performers.
    
    Searches across all major European leagues to find the team.
    
    Args:
        team_name: Team name (e.g., "Manchester City")
        top_n: Number of top players (default: 5)
    
    Returns:
        {
            "team_name": "Manchester City",
            "top_players": [
                {
                    "player_name": "E. Haaland",
                    "player_type": "Forwards",
                    "goals": 15,
                    "assists": 0,
                    "matches_played": 20
                },
                ...
            ],
            "total_players": 2,
            "error": None
        }
    """
    if not APIFOOTBALL_API_KEY:
        return {
            "team_name": team_name,
            "top_players": [],
            "total_players": 0,
            "error": "APIFOOTBALL_API_KEY not found"
        }
    
    try:
        # Step 1: Find team across all major leagues
        team_id, league_id, actual_name = _find_team_league(team_name)
        
        if not team_id:
            return {
                "team_name": team_name,
                "top_players": [],
                "total_players": 0,
                "error": f"Team '{team_name}' not found"
            }
        
        # Step 2: Get league top scorers and filter by team
        scorers_response = requests.get(
            BASE_URL,
            params={"action": "get_topscorers", "league_id": league_id, "APIkey": APIFOOTBALL_API_KEY},
            timeout=TIMEOUT
        )
        
        if scorers_response.status_code != 200:
            return {
                "team_name": team_name,
                "top_players": [],
                "total_players": 0,
                "error": f"Scorers API error: {scorers_response.status_code}"
            }
        
        all_players = scorers_response.json()
        
        # Filter by team and calculate contribution
        team_players = []
        for player in all_players:
            if player.get("team_key") == str(team_id):
                goals = int(player.get("goals", 0) or 0)
                assists = int(player.get("assists", 0) or 0)
                
                team_players.append({
                    "player_name": player.get("player_name", "Unknown"),
                    "player_type": player.get("player_type", "Unknown"),
                    "goals": goals,
                    "assists": assists,
                    "matches_played": int(player.get("player_match_played", 0) or 0),
                    "_contribution": goals + assists
                })
        
        # Sort by contribution (goals + assists)
        team_players.sort(key=lambda x: x["_contribution"], reverse=True)
        
        # Take top N and remove internal field
        top_players = team_players[:top_n]
        for p in top_players:
            del p["_contribution"]
        
        return {
            "team_name": team_name,
            "top_players": top_players,
            "total_players": len(top_players),
            "error": None
        }
    
    except requests.Timeout:
        return {
            "team_name": team_name,
            "top_players": [],
            "total_players": 0,
            "error": f"Request timeout after {TIMEOUT}s"
        }
    except Exception as e:
        return {
            "team_name": team_name,
            "top_players": [],
            "total_players": 0,
            "error": f"Unexpected error: {str(e)}"
        }
