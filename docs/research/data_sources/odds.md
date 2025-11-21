# Odds Sources

**Status:** 🟢 **FREE API - CRITICAL**

---

## Primary: The-Odds-API ⭐ **RECOMMENDED**

**Website:** https://the-odds-api.com  
**Type:** RESTful API  
**Cost:** FREE (500 requests/month)  
**Status:** 🟢

### ✅ Why This Replaces winner.co.il

| Criterion | winner.co.il | The-Odds-API |
|-----------|--------------|--------------|
| **Access Method** | 🔴 Scraping (Selenium) | 🟢 REST API |
| **Reliability** | 🔴 Fragile (React SPA) | 🟢 Stable |
| **Anti-Bot Protection** | 🔴 Incapsula | 🟢 None (API) |
| **Maintenance** | 🔴 High (HTML changes) | 🟢 Low (versioned API) |
| **Coverage** | 🟡 Israeli odds only | 🟢 Global bookmakers |

### Features
- ✅ Free tier: 500 requests/month (≈16/day)
- ✅ International bookmakers (US, UK, EU, Australia)
- ✅ Major football leagues (EPL, La Liga, Bundesliga, Serie A, etc.)
- ✅ JSON format, RESTful API
- ✅ Decimal, American odds formats
- ✅ Head-to-head, spreads, totals markets

### Rate Limits
- **Free Plan**: 500 requests/month
- **Pro Plans**: Starting at $20/month (🔴 DISABLED for MVP)

### Registration
```bash
# Sign up at: https://the-odds-api.com
# Get API key immediately via email - no credit card required
```

### Example API Call

#### 1. Get Available Sports
```python
import requests

API_KEY = "your_api_key"
BASE_URL = "https://api.the-odds-api.com/v4"

# List all sports
response = requests.get(
    f"{BASE_URL}/sports",
    params={"apiKey": API_KEY}
)

# Example response:
[
  {
    "key": "soccer_epl",
    "group": "Soccer",
    "title": "EPL",
    "description": "English Premier League",
    "active": true,
    "has_outrights": false
  },
  {
    "key": "soccer_spain_la_liga",
    "group": "Soccer",
    "title": "La Liga",
    "active": true
  }
]
```

#### 2. Get Odds for Specific League
```python
# Get odds for Premier League
sport_key = "soccer_epl"
regions = "uk,eu"  # UK and EU bookmakers
markets = "h2h"     # Head-to-head (1X2 betting)
odds_format = "decimal"

response = requests.get(
    f"{BASE_URL}/sports/{sport_key}/odds",
    params={
        "apiKey": API_KEY,
        "regions": regions,
        "markets": markets,
        "oddsFormat": odds_format
    }
)

# Example response:
{
  "id": "abc123",
  "sport_key": "soccer_epl",
  "sport_title": "EPL",
  "commence_time": "2025-11-20T15:00:00Z",
  "home_team": "Manchester United",
  "away_team": "Liverpool",
  "bookmakers": [
    {
      "key": "williamhill",
      "title": "William Hill",
      "markets": [
        {
          "key": "h2h",
          "outcomes": [
            {"name": "Manchester United", "price": 2.10},  # Home win
            {"name": "Draw", "price": 3.40},               # Draw
            {"name": "Liverpool", "price": 3.50}           # Away win
          ]
        }
      ]
    }
  ]
}
```

---

## Odds Format Conversion

### Israeli Format (winner.co.il style)
Israeli odds show **winnings per 1 ILS wagered** (excluding stake).

**Example:** If odds are "1.10", you win 1.10 ILS profit per 1 ILS bet (total return: 2.10 ILS).

### Decimal Format (The-Odds-API)
Decimal odds show **total return per 1 unit wagered** (including stake).

**Example:** Decimal 2.10 means total return of 2.10 per 1 unit bet (profit: 1.10).

### Conversion Formula
```python
def decimal_to_israeli(decimal_odds: float) -> float:
    """
    Convert decimal odds to Israeli format.
    
    Israeli odds = Decimal odds - 1
    
    Example:
        Decimal 2.10 → Israeli 1.10
        Decimal 3.50 → Israeli 2.50
    """
    return round(decimal_odds - 1, 2)

def israeli_to_decimal(israeli_odds: float) -> float:
    """
    Convert Israeli odds to decimal format.
    
    Decimal odds = Israeli odds + 1
    """
    return round(israeli_odds + 1, 2)

# Usage example
decimal_home = 2.10
decimal_draw = 3.40
decimal_away = 3.50

israeli_home = decimal_to_israeli(decimal_home)  # 1.10
israeli_draw = decimal_to_israeli(decimal_draw)  # 2.40
israeli_away = decimal_to_israeli(decimal_away)  # 2.50

print(f"Israeli format: 1={israeli_home}, X={israeli_draw}, 2={israeli_away}")
# Output: Israeli format: 1=1.10, X=2.40, 2=2.50
```

---

## Data Structure (Normalized)

```python
from pydantic import BaseModel
from typing import List
from datetime import datetime

class BettingOdds(BaseModel):
    match_id: str
    home_team: str
    away_team: str
    kickoff_time: datetime
    odds_1: float  # Home win (Israeli format)
    odds_x: float  # Draw (Israeli format)
    odds_2: float  # Away win (Israeli format)
    bookmaker: str
    source: str = "the-odds-api"
    fetched_at: datetime

# Example usage:
odds = BettingOdds(
    match_id="epl_20251120_manunited_liverpool",
    home_team="Manchester United",
    away_team="Liverpool",
    kickoff_time=datetime(2025, 11, 20, 15, 0),
    odds_1=1.10,  # Converted from decimal 2.10
    odds_x=2.40,  # Converted from decimal 3.40
    odds_2=2.50,  # Converted from decimal 3.50
    bookmaker="williamhill",
    fetched_at=datetime.now()
)
```

---

## Implementation Strategy

### Daily Odds Fetch
```python
def fetch_daily_odds(leagues: List[str]) -> List[BettingOdds]:
    """
    Fetch odds for specified leagues once per day.
    
    Rate limit: 500 requests/month ≈ 16/day
    Strategy: Fetch in morning (e.g., 10:00 AM), cache for 24 hours
    """
    all_odds = []
    
    for league_key in leagues:
        response = requests.get(
            f"{BASE_URL}/sports/{league_key}/odds",
            params={
                "apiKey": API_KEY,
                "regions": "uk,eu",
                "markets": "h2h",
                "oddsFormat": "decimal"
            }
        )
        
        for event in response.json():
            # Parse and convert to Israeli format
            odds = parse_odds_response(event)
            all_odds.append(odds)
    
    return all_odds

def parse_odds_response(event: dict) -> BettingOdds:
    """Parse The-Odds-API response and convert to Israeli format."""
    bookmaker = event["bookmakers"][0]  # Use first bookmaker
    outcomes = bookmaker["markets"][0]["outcomes"]
    
    # Extract decimal odds
    home_decimal = next(o["price"] for o in outcomes if o["name"] == event["home_team"])
    draw_decimal = next(o["price"] for o in outcomes if o["name"] == "Draw")
    away_decimal = next(o["price"] for o in outcomes if o["name"] == event["away_team"])
    
    # Convert to Israeli format
    return BettingOdds(
        match_id=event["id"],
        home_team=event["home_team"],
        away_team=event["away_team"],
        kickoff_time=datetime.fromisoformat(event["commence_time"].replace("Z", "+00:00")),
        odds_1=decimal_to_israeli(home_decimal),
        odds_x=decimal_to_israeli(draw_decimal),
        odds_2=decimal_to_israeli(away_decimal),
        bookmaker=bookmaker["title"],
        fetched_at=datetime.now()
    )
```

---

## 🔴 DISABLED: winner.co.il

**Website:** https://www.winner.co.il  
**Status:** 🔴 DISABLED  
**Reason:** Too fragile (React SPA scraping with Incapsula protection)

**User Feedback:** "I don't want winner.co.il → it is too fragile"

**Why It Was Problematic:**
- Requires Selenium/Playwright for dynamic content
- Incapsula anti-bot protection
- Hebrew language parsing
- Site layout changes frequently
- High maintenance burden

---

## 🔴 DISABLED: Other Paid Sources

### OddsMatrix
- **Status:** 🔴 DISABLED
- **Reason:** Paid only, enterprise pricing

### Sportradar Odds
- **Status:** 🔴 DISABLED
- **Reason:** Paid subscription required

---

## Testing Checklist

- [ ] Register for The-Odds-API key
- [ ] Test `/sports` endpoint (list available leagues)
- [ ] Test `/odds` endpoint for EPL
- [ ] Verify decimal odds format
- [ ] Implement conversion to Israeli format
- [ ] Test rate limit tracking (500/month)
- [ ] Cache odds data for 24 hours
- [ ] Validate data structure (home, draw, away)
- [ ] Handle missing bookmakers gracefully
- [ ] Test error handling (API down, rate limit exceeded)
