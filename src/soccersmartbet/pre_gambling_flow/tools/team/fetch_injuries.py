"""
Fetch team's current injuries using FotMob API.

Clean interface: Accepts team name, returns injured/unavailable players.
NO API KEY REQUIRED - uses unofficial FotMob API.
Gets injury data from match lineup (unavailable players).
"""

from typing import Dict, Any, Optional

from ..fotmob_client import get_fotmob_client


def fetch_injuries(team_name: str, opponent_name: Optional[str] = None) -> Dict[str, Any]:
    """
    Fetch team's current injury/unavailability list.

    Gets unavailable players from the team's upcoming match lineup.
    If opponent_name is provided, searches for that specific match.
    Otherwise uses the team's next scheduled match.

    Args:
        team_name: Team name (e.g., "Manchester City", "Deportivo Alavés")
        opponent_name: Optional opponent name to find specific match

    Returns:
        {
            "team_name": "Manchester City",
            "injuries": [
                {
                    "player_name": "Mateo Kovacic",
                    "player_type": "Midfielder",
                    "injury_type": "injury",
                    "expected_return": "Doubtful"
                },
                ...
            ],
            "total_injuries": 2,
            "source": "upcoming_match" | "team_not_found" | "no_upcoming_match",
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
                "injuries": [],
                "total_injuries": 0,
                "source": "team_not_found",
                "error": f"Team '{team_name}' not found in any major league",
            }

        # Get team data to find next match
        team_data = client.get_team_data(team_info["id"])

        if not team_data:
            return {
                "team_name": team_name,
                "injuries": [],
                "total_injuries": 0,
                "source": "team_not_found",
                "error": f"Could not fetch team data for '{team_name}'",
            }

        overview = team_data.get("overview", {})
        next_match = overview.get("nextMatch", {})

        if not next_match:
            return {
                "team_name": team_info.get("name", team_name),
                "injuries": [],
                "total_injuries": 0,
                "source": "no_upcoming_match",
                "error": None,  # Not an error, just no upcoming match
            }

        match_id = next_match.get("id")

        if not match_id:
            return {
                "team_name": team_info.get("name", team_name),
                "injuries": [],
                "total_injuries": 0,
                "source": "no_match_id",
                "error": None,
            }

        # Get match details with lineup and unavailable players
        match_data = client.get_match_data(match_id)

        if not match_data:
            return {
                "team_name": team_info.get("name", team_name),
                "injuries": [],
                "total_injuries": 0,
                "source": "match_data_unavailable",
                "error": f"Could not fetch match data for match {match_id}",
            }

        content = match_data.get("content", {})
        lineup = content.get("lineup", {})

        if not lineup:
            return {
                "team_name": team_info.get("name", team_name),
                "injuries": [],
                "total_injuries": 0,
                "source": "no_lineup_data",
                "error": None,  # Lineup not yet available
            }

        # Determine if team is home or away
        home_team = lineup.get("homeTeam", {})
        away_team = lineup.get("awayTeam", {})

        team_lineup = None
        home_name = home_team.get("name", "")
        away_name = away_team.get("name", "")

        # Match team name
        team_normalized = team_info.get("name", "").lower()
        if team_normalized in home_name.lower() or home_name.lower() in team_normalized:
            team_lineup = home_team
        elif team_normalized in away_name.lower() or away_name.lower() in team_normalized:
            team_lineup = away_team
        else:
            # Try with original team_name
            if team_name.lower() in home_name.lower() or home_name.lower() in team_name.lower():
                team_lineup = home_team
            elif team_name.lower() in away_name.lower() or away_name.lower() in team_name.lower():
                team_lineup = away_team

        if not team_lineup:
            return {
                "team_name": team_info.get("name", team_name),
                "injuries": [],
                "total_injuries": 0,
                "source": "team_not_in_lineup",
                "error": None,
            }

        # Extract unavailable players
        unavailable = team_lineup.get("unavailable", [])

        injuries = []
        for player in unavailable:
            unavailability = player.get("unavailability", {})

            injuries.append(
                {
                    "player_name": player.get("name", "Unknown"),
                    "player_type": _get_position_name(player.get("positionId")),
                    "injury_type": unavailability.get("type", "unknown"),
                    "expected_return": unavailability.get("expectedReturn", "Unknown"),
                }
            )

        return {
            "team_name": team_info.get("name", team_name),
            "injuries": injuries,
            "total_injuries": len(injuries),
            "source": "upcoming_match",
            "error": None,
        }

    except Exception as e:
        return {
            "team_name": team_name,
            "injuries": [],
            "total_injuries": 0,
            "source": "error",
            "error": f"Unexpected error: {str(e)}",
        }


def _get_position_name(position_id: Optional[int]) -> str:
    """Convert FotMob position ID to position name."""
    if position_id is None:
        return "Unknown"

    positions = {
        1000: "Goalkeeper",
        2000: "Defender",
        3000: "Midfielder",
        4000: "Forward",
    }

    # FotMob uses ranges (e.g., 1001-1999 for goalkeepers variations)
    base_id = (position_id // 1000) * 1000
    return positions.get(base_id, "Unknown")
