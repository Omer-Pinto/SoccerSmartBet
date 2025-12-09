"""
Fetch team's recent match form.

Clean interface: Accepts team name, returns last 5 matches.
"""

import os
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Tuple
import requests
from dotenv import load_dotenv

load_dotenv()

APIFOOTBALL_API_KEY = os.getenv("APIFOOTBALL_API_KEY")
BASE_URL = "https://apiv3.apifootball.com"
TIMEOUT = 15

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


def fetch_form(team_name: str, limit: int = 5) -> Dict[str, Any]:
    """
    Fetch team's recent match results.
    
    Searches across all major European leagues to find the team.
    
    Args:
        team_name: Team name (e.g., "Manchester City")
        limit: Number of recent matches (default: 5)
    
    Returns:
        {
            "team_name": "Manchester City",
            "matches": [
                {
                    "date": "2025-12-02",
                    "opponent": "Fulham",
                    "home_away": "HOME" | "AWAY",
                    "result": "W" | "D" | "L",
                    "goals_for": 5,
                    "goals_against": 4,
                    "competition": "Premier League"
                },
                ...
            ],
            "record": {"wins": 3, "draws": 1, "losses": 1},
            "error": None
        }
    """
    if not APIFOOTBALL_API_KEY:
        return {
            "team_name": team_name,
            "matches": [],
            "record": {"wins": 0, "draws": 0, "losses": 0},
            "error": "APIFOOTBALL_API_KEY not found"
        }
    
    try:
        # Step 1: Find team across all major leagues
        team_id, league_id, actual_name = _find_team_league(team_name)
        
        if not team_id:
            return {
                "team_name": team_name,
                "matches": [],
                "record": {"wins": 0, "draws": 0, "losses": 0},
                "error": f"Team '{team_name}' not found in any major league"
            }
        
        # Step 2: Get recent matches
        to_date = datetime.now().strftime("%Y-%m-%d")
        from_date = (datetime.now() - timedelta(days=60)).strftime("%Y-%m-%d")
        
        matches_response = requests.get(
            BASE_URL,
            params={
                "action": "get_events",
                "from": from_date,
                "to": to_date,
                "team_id": team_id,
                "APIkey": APIFOOTBALL_API_KEY
            },
            timeout=TIMEOUT
        )
        
        if matches_response.status_code != 200:
            return {
                "team_name": team_name,
                "matches": [],
                "record": {"wins": 0, "draws": 0, "losses": 0},
                "error": f"Matches API error: {matches_response.status_code}"
            }
        
        all_matches = matches_response.json()
        
        # Filter finished matches only
        team_matches = []
        for match in all_matches:
            if match.get("match_status") != "Finished":
                continue
            
            is_home = match.get("match_hometeam_id") == str(team_id)
            
            if is_home:
                opponent = match.get("match_awayteam_name", "Unknown")
                goals_for = int(match.get("match_hometeam_score", 0))
                goals_against = int(match.get("match_awayteam_score", 0))
                home_away = "HOME"
            else:
                opponent = match.get("match_hometeam_name", "Unknown")
                goals_for = int(match.get("match_awayteam_score", 0))
                goals_against = int(match.get("match_hometeam_score", 0))
                home_away = "AWAY"
            
            if goals_for > goals_against:
                result = "W"
            elif goals_for < goals_against:
                result = "L"
            else:
                result = "D"
            
            team_matches.append({
                "date": match.get("match_date", ""),
                "opponent": opponent,
                "home_away": home_away,
                "result": result,
                "goals_for": goals_for,
                "goals_against": goals_against,
                "competition": match.get("league_name", "Unknown")
            })
        
        # Sort by date descending
        team_matches.sort(key=lambda x: x["date"], reverse=True)
        team_matches = team_matches[:limit]
        
        # Calculate record
        wins = sum(1 for m in team_matches if m["result"] == "W")
        draws = sum(1 for m in team_matches if m["result"] == "D")
        losses = sum(1 for m in team_matches if m["result"] == "L")
        
        return {
            "team_name": team_name,
            "matches": team_matches,
            "record": {"wins": wins, "draws": draws, "losses": losses},
            "error": None
        }
    
    except requests.Timeout:
        return {
            "team_name": team_name,
            "matches": [],
            "record": {"wins": 0, "draws": 0, "losses": 0},
            "error": f"Request timeout after {TIMEOUT}s"
        }
    except Exception as e:
        return {
            "team_name": team_name,
            "matches": [],
            "record": {"wins": 0, "draws": 0, "losses": 0},
            "error": f"Unexpected error: {str(e)}"
        }
