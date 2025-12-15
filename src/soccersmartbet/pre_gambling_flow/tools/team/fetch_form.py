"""Fetch team's recent match form using FotMob API."""

from typing import Dict, Any
from datetime import datetime
from ..fotmob_client import get_fotmob_client


def fetch_form(team_name: str, limit: int = 5) -> Dict[str, Any]:
    """Fetch team's recent match results with scores."""
    try:
        client = get_fotmob_client()
        team_info = client.find_team(team_name)
        if not team_info:
            return _error(team_name, f"Team '{team_name}' not found")

        team_data = client.get_team_data(team_info["id"])
        if not team_data:
            return _error(team_name, f"Could not fetch team data")

        team_form = team_data.get("overview", {}).get("teamForm", [])
        if not team_form:
            return _result(team_info.get("name", team_name), [])

        team_id = team_info["id"]
        matches = []
        for entry in team_form[:limit]:
            tooltip = entry.get("tooltipText", {})
            home_id = tooltip.get("homeTeamId")

            # Determine home/away and extract scores
            is_home = (home_id == team_id)
            if is_home:
                opponent = tooltip.get("awayTeam", "Unknown")
                goals_for = tooltip.get("homeScore")
                goals_against = tooltip.get("awayScore")
            else:
                opponent = tooltip.get("homeTeam", "Unknown")
                goals_for = tooltip.get("awayScore")
                goals_against = tooltip.get("homeScore")

            # Parse date
            utc_time = entry.get("date", {}).get("utcTime", "")
            try:
                match_date = datetime.fromisoformat(utc_time.replace("Z", "+00:00")).strftime("%Y-%m-%d")
            except (ValueError, TypeError):
                match_date = "Unknown"

            matches.append({
                "date": match_date,
                "opponent": opponent,
                "home_away": "HOME" if is_home else "AWAY",
                "result": entry.get("resultString", "?"),
                "goals_for": goals_for,
                "goals_against": goals_against,
            })

        return _result(team_info.get("name", team_name), matches)

    except Exception as e:
        return _error(team_name, str(e))


def _result(team_name: str, matches: list) -> Dict[str, Any]:
    wins = sum(1 for m in matches if m["result"] == "W")
    draws = sum(1 for m in matches if m["result"] == "D")
    losses = sum(1 for m in matches if m["result"] == "L")
    return {
        "team_name": team_name,
        "matches": matches,
        "record": {"wins": wins, "draws": draws, "losses": losses},
        "error": None,
    }


def _error(team_name: str, msg: str) -> Dict[str, Any]:
    return {
        "team_name": team_name,
        "matches": [],
        "record": {"wins": 0, "draws": 0, "losses": 0},
        "error": msg,
    }
