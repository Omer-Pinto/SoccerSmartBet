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

**Note:** **apifootball.com** (no hyphen) is a completely different, legitimate service.

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
| **api-football.com** | **2021-2023 data only** | ❌ Fraudulent | **apifootball.com** |
| Sportmonks | 14-day trial only | ❌ No | apifootball.com |
| StatPal | No clear free tier | ❌ Unknown | apifootball.com |
| Enetpulse | Free testing only | ❌ No | apifootball.com |
| SoccersAPI | 15-day trial only | ❌ No | apifootball.com |
| SportDevs | No free tier | ❌ No | apifootball.com |
| injuriesandsuspensions.com | Subscription required | ❌ No | apifootball.com |

**Pattern:** Most "free" football APIs are trial-only or paid-only. **apifootball.com** and **football-data.org** are rare exceptions with sustained free tiers.

---

## Lessons Learned

1. **Verify free tier limits EARLY** - don't assume "free plan" means sustained free access
2. **Check date ranges for free data** - api-football.com's 2021-2023 limitation was hidden
3. **Test API endpoints before committing** - always verify with sample requests
4. **Read community forums** - official docs often hide limitations
5. **Prioritize APIs with proven free tiers** - football-data.org has been free for years

---

## If You're Considering a Paid API

**Decision criteria:**
1. **Cost must be << LLM costs** - SoccerSmartBet constraint is "LLM costs only"
2. **Must provide critical data unavailable for free** - injuries/H2H/form are now covered by free sources
3. **Must have clear ROI** - e.g., significantly better data quality or coverage

**Current status:** No paid APIs justified - free sources (apifootball.com, football-data.org, The Odds API, Open-Meteo) cover all critical verticals.

---

**Last Updated:** 2025-11-25  
**Researcher:** Football Research Droid
