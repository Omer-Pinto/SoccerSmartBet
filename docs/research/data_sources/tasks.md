# Data Sources - API Registrations

**Purpose:** Checklist for acquiring API keys for Pre-Gambling Flow data sources  
**Status:** Updated - api-football.com fraud corrected, apifootball.com added

---

## Overview

This document lists all free API services that require registration and API key acquisition. Complete these registrations before implementing data fetchers.

**See:** [executive_summary.md](executive_summary.md) for full data stack overview and [sources/](sources/) for detailed API documentation.

**⚠️ IMPORTANT:** Do NOT confuse **apifootball.com** (legitimate, no hyphen) with **api-football.com** (fraudulent, with hyphen). See [sources/NON_VIABLE_SOURCES.md](sources/NON_VIABLE_SOURCES.md).

---

## Required API Registrations

### 1. football-data.org - Fixtures & H2H Source

**Purpose:** Fetch daily fixtures and head-to-head statistics  
**Free Tier:** 100 requests/day, 10 requests/minute

- [ ] Visit https://www.football-data.org/client/register
- [ ] Sign up with email (no credit card required)
- [ ] Copy API key from dashboard
- [ ] Add to project `.env` file:
  ```bash
  FOOTBALL_DATA_API_KEY=your_api_key_here
  ```
- [ ] Test API access (fixtures):
  ```bash
  curl -H "X-Auth-Token: YOUR_KEY" https://api.football-data.org/v4/matches
  ```
- [ ] Test H2H endpoint:
  ```bash
  curl -H "X-Auth-Token: YOUR_KEY" https://api.football-data.org/v4/matches/MATCH_ID/head2head
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

### 3. apifootball.com - Injuries, H2H Backup, Team Form

**Purpose:** Fetch injuries, suspensions, H2H statistics (backup), team form  
**Free Tier:** 180 requests/hour (6,480 requests/day)

**⚠️ NOTE:** This is **apifootball.com** (NO hyphen), NOT api-football.com (fraudulent).

- [ ] Visit https://apifootball.com/
- [ ] Create free account
- [ ] Get API key from dashboard
- [ ] Add to project `.env` file:
  ```bash
  APIFOOTBALL_API_KEY=your_api_key_here
  ```
- [ ] Test teams endpoint (includes injury data):
  ```bash
  curl "https://apiv3.apifootball.com/?action=get_teams&league_id=152&APIkey=YOUR_KEY"
  ```
- [ ] Test events endpoint (for H2H and team form):
  ```bash
  curl "https://apiv3.apifootball.com/?action=get_events&from=2024-01-01&to=2024-12-31&team_id=141&APIkey=YOUR_KEY"
  ```
- [ ] Verify `player_injured` field in response

**Detailed Docs:** [sources/apifootball.md](sources/apifootball.md)

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
APIFOOTBALL_API_KEY=get_from_apifootball.com_dashboard

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
| football-data.org | Fixtures, H2H | ✅ Yes | `FOOTBALL_DATA_API_KEY` | 100 req/day, 10 req/min |
| The Odds API | Odds | ✅ Yes | `ODDS_API_KEY` | 500 credits/month |
| **apifootball.com** | Injuries, H2H backup, Team Form | ✅ Yes | `APIFOOTBALL_API_KEY` | 180 req/hour (6,480 req/day) |
| Open-Meteo | Weather | ❌ No | N/A | 10,000 req/day |

**Total API Keys Needed:** 3

**Changed from previous version:** 
- ❌ Removed: API-Football (`API_FOOTBALL_KEY`) - fraudulent (2021-2023 data only)
- ✅ Added: apifootball.com (`APIFOOTBALL_API_KEY`) - legitimate 180 req/hour FREE
- ✅ Expanded: football-data.org now also used for H2H (not just fixtures)

---

## ⚠️ CRITICAL: Do NOT Use api-football.com

**Why:** api-football.com's free tier only provides **2021-2023 data**, making it useless for live betting in 2025.

**What to use instead:**
- **Injuries:** apifootball.com (180 req/hour)
- **H2H:** football-data.org (already using) + apifootball.com backup
- **Team Form:** apifootball.com

**See:** [sources/NON_VIABLE_SOURCES.md](sources/NON_VIABLE_SOURCES.md) for full explanation of the fraud.

---

## Next Steps

1. **Complete all registrations** above and test each API
2. **Verify apifootball.com returns 2024-2025 data** (unlike api-football.com)
3. **Implementation tasks** will be incorporated into main task breakdown (see [BATCH_PLAN.md](../../../status/pre_gambling_flow/BATCH_PLAN.md))
4. **Tool development** will reference source documentation from [sources/](sources/) directory

---

## See Also

- [executive_summary.md](executive_summary.md) - Full data stack overview and status
- [verticals/](verticals/) - Requirements for each data vertical
- [sources/](sources/) - Detailed API documentation with code examples
- [sources/NON_VIABLE_SOURCES.md](sources/NON_VIABLE_SOURCES.md) - Fraudulent sources to avoid
- [PRE_GAMBLING_OPTIMIZED_FLOW_TASKS.md](../../../status/pre_gambling_flow/PRE_GAMBLING_OPTIMIZED_FLOW_TASKS.md) - Main task breakdown
