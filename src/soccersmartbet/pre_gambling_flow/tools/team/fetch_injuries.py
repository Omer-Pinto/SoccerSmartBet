"""Fetch team's current injuries using FotMob squad data."""

from typing import Any, Dict, List

from ..fotmob_client import get_fotmob_client

# Mapping from FotMob injury id to human-readable type.
# IDs are empirically observed from live FotMob responses (as of 2026-04-06),
# not documented in any official FotMob spec. May need updating if IDs rotate.
# Unmapped ids fall back to "Injury".
_INJURY_TYPE_MAP: Dict[str, str] = {
    "30": "Muscle Injury",
    "42": "Knock / Fitness",
    "69": "Ligament / Knee",
    "76": "Long-Term Injury",
    "101": "Broken Bone",
}

# Squad group titles that are actual players (skip the coach group).
_PLAYER_GROUPS = {"keepers", "defenders", "midfielders", "attackers"}


def fetch_injuries(team_name: str) -> Dict[str, Any]:
    """Fetch team's current injury list from squad data.

    Reads ``squad.squad[].members[].injury`` — only players with a non-None
    ``injury`` value are included in the result.

    Args:
        team_name: Team name (e.g., "Barcelona", "Manchester City").

    Returns:
        Dictionary with keys:
            team_name (str): Resolved team name.
            injuries (list[dict]): Each entry has ``player_name``,
                ``position_group``, ``injury_type``, and ``expected_return``.
            total_injuries (int): Count of injured players.
            source (str): Always ``"squad"`` on success.
            error (str | None): Error message or ``None`` on success.
    """
    try:
        client = get_fotmob_client()

        team_info = client.find_team(team_name)
        if not team_info:
            return _error(team_name, f"Team '{team_name}' not found")

        team_data = client.get_team_data(team_info["id"])
        if not team_data:
            return _error(team_name, "Could not fetch team data")

        squad_groups: List[Dict[str, Any]] = (
            team_data.get("squad", {}).get("squad", [])
        )
        if not squad_groups:
            return _result(team_info.get("name", team_name), [], "squad_unavailable")

        injuries: List[Dict[str, Any]] = []
        for group in squad_groups:
            group_title: str = group.get("title", "").lower()
            if group_title not in _PLAYER_GROUPS:
                continue
            for member in group.get("members", []):
                injury = member.get("injury")
                if not injury:
                    continue
                injury_id = str(injury.get("id", ""))
                injuries.append(
                    {
                        "player_name": member.get("name", "Unknown"),
                        "position_group": group_title,
                        "injury_type": _INJURY_TYPE_MAP.get(injury_id, "Injury"),
                        "expected_return": injury.get("expectedReturn", "Unknown"),
                    }
                )

        return _result(team_info.get("name", team_name), injuries, "squad")

    except Exception as exc:
        return _error(team_name, str(exc))


def _result(team_name: str, injuries: List[Dict[str, Any]], source: str) -> Dict[str, Any]:
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
