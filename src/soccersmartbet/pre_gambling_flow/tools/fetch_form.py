"""
fetch_form tool - Retrieve team's recent match results.

This is a "dumb fetcher" that retrieves raw match data from apifootball.com.
No AI analysis - just data retrieval for the Team Intelligence Agent.

Data Source: apifootball.com (get_events endpoint)
Rate Limit: 180 requests/hour (6,480/day) on free tier
API Docs: https://apifootball.com/documentation/
"""

import os
from datetime import datetime, timedelta
from typing import Any

import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# API Configuration
API_KEY = os.getenv("APIFOOTBALL_API_KEY")
BASE_URL = "https://apiv3.apifootball.com"
DEFAULT_TIMEOUT = 10  # seconds


def fetch_form(team_id: int, limit: int = 5) -> dict[str, Any]:
    """
    Fetch recent match results for a team (last N games).

    This tool retrieves raw match data from apifootball.com's get_events endpoint
    and structures it for the Team Intelligence Agent to analyze form trends.

    Args:
        team_id: apifootball.com team ID (integer)
        limit: Number of recent matches to retrieve (default: 5)

    Returns:
        dict with structure:
        {
            "matches": [
                {
                    "date": "2024-11-15",
                    "opponent": "Team B",
                    "home_away": "HOME" | "AWAY",
                    "result": "W" | "D" | "L",
                    "goals_for": 2,
                    "goals_against": 1,
                    "competition": "Premier League"
                },
                ...
            ],
            "total_matches": 5,
            "record": {
                "wins": 3,
                "draws": 1,
                "losses": 1
            }
        }

        On error, returns:
        {
            "error": "Error message",
            "matches": [],
            "total_matches": 0,
            "record": {"wins": 0, "draws": 0, "losses": 0}
        }

    Example:
        >>> form = fetch_form(team_id=33, limit=5)  # Man City last 5 games
        >>> print(form["record"])  # {"wins": 4, "draws": 1, "losses": 0}
    """
    # Validate API key
    if not API_KEY:
        return {
            "error": "APIFOOTBALL_API_KEY not found in environment",
            "matches": [],
            "total_matches": 0,
            "record": {"wins": 0, "draws": 0, "losses": 0}
        }

    try:
        # Get matches from last 60 days (we'll filter to most recent N)
        to_date = datetime.now().strftime("%Y-%m-%d")
        from_date = (datetime.now() - timedelta(days=60)).strftime("%Y-%m-%d")

        params = {
            "APIkey": API_KEY,
            "action": "get_events",
            "from": from_date,
            "to": to_date,
        }

        response = requests.get(BASE_URL, params=params, timeout=DEFAULT_TIMEOUT)
        response.raise_for_status()

        data = response.json()

        # Filter matches involving this team (as home or away)
        team_matches = []
        for match in data:
            # Skip if not finished
            if match.get("match_status") != "Finished":
                continue

            match_home_id = match.get("match_hometeam_id")
            match_away_id = match.get("match_awayteam_id")

            # Check if our team is involved
            if match_home_id == str(team_id):
                # Team played at home
                opponent = match.get("match_awayteam_name", "Unknown")
                goals_for = int(match.get("match_hometeam_score", 0))
                goals_against = int(match.get("match_awayteam_score", 0))
                home_away = "HOME"
            elif match_away_id == str(team_id):
                # Team played away
                opponent = match.get("match_hometeam_name", "Unknown")
                goals_for = int(match.get("match_awayteam_score", 0))
                goals_against = int(match.get("match_hometeam_score", 0))
                home_away = "AWAY"
            else:
                # Not our team
                continue

            # Determine result
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

        # Sort by date descending (most recent first) and limit
        team_matches.sort(key=lambda x: x["date"], reverse=True)
        team_matches = team_matches[:limit]

        # Calculate W/D/L record
        wins = sum(1 for m in team_matches if m["result"] == "W")
        draws = sum(1 for m in team_matches if m["result"] == "D")
        losses = sum(1 for m in team_matches if m["result"] == "L")

        return {
            "matches": team_matches,
            "total_matches": len(team_matches),
            "record": {
                "wins": wins,
                "draws": draws,
                "losses": losses
            }
        }

    except requests.exceptions.Timeout:
        return {
            "error": f"Request timeout after {DEFAULT_TIMEOUT}s",
            "matches": [],
            "total_matches": 0,
            "record": {"wins": 0, "draws": 0, "losses": 0}
        }
    except requests.exceptions.RequestException as e:
        return {
            "error": f"API request failed: {str(e)}",
            "matches": [],
            "total_matches": 0,
            "record": {"wins": 0, "draws": 0, "losses": 0}
        }
    except (KeyError, ValueError, TypeError) as e:
        return {
            "error": f"Data parsing error: {str(e)}",
            "matches": [],
            "total_matches": 0,
            "record": {"wins": 0, "draws": 0, "losses": 0}
        }
