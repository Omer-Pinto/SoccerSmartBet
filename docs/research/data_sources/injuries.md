# Injury & Suspension Data

**Status:** 🟡 **FREE WITH LIMITS**

---

## Primary: API-Football Sidelined Endpoint

**Website:** https://www.api-football.com  
**Type:** RESTful API  
**Cost:** FREE (100 requests/day)  
**Status:** 🟡

### Features
- ✅ Included in free tier
- ✅ Injury type and severity
- ✅ Expected return dates
- ✅ Suspension tracking (red cards, yellow accumulation)
- ✅ Player identification (ID, name)
- ⚠️ 100 requests/day limit

### Example API Call
```python
import requests

API_KEY = "your_rapidapi_key"
BASE_URL = "https://v3.football.api-sports.io"

headers = {
    "x-rapidapi-host": "v3.football.api-sports.io",
    "x-rapidapi-key": API_KEY
}

# Get injuries and suspensions for a team
params = {"team": 33}  # Manchester United
response = requests.get(
    f"{BASE_URL}/sidelined",
    headers=headers,
    params=params
)

# Example response:
{
  "response": [
    {
      "type": "Knee Injury",
      "start": "2025-10-15",
      "end": "2025-12-01",
      "player": {
        "id": 276,
        "name": "Bruno Fernandes"
      }
    },
    {
      "type": "Red Card",
      "start": "2025-11-10",
      "end": "2025-11-24",
      "player": {
        "id": 1456,
        "name": "Casemiro"
      }
    },
    {
      "type": "Yellow Cards",
      "start": "2025-11-18",
      "end": "2025-11-25",
      "player": {
        "id": 892,
        "name": "Marcus Rashford"
      }
    }
  ]
}
```

### Data Includes
- **Injury Types**: Knee, ankle, hamstring, muscle, concussion, etc.
- **Suspension Types**: Red card, yellow card accumulation
- **Dates**: Start date, expected return date
- **Player Info**: ID, name

---

## Data Structure (Normalized)

```python
from pydantic import BaseModel
from typing import Literal, Optional
from datetime import date

class PlayerSidelined(BaseModel):
    player_id: int
    player_name: str
    team_id: int
    type: Literal["injury", "suspension"]
    reason: str  # e.g., "Knee Injury", "Red Card"
    start_date: date
    expected_return: Optional[date]
    severity: Literal["minor", "moderate", "severe", "unknown"]
    
    @property
    def is_active(self) -> bool:
        """Check if player is currently sidelined."""
        today = date.today()
        if self.expected_return:
            return self.start_date <= today <= self.expected_return
        return today >= self.start_date

# Example usage:
injury = PlayerSidelined(
    player_id=276,
    player_name="Bruno Fernandes",
    team_id=33,
    type="injury",
    reason="Knee Injury",
    start_date=date(2025, 10, 15),
    expected_return=date(2025, 12, 1),
    severity="moderate"
)

suspension = PlayerSidelined(
    player_id=1456,
    player_name="Casemiro",
    team_id=33,
    type="suspension",
    reason="Red Card",
    start_date=date(2025, 11, 10),
    expected_return=date(2025, 11, 24),
    severity="unknown"
)
```

---

## Rate Limit Strategy

### Problem
- 100 requests/day limit
- Need injury data for **2 teams per game**
- If 3 games/day → 6 team requests

### Solution: Batch & Cache
```python
from datetime import datetime, timedelta
import redis

CACHE_TTL = 24 * 60 * 60  # 24 hours

def get_team_injuries(team_id: int) -> List[PlayerSidelined]:
    """
    Fetch injuries with 24-hour cache.
    
    Injury data changes slowly, so daily fetch is sufficient.
    """
    cache_key = f"injuries_team_{team_id}"
    cached = redis.get(cache_key)
    
    if cached:
        return json.loads(cached)
    
    # Fetch from API
    injuries = fetch_from_api_football(team_id)
    
    # Cache for 24 hours
    redis.setex(cache_key, CACHE_TTL, json.dumps(injuries))
    
    return injuries

def batch_fetch_injuries(team_ids: List[int]) -> dict:
    """
    Fetch injuries for multiple teams in one go.
    
    Saves API calls by batching requests.
    """
    results = {}
    
    for team_id in team_ids:
        results[team_id] = get_team_injuries(team_id)
    
    return results
```

---

## Severity Classification

API-Football doesn't provide severity, so we infer it:

```python
def classify_injury_severity(injury_type: str, duration_days: int) -> str:
    """
    Classify injury severity based on type and expected duration.
    
    Rules:
    - ACL, fracture, surgery → severe
    - Hamstring, muscle tears → moderate
    - Knock, bruise, minor strain → minor
    - Unknown/missing return date → unknown
    """
    severe_keywords = ["acl", "fracture", "surgery", "cruciate", "rupture"]
    moderate_keywords = ["hamstring", "muscle", "groin", "calf", "tear"]
    minor_keywords = ["knock", "bruise", "strain", "fatigue"]
    
    injury_lower = injury_type.lower()
    
    # Check keywords
    if any(kw in injury_lower for kw in severe_keywords):
        return "severe"
    if any(kw in injury_lower for kw in moderate_keywords):
        return "moderate"
    if any(kw in injury_lower for kw in minor_keywords):
        return "minor"
    
    # Check duration
    if duration_days > 60:
        return "severe"
    elif duration_days > 14:
        return "moderate"
    elif duration_days > 0:
        return "minor"
    
    return "unknown"
```

---

## 🔴 DISABLED: Paid Sources

### Sportmonks Injury Reports
- **Status:** 🔴 DISABLED
- **Reason:** Paid plans only
- **Features:** Detailed epidemiology, ACL tracking (not needed for MVP)

### TransferMarkt Scraping
- **Status:** 🔴 DISABLED
- **Reason:** Scraping required (fragile)
- **Note:** Has detailed injury data but requires web scraping

---

## 🔴 DISABLED: League-Specific Scrapers

### premierleagueinjuries.com
- **Status:** 🔴 DISABLED
- **Reason:** Premier League only, scraping required

### sportsgambler.com/injuries
- **Status:** 🔴 DISABLED
- **Reason:** Scraping required, inconsistent format

---

## Implementation Checklist

- [ ] Register for API-Football key (RapidAPI)
- [ ] Test `/sidelined` endpoint for sample team
- [ ] Implement severity classification logic
- [ ] Set up 24-hour caching
- [ ] Test with 2-3 teams to verify data structure
- [ ] Handle missing return dates gracefully
- [ ] Validate player IDs match fixture data
- [ ] Log API usage to track rate limits
- [ ] Implement fallback for API failures
- [ ] Create alert if daily limit exceeded
