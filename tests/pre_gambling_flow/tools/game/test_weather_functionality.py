"""Test fetch_weather functionality with real data."""

import sys
from pathlib import Path
from datetime import datetime, timedelta

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent / "src"))

from soccersmartbet.pre_gambling_flow.tools.game import fetch_weather


def test_fetch_weather():
    """Test weather retrieval for match."""
    tomorrow = (datetime.now() + timedelta(days=1)).replace(hour=15, minute=0)
    match_datetime = tomorrow.isoformat()
    
    result = fetch_weather("Manchester City", "Chelsea", match_datetime)
    
    assert "error" in result
    assert "temperature_celsius" in result
    assert "venue_city" in result
    
    if result["error"]:
        print(f"Error: {result['error']}")
    else:
        print(f"✅ Weather for {result['venue_city']}:")
        print(f"   Temperature: {result['temperature_celsius']}°C")
        print(f"   Precipitation: {result['precipitation_mm']}mm")
        print(f"   Conditions: {result['conditions']}")


if __name__ == "__main__":
    test_fetch_weather()
