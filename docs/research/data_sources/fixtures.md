# Fixtures APIs

**Status:** 🟢 **FREE API - RECOMMENDED**

---

## Primary: football-data.org

**Website:** https://www.football-data.org  
**Type:** RESTful API  
**Cost:** FREE (12 competitions)  
**Status:** 🟢

### Features
- ✅ 12 major competitions (Premier League, La Liga, Bundesliga, etc.)
- ✅ Fixtures, results, standings, teams
- ✅ 10 API calls per minute
- ✅ Well-documented, reliable
- ❌ Delayed scores on free tier (use for pre-match only)

### Rate Limits
- **Free Plan**: 10 requests/minute, 100 requests/day (non-authenticated)
- **Free Registered**: 10 requests/minute (authenticated)

### Registration
```bash
# Sign up at: https://www.football-data.org/client/register
# Get API key immediately - no credit card required
```

### Example API Call
```python
import requests

API_KEY = "your_api_key"
BASE_URL = "https://api.football-data.org/v4"

# Get today's fixtures
headers = {"X-Auth-Token": API_KEY}
response = requests.get(f"{BASE_URL}/matches", headers=headers)

# Example response structure:
{
  "matches": [
    {
      "id": 327105,
      "utcDate": "2025-11-20T19:45:00Z",
      "status": "SCHEDULED",
      "homeTeam": {"id": 65, "name": "Manchester City"},
      "awayTeam": {"id": 66, "name": "Manchester United"},
      "competition": {"id": 2021, "name": "Premier League"}
    }
  ]
}
```

### Coverage
- English Premier League
- Spanish La Liga
- German Bundesliga
- Italian Serie A
- French Ligue 1
- UEFA Champions League
- European Championship
- World Cup
- + 4 more

---

## Backup: API-Football (RapidAPI)

**Website:** https://www.api-football.com  
**Type:** RESTful API  
**Cost:** FREE (100 requests/day)  
**Status:** 🟡

### Features
- ✅ 1,200+ leagues and cups
- ✅ Live scores (15-second updates)
- ✅ Fixtures, standings, H2H, events
- ✅ Injuries, suspensions included
- ✅ Pre-match and live odds
- ✅ Player statistics

### Rate Limits
- **Free Plan**: 100 requests/day, 10 requests/minute
- **Pro Plan**: $19/month for 7,500 requests/day (🔴 DISABLED for MVP)

### Registration
```bash
# Sign up at: https://dashboard.api-football.com/register
# OR via RapidAPI: https://rapidapi.com/api-sports/api/api-football
```

### Example API Call
```python
import requests

API_KEY = "your_rapidapi_key"
BASE_URL = "https://v3.football.api-sports.io"

headers = {
    "x-rapidapi-host": "v3.football.api-sports.io",
    "x-rapidapi-key": API_KEY
}

# Get fixtures for today
params = {"date": "2025-11-20"}
response = requests.get(f"{BASE_URL}/fixtures", headers=headers, params=params)

# Example response:
{
  "response": [
    {
      "fixture": {
        "id": 1234567,
        "date": "2025-11-20T19:45:00+00:00",
        "venue": {"name": "Old Trafford", "city": "Manchester"}
      },
      "teams": {
        "home": {"id": 33, "name": "Manchester United"},
        "away": {"id": 34, "name": "Newcastle"}
      },
      "league": {"id": 39, "name": "Premier League"}
    }
  ]
}
```

---

## 🔴 DISABLED: TheSportsDB

**Website:** https://www.thesportsdb.com  
**Status:** 🔴 DISABLED  
**Reason:** Rate-limited, unreliable for production

**Note:** Free tier exists but not recommended for MVP due to inconsistent availability.

---

## Implementation Notes

### Caching Strategy
```python
# Cache today's fixtures for 6 hours
# Only re-fetch if:
# 1. Cache expired
# 2. User manually refreshes
# 3. New game added after initial fetch

import time

CACHE_TTL = 6 * 60 * 60  # 6 hours

def get_fixtures_cached(date_str):
    cache_key = f"fixtures_{date_str}"
    cached = redis.get(cache_key)
    
    if cached:
        return json.loads(cached)
    
    # Fetch fresh data
    fixtures = fetch_fixtures_from_api(date_str)
    
    # Cache with TTL
    redis.setex(cache_key, CACHE_TTL, json.dumps(fixtures))
    
    return fixtures
```

### Error Handling
```python
def fetch_fixtures_from_api(date_str):
    try:
        # Try primary source
        return fetch_from_football_data(date_str)
    except RateLimitError:
        # Fall back to API-Football
        return fetch_from_api_football(date_str)
    except Exception as e:
        logging.error(f"Fixtures fetch failed: {e}")
        raise
```
