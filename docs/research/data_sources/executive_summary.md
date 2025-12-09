# SoccerSmartBet - Data Sources Executive Summary

**Date:** 2025-11-25  
**Researcher:** Football Research Droid  
**Status:** Updated - api-football.com fraud corrected, viable alternatives added

---

## 🛠️ Currently Implemented Tools (Batch 5 - Complete)

**Status:** ✅ 8 tools implemented and tested  
**Location:** `src/soccersmartbet/pre_gambling_flow/tools/`

| Tool | Type | Vertical | Source | Status |
|------|------|----------|--------|--------|
| `fetch_h2h` | Game | H2H History | football-data.org | ✅ Working |
| `fetch_venue` | Game | Venue Info | apifootball.com | ✅ Working |
| `fetch_weather` | Game | Weather | Open-Meteo + Nominatim | ✅ Working |
| `fetch_odds` | Game | Betting Lines | The Odds API | ✅ Working |
| `fetch_form` | Team | Recent Form | apifootball.com | ✅ Working |
| `fetch_injuries` | Team | Injuries | apifootball.com | ✅ Working |
| `fetch_key_players_form` | Team | Player Stats | apifootball.com | ✅ Working |
| `calculate_recovery_time` | Team | Recovery Days | apifootball.com | ✅ Working |

**Tool Interfaces:**
- **Game tools** (4): Accept `(home_team, away_team)` - called once per match
- **Team tools** (4): Accept `(team_name)` - called twice per match (once per team)
- **Total calls per match:** 12 (4 game + 4 home + 4 away)

**Key Features:**
- ✅ NO hardcoded league IDs - tools search across all major leagues automatically
- ✅ Works for Premier League, La Liga, Serie A, Bundesliga, Ligue 1, Champions League
- ✅ Weather uses geocoding API - works for ANY city worldwide (not just English cities)
- ✅ Comprehensive integration test - validates all 12 tool calls for user-provided teams

**Not Implemented (Future Batches):**
- ❌ Team news (requires scraping)
- ❌ Suspension tracking (API returns empty data)
- ❌ Returning players (API cannot track status changes)

---

## 📊 Recommended Data Stack (Research Reference)

| Vertical | Source | Status | Ease of Use | Notes |
|----------|--------|--------|-------------|-------|
| **Fixtures** | football-data.org | ✅ Enabled | 🟢 Free API + Key | 12 competitions, 10 req/min |
| **Odds** | The Odds API | ✅ Enabled | 🟢 Free API + Key | 500 credits/month, decimal format |
| **Injuries/Suspensions** | apifootball.com | ✅ Enabled | 🟢 Free API + Key | 180 req/hour (6,480/day), player injury tracking |
| **H2H Stats** | football-data.org | ✅ Enabled | 🟢 Free API + Key | /matches/{id}/head2head endpoint |
| **H2H Stats (Backup)** | apifootball.com | ✅ Enabled | 🟢 Free API + Key | Event filtering for H2H matches |
| **Team Form** | apifootball.com | ✅ Enabled | 🟢 Free API + Key | Recent matches per team |
| **Weather** | Open-Meteo | ✅ Enabled | 🟢 Free, No Key | 10k req/day, no signup needed |
| **Team News** | Scraping | 🔴 Disabled | 🔴 Scraping | Paid APIs only, scrapers too fragile |
| **Player Form** | apifootball.com | 🟡 Limited | 🟢 Free API + Key | Basic stats (goals/assists/games played) |
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

## 🚫 CRITICAL: api-football.com is FRAUDULENT

**⚠️ DO NOT USE api-football.com (with hyphen)**

**Initial research error:** Task 0.1 initially recommended api-football.com for injuries, suspensions, and H2H statistics.

**Discovered fraud:** api-football.com's **free tier only provides 2021-2023 data**, making it completely useless for live betting in 2025.

**Corrected sources:**
- ✅ **apifootball.com** (NO hyphen) - legitimate free API, 180 req/hour
- ✅ **football-data.org** (already in use) - expanded to H2H
- ✅ **TheSportsDB.com** (backup) - free tier available

See [NON_VIABLE_SOURCES.md](sources/NON_VIABLE_SOURCES.md) for full details on the fraud.

---

## 🎯 Primary Sources (One Per Vertical)

### Fixtures
- **Source:** [football-data.org](sources/football-data.org.md)
- **Why:** 12 major competitions, reliable, well-documented

### Odds
- **Source:** [The Odds API](sources/the-odds-api.md)
- **Why:** Free 500 credits/month, decimal odds (Israeli format), stable API

### Injuries & Suspensions
- **Source:** [apifootball.com](sources/apifootball.md)
- **Why:** 180 req/hour FREE, `player_injured` field in team data, 6,480 req/day capacity
- **Backup:** TheSportsDB.com (100 req/min free)

### H2H Statistics
- **Source:** [football-data.org /matches/{id}/head2head endpoint](sources/football-data.org.md)
- **Why:** Already in use for fixtures, simple H2H subresource
- **Backup:** [apifootball.com](sources/apifootball.md) - filter events by both teams

### Team Form (Recent Matches)
- **Source:** [apifootball.com](sources/apifootball.md)
- **Why:** Get last N matches per team via events endpoint
- **Backup:** football-data.org /teams/{id}/matches endpoint

### Weather
- **Source:** [Open-Meteo](sources/open-meteo.md)
- **Why:** No API key required, 10k requests/day free

---

## ⚠️ Key Concerns

### Enabled Sources
1. **Rate Limits:** apifootball.com provides 180 req/hour (6,480/day) - more than sufficient
   - Mitigation: Cache data, ~20-30 requests/day expected
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
| apifootball.com | https://apifootball.com/ | Yes (free) | `APIFOOTBALL_API_KEY` |
| Open-Meteo | N/A | No | N/A |

**Instructions:** 
- Sign up for each service above
- Save API keys to `.env` file using variable names in table
- See individual source docs for detailed setup: [sources/](sources/)

### 2. Priority Implementation Order
1. ✅ Fixtures fetcher (football-data.org) - foundation for game selection
2. ✅ Odds fetcher (The Odds API) - critical for filtering games
3. ✅ Weather fetcher (Open-Meteo) - cancellation risk assessment
4. ✅ Injuries/Suspensions fetcher (apifootball.com) - team strength evaluation
5. ✅ H2H fetcher (football-data.org + apifootball.com backup) - historical context
6. ✅ Team form fetcher (apifootball.com) - recent performance

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
- **[sources/NON_VIABLE_SOURCES.md](sources/NON_VIABLE_SOURCES.md)**: Fraudulent/paid sources to avoid
- **[data_sources_original.md](../data_sources_original.md)**: Full original research (backup reference)
- **[tasks.md](tasks.md)**: Action items for API registrations

---

## 🔄 Changes from Previous Version

### 1. **CRITICAL FIX: api-football.com Fraud Discovered**
   - **Removed:** api-football.com (free tier limited to 2021-2023 data)
   - **Added:** apifootball.com (legitimate 180 req/hour FREE API)
   - **Added:** football-data.org H2H endpoint (already using this API)
   - **Added:** NON_VIABLE_SOURCES.md documenting the fraud

### 2. **New Source: apifootball.com**
   - Replaces api-football.com for injuries, suspensions, H2H, team form
   - 180 req/hour (6,480 req/day) vs api-football.com's fraudulent 100 req/day
   - Simpler API, no nested authentication headers
   - See [sources/apifootball.md](sources/apifootball.md)

### 3. **Expanded football-data.org Usage**
   - Already using for fixtures
   - Now also using `/matches/{id}/head2head` endpoint for H2H
   - Can also use `/teams/{id}/matches` for team form backup

### 4. **Disabled scraping-based verticals**
   - Team news (BBC, ESPN scraping)
   - Morale/coach news
   - Rotation policy
   - Reason: Too fragile, legal concerns, not critical for MVP

### 5. **No paid services**
   - Sportmonks team news (paid only)
   - Any enterprise APIs
   - Reason: LLM costs only, per project constraints

---

## 🎓 Lessons Learned

1. **Always verify free tier date ranges** - api-football.com's 2021-2023 limitation was not obvious
2. **Test API endpoints before committing** - sample requests would have revealed the fraud earlier
3. **Read community forums** - official docs often hide critical limitations
4. **Beware of "free tier" marketing** - many services offer trial-only, not sustained free access
5. **Prioritize APIs with proven longevity** - football-data.org has been free for years

---

## 📊 Final Data Stack Summary

**Core APIs (FREE, Sustained):**
1. **football-data.org** - Fixtures, H2H
2. **The Odds API** - Betting lines
3. **apifootball.com** - Injuries, suspensions, H2H backup, team form
4. **Open-Meteo** - Weather

**Total API Keys Needed:** 3 (football-data.org, The Odds API, apifootball.com)

**Estimated Daily Requests:**
- Fixtures: 1 request/day
- Odds: 3-5 requests/day (filtered games only)
- Weather: 3-5 requests/day
- Injuries: 6-10 requests/day (2 per game)
- H2H: 3-5 requests/day (1 per game)
- Team Form: 6-10 requests/day (2 per game)
- **Total:** ~25-40 requests/day across all APIs

**Well under all rate limits.**

---

**See:** [verticals/](verticals/) for detailed vertical analysis and [sources/](sources/) for API documentation.

**⚠️ IMPORTANT:** Do NOT confuse **apifootball.com** (legitimate, no hyphen) with **api-football.com** (fraudulent, with hyphen).
