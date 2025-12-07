"""Test fetch_key_players_form functionality with real data."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent / "src"))

from soccersmartbet.pre_gambling_flow.tools.team import fetch_key_players_form


def test_fetch_key_players():
    """Test key players retrieval for team."""
    result = fetch_key_players_form("Manchester City", top_n=5)
    
    assert "error" in result
    assert "top_players" in result
    assert "total_players" in result
    
    if result["error"]:
        print(f"Error: {result['error']}")
    else:
        print(f"✅ {result['team_name']} - Top {result['total_players']} players:")
        for player in result["top_players"]:
            print(f"   {player['player_name']}: {player['goals']}G + {player['assists']}A")


if __name__ == "__main__":
    test_fetch_key_players()
