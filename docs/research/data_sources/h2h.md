# Head-to-Head (H2H) Statistics

**Status:** 🟡 **FREE WITH LIMITS**

---

## Primary: API-Football H2H Endpoint

**Website:** https://www.api-football.com  
**Type:** RESTful API  
**Cost:** FREE (100 requests/day)  
**Status:** 🟡

### Features
- ✅ Included in free tier
- ✅ Recent matches between two teams
- ✅ Full match details (score, date, venue)
- ✅ Historical data
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

# Get head-to-head between two teams
params = {
    "h2h": "33-34"  # Man United (33) vs Newcastle (34)
}

response = requests.get(
    f"{BASE_URL}/fixtures/headtohead",
    headers=headers,
    params=params
)

# Example response:
{
  "response": [
    {
      "fixture": {
        "id": 123456,
        "date": "2024-10-06T14:00:00+00:00",
        "venue": {"name": "Old Trafford", "city": "Manchester"}
      },
      "teams": {
        "home": {"id": 33, "name": "Manchester United", "winner": true},
        "away": {"id": 34, "name": "Newcastle", "winner": false}
      },
      "goals": {"home": 3, "away": 0},
      "score": {
        "halftime": {"home": 1, "away": 0},
        "fulltime": {"home": 3, "away": 0}
      }
    },
    {
      "fixture": {
        "id": 123455,
        "date": "2024-05-15T19:45:00+00:00"
      },
      "teams": {
        "home": {"id": 34, "name": "Newcastle", "winner": false},
        "away": {"id": 33, "name": "Manchester United", "winner": false}
      },
      "goals": {"home": 2, "away": 2}
    }
  ]
}
```

---

## Data Structure

```python
from pydantic import BaseModel
from typing import Literal, Optional
from datetime import datetime

class H2HMatch(BaseModel):
    fixture_id: int
    date: datetime
    home_team: str
    away_team: str
    home_goals: int
    away_goals: int
    result: Literal["home_win", "draw", "away_win"]
    venue: Optional[str]
    
    @classmethod
    def from_api_response(cls, data: dict):
        """Parse API-Football H2H response."""
        home_goals = data["goals"]["home"]
        away_goals = data["goals"]["away"]
        
        if home_goals > away_goals:
            result = "home_win"
        elif home_goals < away_goals:
            result = "away_win"
        else:
            result = "draw"
        
        return cls(
            fixture_id=data["fixture"]["id"],
            date=datetime.fromisoformat(data["fixture"]["date"].replace("Z", "+00:00")),
            home_team=data["teams"]["home"]["name"],
            away_team=data["teams"]["away"]["name"],
            home_goals=home_goals,
            away_goals=away_goals,
            result=result,
            venue=data["fixture"]["venue"]["name"] if "venue" in data["fixture"] else None
        )

class H2HStats(BaseModel):
    """Aggregate H2H statistics."""
    team_a: str
    team_b: str
    total_matches: int
    team_a_wins: int
    team_b_wins: int
    draws: int
    team_a_goals: int
    team_b_goals: int
    recent_matches: List[H2HMatch]  # Last 5-10 matches
    
    @property
    def team_a_win_rate(self) -> float:
        return self.team_a_wins / self.total_matches if self.total_matches > 0 else 0
    
    @property
    def team_b_win_rate(self) -> float:
        return self.team_b_wins / self.total_matches if self.total_matches > 0 else 0
    
    @property
    def draw_rate(self) -> float:
        return self.draws / self.total_matches if self.total_matches > 0 else 0
```

---

## Analysis Patterns

```python
def analyze_h2h(matches: List[H2HMatch], home_team: str) -> dict:
    """
    Extract betting-relevant patterns from H2H.
    
    Returns insights for AI agent to use.
    """
    total = len(matches)
    if total == 0:
        return {"pattern": "no_history"}
    
    # Count results from home team's perspective
    home_wins = sum(1 for m in matches if (m.home_team == home_team and m.result == "home_win") or (m.away_team == home_team and m.result == "away_win"))
    away_wins = total - home_wins - sum(1 for m in matches if m.result == "draw")
    draws = sum(1 for m in matches if m.result == "draw")
    
    # Goal statistics
    total_goals = sum(m.home_goals + m.away_goals for m in matches)
    avg_goals = total_goals / total
    
    # Recent form (last 3 matches)
    recent_results = [m.result for m in matches[:3]]
    
    # Patterns
    high_scoring = avg_goals > 3.0
    low_scoring = avg_goals < 1.5
    home_dominant = home_wins / total > 0.6
    draw_prone = draws / total > 0.4
    
    return {
        "total_matches": total,
        "home_wins": home_wins,
        "away_wins": away_wins,
        "draws": draws,
        "avg_goals_per_game": round(avg_goals, 2),
        "recent_form": recent_results,
        "patterns": {
            "high_scoring": high_scoring,
            "low_scoring": low_scoring,
            "home_dominant": home_dominant,
            "draw_prone": draw_prone
        }
    }

# Example output:
{
  "total_matches": 8,
  "home_wins": 5,
  "away_wins": 2,
  "draws": 1,
  "avg_goals_per_game": 2.8,
  "recent_form": ["home_win", "draw", "home_win"],
  "patterns": {
    "high_scoring": False,
    "low_scoring": False,
    "home_dominant": True,
    "draw_prone": False
  }
}
```

---

## Backup: football-data.org

**Status:** 🟢  
**Note:** H2H available via team match history

```python
# Get H2H via match history
team1_matches = requests.get(
    f"{BASE_URL}/teams/65/matches",
    headers={"X-Auth-Token": API_KEY}
)

team2_matches = requests.get(
    f"{BASE_URL}/teams/66/matches",
    headers={"X-Auth-Token": API_KEY}
)

# Filter for matches where both teams played each other
h2h_matches = [
    m for m in team1_matches.json()["matches"]
    if m["homeTeam"]["id"] == 66 or m["awayTeam"]["id"] == 66
]
```

---

## Rate Limit Strategy

### Problem
- 100 requests/day limit (API-Football)
- Need H2H for **1 pair per game**
- 3 games/day = 3 H2H requests

### Solution: Cache Long-Term
```python
CACHE_TTL = 7 * 24 * 60 * 60  # 7 days

def get_h2h_stats(team_a_id: int, team_b_id: int) -> H2HStats:
    """
    Fetch H2H with 7-day cache.
    
    H2H history changes slowly, so weekly refresh is fine.
    """
    cache_key = f"h2h_{min(team_a_id, team_b_id)}_{max(team_a_id, team_b_id)}"
    cached = redis.get(cache_key)
    
    if cached:
        return H2HStats(**json.loads(cached))
    
    # Fetch from API
    h2h = fetch_h2h_from_api(team_a_id, team_b_id)
    
    # Cache for 7 days
    redis.setex(cache_key, CACHE_TTL, h2h.json())
    
    return h2h
```

---

## 🔴 DISABLED: Scraping Sources

### AllSportsAPI
- **Status:** 🔴 DISABLED
- **Reason:** 2 random leagues per year (unreliable)

### Manual Scraping
- **Status:** 🔴 DISABLED
- **Reason:** API-Football sufficient for MVP

---

## Implementation Checklist

- [ ] Test API-Football H2H endpoint
- [ ] Parse response into H2HMatch objects
- [ ] Implement aggregate statistics (H2HStats)
- [ ] Build pattern analysis function
- [ ] Set up 7-day caching
- [ ] Handle cases with no H2H history
- [ ] Validate team IDs match fixture data
- [ ] Test with multiple team pairs
- [ ] Log API usage
- [ ] Implement fallback to football-data.org
