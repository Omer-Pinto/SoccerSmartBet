"""Test fetch_venue functionality with real data."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent / "src"))

from soccersmartbet.pre_gambling_flow.tools.game import fetch_venue


def test_fetch_venue():
    """Test venue retrieval for match."""
    result = fetch_venue("Manchester City", "Tottenham")
    
    assert "error" in result
    assert "venue_name" in result
    assert "venue_city" in result
    
    if result["error"]:
        print(f"Error: {result['error']}")
    else:
        print(f"✅ Venue: {result['venue_name']}")
        print(f"   City: {result['venue_city']}")
        print(f"   Capacity: {result['venue_capacity']}")


if __name__ == "__main__":
    test_fetch_venue()
