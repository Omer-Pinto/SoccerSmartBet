# SoccerSmartBet - Data Sources Executive Summary

**Date:** 2025-11-25  
**Researcher:** Football Research Droid  
**Status:** Updated - api-football.com fraud corrected, viable alternatives added

---

## 🛠️ Currently Implemented Tools (Batch 6 - TheSportsDB Migration)

**Status:** ✅ 8 tools implemented (migrated from APIfootball.com to TheSportsDB)  
**Date Updated:** 2025-12-11  
**Location:** `src/soccersmartbet/pre_gambling_flow/tools/`

| Tool | Type | Vertical | Source | Status |
|------|------|----------|--------|--------|
| `fetch_h2h` | Game | H2H History | football-data.org | ✅ Working |
| `fetch_venue` | Game | Venue Info | **TheSportsDB** | ✅ Migrated |
| `fetch_weather` | Game | Weather | Open-Meteo + Nominatim | ✅ Working |
| `fetch_odds` | Game | Betting Lines | The Odds API | ✅ Working |
| `fetch_form` | Team | Recent Form | football-data.org | ✅ Working |
| `fetch_injuries` | Team | Injuries | **TheSportsDB** | ⚠️ Match-specific |
| `fetch_league_position` | Team | **League Standing** | **TheSportsDB** | ✅ **NEW!** |
| `calculate_recovery_time` | Team | Recovery Days | football-data.org | ✅ Working |

**Tool Interfaces:**
- **Game tools** (4): Accept `(home_team, away_team)` - called once per match
- **Team tools** (4): Accept `(team_name)` - called twice per match (once per team)
- **Total calls per match:** 12 (4 game + 4 home + 4 away)

**Key Features:**
- ✅ NO hardcoded league IDs - tools search across all major leagues automatically
- ✅ Works for Premier League, La Liga, Serie A, Bundesliga, Ligue 1, Champions League
- ✅ Weather uses geocoding API - works for ANY city worldwide (not just English cities)
- ✅ Comprehensive integration test - validates all 12 tool calls for user-provided teams

**Tool Changes (Batch 6):**
- ✅ **Added:** `fetch_league_position` - Team's league position, points, W/D/L record (TheSportsDB)
  - ⚠️ **Limitation:** Free tier only returns top 5 teams per league
- ❌ **Removed:** `fetch_key_players_form` - No free API available for player goals/assists stats
- ✅ **Migrated:** `fetch_venue` → TheSportsDB `/searchteams.php` (fixed lookupteam bug)
- ✅ **Migrated:** `fetch_weather` → Uses `fetch_venue` for city, then Open-Meteo (no APIfootball dependency)
- ✅ **Migrated:** `fetch_form` → football-data.org (was still using APIfootball)
- ✅ **Migrated:** `calculate_recovery_time` → Uses `fetch_form` (was still using APIfootball)
- ⚠️ **Migrated:** `fetch_injuries` → TheSportsDB `/eventsnext` + `/lookuplineup` (match-specific, may return empty if no upcoming matches)

**Not Implemented (By Design):**
- ❌ Team news (requires scraping - too fragile)
- ❌ Player statistics (goals/assists) - No free API available (removed in Batch 6)
- ❌ Suspension tracking - TheSportsDB doesn't provide this
- ❌ Returning players - Cannot track status changes with free APIs

---

## 📊 Current Data Stack (As of Batch 6)

| Vertical | Source | Status | Rate Limit | Notes |
|----------|--------|--------|------------|-------|
| **Fixtures** | football-data.org | ✅ Active | 10 req/min | 12 competitions |
| **Odds** | The Odds API | ✅ Active | 500 credits/month | Decimal format |
| **H2H Stats** | football-data.org | ✅ Active | 10 req/min | /matches/{id}/head2head |
| **Weather** | Open-Meteo | ✅ Active | 10k req/day | No API key needed |
| **Venue Info** | **TheSportsDB** | ✅ Active | 100 req/min | Migrated in Batch 6 |
| **Injuries** | **TheSportsDB** | ⚠️ Limited | 100 req/min | Match-specific only (lineup-based) |
| **Team Form** | football-data.org | ✅ Active | 10 req/min | Last 5-10 matches |
| **League Position** | **TheSportsDB** | ⚠️ **NEW** | 100 req/min | **Free tier: Top 5 teams only** |
| **Recovery Time** | Derived | ✅ Active | N/A | Calculated from match dates |
| **Player Stats** | N/A | ❌ **Removed** | N/A | No free API available |
| **Team News** | N/A | 🔴 Disabled | N/A | Scraping too fragile |
| **Suspensions** | N/A | 🔴 Disabled | N/A | Not available in free APIs |

**Legend:**
- ✅ **Enabled**: Ready to implement with free API
- 🟡 **Limited**: Available but with reduced functionality
- 🔴 **Disabled**: Scraping-only or paid-only, not implemented

**Ease of Use:**
- 🟢 Free service with simple API (free tier or no key required)
- 🟡 Free service with limits (requires API key from registration)
- 🔴 Scraping required or paid-only service

---

## 🚫 CRITICAL: APIfootball.com Trial Expired

**⚠️ APIfootball.com is NO LONGER USED (trial expired Dec 14, 2025)**

**Previous usage:** Batch 5 used APIfootball.com for venue, injuries, team form, and player stats.

**Migration (Batch 6):** All tools migrated to **TheSportsDB** (100% free, no trial):
- ✅ **TheSportsDB.com** - Primary source for venue, injuries, league position
- ✅ **football-data.org** - Team form, H2H (already in use)
- ❌ **Player stats** - Removed (no free API available)

**Other sources to avoid:**
- ❌ **api-football.com** (with hyphen) - Free tier only provides 2021-2023 data

See [apifootball_alternatives_report.md](../apifootball_alternatives_report.md) for full migration research.

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

## 📊 Final Data Stack Summary (Batch 6)

**Core APIs (FREE, Sustained):**
1. **football-data.org** - Fixtures, H2H, Team Form
2. **The Odds API** - Betting lines
3. **TheSportsDB** - Venue, Injuries (match-specific), League Position
4. **Open-Meteo** - Weather (no key needed)

**Total API Keys Needed:** 3 
- `FOOTBALL_DATA_API_KEY`
- `ODDS_API_KEY`
- `THESPORTSDB_API_KEY` (default: "3" for free test key)

**Estimated Daily Requests (3-5 games/day):**
- Fixtures: 1 request/day (football-data.org)
- Odds: 3-5 requests/day (The Odds API - filtered games only)
- Weather: 3-5 requests/day (Open-Meteo)
- Venue: 3-5 requests/day (TheSportsDB)
- Injuries: 3-5 requests/day (TheSportsDB - 1 per match)
- League Position: 2-4 requests/day (TheSportsDB - 1 per league, not per team!)
- H2H: 3-5 requests/day (football-data.org)
- Team Form: 6-10 requests/day (football-data.org - 2 per game)
- **Total:** ~25-40 requests/day across all APIs

**Rate Limit Status:** ✅ Well under all limits
- football-data.org: 10/min (using ~15/day)
- The Odds API: 500/month (using ~150/month)
- TheSportsDB: 100/min (using ~15/day)
- Open-Meteo: 10k/day (using ~5/day)

---

**See:**  
- [apifootball_alternatives_report.md](../apifootball_alternatives_report.md) - Full migration research (Batch 6)
- [verticals/](verticals/) - Detailed vertical analysis (Batch 2-5 research)
- [sources/](sources/) - API documentation for all sources

**⚠️ MIGRATION NOTES:**
- APIfootball.com trial expired Dec 14, 2025 - **NO LONGER USED**
- All tools migrated to TheSportsDB (100% free, no trial)
- Player stats tool **REMOVED** - no free API available
- League position tool **ADDED** - new feature from TheSportsDB
