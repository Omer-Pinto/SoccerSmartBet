# The Odds API

**Website:** https://the-odds-api.com  
**Type:** REST API  
**Cost:** FREE (500 credits/month)  
**Status:** ✅ Primary source for [Odds](../verticals/odds.md)

---

## Overview

The Odds API provides betting odds from bookmakers worldwide via a simple REST API, serving as the primary odds source for SoccerSmartBet.

---

## Why This Source?

1. **No Scraping:** Stable REST API with reliable uptime
2. **Decimal Odds:** Uses decimal format (2.10 = 2.10× stake), matching Israeli Toto system
3. **Free Tier:** 500 credits/month = ~16 requests/day
4. **Global Coverage:** EPL, La Liga, Bundesliga, Serie A, Ligue 1, Champions League
5. **Multiple Bookmakers:** Aggregates odds from Betfair, Pinnacle, Bet365, etc.

---

## Features

- ✅ 500 credits/month free tier
- ✅ Decimal and American odds formats
- ✅ Pre-match and in-play odds
- ✅ h2h (moneyline), spreads, totals markets
- ✅ 70+ sports, 40+ bookmakers
- ✅ JSON format
- ✅ Real-time updates

---

## Pricing

| Plan | Credits/Month | Cost | Notes |
|------|---------------|------|-------|
| **Starter** | 500 | FREE | All sports, most bookmakers |
| 20K | 20,000 | $30/month | + Historical odds |
| 100K | 100,000 | $59/month | + Historical odds |

**For SoccerSmartBet:** Starter plan sufficient (3-5 games/day × 30 days = 90-150 credits/month)

---

## Registration

1. Visit: https://the-odds-api.com/
2. Click "Get API Key" and enter email
3. Receive API key via email immediately
4. Add to `.env` file:
   ```bash
   ODDS_API_KEY=your_api_key_here
   ```

---

## API Endpoints

### Get In-Season Sports
```http
GET https://api.the-odds-api.com/v4/sports/?apiKey=YOUR_API_KEY
```

**Response:**
```json
[
  {
    "key": "soccer_epl",
    "group": "soccer",
    "title": "Premier League",
    "description": "English Premier League",
    "active": true,
    "has_outrights": false
  },
  {
    "key": "soccer_spain_la_liga",
    "group": "soccer",
    "title": "La Liga",
    "description": "Spanish La Liga",
    "active": true,
    "has_outrights": false
  }
]
```

**Note:** This endpoint does NOT count against your quota.

---

### Get Odds for Soccer Matches

```http
GET https://api.the-odds-api.com/v4/sports/soccer_epl/odds/
  ?apiKey=YOUR_API_KEY
  &regions=eu
  &markets=h2h
  &oddsFormat=decimal
```

**Parameters:**
- `regions`: `us`, `uk`, `eu`, `au` (use `eu` for European bookmakers)
- `markets`: `h2h` (head-to-head/moneyline), `spreads`, `totals`
- `oddsFormat`: `decimal` (recommended) or `american`

**Response:**
```json
[
  {
    "id": "bda33adca828c09dc3cac3a856aef176",
    "sport_key": "soccer_epl",
    "sport_title": "Premier League",
    "commence_time": "2025-11-20T19:45:00Z",
    "home_team": "Manchester United",
    "away_team": "Liverpool",
    "bookmakers": [
      {
        "key": "betfair",
        "title": "Betfair",
        "last_update": "2025-11-20T10:46:09Z",
        "markets": [
          {
            "key": "h2h",
            "last_update": "2025-11-20T10:46:09Z",
            "outcomes": [
              {
                "name": "Manchester United",
                "price": 2.10
              },
              {
                "name": "Draw",
                "price": 3.40
              },
              {
                "name": "Liverpool",
                "price": 3.50
              }
            ]
          }
        ]
      }
    ]
  }
]
```

---

## Python Code Example

```python
import requests
from typing import List, Dict

class OddsAPIFetcher:
    """Fetches betting odds from The Odds API"""
    
    BASE_URL = "https://api.the-odds-api.com/v4"
    
    def __init__(self, api_key: str):
        self.api_key = api_key
    
    def get_sports(self) -> List[Dict]:
        """Get list of in-season sports (does not count against quota)"""
        response = requests.get(
            f"{self.BASE_URL}/sports/",
            params={"apiKey": self.api_key}
        )
        response.raise_for_status()
        return response.json()
    
    def get_odds(
        self,
        sport_key: str = "soccer_epl",
        regions: str = "eu",
        markets: str = "h2h",
        odds_format: str = "decimal"
    ) -> List[Dict]:
        """
        Fetch odds for a specific sport
        
        Args:
            sport_key: e.g., 'soccer_epl', 'soccer_spain_la_liga'
            regions: 'us', 'uk', 'eu', 'au'
            markets: 'h2h', 'spreads', 'totals'
            odds_format: 'decimal' or 'american'
        
        Returns:
            List of matches with bookmaker odds
        """
        params = {
            "apiKey": self.api_key,
            "regions": regions,
            "markets": markets,
            "oddsFormat": odds_format
        }
        
        response = requests.get(
            f"{self.BASE_URL}/sports/{sport_key}/odds/",
            params=params
        )
        response.raise_for_status()
        
        # Check remaining quota
        remaining = response.headers.get("x-requests-remaining")
        print(f"Remaining API credits: {remaining}")
        
        return response.json()
    
    def extract_odds(self, match_data: Dict, bookmaker_key: str = "betfair") -> Dict:
        """
        Extract 1/X/2 odds from match data
        
        Args:
            match_data: Single match object from API response
            bookmaker_key: Preferred bookmaker (default: betfair)
        
        Returns:
            {"1": 2.10, "X": 3.40, "2": 3.50}
        """
        home_team = match_data["home_team"]
        away_team = match_data["away_team"]
        
        # Find preferred bookmaker
        bookmaker = next(
            (b for b in match_data["bookmakers"] if b["key"] == bookmaker_key),
            match_data["bookmakers"][0] if match_data["bookmakers"] else None
        )
        
        if not bookmaker:
            return None
        
        # Extract h2h market odds
        h2h_market = next(
            (m for m in bookmaker["markets"] if m["key"] == "h2h"),
            None
        )
        
        if not h2h_market:
            return None
        
        outcomes = h2h_market["outcomes"]
        
        # Map to 1/X/2 format
        odds = {}
        for outcome in outcomes:
            if outcome["name"] == home_team:
                odds["1"] = outcome["price"]
            elif outcome["name"] == away_team:
                odds["2"] = outcome["price"]
            elif outcome["name"] == "Draw":
                odds["X"] = outcome["price"]
        
        return odds


# Example usage
if __name__ == "__main__":
    import os
    
    api_key = os.getenv("ODDS_API_KEY")
    fetcher = OddsAPIFetcher(api_key)
    
    # Get EPL odds
    matches = fetcher.get_odds(sport_key="soccer_epl")
    
    for match in matches:
        print(f"{match['home_team']} vs {match['away_team']}")
        print(f"  Kickoff: {match['commence_time']}")
        
        odds = fetcher.extract_odds(match)
        if odds:
            print(f"  Odds (1/X/2): {odds.get('1')}/{odds.get('X')}/{odds.get('2')}")
        print()
```

---

## Soccer Sport Keys

| League | Sport Key | Region |
|--------|-----------|--------|
| Premier League | `soccer_epl` | UK |
| La Liga | `soccer_spain_la_liga` | EU |
| Bundesliga | `soccer_germany_bundesliga` | EU |
| Serie A | `soccer_italy_serie_a` | EU |
| Ligue 1 | `soccer_france_ligue_one` | EU |
| Champions League | `soccer_uefa_champs_league` | EU |
| Europa League | `soccer_uefa_europa_league` | EU |

**Full list:** Call `GET /v4/sports/` endpoint

---

## Quota Management

### Cost per Request
- **1 credit** = 1 sport + 1 region + 1 market combination
- Example: `soccer_epl` + `eu` + `h2h` = 1 credit

### Optimization Strategy
1. **Fetch odds ONLY for filtered games** (after Smart Game Picker selects interesting matches)
2. **Use single region:** `eu` for European bookmakers (Betfair, Pinnacle)
3. **Use single market:** `h2h` only (no spreads/totals needed)
4. **Batch by league:** If 3 EPL games selected, 1 request returns all EPL odds (filter later)

### Example Daily Usage
- 3-5 games/day selected by Smart Game Picker
- Typically from 2-3 different leagues
- **Cost:** 2-3 credits/day
- **Monthly:** ~70 credits/month (well under 500 limit)

---

## Decimal Odds Format (Israeli System)

The Odds API returns decimal odds by default, which match the Israeli Toto system:

| Decimal Odd | Meaning | Bet 100 NIS | Win Amount | Profit |
|-------------|---------|-------------|------------|--------|
| 2.10 | Home win | 100 NIS | 210 NIS | 110 NIS |
| 3.40 | Draw | 100 NIS | 340 NIS | 240 NIS |
| 3.50 | Away win | 100 NIS | 350 NIS | 250 NIS |

**No conversion needed** - use odds directly in calculations.

---

## Implementation Notes

### For Pre-Gambling Flow

1. **Trigger:** After Smart Game Picker selects interesting games
2. **Fetch:** Get odds for those specific games only
3. **Filter:** Apply minimum odds threshold (e.g., all odds > 1.5)
4. **Store:** Persist to DB with `fetched_at` timestamp
5. **Quota Check:** Monitor `x-requests-remaining` header, alert if < 100 credits remaining

### Preferred Bookmakers (European Region)

- **Betfair:** Most reliable, high liquidity
- **Pinnacle:** Sharp odds, low margin
- **Bet365:** Wide coverage

**Fallback:** If preferred bookmaker missing, use first available bookmaker in response.

---

## See Also

- [Odds Vertical](../verticals/odds.md) - Requirements and implementation strategy
- [Task 3.3: Fetch Lines Node](../../../../PRE_GAMBLING_OPTIMIZED_FLOW_TASKS.md#33-fetch-lines-from-winnercoil-node) - Implementation task (needs update)
- [Official API Docs](https://the-odds-api.com/liveapi/guides/v4/)
