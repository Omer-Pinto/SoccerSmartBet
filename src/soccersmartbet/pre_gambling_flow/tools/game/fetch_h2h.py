"""
Fetch head-to-head match history between two teams.

Clean interface: Accepts team names, returns historical match data.
"""

import os
from typing import Dict, Any
import requests
from dotenv import load_dotenv
from soccersmartbet.team_registry import normalize_team_name, resolve_team

load_dotenv()

# API Configuration
FOOTBALL_DATA_API_KEY = os.getenv("FOOTBALL_DATA_API_KEY")
BASE_URL = "https://api.football-data.org/v4"
TIMEOUT = 10


def fetch_h2h(home_team_name: str, away_team_name: str, limit: int = 5) -> Dict[str, Any]:
    """
    Fetch head-to-head match history between two teams.
    
    Finds the next scheduled match between these teams and retrieves their
    historical encounters. Searches across all major European competitions.
    
    Args:
        home_team_name: Home team name (e.g., "Manchester City")
        away_team_name: Away team name (e.g., "Tottenham")
        limit: Number of historical matches to return (default: 5)
    
    Returns:
        {
            "home_team": "Manchester City",
            "away_team": "Tottenham",
            "upcoming_match_id": 123456,
            "upcoming_match_date": "2025-12-15",
            "h2h_matches": [
                {
                    "date": "2025-02-02",
                    "home_team": "Tottenham",
                    "away_team": "Manchester City",
                    "score_home": 1,
                    "score_away": 3,
                    "winner": "Tottenham"
                },
                ...
            ],
            "total_h2h": 5,
            "error": None
        }
        
        On error:
        {
            "home_team": home_team_name,
            "away_team": away_team_name,
            "upcoming_match_id": None,
            "upcoming_match_date": None,
            "h2h_matches": [],
            "total_h2h": 0,
            "error": "Error description"
        }
    """
    if not FOOTBALL_DATA_API_KEY:
        return {
            "home_team": home_team_name,
            "away_team": away_team_name,
            "upcoming_match_id": None,
            "upcoming_match_date": None,
            "h2h_matches": [],
            "total_h2h": 0,
            "error": "FOOTBALL_DATA_API_KEY not found in environment"
        }
    
    headers = {"X-Auth-Token": FOOTBALL_DATA_API_KEY}
    
    try:
        # Step 1: Find next scheduled match between these teams
        # Search across all major competitions
        search_urls = [
            f"{BASE_URL}/competitions/PL/matches",   # Premier League
            f"{BASE_URL}/competitions/PD/matches",   # La Liga
            f"{BASE_URL}/competitions/SA/matches",   # Serie A
            f"{BASE_URL}/competitions/BL1/matches",  # Bundesliga
            f"{BASE_URL}/competitions/FL1/matches",  # Ligue 1
            f"{BASE_URL}/competitions/CL/matches",   # Champions League
        ]
        
        upcoming_match = None

        # Resolve input names to canonical names for robust matching
        home_canonical = resolve_team(home_team_name) or home_team_name
        away_canonical = resolve_team(away_team_name) or away_team_name
        home_input_norm = normalize_team_name(home_canonical)
        away_input_norm = normalize_team_name(away_canonical)

        # Collect all candidate matches across competitions, then pick earliest
        candidates = []

        # Try each competition URL
        for url in search_urls:
            response = requests.get(
                url,
                headers=headers,
                params={"status": "SCHEDULED"},
                timeout=TIMEOUT
            )

            if response.status_code != 200:
                continue  # Try next competition

            matches = response.json().get("matches", [])

            # Find matches between these two teams
            for match in matches:
                # Skip placeholder matches where team names are not yet assigned
                home_name = (match.get("homeTeam") or {}).get("name")
                away_name = (match.get("awayTeam") or {}).get("name")
                if not home_name or not away_name:
                    continue

                # Resolve API names to canonical for apples-to-apples comparison
                home_resolved = resolve_team(home_name) or home_name
                away_resolved = resolve_team(away_name) or away_name
                home_norm = normalize_team_name(home_resolved)
                away_norm = normalize_team_name(away_resolved)

                # Check if team names match (either order) using canonical names
                home_matches_input_home = home_input_norm in home_norm or home_norm in home_input_norm
                away_matches_input_away = away_input_norm in away_norm or away_norm in away_input_norm

                home_matches_input_away = home_input_norm in away_norm or away_norm in home_input_norm
                away_matches_input_home = away_input_norm in home_norm or home_norm in away_input_norm

                if (home_matches_input_home and away_matches_input_away) or \
                   (home_matches_input_away and away_matches_input_home):
                    candidates.append(match)

        # Pick the earliest scheduled match among all candidates
        if candidates:
            candidates.sort(key=lambda m: m.get("utcDate") or "")
            upcoming_match = candidates[0]
        
        if not upcoming_match:
            return {
                "home_team": home_team_name,
                "away_team": away_team_name,
                "upcoming_match_id": None,
                "upcoming_match_date": None,
                "h2h_matches": [],
                "total_h2h": 0,
                "error": f"No upcoming match found between {home_team_name} and {away_team_name}"
            }
        
        match_id = upcoming_match["id"]
        match_date = upcoming_match.get("utcDate", "")[:10]
        
        # Step 2: Get H2H history for this match
        h2h_response = requests.get(
            f"{BASE_URL}/matches/{match_id}/head2head",
            headers=headers,
            params={"limit": limit},
            timeout=TIMEOUT
        )
        
        if h2h_response.status_code != 200:
            return {
                "home_team": home_team_name,
                "away_team": away_team_name,
                "upcoming_match_id": match_id,
                "upcoming_match_date": match_date,
                "h2h_matches": [],
                "total_h2h": 0,
                "error": f"H2H API error: {h2h_response.status_code}"
            }
        
        h2h_data = h2h_response.json()
        h2h_matches = []
        
        for match in h2h_data.get("matches", []):
            utc_date = match.get("utcDate", "")
            match_date_str = utc_date[:10] if utc_date else "Unknown"
            
            home = match.get("homeTeam", {}).get("name", "Unknown")
            away = match.get("awayTeam", {}).get("name", "Unknown")
            
            score = match.get("score", {}).get("fullTime", {})
            score_home = score.get("home")
            score_away = score.get("away")
            
            winner = "DRAW"
            if score_home is not None and score_away is not None:
                if score_home > score_away:
                    # home side of THIS historical match won — resolve to user's input name
                    home_match_canonical = resolve_team(home) or home
                    input_home_canonical = resolve_team(home_team_name) or home_team_name
                    if normalize_team_name(home_match_canonical) == normalize_team_name(input_home_canonical):
                        winner = home_team_name
                    else:
                        winner = away_team_name
                elif score_away > score_home:
                    # away side of THIS historical match won — resolve to user's input name
                    away_match_canonical = resolve_team(away) or away
                    input_home_canonical = resolve_team(home_team_name) or home_team_name
                    if normalize_team_name(away_match_canonical) == normalize_team_name(input_home_canonical):
                        winner = home_team_name
                    else:
                        winner = away_team_name
            
            h2h_matches.append({
                "date": match_date_str,
                "home_team": home,
                "away_team": away,
                "score_home": score_home,
                "score_away": score_away,
                "winner": winner
            })
        
        return {
            "home_team": home_team_name,
            "away_team": away_team_name,
            "upcoming_match_id": match_id,
            "upcoming_match_date": match_date,
            "h2h_matches": h2h_matches,
            "total_h2h": len(h2h_matches),
            "error": None
        }
    
    except requests.Timeout:
        return {
            "home_team": home_team_name,
            "away_team": away_team_name,
            "upcoming_match_id": None,
            "upcoming_match_date": None,
            "h2h_matches": [],
            "total_h2h": 0,
            "error": f"Request timeout after {TIMEOUT}s"
        }
    except Exception as e:
        return {
            "home_team": home_team_name,
            "away_team": away_team_name,
            "upcoming_match_id": None,
            "upcoming_match_date": None,
            "h2h_matches": [],
            "total_h2h": 0,
            "error": f"Unexpected error: {str(e)}"
        }
