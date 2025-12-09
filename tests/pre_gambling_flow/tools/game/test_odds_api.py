"""Test The Odds API availability for betting odds."""

import os
import requests
from dotenv import load_dotenv

load_dotenv()


def test_odds_api_available():
    """Test that The Odds API endpoint is accessible."""
    api_key = os.getenv("ODDS_API_KEY")
    
    if not api_key:
        print("❌ ODDS_API_KEY not found")
        return False
    
    # Test getting EPL odds
    response = requests.get(
        "https://api.the-odds-api.com/v4/sports/soccer_epl/odds/",
        params={
            "apiKey": api_key,
            "regions": "eu",
            "markets": "h2h",
            "oddsFormat": "decimal"
        },
        timeout=10
    )
    
    if response.status_code != 200:
        print(f"❌ API error: {response.status_code}")
        return False
    
    matches = response.json()
    
    # Check remaining quota
    remaining = response.headers.get("x-requests-remaining", "unknown")
    
    print(f"✅ API accessible - {len(matches)} matches with odds")
    print(f"📊 Remaining credits: {remaining}")
    return True


if __name__ == "__main__":
    test_odds_api_available()
