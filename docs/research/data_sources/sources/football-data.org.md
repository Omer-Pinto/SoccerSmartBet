# football-data.org

**Website:** https://www.football-data.org  
**Type:** REST API  
**Cost:** FREE (12 competitions)  
**Status:** ✅ Primary source for [Fixtures](../verticals/fixtures.md)

---

## Overview

football-data.org provides free access to football match data for 12 major competitions. It's the **primary source for daily fixtures** in SoccerSmartBet due to reliability and documentation quality.

---

## Features

- ✅ 12 major competitions (see coverage below)
- ✅ Fixtures, results, standings, teams
- ✅ 10 API calls per minute
- ✅ Well-documented, reliable
- ✅ JSON format
- ❌ Delayed scores on free tier (use for pre-match only, not live)

---

## Rate Limits

- **Free Plan (no auth)**: 10 requests/minute, 100 requests/day
- **Free Registered**: 10 requests/minute (authenticated with API key)
- **Paid Plan**: Higher limits (not needed for this project)

---

## Registration

1. Visit: https://www.football-data.org/client/register
2. Provide email address
3. Get API key immediately (no credit card required)
4. Add to `.env` file:
   ```bash
   FOOTBALL_DATA_API_KEY=your_api_key_here
   ```

---

## API Endpoints

### Get Today's Matches
```http
GET https://api.football-data.org/v4/matches
```

**Headers:**
```http
X-Auth-Token: YOUR_API_KEY
```

**Response:**
```json
{
  "filters": {},
  "resultSet": {
    "count": 10,
    "competitions": "PL,CL",
    "first": "2025-11-20",
    "last": "2025-11-20"
  },
  "matches": [
    {
      "id": 327105,
      "utcDate": "2025-11-20T19:45:00Z",
      "status": "SCHEDULED",
      "matchday": 12,
      "stage": "REGULAR_SEASON",
      "homeTeam": {
        "id": 65,
        "name": "Manchester City",
        "shortName": "Man City",
        "tla": "MCI",
        "crest": "https://crests.football-data.org/65.png"
      },
      "awayTeam": {
        "id": 66,
        "name": "Manchester United",
        "shortName": "Man Utd",
        "tla": "MUN",
        "crest": "https://crests.football-data.org/66.png"
      },
      "score": {
        "fullTime": {"home": null, "away": null}
      },
      "competition": {
        "id": 2021,
        "name": "Premier League",
        "code": "PL",
        "type": "LEAGUE",
        "emblem": "https://crests.football-data.org/PL.png"
      },
      "season": {
        "id": 2024,
        "startDate": "2025-08-16",
        "endDate": "2026-05-23"
      }
    }
  ]
}
```

---

## Python Code Example

```python
import requests
from typing import List, Dict
from datetime import date

class FootballDataFetcher:
    """Fetches fixtures from football-data.org API"""
    
    BASE_URL = "https://api.football-data.org/v4"
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.headers = {"X-Auth-Token": api_key}
    
    def get_todays_fixtures(self) -> List[Dict]:
        """
        Fetch today's football fixtures
        
        Returns:
            List of match dictionaries with id, teams, time, competition
        """
        response = requests.get(
            f"{self.BASE_URL}/matches",
            headers=self.headers
        )
        response.raise_for_status()
        
        data = response.json()
        return data.get("matches", [])
    
    def get_fixtures_by_date(self, date_str: str) -> List[Dict]:
        """
        Fetch fixtures for a specific date
        
        Args:
            date_str: Date in YYYY-MM-DD format
        
        Returns:
            List of matches
        """
        params = {"date": date_str}
        response = requests.get(
            f"{self.BASE_URL}/matches",
            headers=self.headers,
            params=params
        )
        response.raise_for_status()
        
        return response.json().get("matches", [])
    
    def get_fixtures_by_competition(self, competition_code: str) -> List[Dict]:
        """
        Fetch fixtures for a specific competition
        
        Args:
            competition_code: e.g., 'PL' for Premier League, 'CL' for Champions League
        
        Returns:
            List of matches
        """
        response = requests.get(
            f"{self.BASE_URL}/competitions/{competition_code}/matches",
            headers=self.headers
        )
        response.raise_for_status()
        
        return response.json().get("matches", [])


# Example usage
if __name__ == "__main__":
    import os
    
    api_key = os.getenv("FOOTBALL_DATA_API_KEY")
    fetcher = FootballDataFetcher(api_key)
    
    # Get today's fixtures
    fixtures = fetcher.get_todays_fixtures()
    
    for match in fixtures:
        print(f"{match['homeTeam']['name']} vs {match['awayTeam']['name']}")
        print(f"  Competition: {match['competition']['name']}")
        print(f"  Kickoff: {match['utcDate']}")
        print()
```

---

## Coverage (12 Free Competitions)

1. **English Premier League** (PL)
2. **Spanish La Liga** (PD)
3. **German Bundesliga** (BL1)
4. **Italian Serie A** (SA)
5. **French Ligue 1** (FL1)
6. **Portuguese Primeira Liga** (PPL)
7. **Dutch Eredivisie** (DED)
8. **UEFA Champions League** (CL)
9. **UEFA Europa League** (EL)
10. **European Championship** (EC)
11. **FIFA World Cup** (WC)
12. **Brazilian Série A** (BSA)

**Note:** Free tier does NOT include:
- Lower-tier divisions (Championship, Serie B, etc.)
- International friendlies
- Domestic cups (FA Cup, Copa del Rey)

---

## Implementation Notes

### For Pre-Gambling Flow

1. **Trigger:** Fetch once daily at configured time (e.g., 14:00 UTC)
2. **Caching:** Store fixtures in DB with `fetched_at` timestamp
3. **Filtering:** Pass to Smart Game Picker for interesting game selection
4. **Quota Management:** 1 request for all today's fixtures (efficient)
5. **Error Handling:** If quota exhausted, fallback to API-Football

### Error Responses

**429 Too Many Requests:**
```json
{
  "message": "You exceeded your API request limit",
  "errorCode": 429
}
```
**Action:** Wait 60 seconds or fallback to API-Football

**401 Unauthorized:**
```json
{
  "message": "Your API token is invalid",
  "errorCode": 401
}
```
**Action:** Check API key in `.env` file

---

## See Also

- [Fixtures Vertical](../verticals/fixtures.md) - Why this source was chosen
- [API-Football](./api-football.md) - Backup source for fixtures
- [Official API Docs](https://www.football-data.org/documentation/quickstart)
