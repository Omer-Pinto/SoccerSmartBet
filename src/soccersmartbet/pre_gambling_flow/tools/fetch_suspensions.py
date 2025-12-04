"""
Fetch team suspensions from apifootball.com API.

This is a "dumb fetcher" tool that retrieves raw suspension data without analysis.
The Team Intelligence Agent will analyze the impact of suspensions on lineup strength.

Data Source: apifootball.com (180 requests/hour free tier)
API Docs: https://apifootball.com/documentation/
Endpoint: get_teams (returns team with player suspension indicators)

Note: apifootball.com may not provide explicit "suspended" status. This tool infers
suspensions from red cards and yellow card accumulation based on common league rules.
For more accurate suspension data, cross-reference with league-specific rules.
"""

import os
from typing import Dict, Any, Optional
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# API Configuration
API_KEY = os.getenv("APIFOOTBALL_API_KEY")
BASE_URL = "https://apiv3.apifootball.com"
DEFAULT_TIMEOUT = 10  # seconds


def fetch_suspensions(team_id: int, league_id: int) -> Dict[str, Any]:
    """
    Fetch current suspension list for a team.

    This tool retrieves player suspension data from apifootball.com. Suspensions are
    inferred from red cards (immediate suspension) and yellow card accumulation
    (typically 5 yellows = 1 game suspension in major leagues).

    NOTE: apifootball.com may not explicitly mark suspension status. This implementation
    uses heuristics based on card data. For production use, consider league-specific
    suspension tracking APIs or official league sources.

    Parameters
    ----------
    team_id : int
        apifootball.com team ID (e.g., 33 for Manchester City)
    league_id : int
        apifootball.com league ID (e.g., 152 for Premier League)

    Returns
    -------
    dict
        Suspension data in the format:
        {
            "suspensions": [
                {
                    "player_name": "John Doe",
                    "suspension_type": "Red Card" or "Yellow Accumulation",
                    "suspension_reason": "Direct Red Card" or "5 Yellow Cards",
                    "games_remaining": <inferred based on card type>
                },
                ...
            ],
            "total_suspensions": <count of suspended players>,
            "error": <error message if request failed, else None>
        }

    Examples
    --------
    >>> fetch_suspensions(team_id=33, league_id=152)
    {
        "suspensions": [
            {
                "player_name": "Kyle Walker",
                "suspension_type": "Red Card",
                "suspension_reason": "Direct Red Card",
                "games_remaining": 1
            }
        ],
        "total_suspensions": 1,
        "error": None
    }

    >>> fetch_suspensions(team_id=999, league_id=152)  # Invalid team
    {
        "suspensions": [],
        "total_suspensions": 0,
        "error": "Team not found in league data"
    }

    Notes
    -----
    - Red cards typically result in 1-3 game suspensions depending on severity
    - Yellow accumulation (5 yellows) typically results in 1 game suspension
    - This tool assumes recent cards indicate current suspensions
    - For accurate suspension tracking, use official league sources or specialized APIs
    - Rate limit: 180 requests/hour (6,480/day) on free tier
    """
    # Validate API key
    if not API_KEY:
        return {
            "suspensions": [],
            "total_suspensions": 0,
            "error": "APIFOOTBALL_API_KEY not found in environment variables"
        }

    # Build request parameters
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

        # Handle empty or invalid response
        if not isinstance(data, list) or not data:
            return {
                "suspensions": [],
                "total_suspensions": 0,
                "error": "No teams data returned from API"
            }

        # Find the specific team
        team_data = None
        for team in data:
            # Match by team_key (ID) if available, fallback to name matching
            if str(team.get("team_key", "")) == str(team_id):
                team_data = team
                break

        if not team_data:
            return {
                "suspensions": [],
                "total_suspensions": 0,
                "error": f"Team with ID {team_id} not found in league {league_id}"
            }

        # Extract players with suspension indicators
        players = team_data.get("players", [])
        if not players:
            return {
                "suspensions": [],
                "total_suspensions": 0,
                "error": None
            }

        suspended_players = []

        for player in players:
            player_name = player.get("player_name", "Unknown")
            red_cards = int(player.get("player_red_cards", 0) or 0)
            yellow_cards = int(player.get("player_yellow_cards", 0) or 0)

            # Infer suspension from card data
            # Red card = likely suspended for next 1-3 games
            if red_cards > 0:
                suspended_players.append({
                    "player_name": player_name,
                    "suspension_type": "Red Card",
                    "suspension_reason": f"{red_cards} Red Card(s) this season",
                    "games_remaining": 1  # Conservative estimate; actual varies by league
                })

            # Yellow accumulation = typically 5 yellows = 1 game suspension
            elif yellow_cards >= 5:
                # Calculate suspension games (every 5 yellows = 1 game)
                suspension_count = yellow_cards // 5
                suspended_players.append({
                    "player_name": player_name,
                    "suspension_type": "Yellow Accumulation",
                    "suspension_reason": f"{yellow_cards} Yellow Cards (threshold: 5)",
                    "games_remaining": suspension_count
                })

        return {
            "suspensions": suspended_players,
            "total_suspensions": len(suspended_players),
            "error": None
        }

    except requests.exceptions.Timeout:
        return {
            "suspensions": [],
            "total_suspensions": 0,
            "error": f"Request timeout after {DEFAULT_TIMEOUT} seconds"
        }
    except requests.exceptions.RequestException as e:
        return {
            "suspensions": [],
            "total_suspensions": 0,
            "error": f"API request failed: {str(e)}"
        }
    except (ValueError, KeyError) as e:
        return {
            "suspensions": [],
            "total_suspensions": 0,
            "error": f"Error parsing API response: {str(e)}"
        }
    except Exception as e:
        return {
            "suspensions": [],
            "total_suspensions": 0,
            "error": f"Unexpected error: {str(e)}"
        }
