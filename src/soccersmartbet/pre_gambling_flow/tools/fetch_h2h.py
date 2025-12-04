"""
Head-to-head match history fetcher tool.

Retrieves recent H2H match results between two teams from football-data.org API.
This is a "dumb fetcher" - returns raw match data without AI analysis.

Data Source: football-data.org /matches/{id}/head2head endpoint
Rate Limit: 10 requests/minute (free tier)
API Docs: https://www.football-data.org/documentation/quickstart
"""

import os
from typing import Any
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# API Configuration
BASE_URL = "https://api.football-data.org/v4"
API_KEY = os.getenv("FOOTBALL_DATA_API_KEY")
REQUEST_TIMEOUT = 10  # seconds


def fetch_h2h(
    home_team_id: int,
    away_team_id: int,
    limit: int = 5
) -> dict[str, Any]:
    """
    Fetch head-to-head match history between two teams.

    This tool retrieves the most recent matches between two teams to enable
    pattern analysis by the Game Intelligence Agent. Returns raw match data
    without interpretation - agents handle the analysis.

    Args:
        home_team_id: football-data.org team ID for home team
        away_team_id: football-data.org team ID for away team
        limit: Number of recent H2H matches to retrieve (default: 5)

    Returns:
        Dictionary with structure:
        {
            "matches": [
                {
                    "date": "2024-11-15",
                    "home_team": "Team A",
                    "away_team": "Team B",
                    "score_home": 2,
                    "score_away": 1,
                    "winner": "HOME_TEAM" | "AWAY_TEAM" | "DRAW"
                },
                ...
            ],
            "total_matches": 5,
            "error": None  # or error message if request failed
        }

    Error Handling:
        - Missing API key: Returns error dict with message
        - API request failure: Returns error dict with status code
        - Network timeout: Returns error dict with timeout message
        - Partial data: Returns available matches with flag

    Example:
        >>> result = fetch_h2h(home_team_id=57, away_team_id=61, limit=3)
        >>> print(f"Found {result['total_matches']} H2H matches")
        >>> for match in result['matches']:
        ...     print(f"{match['date']}: {match['home_team']} vs {match['away_team']}")
    """
    # Validate API key
    if not API_KEY:
        return {
            "matches": [],
            "total_matches": 0,
            "error": "FOOTBALL_DATA_API_KEY not found in environment variables"
        }

    # First, we need to get a match ID between these two teams
    # We'll search for upcoming matches to get a match ID for H2H lookup
    try:
        # Try to find an upcoming match between these teams
        # This is a workaround since the H2H endpoint requires a match ID
        from datetime import datetime, timedelta
        
        today = datetime.now().strftime("%Y-%m-%d")
        future = (datetime.now() + timedelta(days=365)).strftime("%Y-%m-%d")
        
        # Search for matches involving either team
        headers = {"X-Auth-Token": API_KEY}
        
        # Try to get matches for home team
        matches_response = requests.get(
            f"{BASE_URL}/teams/{home_team_id}/matches",
            headers=headers,
            params={"dateFrom": "2020-01-01", "dateTo": future},
            timeout=REQUEST_TIMEOUT
        )
        
        if matches_response.status_code != 200:
            return {
                "matches": [],
                "total_matches": 0,
                "error": f"API request failed with status {matches_response.status_code}: {matches_response.text}"
            }
        
        matches_data = matches_response.json()
        
        # Find a match between these two teams
        match_id = None
        for match in matches_data.get("matches", []):
            home_id = match.get("homeTeam", {}).get("id")
            away_id = match.get("awayTeam", {}).get("id")
            
            if (home_id == home_team_id and away_id == away_team_id) or \
               (home_id == away_team_id and away_id == home_team_id):
                match_id = match.get("id")
                break
        
        if not match_id:
            return {
                "matches": [],
                "total_matches": 0,
                "error": f"No matches found between team {home_team_id} and team {away_team_id}"
            }
        
        # Now fetch H2H data using the match ID
        h2h_response = requests.get(
            f"{BASE_URL}/matches/{match_id}/head2head",
            headers=headers,
            params={"limit": limit},
            timeout=REQUEST_TIMEOUT
        )
        
        if h2h_response.status_code != 200:
            return {
                "matches": [],
                "total_matches": 0,
                "error": f"H2H API request failed with status {h2h_response.status_code}: {h2h_response.text}"
            }
        
        h2h_data = h2h_response.json()
        
        # Parse matches from response
        matches = []
        for match in h2h_data.get("matches", []):
            # Extract match data
            utc_date = match.get("utcDate", "")
            match_date = utc_date[:10] if utc_date else "Unknown"
            
            home_team = match.get("homeTeam", {}).get("name", "Unknown")
            away_team = match.get("awayTeam", {}).get("name", "Unknown")
            
            score = match.get("score", {}).get("fullTime", {})
            score_home = score.get("home")
            score_away = score.get("away")
            
            # Determine winner
            winner = "DRAW"
            if score_home is not None and score_away is not None:
                if score_home > score_away:
                    winner = "HOME_TEAM"
                elif score_away > score_home:
                    winner = "AWAY_TEAM"
            
            matches.append({
                "date": match_date,
                "home_team": home_team,
                "away_team": away_team,
                "score_home": score_home,
                "score_away": score_away,
                "winner": winner
            })
        
        return {
            "matches": matches,
            "total_matches": len(matches),
            "error": None
        }
    
    except requests.Timeout:
        return {
            "matches": [],
            "total_matches": 0,
            "error": f"Request timeout after {REQUEST_TIMEOUT} seconds"
        }
    except requests.RequestException as e:
        return {
            "matches": [],
            "total_matches": 0,
            "error": f"Network error: {str(e)}"
        }
    except Exception as e:
        return {
            "matches": [],
            "total_matches": 0,
            "error": f"Unexpected error: {str(e)}"
        }
