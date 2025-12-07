"""Test fetch_form functionality with real data."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent / "src"))

from soccersmartbet.pre_gambling_flow.tools.team import fetch_form


def test_fetch_form():
    """Test form retrieval for team."""
    result = fetch_form("Manchester City", limit=5)
    
    assert "error" in result
    assert "matches" in result
    assert "record" in result
    
    if result["error"]:
        print(f"Error: {result['error']}")
    else:
        print(f"✅ {result['team_name']} - Last 5 matches:")
        print(f"   Record: W{result['record']['wins']}-D{result['record']['draws']}-L{result['record']['losses']}")
        for match in result["matches"]:
            print(f"   {match['date']}: {match['result']} vs {match['opponent']} ({match['goals_for']}-{match['goals_against']})")


if __name__ == "__main__":
    test_fetch_form()
