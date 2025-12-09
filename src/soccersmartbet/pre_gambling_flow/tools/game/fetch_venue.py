"""
Fetch venue information for a match between two teams.

Clean interface: Accepts both team names, returns home team's venue.
"""

import os
from typing import Dict, Any, Optional, Tuple
import requests
from dotenv import load_dotenv

load_dotenv()

# API Configuration
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


def fetch_venue(home_team_name: str, away_team_name: str) -> Dict[str, Any]:
    """
    Fetch venue information for match between two teams.
    
    Returns the home team's venue details. Searches across all major European leagues.
    
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
            "venue_address": "Rowsley Street",
            "venue_surface": "grass",
            "error": None
        }
    """
    if not APIFOOTBALL_API_KEY:
        return {
            "home_team": home_team_name,
            "away_team": away_team_name,
            "venue_name": None,
            "venue_city": None,
            "venue_capacity": None,
            "venue_address": None,
            "venue_surface": None,
            "error": "APIFOOTBALL_API_KEY not found"
        }
    
    try:
        # Find home team across all major leagues
        team_id, league_id, actual_name = _find_team_league(home_team_name)
        
        if not team_id:
            return {
                "home_team": home_team_name,
                "away_team": away_team_name,
                "venue_name": None,
                "venue_city": None,
                "venue_capacity": None,
                "venue_address": None,
                "venue_surface": None,
                "error": f"Team '{home_team_name}' not found in any major league"
            }
        
        # Get full team data with venue
        response = requests.get(
            BASE_URL,
            params={"action": "get_teams", "league_id": league_id, "APIkey": APIFOOTBALL_API_KEY},
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
        
        teams = response.json()
        team_data = None
        
        for team in teams:
            if team["team_key"] == team_id:
                team_data = team
                break
        
        if not team_data:
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
        
        venue = team_data.get("venue", {})
        
        return {
            "home_team": team_data.get("team_name"),
            "away_team": away_team_name,
            "venue_name": venue.get("venue_name"),
            "venue_city": venue.get("venue_city"),
            "venue_capacity": venue.get("venue_capacity"),
            "venue_address": venue.get("venue_address"),
            "venue_surface": venue.get("venue_surface"),
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
