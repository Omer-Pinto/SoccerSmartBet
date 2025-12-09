"""Test apifootball.com API availability for form data."""

import os
import requests
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()


def test_form_api_available():
    """Test that apifootball.com events endpoint is accessible."""
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
    
    print(f"✅ API accessible - {len(events)} recent events")
    return True


if __name__ == "__main__":
    test_form_api_available()
