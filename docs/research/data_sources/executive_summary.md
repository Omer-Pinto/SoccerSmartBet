# SoccerSmartBet - Data Sources Executive Summary

**Date:** 2025-12-14
**Researcher:** Football Research Droid
**Status:** Updated - Batch 6 complete, migrated to FotMob API (free, no rate limits)

---

## 🛠️ Currently Implemented Tools (Batch 6 - Complete)

**Status:** ✅ 8 tools implemented and tested
**Location:** `src/soccersmartbet/pre_gambling_flow/tools/`

| Tool | Type | Vertical | Source | Status |
|------|------|----------|--------|--------|
| `fetch_h2h` | Game | H2H History | football-data.org | ✅ Working |
| `fetch_venue` | Game | Venue Info | FotMob API (mobfot) | ✅ Working |
| `fetch_weather` | Game | Weather | FotMob + Open-Meteo | ✅ Working |
| `fetch_odds` | Game | Betting Lines | The Odds API | ✅ Working |
| `fetch_form` | Team | Recent Form | FotMob API (mobfot) | ✅ Working |
| `fetch_injuries` | Team | Injuries | FotMob API (mobfot) | ✅ Working |
| `fetch_league_position` | Team | League Standings | FotMob API (mobfot) | ✅ Working |
| `calculate_recovery_time` | Team | Recovery Days | FotMob API (mobfot) | ✅ Working |

**Tool Interfaces:**
- **Game tools** (4): Accept `(home_team, away_team)` - called once per match
- **Team tools** (4): Accept `(team_name)` - called twice per match (once per team)
- **Total calls per match:** 12 (4 game + 4 home + 4 away)

**Key Features:**
- ✅ NO hardcoded league IDs - tools search across all major leagues automatically
- ✅ Works for Premier League, La Liga, Serie A, Bundesliga, Ligue 1, Champions League, Eredivisie, Primeira Liga
- ✅ Weather uses geocoding API - works for ANY city worldwide (not just English cities)
- ✅ Comprehensive integration test - validates all 12 tool calls for user-provided teams
- ✅ **NEW:** FotMob API via mobfot package - NO rate limits, NO API key required

**Not Implemented (Future Batches):**
- ❌ Team news (requires scraping)
- ❌ Suspension tracking (API returns empty data)
- ❌ Returning players (API cannot track status changes)
- ❌ Player stats/form (no free API for individual player data)

---

## 📊 Recommended Data Stack (Research Reference)

| Vertical | Source | Status | Ease of Use | Notes |
|----------|--------|--------|-------------|-------|
| **Fixtures** | football-data.org | ✅ Enabled | 🟢 Free API + Key | 12 competitions, 10 req/min |
| **Odds** | The Odds API | ✅ Enabled | 🟢 Free API + Key | 500 credits/month, decimal format |
| **H2H Stats** | football-data.org | ✅ Enabled | 🟢 Free API + Key | /matches/{id}/head2head endpoint |
| **Team Form** | FotMob (mobfot) | ✅ Enabled | 🟢 Free, No Key | Recent W/D/L from teamForm |
| **League Standings** | FotMob (mobfot) | ✅ Enabled | 🟢 Free, No Key | ALL teams in league (not top 5) |
| **Injuries** | FotMob (mobfot) | ✅ Enabled | 🟢 Free, No Key | Via match lineup.unavailable |
| **Venue Info** | FotMob (mobfot) | ✅ Enabled | 🟢 Free, No Key | Stadium name, city, capacity |
| **Recovery Time** | FotMob (mobfot) | ✅ Enabled | 🟢 Free, No Key | Via lastMatch data |
| **Weather** | Open-Meteo | ✅ Enabled | 🟢 Free, No Key | 10k req/day, no signup needed |
| **Team News** | Scraping | 🔴 Disabled | 🔴 Scraping | Paid APIs only, scrapers too fragile |
| **Player Form** | N/A | 🔴 Disabled | 🔴 No Free API | Free APIs don't provide individual player stats |
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

## 🚫 NON-VIABLE SOURCES

### api-football.com (FRAUDULENT)
**⚠️ DO NOT USE api-football.com (with hyphen)**
- Free tier only provides 2021-2023 data, useless for live betting in 2025

### apifootball.com (EXPIRED TRIAL)
**⚠️ DO NOT USE apifootball.com (no hyphen)**
- Was recommended in Batch 5, trial period has EXPIRED
- football-data.org had severe 429 rate limit errors (10 req/min was insufficient)

### TheSportsDB.com (LIMITED)
**⚠️ DO NOT USE TheSportsDB for standings**
- Free tier only returns TOP 5 teams in league standings
- Cannot get full 20-team table needed for league position tool

**Corrected sources (Batch 6):**
- ✅ **FotMob API (mobfot)** - NO rate limits, NO API key, returns ALL data
- ✅ **football-data.org** - H2H only (rate limits acceptable for single endpoint)
- ✅ **The Odds API** - Odds only (500 credits/month sufficient)

See [NON_VIABLE_SOURCES.md](sources/NON_VIABLE_SOURCES.md) for full details.

---

## 🎯 Primary Sources (One Per Vertical)

### Fixtures & H2H Statistics
- **Source:** [football-data.org](sources/football-data.org.md)
- **Why:** 12 major competitions, reliable H2H endpoint
- **Note:** 10 req/min limit - use sparingly, H2H only

### Odds
- **Source:** [The Odds API](sources/the-odds-api.md)
- **Why:** Free 500 credits/month, decimal odds (Israeli format), stable API

### Team Form, Venue, Injuries, League Position, Recovery Time
- **Source:** [FotMob API (mobfot)](sources/fotmob.md)
- **Why:** NO rate limits, NO API key, returns ALL teams in standings
- **Python Package:** `mobfot` (unofficial FotMob API wrapper)
- **Data Available:**
  - Team form via `team.overview.teamForm` (W/D/L + scores)
  - Venue via `team.overview.venue.widget` (name, city, capacity)
  - Injuries via `match.lineup.unavailable` (player name, injury type)
  - League standings via `league.table` (ALL 20 teams, not just top 5)
  - Last match date via `team.overview.lastMatch` (for recovery time)

### Weather
- **Source:** [Open-Meteo](sources/open-meteo.md)
- **Why:** No API key required, 10k requests/day free
- **Note:** Uses FotMob for venue city lookup, then Open-Meteo for forecast

---

## ⚠️ Key Concerns

### Enabled Sources
1. **FotMob API (mobfot):** Unofficial API, no rate limits observed
   - Risk: Could be blocked or change without notice (unofficial)
   - Mitigation: Tested with 10+ rapid requests, no issues
   - Fallback: Would need to find alternative or implement scraping
2. **The Odds API Credits:** 500 credits/month = ~16 days at 30 games/day
   - Mitigation: Request odds only for filtered games (3-5/day), not all fixtures
3. **football-data.org Rate Limits:** 10 req/min caused 429 errors in Batch 5
   - Mitigation: Only use for H2H (1 request per match), not team data
   - FotMob handles team data where rate limits were problematic

### Disabled Verticals
1. **Team News (scraping-based):** BBC, ESPN, Sky Sports all require scraping
   - Risk: Site changes break scrapers, legal ToS concerns
   - Decision: Disable for now, revisit if MCP tools mature
2. **Player Form/Stats:** No free API provides individual player statistics
   - Decision: Replaced with league position tool (more reliable data)
3. **Morale/Coach News:** No structured APIs, news scraping only
   - Decision: Disable, rely on injury data only
4. **Rotation Policy:** Coach statements scraped from news sites
   - Decision: Disable, too unreliable for betting decisions

---

## 📝 Next Steps for Implementation

### 1. API Registrations Required

| Service | Registration URL | API Key Needed | .env Variable Name |
|---------|------------------|----------------|-------------------|
| football-data.org | https://www.football-data.org/client/register | Yes (free) | `FOOTBALL_DATA_API_KEY` |
| The Odds API | https://the-odds-api.com/ | Yes (free) | `ODDS_API_KEY` |
| FotMob (mobfot) | N/A | No | N/A |
| Open-Meteo | N/A | No | N/A |

**Instructions:**
- Sign up for football-data.org and The Odds API
- Save API keys to `.env` file using variable names in table
- Install mobfot package: `pip install mobfot`
- See individual source docs for detailed setup: [sources/](sources/)

### 2. Implementation Status (All Complete)
1. ✅ H2H fetcher (football-data.org) - historical match context
2. ✅ Odds fetcher (The Odds API) - betting lines
3. ✅ Weather fetcher (FotMob + Open-Meteo) - match conditions
4. ✅ Venue fetcher (FotMob) - stadium info
5. ✅ Team form fetcher (FotMob) - recent W/D/L
6. ✅ Injuries fetcher (FotMob) - unavailable players
7. ✅ League position fetcher (FotMob) - standings data
8. ✅ Recovery time calculator (FotMob) - days since last match

### 3. Testing & Validation
- ✅ Integration test validates all 12 tool calls per match
- ✅ FotMob rate limits tested (10+ rapid requests, no issues)
- ✅ All tools accept team NAMES (not API-specific IDs)

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

### Batch 6: FotMob Migration (2025-12-14)

#### 1. **CRITICAL: Migrated from apifootball.com to FotMob**
   - **Removed:** apifootball.com (trial expired, no longer usable)
   - **Removed:** football-data.org for team data (429 rate limit errors)
   - **Added:** FotMob API via `mobfot` Python package
   - **Benefits:** NO rate limits, NO API key required, returns ALL data

#### 2. **New Tool: fetch_league_position**
   - Replaces `fetch_key_players_form` (no free API for player stats)
   - Returns full 20-team league standings (TheSportsDB only gave top 5)
   - Uses FotMob league table data

#### 3. **Updated Weather Tool**
   - Now uses FotMob for venue city lookup (instead of apifootball.com)
   - Open-Meteo still provides actual weather forecast

#### 4. **FotMob Client Architecture**
   - Created `fotmob_client.py` wrapper with:
     - Team name → FotMob ID resolution across 9 major leagues
     - In-memory caching for league data
     - Name normalization (handles accents, FC/CF prefixes)

### Batch 5 (Previous - Now Superseded)

#### 1. **CRITICAL FIX: api-football.com Fraud Discovered**
   - **Removed:** api-football.com (free tier limited to 2021-2023 data)
   - **Added:** apifootball.com (legitimate 180 req/hour FREE API)
   - **Note:** apifootball.com trial has now expired (Batch 6 migration)

#### 2. **Disabled scraping-based verticals**
   - Team news (BBC, ESPN scraping)
   - Morale/coach news
   - Rotation policy
   - Reason: Too fragile, legal concerns, not critical for MVP

#### 3. **No paid services**
   - Sportmonks team news (paid only)
   - Any enterprise APIs
   - Reason: LLM costs only, per project constraints

---

## 🎓 Lessons Learned

1. **Always verify free tier date ranges** - api-football.com's 2021-2023 limitation was not obvious
2. **Test API endpoints before committing** - sample requests would have revealed the fraud earlier
3. **Read community forums** - official docs often hide critical limitations
4. **Beware of "free tier" marketing** - many services offer trial-only, not sustained free access
5. **Rate limits matter at scale** - football-data.org's 10 req/min was insufficient for multi-tool usage
6. **Unofficial APIs can be more reliable** - FotMob has no rate limits despite being unofficial
7. **Always test standings endpoints** - TheSportsDB only returns top 5 teams (useless for league position)
8. **Team name resolution is critical** - APIs use internal IDs, tools must accept human-readable names

---

## 📊 Final Data Stack Summary

**Core APIs (FREE, No Rate Limit Issues):**
1. **FotMob (mobfot)** - Team form, venue, injuries, league position, recovery time (NO API KEY)
2. **football-data.org** - H2H only (rate limit OK for single endpoint)
3. **The Odds API** - Betting lines (500 credits/month)
4. **Open-Meteo** - Weather forecasts (NO API KEY)

**Total API Keys Needed:** 2 (football-data.org, The Odds API)

**Estimated Daily Requests:**
- FotMob: 20-30 requests/day (NO LIMIT)
- Odds: 3-5 requests/day (filtered games only)
- Weather: 3-5 requests/day (via Open-Meteo)
- H2H: 3-5 requests/day (1 per game)
- **Total:** ~35-45 requests/day across all APIs

**No rate limit concerns with current stack.**

---

**See:** [verticals/](verticals/) for detailed vertical analysis and [sources/](sources/) for API documentation.

**⚠️ IMPORTANT:**
- Do NOT use **apifootball.com** (trial expired)
- Do NOT use **api-football.com** (fraudulent, only 2021-2023 data)
- Do NOT use **TheSportsDB** for standings (only top 5 teams)
- Use **FotMob (mobfot)** for all team-related data
