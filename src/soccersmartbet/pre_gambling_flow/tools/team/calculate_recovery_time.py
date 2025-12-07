"""
Calculate days since team's last match (recovery time).

Clean interface: Accepts team name and upcoming match date.
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


def calculate_recovery_time(team_name: str, upcoming_match_date: str) -> Dict[str, Any]:
    """
    Calculate days between team's last match and upcoming match.
    
    Searches across all major European leagues to find the team.
    
    Args:
        team_name: Team name (e.g., "Manchester City")
        upcoming_match_date: Date of upcoming match (YYYY-MM-DD)
    
    Returns:
        {
            "team_name": "Manchester City",
            "last_match_date": "2025-12-02",
            "upcoming_match_date": "2025-12-06",
            "recovery_days": 4,
            "recovery_status": "Short" | "Normal" | "Extended",
            "error": None
        }
    """
    if not APIFOOTBALL_API_KEY:
        return {
            "team_name": team_name,
            "last_match_date": None,
            "upcoming_match_date": upcoming_match_date,
            "recovery_days": None,
            "recovery_status": None,
            "error": "APIFOOTBALL_API_KEY not found"
        }
    
    try:
        # Step 1: Find team across all major leagues
        team_id, league_id, actual_name = _find_team_league(team_name)
        
        if not team_id:
            return {
                "team_name": team_name,
                "last_match_date": None,
                "upcoming_match_date": upcoming_match_date,
                "recovery_days": None,
                "recovery_status": None,
                "error": f"Team '{team_name}' not found in any major league"
            }
        
        # Step 2: Get recent matches
        to_date = datetime.now().strftime("%Y-%m-%d")
        from_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
        
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
                "last_match_date": None,
                "upcoming_match_date": upcoming_match_date,
                "recovery_days": None,
                "recovery_status": None,
                "error": f"Matches API error: {matches_response.status_code}"
            }
        
        matches = matches_response.json()
        
        # Find most recent finished match
        finished_matches = [m for m in matches if m.get("match_status") == "Finished"]
        
        if not finished_matches:
            return {
                "team_name": team_name,
                "last_match_date": None,
                "upcoming_match_date": upcoming_match_date,
                "recovery_days": None,
                "recovery_status": None,
                "error": "No recent finished matches found"
            }
        
        # Sort by date descending
        finished_matches.sort(key=lambda x: x.get("match_date", ""), reverse=True)
        last_match_date = finished_matches[0].get("match_date")
        
        # Calculate recovery days
        last_date = datetime.strptime(last_match_date, "%Y-%m-%d")
        upcoming_date = datetime.strptime(upcoming_match_date, "%Y-%m-%d")
        recovery_days = (upcoming_date - last_date).days
        
        # Classify recovery status
        if recovery_days < 3:
            recovery_status = "Short"
        elif recovery_days <= 7:
            recovery_status = "Normal"
        else:
            recovery_status = "Extended"
        
        return {
            "team_name": team_name,
            "last_match_date": last_match_date,
            "upcoming_match_date": upcoming_match_date,
            "recovery_days": recovery_days,
            "recovery_status": recovery_status,
            "error": None
        }
    
    except requests.Timeout:
        return {
            "team_name": team_name,
            "last_match_date": None,
            "upcoming_match_date": upcoming_match_date,
            "recovery_days": None,
            "recovery_status": None,
            "error": f"Request timeout after {TIMEOUT}s"
        }
    except Exception as e:
        return {
            "team_name": team_name,
            "last_match_date": None,
            "upcoming_match_date": upcoming_match_date,
            "recovery_days": None,
            "recovery_status": None,
            "error": f"Unexpected error: {str(e)}"
        }
