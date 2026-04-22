"""
Fetch all scheduled fixtures for a given date.

Clean interface: Accepts an optional date string, returns all matches
across all subscribed competitions from football-data.org.
"""

import os
from datetime import date as date_type, timedelta
from typing import Any, Dict, List, Optional

import requests
from dotenv import load_dotenv

from soccersmartbet.utils.timezone import today_isr

load_dotenv()

# API Configuration
FOOTBALL_DATA_API_KEY = os.getenv("FOOTBALL_DATA_API_KEY")
BASE_URL = "https://api.football-data.org/v4"
# 30s because football-data.org free tier is notably slow; typical response
# time is 12-15s, so 10s (used elsewhere) causes spurious timeouts here.
TIMEOUT = 30


def fetch_daily_fixtures(date: Optional[str] = None) -> Dict[str, Any]:
    """Fetch all fixtures for a given date.

    Queries the football-data.org /v4/matches endpoint for all competitions
    the API key is subscribed to. Returns every match scheduled on the
    requested date, regardless of competition.

    Args:
        date: Date in YYYY-MM-DD format. Defaults to today (ISR timezone).

    Returns:
        On success::

            {
                "date": "2026-04-08",
                "fixtures": [
                    {
                        "match_id": 123456,
                        "home_team": "Barcelona",
                        "away_team": "Atletico Madrid",
                        "competition": "Champions League",
                        "kickoff_time": "2026-04-08T19:00:00Z",
                        "status": "SCHEDULED",
                        "home_team_id": 81,
                        "away_team_id": 78,
                    },
                    ...
                ],
                "total": 12,
                "error": None,
            }

        On error, ``fixtures`` is ``[]``, ``total`` is ``0``, and
        ``error`` contains a description string.
    """
    resolved_date: str = date if date is not None else str(today_isr())

    error_base: Dict[str, Any] = {
        "date": resolved_date,
        "fixtures": [],
        "total": 0,
    }

    if not FOOTBALL_DATA_API_KEY:
        return {**error_base, "error": "FOOTBALL_DATA_API_KEY not found in environment"}

    headers = {"X-Auth-Token": FOOTBALL_DATA_API_KEY}

    try:
        response = requests.get(
            f"{BASE_URL}/matches",
            headers=headers,
            params={
                "dateFrom": resolved_date,
                "dateTo": str(date_type.fromisoformat(resolved_date) + timedelta(days=1)),
            },
            timeout=TIMEOUT,
        )

        if response.status_code != 200:
            return {
                **error_base,
                "error": f"API error: {response.status_code} - {response.text[:200]}",
            }

        raw_matches: List[Dict[str, Any]] = response.json().get("matches", [])

        # Filter to only matches on the requested date (API returns date+1 too)
        fixtures: List[Dict[str, Any]] = [
            {
                "match_id": match.get("id"),
                "home_team": match.get("homeTeam", {}).get("name", "Unknown"),
                "away_team": match.get("awayTeam", {}).get("name", "Unknown"),
                "competition": match.get("competition", {}).get("name", "Unknown"),
                "kickoff_time": match.get("utcDate"),
                "status": match.get("status"),
                "home_team_id": match.get("homeTeam", {}).get("id"),
                "away_team_id": match.get("awayTeam", {}).get("id"),
            }
            for match in raw_matches
            if (match.get("utcDate") or "").startswith(resolved_date)
        ]

        return {
            "date": resolved_date,
            "fixtures": fixtures,
            "total": len(fixtures),
            "error": None,
        }

    except requests.Timeout:
        return {**error_base, "error": f"Request timeout after {TIMEOUT}s"}
    except Exception as exc:
        return {**error_base, "error": f"Unexpected error: {str(exc)}"}
