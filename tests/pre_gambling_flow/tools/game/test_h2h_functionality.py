"""Test fetch_h2h functionality with real data."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent / "src"))

from soccersmartbet.pre_gambling_flow.tools.game import fetch_h2h


def test_fetch_h2h():
    """Test H2H retrieval for two teams."""
    result = fetch_h2h("Chelsea", "Everton", limit=5)
    
    assert "error" in result
    assert "h2h_matches" in result
    assert "total_h2h" in result
    
    if result["error"]:
        print(f"Error: {result['error']}")
    else:
        print(f"✅ Found {result['total_h2h']} H2H matches")
        print(f"Upcoming match: {result.get('upcoming_match_date')}")
        for match in result["h2h_matches"][:3]:
            print(f"  {match['date']}: {match['home_team']} {match['score_home']}-{match['score_away']} {match['away_team']}")


if __name__ == "__main__":
    test_fetch_h2h()
