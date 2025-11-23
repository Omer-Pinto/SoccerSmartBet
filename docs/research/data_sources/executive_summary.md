# SoccerSmartBet - Data Sources Executive Summary

**Date:** 2025-11-22  
**Researcher:** Football Research Droid  
**Status:** Updated per PR #2 review feedback

---

## 📊 Recommended Data Stack

| Vertical | Source | Status | Ease of Use | Notes |
|----------|--------|--------|-------------|-------|
| **Fixtures** | football-data.org | ✅ Enabled | 🟢 Free API + Key | 12 competitions, 10 req/min |
| **Odds** | The Odds API | ✅ Enabled | 🟢 Free API + Key | 500 credits/month, decimal format |
| **Injuries/Suspensions** | API-Football | ✅ Enabled | 🟢 Free API + Key | Included in free tier (100 req/day) |
| **H2H Stats** | API-Football | ✅ Enabled | 🟢 Free API + Key | Same as injuries source |
| **Weather** | Open-Meteo | ✅ Enabled | 🟢 Free, No Key | 10k req/day, no signup needed |
| **Team News** | Scraping | 🔴 Disabled | 🔴 Scraping | Paid APIs only, scrapers too fragile |
| **Player Form** | API-Football | 🟡 Limited | 🟢 Free API + Key | Basic stats only (goals/assists) |
| **Morale/Coach News** | Scraping | 🔴 Disabled | 🔴 Scraping | No structured APIs available |
| **Rotation Policy** | Manual/Scraping | 🔴 Disabled | 🔴 Scraping | Coach statements only, unreliable |

**Legend:**
- ✅ **Enabled**: Ready to implement with free API
- 🟡 **Limited**: Available but with reduced functionality
- 🔴 **Disabled**: Scraping-only or paid-only, not implemented

**Ease of Use:**
- 🟢 Free service with simple API (free tier or no key required)
- 🟡 Free service with limits (requires API key from registration)
- 🔴 Scraping required or paid-only service

---

## 🎯 Primary Sources (One Per Vertical)

### Fixtures
- **Source:** [football-data.org](sources/football-data.org.md)
- **Why:** 12 major competitions, reliable, well-documented

### Odds
- **Source:** [The Odds API](sources/the-odds-api.md)
- **Why:** Free 500 credits/month, decimal odds (Israeli format), stable API

### Injuries & Suspensions
- **Source:** [API-Football Sidelined Endpoint](sources/api-football.md#sidelined)
- **Why:** Included in free tier, comprehensive data

### H2H Statistics
- **Source:** [API-Football H2H Endpoint](sources/api-football.md#h2h)
- **Why:** Same API as injuries, efficient quota usage

### Weather
- **Source:** [Open-Meteo](sources/open-meteo.md)
- **Why:** No API key required, 10k requests/day free

---

## ⚠️ Key Concerns

### Enabled Sources
1. **Rate Limits:** API-Football limited to 100 requests/day on free tier
   - Mitigation: Cache data, optimize requests
2. **The Odds API Credits:** 500 credits/month = ~16 days at 30 games/day
   - Mitigation: Request odds only for filtered games (3-5/day), not all fixtures
3. **League Coverage:** football-data.org only covers 12 competitions
   - Mitigation: Acceptable for MVP, matches project scope

### Disabled Verticals
1. **Team News (scraping-based):** BBC, ESPN, Sky Sports all require scraping
   - Risk: Site changes break scrapers, legal ToS concerns
   - Decision: Disable for now, revisit if MCP tools mature
2. **Morale/Coach News:** No structured APIs, news scraping only
   - Decision: Disable, rely on injury/suspension data only
3. **Rotation Policy:** Coach statements scraped from news sites
   - Decision: Disable, too unreliable for betting decisions

---

## 📝 Next Steps for Implementation

### 1. API Registrations Required

| Service | Registration URL | API Key Needed | .env Variable Name |
|---------|------------------|----------------|-------------------|
| football-data.org | https://www.football-data.org/client/register | Yes (free) | `FOOTBALL_DATA_API_KEY` |
| The Odds API | https://the-odds-api.com/ | Yes (free) | `ODDS_API_KEY` |
| API-Football | https://dashboard.api-football.com/register | Yes (free) | `API_FOOTBALL_KEY` |
| Open-Meteo | N/A | No | N/A |

**Instructions:** 
- Sign up for each service above
- Save API keys to `.env` file using variable names in table
- See individual source docs for detailed setup: [sources/](sources/)

### 2. Priority Implementation Order
1. ✅ Fixtures fetcher (football-data.org) - foundation for game selection
2. ✅ Odds fetcher (The Odds API) - critical for filtering games
3. ✅ Weather fetcher (Open-Meteo) - cancellation risk assessment
4. ✅ Injuries/Suspensions fetcher (API-Football) - team strength evaluation
5. ✅ H2H fetcher (API-Football) - historical context

### 3. Testing & Validation
- Test all APIs with sample requests (see [tasks.md](tasks.md))
- Verify rate limits don't block daily workflow
- Implement fallback logic for API failures
- Monitor quota usage in production

---

## 📚 Documentation Structure

- **[executive_summary.md](executive_summary.md)** (this file): Overview, status table, next steps
- **[verticals/](verticals/)**: One file per data vertical (fixtures, odds, injuries, etc.)
- **[sources/](sources/)**: One file per data source with code examples and API details
- **[data_sources_original.md](../data_sources_original.md)**: Full original research (backup reference)
- **[tasks.md](tasks.md)**: Action items for API registrations

---

## 🔄 Changes from Original Research

1. **Structured documentation**
   - Split 900-line file into focused, consumable docs
   - Separated source details from vertical overviews
   - Moved code examples to source-specific files

2. **Disabled scraping-based verticals**
   - Team news (BBC, ESPN scraping)
   - Morale/coach news
   - Rotation policy
   - Reason: Too fragile, legal concerns, not critical for MVP

3. **No paid services**
   - Sportmonks team news (paid only)
   - Any enterprise APIs
   - Reason: LLM costs only, per project constraints

---

**See:** [verticals/](verticals/) for detailed vertical analysis and [sources/](sources/) for API documentation.
