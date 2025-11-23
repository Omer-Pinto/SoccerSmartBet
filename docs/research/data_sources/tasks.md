# Data Sources - API Registrations

**Purpose:** Checklist for acquiring API keys for Pre-Gambling Flow data sources  
**Status:** Ready for execution after PR #2 approval

---

## Overview

This document lists all free API services that require registration and API key acquisition. Complete these registrations before implementing data fetchers.

**See:** [executive_summary.md](executive_summary.md) for full data stack overview and [sources/](sources/) for detailed API documentation.

---

## Required API Registrations

### 1. football-data.org - Fixtures Source

**Purpose:** Fetch daily fixtures for major European leagues  
**Free Tier:** 100 requests/day, 10 requests/minute

- [ ] Visit https://www.football-data.org/client/register
- [ ] Sign up with email (no credit card required)
- [ ] Copy API key from dashboard
- [ ] Add to project `.env` file:
  ```bash
  FOOTBALL_DATA_API_KEY=your_api_key_here
  ```
- [ ] Test API access:
  ```bash
  curl -H "X-Auth-Token: YOUR_KEY" https://api.football-data.org/v4/matches
  ```

**Detailed Docs:** [sources/football-data.org.md](sources/football-data.org.md)

---

### 2. The Odds API - Betting Odds Source

**Purpose:** Fetch 1/X/2 betting odds from European bookmakers  
**Free Tier:** 500 credits/month

- [ ] Visit https://the-odds-api.com/
- [ ] Click "Get API Key" and enter email
- [ ] Check email for API key
- [ ] Add to project `.env` file:
  ```bash
  ODDS_API_KEY=your_api_key_here
  ```
- [ ] Test API access (does NOT count against quota):
  ```bash
  curl "https://api.the-odds-api.com/v4/sports/?apiKey=YOUR_KEY"
  ```
- [ ] Test odds endpoint for EPL:
  ```bash
  curl "https://api.the-odds-api.com/v4/sports/soccer_epl/odds/?apiKey=YOUR_KEY&regions=eu&markets=h2h&oddsFormat=decimal"
  ```
- [ ] Check remaining credits in response headers (`x-requests-remaining`)

**Detailed Docs:** [sources/the-odds-api.md](sources/the-odds-api.md)

---

### 3. API-Football - Injuries, H2H, Player Stats

**Purpose:** Fetch injuries, suspensions, H2H statistics, player form  
**Free Tier:** 100 requests/day

- [ ] Visit https://dashboard.api-football.com/register
- [ ] Create free account
- [ ] Get API key from dashboard
- [ ] Add to project `.env` file:
  ```bash
  API_FOOTBALL_KEY=your_api_key_here
  ```
- [ ] Test sidelined endpoint (injuries):
  ```bash
  curl -H "x-rapidapi-host: v3.football.api-sports.io" \
       -H "x-rapidapi-key: YOUR_KEY" \
       "https://v3.football.api-sports.io/sidelined?team=33"
  ```

**Detailed Docs:** [sources/api-football.md](sources/api-football.md)

---

### 4. Open-Meteo - Weather Data (No Registration)

**Purpose:** Fetch weather forecasts for match venues  
**Free Tier:** 10,000 requests/day, no API key required

- [ ] Test weather API (no key required):
  ```bash
  curl "https://api.open-meteo.com/v1/forecast?latitude=53.4631&longitude=-2.2913&hourly=temperature_2m,precipitation,windspeed_10m"
  ```
- [ ] Confirm response format matches documentation
- [ ] No `.env` entry needed

**Detailed Docs:** [sources/open-meteo.md](sources/open-meteo.md)

---

## Environment Configuration

### Create `.env.example` Template

Create a `.env.example` file in the project root with the following structure:

```bash
# Football Data Sources (Task 0.1)
FOOTBALL_DATA_API_KEY=get_from_football-data.org_register_page
ODDS_API_KEY=get_from_the-odds-api.com
API_FOOTBALL_KEY=get_from_api-football.com_dashboard

# Open-Meteo (no key required)
# No configuration needed

# LangSmith (Task 0.2)
LANGCHAIN_API_KEY=your_langsmith_key
LANGCHAIN_PROJECT=SoccerSmartBet
```

### Setup Checklist
- [ ] Create `.env.example` in project root
- [ ] Add `.env` to `.gitignore` (if not already)
- [ ] Copy `.env.example` to `.env` and fill in actual keys
- [ ] Test all API endpoints with your keys

---

## Summary Table

| Service | Vertical | API Key Needed | .env Variable | Free Tier Limit |
|---------|----------|----------------|---------------|-----------------|
| football-data.org | Fixtures | ✅ Yes | `FOOTBALL_DATA_API_KEY` | 100 req/day |
| The Odds API | Odds | ✅ Yes | `ODDS_API_KEY` | 500 credits/month |
| API-Football | Injuries, H2H, Form | ✅ Yes | `API_FOOTBALL_KEY` | 100 req/day |
| Open-Meteo | Weather | ❌ No | N/A | 10,000 req/day |

**Total API Keys Needed:** 3

---

## Next Steps

1. **Complete all registrations** above and test each API
2. **Implementation tasks** will be incorporated into main task breakdown (see [BATCH_PLAN.md](../../../BATCH_PLAN.md))
3. **Tool development** will reference source documentation from [sources/](sources/) directory

---

## See Also

- [executive_summary.md](executive_summary.md) - Full data stack overview and status
- [verticals/](verticals/) - Requirements for each data vertical
- [sources/](sources/) - Detailed API documentation with code examples
- [PRE_GAMBLING_OPTIMIZED_FLOW_TASKS.md](../../../PRE_GAMBLING_OPTIMIZED_FLOW_TASKS.md) - Main task breakdown
