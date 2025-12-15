"""
Calculate days since team's last match (recovery time) using FotMob API.

Clean interface: Accepts team name and upcoming match date.
NO API KEY REQUIRED - uses unofficial FotMob API.
"""

from datetime import datetime
from typing import Dict, Any

from ..fotmob_client import get_fotmob_client


def calculate_recovery_time(team_name: str, upcoming_match_date: str) -> Dict[str, Any]:
    """
    Calculate days between team's last match and upcoming match.

    Uses FotMob's team overview.lastMatch data for the most recent match.

    Args:
        team_name: Team name (e.g., "Manchester City", "Deportivo Alavés")
        upcoming_match_date: Date of upcoming match (YYYY-MM-DD)

    Returns:
        {
            "team_name": "Manchester City",
            "last_match_date": "2025-12-02",
            "upcoming_match_date": "2025-12-06",
            "recovery_days": 4,
            "recovery_status": "Short" | "Normal" | "Extended",
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
                "last_match_date": None,
                "upcoming_match_date": upcoming_match_date,
                "recovery_days": None,
                "recovery_status": None,
                "error": f"Team '{team_name}' not found in any major league",
            }

        # Get team data with lastMatch
        team_data = client.get_team_data(team_info["id"])

        if not team_data:
            return {
                "team_name": team_name,
                "last_match_date": None,
                "upcoming_match_date": upcoming_match_date,
                "recovery_days": None,
                "recovery_status": None,
                "error": f"Could not fetch team data for '{team_name}'",
            }

        overview = team_data.get("overview", {})
        last_match = overview.get("lastMatch", {})

        if not last_match:
            return {
                "team_name": team_info.get("name", team_name),
                "last_match_date": None,
                "upcoming_match_date": upcoming_match_date,
                "recovery_days": None,
                "recovery_status": None,
                "error": "No recent match data found",
            }

        # Get last match date
        status = last_match.get("status", {})
        utc_time = status.get("utcTime", "")

        if not utc_time:
            return {
                "team_name": team_info.get("name", team_name),
                "last_match_date": None,
                "upcoming_match_date": upcoming_match_date,
                "recovery_days": None,
                "recovery_status": None,
                "error": "Last match date not available",
            }

        # Parse dates
        try:
            last_dt = datetime.fromisoformat(utc_time.replace("Z", "+00:00"))
            last_match_date = last_dt.strftime("%Y-%m-%d")
        except (ValueError, TypeError):
            return {
                "team_name": team_info.get("name", team_name),
                "last_match_date": None,
                "upcoming_match_date": upcoming_match_date,
                "recovery_days": None,
                "recovery_status": None,
                "error": f"Could not parse last match date: {utc_time}",
            }

        try:
            # Handle various date formats
            upcoming_clean = upcoming_match_date.split("T")[0]  # Remove time if present
            upcoming_dt = datetime.strptime(upcoming_clean, "%Y-%m-%d")
        except ValueError:
            return {
                "team_name": team_info.get("name", team_name),
                "last_match_date": last_match_date,
                "upcoming_match_date": upcoming_match_date,
                "recovery_days": None,
                "recovery_status": None,
                "error": f"Invalid upcoming match date format: {upcoming_match_date}",
            }

        # Calculate recovery days
        # Use date only (ignore time)
        last_date_only = datetime(last_dt.year, last_dt.month, last_dt.day)
        recovery_days = (upcoming_dt - last_date_only).days

        # Classify recovery status
        if recovery_days < 3:
            recovery_status = "Short"
        elif recovery_days <= 7:
            recovery_status = "Normal"
        else:
            recovery_status = "Extended"

        return {
            "team_name": team_info.get("name", team_name),
            "last_match_date": last_match_date,
            "upcoming_match_date": upcoming_clean,
            "recovery_days": recovery_days,
            "recovery_status": recovery_status,
            "error": None,
        }

    except Exception as e:
        return {
            "team_name": team_name,
            "last_match_date": None,
            "upcoming_match_date": upcoming_match_date,
            "recovery_days": None,
            "recovery_status": None,
            "error": f"Unexpected error: {str(e)}",
        }
