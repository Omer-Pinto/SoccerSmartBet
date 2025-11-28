# Odds Vertical

**Purpose:** Fetch betting lines (1/X/2 odds) for selected games to enable betting simulation

---

## Requirements

- Odds for home win (1), draw (X), away win (2)
- Decimal format (Israeli system: 2.10 = win 2.10× stake)
- Covers major European leagues
- Must be FREE and stable (no scraping)
- Minimum odds threshold filtering (configurable, e.g., odds > 1.5)

---

## Primary Source: The Odds API

**Status:** ✅ Enabled  
**Type:** REST API, Free tier (500 credits/month)  
**Details:** See [sources/the-odds-api.md](../sources/the-odds-api.md)

### Key Features
- 500 credits/month free tier
- Decimal odds format (matches Israeli Toto system)
- Covers EPL, La Liga, Bundesliga, Serie A, Ligue 1, Champions League
- Real-time updates for pre-match and in-play
- Multiple bookmakers aggregated (DraftKings, FanDuel, Bet365, etc.)

### Odds Format
```json
{
  "home_team": "Manchester United",
  "away_team": "Liverpool",
  "bookmakers": [
    {
      "key": "betfair",
      "markets": [
        {
          "key": "h2h",
          "outcomes": [
            {"name": "Manchester United", "price": 2.10},  // Home (1)
            {"name": "Draw", "price": 3.40},                // Draw (X)
            {"name": "Liverpool", "price": 3.50}            // Away (2)
          ]
        }
      ]
    }
  ]
}
```

### Quota Management
- **500 credits/month** = ~16 requests/day if used daily
- **Strategy:** Only fetch odds for filtered games (3-5/day), not all fixtures
- **Cost per request:** 1 credit per sport/region/market combination

---

## Implementation Notes

1. **Fetch Strategy:** After Smart Game Picker selects interesting games, fetch odds only for those
2. **Filtering:** Apply minimum odds threshold (e.g., filter games where all odds > 1.5)
3. **Bookmaker Selection:** Use Betfair or Pinnacle for European odds (most reliable)
4. **Fallback:** If API fails, skip betting for that day (no scraping backup)

---

## Decimal Odds Format (Israeli System)

The Odds API returns decimal odds, which match the Israeli Toto system:
- **Odd = 2.10:** Bet 100 NIS, win 210 NIS (profit = 110 NIS)
- **Odd = 1.50:** Bet 100 NIS, win 150 NIS (profit = 50 NIS)
- **Odd < 1 is invalid** (no conversion needed)

**Lower odds = less profit, higher odds = more profit**

---

## See Also
- [Task 3.3: Fetch Lines Node](../../../../status/pre_gambling_flow/PRE_GAMBLING_FLOW_TASKS.md#33-fetch-lines-from-winnercoil-node) - needs update to use The Odds API
- [Minimum Odds Threshold Config](../../../../status/pre_gambling_flow/PRE_GAMBLING_FLOW_TASKS.md#12-configuration-management)
