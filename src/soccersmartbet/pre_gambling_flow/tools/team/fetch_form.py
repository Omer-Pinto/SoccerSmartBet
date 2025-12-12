"""
Fetch team's recent match form.

Uses football-data.org to get last N matches.
"""

import os
from typing import Dict, Any
import requests
from dotenv import load_dotenv
from datetime import datetime, timedelta

load_dotenv()

FOOTBALL_DATA_API_KEY = os.getenv("FOOTBALL_DATA_API_KEY")
BASE_URL = "https://api.football-data.org/v4"
TIMEOUT = 15


def fetch_form(team_name: str, limit: int = 5) -> Dict[str, Any]:
    """
    Fetch team's recent match results.
    
    Args:
        team_name: Team name (e.g., "Manchester City")
        limit: Number of recent matches to return (default: 5)
    
    Returns:
        {
            "team_name": "Manchester City",
            "matches": [
                {
                    "date": "2025-12-01",
                    "opponent": "Liverpool",
                    "home_away": "HOME",
                    "result": "W",
                    "goals_for": 3,
                    "goals_against": 1,
                    "competition": "Premier League"
                },
                ...
            ],
            "record": {"wins": 3, "draws": 1, "losses": 1},
            "error": None
        }
    """
    if not FOOTBALL_DATA_API_KEY:
        return {
            "team_name": team_name,
            "matches": [],
            "record": {"wins": 0, "draws": 0, "losses": 0},
            "error": "FOOTBALL_DATA_API_KEY not found"
        }
    
    headers = {"X-Auth-Token": FOOTBALL_DATA_API_KEY}
    
    try:
        # Step 1: Search for team across major competitions
        competitions = ["PL", "PD", "SA", "BL1", "FL1", "CL"]
        team_lower = team_name.lower()
        
        team_id = None
        for comp in competitions:
            try:
                response = requests.get(
                    f"{BASE_URL}/competitions/{comp}/teams",
                    headers=headers,
                    timeout=TIMEOUT
                )
                
                if response.status_code != 200:
                    continue
                
                data = response.json()
                teams = data.get("teams", [])
                
                for team in teams:
                    if team_lower in team.get("name", "").lower() or team_lower in team.get("shortName", "").lower():
                        team_id = team.get("id")
                        break
                
                if team_id:
                    break
            except:
                continue
        
        if not team_id:
            return {
                "team_name": team_name,
                "matches": [],
                "record": {"wins": 0, "draws": 0, "losses": 0},
                "error": f"Team '{team_name}' not found"
            }
        
        # Step 2: Get recent finished matches for this team
        date_to = datetime.now().strftime("%Y-%m-%d")
        date_from = (datetime.now() - timedelta(days=90)).strftime("%Y-%m-%d")
        
        response = requests.get(
            f"{BASE_URL}/teams/{team_id}/matches",
            headers=headers,
            params={
                "status": "FINISHED",
                "dateFrom": date_from,
                "dateTo": date_to
            },
            timeout=TIMEOUT
        )
        
        if response.status_code != 200:
            return {
                "team_name": team_name,
                "matches": [],
                "record": {"wins": 0, "draws": 0, "losses": 0},
                "error": f"API error: {response.status_code}"
            }
        
        data = response.json()
        all_matches = data.get("matches", [])
        
        # Sort by date descending and take last N
        all_matches.sort(key=lambda m: m.get("utcDate", ""), reverse=True)
        recent_matches = all_matches[:limit]
        
        # Format matches
        formatted_matches = []
        wins = draws = losses = 0
        
        for match in recent_matches:
            home_team = match.get("homeTeam", {}).get("name", "")
            away_team = match.get("awayTeam", {}).get("name", "")
            score = match.get("score", {}).get("fullTime", {})
            home_score = score.get("home")
            away_score = score.get("away")
            
            if home_score is None or away_score is None:
                continue  # Skip if no score
            
            is_home = home_team.lower() == team_lower or team_id == match.get("homeTeam", {}).get("id")
            opponent = away_team if is_home else home_team
            goals_for = home_score if is_home else away_score
            goals_against = away_score if is_home else home_score
            
            # Determine result
            if goals_for > goals_against:
                result = "W"
                wins += 1
            elif goals_for < goals_against:
                result = "L"
                losses += 1
            else:
                result = "D"
                draws += 1
            
            formatted_matches.append({
                "date": match.get("utcDate", "")[:10],
                "opponent": opponent,
                "home_away": "HOME" if is_home else "AWAY",
                "result": result,
                "goals_for": goals_for,
                "goals_against": goals_against,
                "competition": match.get("competition", {}).get("name", "Unknown")
            })
        
        return {
            "team_name": team_name,
            "matches": formatted_matches,
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
