"""Fetch team's current injuries using FotMob API."""

from typing import Dict, Any
from ..fotmob_client import get_fotmob_client


def fetch_injuries(team_name: str) -> Dict[str, Any]:
    """Fetch team's current injury/unavailability list from upcoming match."""
    try:
        client = get_fotmob_client()
        team_info = client.find_team(team_name)
        if not team_info:
            return _error(team_name, f"Team '{team_name}' not found")

        team_data = client.get_team_data(team_info["id"])
        if not team_data:
            return _error(team_name, "Could not fetch team data")

        next_match = team_data.get("overview", {}).get("nextMatch", {})
        match_id = next_match.get("id")
        if not match_id:
            return _result(team_info.get("name", team_name), [], "no_upcoming_match")

        match_data = client.get_match_data(match_id)
        if not match_data:
            return _result(team_info.get("name", team_name), [], "match_data_unavailable")

        lineup = match_data.get("content", {}).get("lineup", {})
        if not lineup:
            return _result(team_info.get("name", team_name), [], "lineup_not_available")

        # Find our team in lineup (home or away)
        team_id = team_info["id"]
        home_team = lineup.get("homeTeam", {})
        away_team = lineup.get("awayTeam", {})

        # Check team IDs first, fallback to name matching
        if home_team.get("id") == team_id:
            unavailable = home_team.get("unavailable", [])
        elif away_team.get("id") == team_id:
            unavailable = away_team.get("unavailable", [])
        else:
            # Fallback to name matching
            team_normalized = team_info.get("name", "").lower()
            if team_normalized in home_team.get("name", "").lower():
                unavailable = home_team.get("unavailable", [])
            elif team_normalized in away_team.get("name", "").lower():
                unavailable = away_team.get("unavailable", [])
            else:
                return _result(team_info.get("name", team_name), [], "team_not_in_lineup")

        injuries = [
            {
                "player_name": p.get("name", "Unknown"),
                "injury_type": p.get("unavailability", {}).get("type", "unknown"),
                "expected_return": p.get("unavailability", {}).get("expectedReturn", "Unknown"),
            }
            for p in unavailable
        ]

        return _result(team_info.get("name", team_name), injuries, "upcoming_match")

    except Exception as e:
        return _error(team_name, str(e))


def _result(team_name: str, injuries: list, source: str) -> Dict[str, Any]:
    return {
        "team_name": team_name,
        "injuries": injuries,
        "total_injuries": len(injuries),
        "source": source,
        "error": None,
    }


def _error(team_name: str, msg: str) -> Dict[str, Any]:
    return {
        "team_name": team_name,
        "injuries": [],
        "total_injuries": 0,
        "source": "error",
        "error": msg,
    }
