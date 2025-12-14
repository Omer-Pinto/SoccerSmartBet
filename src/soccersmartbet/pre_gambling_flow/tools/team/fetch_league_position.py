"""
Fetch team's current league position using FotMob API.

Clean interface: Accepts team name, returns league standing.
NO API KEY REQUIRED - uses unofficial FotMob API.
Returns ALL teams in standings (not just top 5 like TheSportsDB free tier).
"""

from typing import Dict, Any

from ..fotmob_client import get_fotmob_client


def fetch_league_position(team_name: str) -> Dict[str, Any]:
    """
    Fetch team's current league position.

    Searches across all major European leagues to find the team.
    Returns full standings data including position, points, W/D/L.

    Args:
        team_name: Team name (e.g., "Manchester City", "Deportivo Alavés")

    Returns:
        {
            "team_name": "Deportivo Alaves",
            "league_name": "La Liga",
            "position": 11,
            "played": 15,
            "won": 5,
            "draw": 3,
            "lost": 7,
            "goals_for": 14,
            "goals_against": 18,
            "goal_difference": -4,
            "points": 18,
            "form": "LLWWL",  # Last 5 results
            "error": None
        }
    """
    try:
        client = get_fotmob_client()

        # Find team by name - this also gets standings data
        team_info = client.find_team(team_name)

        if not team_info:
            return {
                "team_name": team_name,
                "league_name": None,
                "position": None,
                "played": None,
                "won": None,
                "draw": None,
                "lost": None,
                "goals_for": None,
                "goals_against": None,
                "goal_difference": None,
                "points": None,
                "form": None,
                "error": f"Team '{team_name}' not found in any supported league",
            }

        # Get form string from team data
        form = None
        team_data = client.get_team_data(team_info["id"])
        if team_data:
            overview = team_data.get("overview", {})
            team_form = overview.get("teamForm", [])
            if team_form:
                # Build form string from last 5 matches
                form_letters = [f.get("resultString", "?") for f in team_form[:5]]
                form = "".join(form_letters)

        return {
            "team_name": team_info.get("name", team_name),
            "league_name": team_info.get("league_name"),
            "position": team_info.get("position"),
            "played": team_info.get("played"),
            "won": team_info.get("wins"),
            "draw": team_info.get("draws"),
            "lost": team_info.get("losses"),
            "goals_for": team_info.get("goals_for"),
            "goals_against": team_info.get("goals_against"),
            "goal_difference": team_info.get("goal_difference"),
            "points": team_info.get("points"),
            "form": form,
            "error": None,
        }

    except Exception as e:
        return {
            "team_name": team_name,
            "league_name": None,
            "position": None,
            "played": None,
            "won": None,
            "draw": None,
            "lost": None,
            "goals_for": None,
            "goals_against": None,
            "goal_difference": None,
            "points": None,
            "form": None,
            "error": f"Unexpected error: {str(e)}",
        }
