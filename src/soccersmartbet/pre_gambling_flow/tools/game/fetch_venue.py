"""
Fetch venue information for a match between two teams using FotMob API.

Clean interface: Accepts both team names, returns home team's venue.
NO API KEY REQUIRED - uses unofficial FotMob API.
"""

from typing import Dict, Any

from ..fotmob_client import get_fotmob_client


def fetch_venue(home_team_name: str, away_team_name: str) -> Dict[str, Any]:
    """
    Fetch venue information for match between two teams.

    Returns the home team's venue details. Searches across all major European leagues.

    Args:
        home_team_name: Home team name (e.g., "Manchester City")
        away_team_name: Away team name (e.g., "Tottenham")

    Returns:
        {
            "home_team": "Manchester City",
            "away_team": "Tottenham",
            "venue_name": "Etihad Stadium",
            "venue_city": "Manchester",
            "venue_capacity": 55097,
            "venue_address": None,  # FotMob doesn't provide address
            "venue_surface": None,  # FotMob doesn't provide surface
            "error": None
        }
    """
    try:
        client = get_fotmob_client()

        # Find home team by name
        team_info = client.find_team(home_team_name)

        if not team_info:
            return {
                "home_team": home_team_name,
                "away_team": away_team_name,
                "venue_name": None,
                "venue_city": None,
                "venue_capacity": None,
                "venue_address": None,
                "venue_surface": None,
                "error": f"Team '{home_team_name}' not found in any major league",
            }

        # Get team details with venue
        team_data = client.get_team_data(team_info["id"])

        if not team_data:
            return {
                "home_team": home_team_name,
                "away_team": away_team_name,
                "venue_name": None,
                "venue_city": None,
                "venue_capacity": None,
                "venue_address": None,
                "venue_surface": None,
                "error": f"Could not fetch team data for '{home_team_name}'",
            }

        overview = team_data.get("overview", {})
        venue = overview.get("venue", {})

        if not venue:
            return {
                "home_team": team_info.get("name", home_team_name),
                "away_team": away_team_name,
                "venue_name": None,
                "venue_city": None,
                "venue_capacity": None,
                "venue_address": None,
                "venue_surface": None,
                "error": "Venue data not available",
            }

        # FotMob venue data structure
        widget = venue.get("widget", {})

        return {
            "home_team": team_info.get("name", home_team_name),
            "away_team": away_team_name,
            "venue_name": widget.get("name"),
            "venue_city": widget.get("city"),
            "venue_capacity": widget.get("capacity"),
            "venue_address": None,  # FotMob doesn't provide address
            "venue_surface": None,  # FotMob doesn't provide surface type
            "error": None,
        }

    except Exception as e:
        return {
            "home_team": home_team_name,
            "away_team": away_team_name,
            "venue_name": None,
            "venue_city": None,
            "venue_capacity": None,
            "venue_address": None,
            "venue_surface": None,
            "error": f"Unexpected error: {str(e)}",
        }
