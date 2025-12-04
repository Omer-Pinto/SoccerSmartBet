"""
fetch_key_players_form: Retrieve top performers' statistics for a team.

This "dumb fetcher" tool retrieves player statistics from apifootball.com
to identify key contributors for a team. Returns raw data without AI analysis.

Data Source: apifootball.com
Endpoint: get_topscorers (league top scorers)
Rate Limit: 180 requests/hour (6,480/day) - free tier
API Docs: https://apifootball.com/documentation/

Usage Pattern:
- Team Intelligence Agent calls this to assess key player availability
- Returns cumulative season stats (goals, assists, matches played, rating)
- Includes injury status for each player
- Filters league-wide data by team_id

Limitations:
- Returns season totals only (no recent form window available from API)
- Relies on league_id to fetch data, then filters by team_id
- Top scorers endpoint may not include defensive players with low goal contributions
"""

import os
from typing import Optional
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# API Configuration
BASE_URL = "https://apiv3.apifootball.com"
API_KEY = os.getenv("APIFOOTBALL_API_KEY")
DEFAULT_TIMEOUT = 10  # seconds


def fetch_key_players_form(
    team_id: int,
    league_id: int,
    top_n: int = 5,
    timeout: Optional[int] = None
) -> dict:
    """
    Fetch top performers' statistics for a specific team.

    Retrieves league top scorers from apifootball.com, filters by team_id,
    and returns top N players ranked by goals + assists contribution.

    Args:
        team_id: apifootball.com team ID (e.g., 33 for Man City)
        league_id: apifootball.com league ID (e.g., 152 for Premier League)
        top_n: Number of top players to return (default: 5)
        timeout: Request timeout in seconds (default: 10)

    Returns:
        dict with structure:
        {
            "top_players": [
                {
                    "player_name": "John Doe",
                    "player_type": "Attacker",
                    "player_goals": 15,
                    "player_assists": 8,
                    "player_match_played": 20,
                    "player_rating": "7.8",
                    "player_injured": "No"
                },
                ...
            ],
            "total_players": 5
        }
        
        On error:
        {
            "top_players": [],
            "total_players": 0,
            "error": "Error message"
        }

    Example:
        >>> result = fetch_key_players_form(team_id=33, league_id=152, top_n=5)
        >>> print(f"Found {result['total_players']} key players")
        >>> for player in result['top_players']:
        ...     print(f"{player['player_name']}: {player['player_goals']} goals")
    """
    # Validate API key
    if not API_KEY:
        return {
            "top_players": [],
            "total_players": 0,
            "error": "APIFOOTBALL_API_KEY not found in environment"
        }

    # Set timeout
    request_timeout = timeout if timeout is not None else DEFAULT_TIMEOUT

    try:
        # Fetch league top scorers
        params = {
            "APIkey": API_KEY,
            "action": "get_topscorers",
            "league_id": league_id
        }

        response = requests.get(BASE_URL, params=params, timeout=request_timeout)
        response.raise_for_status()

        data = response.json()

        # Handle API error responses
        if isinstance(data, dict) and "error" in data:
            return {
                "top_players": [],
                "total_players": 0,
                "error": f"API error: {data['error']}"
            }

        # Validate response is a list
        if not isinstance(data, list):
            return {
                "top_players": [],
                "total_players": 0,
                "error": f"Unexpected API response format: {type(data)}"
            }

        # Filter players by team_id
        # apifootball.com returns team_key as string, so convert for comparison
        team_id_str = str(team_id)
        team_players = [
            player for player in data
            if player.get("team_key") == team_id_str
        ]

        # If no players found by team_key, try filtering by team_name
        # (some API responses use different field names)
        if not team_players:
            # Try to find team name from any player in the data
            # This is a fallback - normally team_key should work
            team_players = [
                player for player in data
                if str(player.get("team_key", "")) == team_id_str
                or str(player.get("team_id", "")) == team_id_str
            ]

        # Calculate contribution score (goals + assists) for ranking
        for player in team_players:
            goals = int(player.get("goals", 0) or 0)
            assists = int(player.get("assists", 0) or 0)
            player["_contribution_score"] = goals + assists

        # Sort by contribution score (goals + assists) descending
        team_players.sort(key=lambda p: p["_contribution_score"], reverse=True)

        # Take top N players
        top_players = team_players[:top_n]

        # Format output - extract relevant fields
        formatted_players = []
        for player in top_players:
            formatted_players.append({
                "player_name": player.get("player_name", "Unknown"),
                "player_type": player.get("player_type", "Unknown"),
                "player_goals": int(player.get("goals", 0) or 0),
                "player_assists": int(player.get("assists", 0) or 0),
                "player_match_played": int(player.get("player_match_played", 0) or 0),
                "player_rating": player.get("player_rating", "N/A"),
                "player_injured": player.get("player_injured", "Unknown")
            })

        return {
            "top_players": formatted_players,
            "total_players": len(formatted_players)
        }

    except requests.exceptions.Timeout:
        return {
            "top_players": [],
            "total_players": 0,
            "error": f"Request timeout after {request_timeout} seconds"
        }
    except requests.exceptions.RequestException as e:
        return {
            "top_players": [],
            "total_players": 0,
            "error": f"Request failed: {str(e)}"
        }
    except (ValueError, KeyError) as e:
        return {
            "top_players": [],
            "total_players": 0,
            "error": f"Data parsing error: {str(e)}"
        }
    except Exception as e:
        return {
            "top_players": [],
            "total_players": 0,
            "error": f"Unexpected error: {str(e)}"
        }
