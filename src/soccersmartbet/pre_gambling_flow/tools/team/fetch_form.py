"""
Fetch team's recent match form using FotMob API.

Clean interface: Accepts team name, returns last 5 matches.
NO API KEY REQUIRED - uses unofficial FotMob API.
"""

from typing import Dict, Any
from datetime import datetime

from ..fotmob_client import get_fotmob_client


def fetch_form(team_name: str, limit: int = 5) -> Dict[str, Any]:
    """
    Fetch team's recent match results.

    Searches across all major European leagues to find the team.
    Uses FotMob's team form data which shows W/D/L for recent matches.

    Args:
        team_name: Team name (e.g., "Manchester City", "Deportivo Alavés")
        limit: Number of recent matches (default: 5)

    Returns:
        {
            "team_name": "Manchester City",
            "matches": [
                {
                    "date": "2025-12-02",
                    "opponent": "Fulham",
                    "home_away": "HOME" | "AWAY" | "Unknown",
                    "result": "W" | "D" | "L",
                    "goals_for": None,  # FotMob form doesn't include scores
                    "goals_against": None,
                    "competition": "Premier League"
                },
                ...
            ],
            "record": {"wins": 3, "draws": 1, "losses": 1},
            "error": None
        }
    """
    try:
        client = get_fotmob_client()

        # Find team by name
        team_info = client.find_team(team_name)

        if not team_info:
            return {
                "team_name": team_name,
                "matches": [],
                "record": {"wins": 0, "draws": 0, "losses": 0},
                "error": f"Team '{team_name}' not found in any major league",
            }

        # Get team details with form data
        team_data = client.get_team_data(team_info["id"])

        if not team_data:
            return {
                "team_name": team_name,
                "matches": [],
                "record": {"wins": 0, "draws": 0, "losses": 0},
                "error": f"Could not fetch team data for '{team_name}'",
            }

        overview = team_data.get("overview", {})
        team_form = overview.get("teamForm", [])

        if not team_form:
            return {
                "team_name": team_name,
                "matches": [],
                "record": {"wins": 0, "draws": 0, "losses": 0},
                "error": None,  # No error, just no form data available
            }

        # Convert FotMob form to our format
        matches = []
        for i, form_entry in enumerate(team_form[:limit]):
            # Parse date
            date_info = form_entry.get("date", {})
            utc_time = date_info.get("utcTime", "")
            if utc_time:
                try:
                    dt = datetime.fromisoformat(utc_time.replace("Z", "+00:00"))
                    match_date = dt.strftime("%Y-%m-%d")
                except (ValueError, TypeError):
                    match_date = "Unknown"
            else:
                match_date = "Unknown"

            # Get result
            result_string = form_entry.get("resultString", "")
            if result_string == "W":
                result = "W"
            elif result_string == "D":
                result = "D"
            elif result_string == "L":
                result = "L"
            else:
                result = "Unknown"

            # Try to get opponent from link (format: /matches/team1-vs-team2/...)
            link = form_entry.get("linkToMatch", "")
            opponent = "Unknown"
            home_away = "Unknown"

            # Extract team info from teamPageUrl if available
            team_page_url = form_entry.get("teamPageUrl", "")
            if team_page_url:
                # The opponent is the team in teamPageUrl
                # Format: /teams/7732/overview/girona
                parts = team_page_url.split("/")
                if len(parts) >= 5:
                    opponent = parts[-1].replace("-", " ").title()

            matches.append(
                {
                    "date": match_date,
                    "opponent": opponent,
                    "home_away": home_away,
                    "result": result,
                    "goals_for": None,  # FotMob form doesn't include scores
                    "goals_against": None,
                    "competition": team_info.get("league_name", "Unknown"),
                }
            )

        # Calculate record
        wins = sum(1 for m in matches if m["result"] == "W")
        draws = sum(1 for m in matches if m["result"] == "D")
        losses = sum(1 for m in matches if m["result"] == "L")

        return {
            "team_name": team_info.get("name", team_name),
            "matches": matches,
            "record": {"wins": wins, "draws": draws, "losses": losses},
            "error": None,
        }

    except Exception as e:
        return {
            "team_name": team_name,
            "matches": [],
            "record": {"wins": 0, "draws": 0, "losses": 0},
            "error": f"Unexpected error: {str(e)}",
        }
