"""Test apifootball.com API availability for recovery time calculation."""

import os
import requests
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()


def test_recovery_api_available():
    """Test that apifootball.com provides recent match data for recovery calculation."""
    api_key = os.getenv("APIFOOTBALL_API_KEY")
    
    if not api_key:
        print("❌ APIFOOTBALL_API_KEY not found")
        return False
    
    to_date = datetime.now().strftime("%Y-%m-%d")
    from_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
    
    response = requests.get(
        "https://apiv3.apifootball.com/",
        params={
            "action": "get_events",
            "from": from_date,
            "to": to_date,
            "team_id": 80,
            "APIkey": api_key
        },
        timeout=15
    )
    
    if response.status_code != 200:
        print(f"❌ API error: {response.status_code}")
        return False
    
    events = response.json()
    finished = [e for e in events if e.get("match_status") == "Finished"]
    
    print(f"✅ API accessible - {len(finished)} finished matches for recovery calc")
    return True


if __name__ == "__main__":
    test_recovery_api_available()
