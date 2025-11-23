# API-Football

**Website:** https://www.api-football.com  
**Type:** REST API  
**Cost:** FREE (100 requests/day)  
**Status:** ✅ Primary source for [Injuries/Suspensions](../verticals/injuries_suspensions.md) and [H2H](../verticals/h2h.md)

---

## Overview

API-Football (also available via RapidAPI) provides comprehensive football data including injuries, suspensions, and head-to-head statistics. It's the **primary source for team strength assessment** in SoccerSmartBet.

---

## Features

- ✅ 1,200+ leagues and cups
- ✅ Live scores (15-second updates)
- ✅ Fixtures, standings, H2H, events
- ✅ **Injuries and suspensions** (sidelined endpoint)
- ✅ Pre-match and live odds
- ✅ Player statistics
- ✅ JSON format

---

## Rate Limits

- **Free Plan**: 100 requests/day, 10 requests/minute
- **Pro Plan**: $19/month for 7,500 requests/day (not needed)

**For SoccerSmartBet:**
- 3-5 games/day × 2 teams = 6-10 requests for injuries
- ~3-5 requests for H2H
- **Total:** ~10-15 requests/day (well under 100 limit)

---

## Registration

**Option 1: Direct (Recommended)**
1. Visit: https://dashboard.api-football.com/register
2. Create account
3. Get API key from dashboard
4. Add to `.env`:
   ```bash
   API_FOOTBALL_KEY=your_api_key_here
   ```

**Option 2: Via RapidAPI**
1. Visit: https://rapidapi.com/api-sports/api/api-football
2. Subscribe to free tier
3. Use RapidAPI key (headers slightly different)

---

## API Endpoints

### 1. Sidelined (Injuries & Suspensions) {#sidelined}

**Endpoint:**
```http
GET https://v3.football.api-sports.io/sidelined?team=33
```

**Headers:**
```http
x-rapidapi-host: v3.football.api-sports.io
x-rapidapi-key: YOUR_API_KEY
```

**Parameters:**
- `team`: Team ID (required)
- `player`: Player ID (optional, for specific player)

**Response:**
```json
{
  "response": [
    {
      "type": "Knee Injury",
      "start": "2025-10-15",
      "end": "2025-12-01",
      "player": {
        "id": 276,
        "name": "Bruno Fernandes",
        "photo": "https://media.api-sports.io/football/players/276.png"
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
    }
  ]
}
```

**Types:**
- Injuries: "Knee Injury", "Muscle Injury", "ACL", "Hamstring", etc.
- Suspensions: "Red Card", "Yellow Cards", "Suspension"

---

### 2. Head-to-Head {#h2h}

**Endpoint:**
```http
GET https://v3.football.api-sports.io/fixtures/headtohead?h2h=33-34
```

**Parameters:**
- `h2h`: "team1_id-team2_id" format (e.g., "33-34" for Man United vs Newcastle)
- `last`: Number of last matches (optional, default: all available)

**Response:**
```json
{
  "response": [
    {
      "fixture": {
        "id": 123456,
        "referee": "Anthony Taylor",
        "timezone": "UTC",
        "date": "2024-10-06T14:00:00+00:00",
        "timestamp": 1696600800,
        "venue": {
          "id": 556,
          "name": "Old Trafford",
          "city": "Manchester"
        },
        "status": {
          "long": "Match Finished",
          "short": "FT"
        }
      },
      "league": {
        "id": 39,
        "name": "Premier League",
        "country": "England",
        "season": 2024
      },
      "teams": {
        "home": {
          "id": 33,
          "name": "Manchester United",
          "logo": "https://media.api-sports.io/football/teams/33.png",
          "winner": true
        },
        "away": {
          "id": 34,
          "name": "Newcastle",
          "logo": "https://media.api-sports.io/football/teams/34.png",
          "winner": false
        }
      },
      "goals": {
        "home": 3,
        "away": 0
      },
      "score": {
        "halftime": {"home": 2, "away": 0},
        "fulltime": {"home": 3, "away": 0}
      }
    }
  ]
}
```

---

### 3. Fixtures (Backup)

**Endpoint:**
```http
GET https://v3.football.api-sports.io/fixtures?date=2025-11-20
```

**Use Case:** Backup source if football-data.org quota exhausted

---

## Python Code Example

```python
import requests
from typing import List, Dict

class APIFootballFetcher:
    """Fetches data from API-Football"""
    
    BASE_URL = "https://v3.football.api-sports.io"
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.headers = {
            "x-rapidapi-host": "v3.football.api-sports.io",
            "x-rapidapi-key": api_key
        }
    
    def get_sidelined(self, team_id: int) -> List[Dict]:
        """
        Fetch injuries and suspensions for a team
        
        Args:
            team_id: API-Football team ID
        
        Returns:
            List of sidelined players with type, dates, player info
        """
        params = {"team": team_id}
        response = requests.get(
            f"{self.BASE_URL}/sidelined",
            headers=self.headers,
            params=params
        )
        response.raise_for_status()
        
        data = response.json()
        return data.get("response", [])
    
    def get_h2h(self, team1_id: int, team2_id: int, last: int = 10) -> List[Dict]:
        """
        Fetch head-to-head matches between two teams
        
        Args:
            team1_id: First team ID
            team2_id: Second team ID
            last: Number of recent matches (default: 10)
        
        Returns:
            List of past matches
        """
        params = {
            "h2h": f"{team1_id}-{team2_id}",
            "last": last
        }
        response = requests.get(
            f"{self.BASE_URL}/fixtures/headtohead",
            headers=self.headers,
            params=params
        )
        response.raise_for_status()
        
        data = response.json()
        return data.get("response", [])
    
    def get_fixtures_by_date(self, date_str: str) -> List[Dict]:
        """
        Fetch fixtures for a specific date (backup for football-data.org)
        
        Args:
            date_str: Date in YYYY-MM-DD format
        
        Returns:
            List of fixtures
        """
        params = {"date": date_str}
        response = requests.get(
            f"{self.BASE_URL}/fixtures",
            headers=self.headers,
            params=params
        )
        response.raise_for_status()
        
        data = response.json()
        return data.get("response", [])


# Example usage
if __name__ == "__main__":
    import os
    
    api_key = os.getenv("API_FOOTBALL_KEY")
    fetcher = APIFootballFetcher(api_key)
    
    # Get injuries for Manchester United (team_id = 33)
    sidelined = fetcher.get_sidelined(team_id=33)
    
    print("Manchester United - Sidelined Players:")
    for item in sidelined:
        player_name = item["player"]["name"]
        injury_type = item["type"]
        end_date = item.get("end", "Unknown")
        print(f"  {player_name}: {injury_type} (return: {end_date})")
    
    # Get H2H between Man United (33) and Newcastle (34)
    h2h_matches = fetcher.get_h2h(team1_id=33, team2_id=34, last=5)
    
    print("\nMan United vs Newcastle - Last 5 H2H:")
    for match in h2h_matches:
        home = match["teams"]["home"]["name"]
        away = match["teams"]["away"]["name"]
        score = f"{match['goals']['home']}-{match['goals']['away']}"
        date = match["fixture"]["date"][:10]
        print(f"  {date}: {home} {score} {away}")
```

---

## Team ID Mapping

**Note:** API-Football uses internal team IDs. Must map team names to IDs.

### Common Team IDs
| Team | ID |
|------|-----|
| Manchester United | 33 |
| Manchester City | 50 |
| Liverpool | 40 |
| Arsenal | 42 |
| Chelsea | 49 |
| Newcastle | 34 |
| Real Madrid | 541 |
| Barcelona | 529 |
| Bayern Munich | 157 |

**Full mapping:** Fetch from `/teams` endpoint or maintain lookup table in DB.

---

## Implementation Notes

### For Team Intelligence Agent

1. **Fetch injuries per team:**
   - Call `get_sidelined(team_id)` for home and away teams
   - **2 requests per game** (6-10 requests/day for 3-5 games)

2. **AI Analysis Required:**
   - Raw injury list NOT sufficient for betting
   - Agent must determine if injured players are starters vs bench warmers
   - For unknown teams, cross-reference with lineup/form data

### For Game Intelligence Agent

1. **Fetch H2H:**
   - Call `get_h2h(team1_id, team2_id, last=10)` per selected game
   - **3-5 requests/day** for filtered games

2. **AI Pattern Extraction:**
   - Identify home dominance, high-scoring trends, defensive patterns
   - Synthesize into betting-relevant insights

### Quota Management

**Daily Usage Estimate:**
- Injuries: 6-10 requests (2 per game × 3-5 games)
- H2H: 3-5 requests (1 per game)
- **Total:** 9-15 requests/day (buffer: 85-91 requests/day remaining)

**Optimization:**
- Cache sidelined data (changes slowly, re-fetch daily)
- Cache H2H data (history doesn't change, re-fetch weekly)

---

## See Also

- [Injuries/Suspensions Vertical](../verticals/injuries_suspensions.md) - Use case for sidelined endpoint
- [H2H Vertical](../verticals/h2h.md) - Use case for H2H endpoint
- [Team Intelligence Agent](../../../../PRE_GAMBLING_OPTIMIZED_FLOW_TASKS.md#52-team-intelligence-agent-node) - Uses sidelined data
- [Game Intelligence Agent](../../../../PRE_GAMBLING_OPTIMIZED_FLOW_TASKS.md#42-game-intelligence-agent-node) - Uses H2H data
- [Official API Docs](https://www.api-football.com/documentation-v3)
