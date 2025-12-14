# Non-Viable Data Sources

This document catalogs data sources that were researched but found to be **unsuitable** for SoccerSmartBet. Kept for reference to avoid re-researching the same sources.

---

## ❌ api-football.com (FRAUDULENT SERVICE)

**Website:** https://www.api-football.com  
**Status:** 🚫 **FRAUDULENT - DO NOT USE**  
**Reason:** Free tier only provides **2021-2023 historical data**, making it completely useless for live betting in 2025

### What Went Wrong

During initial research (Task 0.1), api-football.com appeared to be a comprehensive FREE API offering:
- Injuries and suspensions
- Head-to-head statistics
- Team statistics
- 100 requests/day free tier

**The Fraud:**  
Only after deeper investigation was it discovered that the **free tier is limited to 2021-2023 data**. This means:
- ❌ No 2024-2025 season data
- ❌ No current injuries
- ❌ No recent matches for team form
- ❌ Completely useless for live betting

### Why This Was Misleading

1. **Marketing claims "1,200+ leagues and cups"** - but doesn't mention free tier is 3+ years old
2. **Documentation shows 2025 examples** - but these require paid plans
3. **Free tier advertised as "100 req/day"** - technically true, but for useless historical data
4. **No clear disclosure** - must dig through forums/community to find this limitation

### What We Replaced It With

| Vertical | Original (Fraud) | Replacement (Viable) |
|----------|------------------|---------------------|
| Injuries/Suspensions | api-football.com | **apifootball.com** (180 req/hour FREE) |
| H2H Statistics | api-football.com | **football-data.org** (already in use) + **apifootball.com** |
| Team Form | api-football.com | **apifootball.com** + **football-data.org** |

**Note:** **apifootball.com** (no hyphen) was recommended as replacement, but has since EXPIRED (see below).

---

## ❌ apifootball.com (TRIAL EXPIRED)

**Website:** https://apifootball.com
**Status:** 🚫 **TRIAL EXPIRED - DO NOT USE**
**Reason:** Free trial period has ended, no longer usable

### What Went Wrong

apifootball.com was recommended in Batch 5 as a legitimate replacement for api-football.com. It worked well during development with:
- 180 requests/hour FREE tier
- Current 2024-2025 data
- Injuries, team form, venue data

**The Problem:**
The "free tier" was actually a **trial period** that has now EXPIRED. The API no longer returns data without a paid subscription.

### What We Replaced It With

| Vertical | Original (Expired) | Replacement (Viable) |
|----------|-------------------|---------------------|
| Team Form | apifootball.com | **FotMob (mobfot)** - NO rate limits, NO API key |
| Injuries | apifootball.com | **FotMob (mobfot)** |
| Venue | apifootball.com | **FotMob (mobfot)** |
| Recovery Time | apifootball.com | **FotMob (mobfot)** |

---

## ❌ TheSportsDB (LIMITED DATA)

**Website:** https://www.thesportsdb.com
**Status:** 🚫 **LIMITED FREE TIER - DO NOT USE FOR STANDINGS**
**Reason:** Free tier only returns TOP 5 teams in league standings

### What Went Wrong

TheSportsDB was considered as a backup source for league standings. However, the free tier has a critical limitation:
- **Only returns the TOP 5 teams** in any league table
- Cannot get full 20-team standings
- Useless for `fetch_league_position` tool (need to know position of ANY team)

### Example Problem

```python
# TheSportsDB free tier response for Premier League standings:
[
    {"intRank": 1, "strTeam": "Liverpool"},
    {"intRank": 2, "strTeam": "Chelsea"},
    {"intRank": 3, "strTeam": "Arsenal"},
    {"intRank": 4, "strTeam": "Nottingham Forest"},
    {"intRank": 5, "strTeam": "Manchester City"}
]
# Missing: Teams ranked 6-20 (e.g., Aston Villa, Brighton, Newcastle, etc.)
```

### What We Use Instead

**FotMob (mobfot)** returns ALL 20 teams in league standings.

---

## ⚠️ football-data.org (RATE LIMITED)

**Website:** https://www.football-data.org
**Status:** 🟡 **USE WITH CAUTION - RATE LIMITS**
**Reason:** 10 req/min limit caused 429 errors in Batch 5

### What Went Wrong

football-data.org was used heavily in Batch 5 for multiple tools. However:
- **10 requests/minute limit** is too low for multi-tool usage
- **Many 429 (rate limit) errors** during integration testing
- Especially problematic when running all 12 tools per match

### Current Usage

football-data.org is still used, but **only for H2H endpoint** where rate limits are acceptable:
- 1 H2H request per match (3-5/day)
- Well under 10 req/min limit when used alone

All other team-related data moved to **FotMob (mobfot)** which has NO rate limits.

---

## ⚠️ Sportmonks

**Website:** https://www.sportmonks.com  
**Status:** 🟡 **PAID ONLY** (14-day free trial)  
**Reason:** No sustained free tier

### What They Offer

- Comprehensive football data (2,500+ leagues)
- Injuries, suspensions, lineups
- Real-time updates
- Well-documented API

### Why Not Viable

- **14-day free trial only** - not sustainable for production
- **Paid plans start at $50+/month** - exceeds "LLM costs only" constraint
- **No free tier for core features** - team news requires paid plan

### Could Be Revisited

If budget constraints change, Sportmonks could be a solid paid alternative.

---

## ⚠️ StatPal API

**Website:** https://statpal.io  
**Status:** 🟡 **PRICING UNCLEAR**  
**Reason:** No explicit free tier

### What They Offer

- Real-time soccer data
- 30-second refresh rate
- Injuries and match statistics

### Why Not Viable

- **No clear free tier** - website doesn't explicitly state free access
- **Appears to be paid service** - requires contact for pricing
- **Better free alternatives exist** - apifootball.com and football-data.org

---

## ⚠️ Enetpulse

**Website:** https://enetpulse.com  
**Status:** 🟡 **PAID AFTER TRIAL**  
**Reason:** Free testing only, then paid

### What They Offer

- Real-time injury and suspension data
- Player and team-level data
- API or XML delivery

### Why Not Viable

- **Free testing only** - not a sustained free tier
- **Enterprise pricing** - appears to target large organizations
- **Better free alternatives exist** - apifootball.com

---

## ⚠️ SoccersAPI

**Website:** https://soccersapi.com  
**Status:** 🟡 **15-DAY FREE TRIAL**  
**Reason:** Trial-only, then paid

### What They Offer

- 800+ leagues and tournaments
- Player statistics, lineups
- Live scores and betting odds

### Why Not Viable

- **15-day trial only** - not sustainable
- **Paid plans required** - pricing not disclosed
- **Better free alternatives exist** - apifootball.com, football-data.org

---

## ⚠️ SportDevs

**Website:** https://sportdevs.com  
**Status:** 🟡 **PAID SERVICE**  
**Reason:** No free tier

### What They Offer

- Ultra-low latency football data
- Multi-language support
- Real-time injuries and match incidents

### Why Not Viable

- **No free tier** - appears to be paid only
- **Affordable plans advertised** - but still paid
- **Better free alternatives exist** - apifootball.com

---

## ⚠️ injuriesandsuspensions.com

**Website:** https://injuriesandsuspensions.com  
**Status:** 🟡 **SUBSCRIPTION REQUIRED**  
**Reason:** Paid subscription for API access

### What They Offer

- Comprehensive injury and suspension tracking
- Multiple league coverage
- API feed for developers

### Why Not Viable

- **Subscription required** - no free tier for API
- **Website may offer limited free data** - but API is paid
- **Better free alternatives exist** - apifootball.com

---

## Summary: Why These Failed

| Source | Main Issue | Free Tier? | Replacement |
|--------|-----------|------------|-------------|
| **api-football.com** | **2021-2023 data only** | ❌ Fraudulent | **FotMob (mobfot)** |
| **apifootball.com** | **Trial EXPIRED** | ❌ Expired | **FotMob (mobfot)** |
| **TheSportsDB** | **Top 5 teams only** | ⚠️ Limited | **FotMob (mobfot)** |
| **football-data.org** | **Rate limits (10/min)** | ⚠️ Limited | H2H only, **FotMob** for rest |
| Sportmonks | 14-day trial only | ❌ No | FotMob (mobfot) |
| StatPal | No clear free tier | ❌ Unknown | FotMob (mobfot) |
| Enetpulse | Free testing only | ❌ No | FotMob (mobfot) |
| SoccersAPI | 15-day trial only | ❌ No | FotMob (mobfot) |
| SportDevs | No free tier | ❌ No | FotMob (mobfot) |
| injuriesandsuspensions.com | Subscription required | ❌ No | FotMob (mobfot) |

**Pattern:** Most "free" football APIs are trial-only, paid-only, or have severe limitations. **FotMob (mobfot)** is the best option with NO rate limits and NO API key required.

---

## Lessons Learned

1. **Verify free tier limits EARLY** - don't assume "free plan" means sustained free access
2. **Check date ranges for free data** - api-football.com's 2021-2023 limitation was hidden
3. **Test API endpoints before committing** - always verify with sample requests
4. **Read community forums** - official docs often hide limitations
5. **"Free tier" often means "trial period"** - apifootball.com's free tier was actually a trial
6. **Rate limits matter at scale** - football-data.org's 10 req/min blocked multi-tool usage
7. **Test standings endpoints thoroughly** - TheSportsDB only returns top 5 teams
8. **Unofficial APIs can be more reliable** - FotMob (mobfot) has no rate limits despite being unofficial

---

## If You're Considering a Paid API

**Decision criteria:**
1. **Cost must be << LLM costs** - SoccerSmartBet constraint is "LLM costs only"
2. **Must provide critical data unavailable for free** - injuries/H2H/form are now covered by free sources
3. **Must have clear ROI** - e.g., significantly better data quality or coverage

**Current status:** No paid APIs justified - free sources (FotMob, football-data.org, The Odds API, Open-Meteo) cover all critical verticals.

---

**Last Updated:** 2025-12-14
**Researcher:** Football Research Droid (Batch 6 update)
