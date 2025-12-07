"""Test fetch_injuries functionality with real data."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent / "src"))

from soccersmartbet.pre_gambling_flow.tools.team import fetch_injuries


def test_fetch_injuries():
    """Test injuries retrieval for team."""
    result = fetch_injuries("Manchester City")
    
    assert "error" in result
    assert "injuries" in result
    assert "total_injuries" in result
    
    if result["error"]:
        print(f"Error: {result['error']}")
    else:
        print(f"✅ {result['team_name']} - {result['total_injuries']} injuries")
        for injury in result["injuries"]:
            print(f"   {injury['player_name']} ({injury['player_type']})")


if __name__ == "__main__":
    test_fetch_injuries()
