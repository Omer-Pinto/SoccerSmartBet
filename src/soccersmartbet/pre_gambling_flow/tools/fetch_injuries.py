"""
Fetch Injuries Tool - Dumb Fetcher for Team Injury Data

Retrieves current injury list for a team from apifootball.com API.
This is a "dumb fetcher" - it returns raw data without AI analysis.

API Reference:
- Endpoint: https://apiv3.apifootball.com
- Action: get_teams (returns team data with player injury info)
- Rate Limit: 180 requests/hour (6,480/day)
- Authentication: API key in query params

Data Source: apifootball.com
Usage Pattern: Team Intelligence Agent uses this to assess injury impact
"""

import os
import requests
from typing import Dict, List, Any
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# API Configuration
API_KEY = os.getenv("APIFOOTBALL_API_KEY")
BASE_URL = "https://apiv3.apifootball.com"
DEFAULT_TIMEOUT = 10


def fetch_injuries(team_id: int, league_id: int) -> Dict[str, Any]:
    """
    Fetch current injury list for a team.
    
    This tool retrieves the list of currently injured players from apifootball.com.
    It filters the team's player roster to return only those with active injuries
    (player_injured == "Yes").
    
    Args:
        team_id: apifootball.com team ID (e.g., 33 for Man City)
        league_id: apifootball.com league ID (e.g., 152 for Premier League)
    
    Returns:
        dict: Structured injury data with format:
            {
                "injuries": [
                    {
                        "player_name": "John Doe",
                        "injury_type": "Knee injury",
                        "injury_reason": "Training",
                        "player_injured": "Yes"
                    },
                    ...
                ],
                "total_injuries": 3,
                "team_id": 33,
                "team_name": "Manchester City"
            }
        
        On error, returns:
            {
                "injuries": [],
                "total_injuries": 0,
                "error": "Error message description"
            }
    
    Example:
        >>> result = fetch_injuries(team_id=33, league_id=152)
        >>> print(f"Found {result['total_injuries']} injured players")
        >>> for injury in result['injuries']:
        ...     print(f"{injury['player_name']}: {injury['injury_type']}")
    
    Note:
        - Returns empty list if no injuries found (not an error)
        - Returns error dict if API call fails
        - Handles missing API key gracefully
        - Uses 10-second timeout for API requests
    """
    
    # Validate API key
    if not API_KEY:
        return {
            "injuries": [],
            "total_injuries": 0,
            "error": "APIFOOTBALL_API_KEY not found in environment"
        }
    
    # Prepare API request
    params = {
        "APIkey": API_KEY,
        "action": "get_teams",
        "league_id": league_id
    }
    
    try:
        # Make API request
        response = requests.get(BASE_URL, params=params, timeout=DEFAULT_TIMEOUT)
        response.raise_for_status()
        
        data = response.json()
        
        # Validate response structure
        if not isinstance(data, list):
            return {
                "injuries": [],
                "total_injuries": 0,
                "error": f"Unexpected API response format: expected list, got {type(data)}"
            }
        
        # Find the specific team
        team = None
        for t in data:
            # Match by team_key (ID) - handle both string and int
            if "team_key" in t and str(t["team_key"]) == str(team_id):
                team = t
                break
        
        if not team:
            return {
                "injuries": [],
                "total_injuries": 0,
                "error": f"Team with ID {team_id} not found in league {league_id}"
            }
        
        # Extract injured players
        injured_players = []
        
        if "players" in team and team["players"]:
            for player in team["players"]:
                # Filter only currently injured players
                if player.get("player_injured") == "Yes":
                    injured_players.append({
                        "player_name": player.get("player_name", "Unknown"),
                        "injury_type": player.get("player_injury_type", "Not specified"),
                        "injury_reason": player.get("player_injury_reason", "Not specified"),
                        "player_injured": player.get("player_injured", "Yes"),
                        # Additional fields for analysis
                        "player_type": player.get("player_type", "Unknown"),  # Position
                        "player_match_played": player.get("player_match_played", "0"),
                        "player_goals": player.get("player_goals", "0")
                    })
        
        return {
            "injuries": injured_players,
            "total_injuries": len(injured_players),
            "team_id": team_id,
            "team_name": team.get("team_name", "Unknown")
        }
    
    except requests.exceptions.Timeout:
        return {
            "injuries": [],
            "total_injuries": 0,
            "error": f"API request timed out after {DEFAULT_TIMEOUT} seconds"
        }
    
    except requests.exceptions.RequestException as e:
        return {
            "injuries": [],
            "total_injuries": 0,
            "error": f"API request failed: {str(e)}"
        }
    
    except Exception as e:
        return {
            "injuries": [],
            "total_injuries": 0,
            "error": f"Unexpected error: {str(e)}"
        }
