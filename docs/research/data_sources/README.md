# Football Data Sources - Research Documentation

**Status:** Restructured from single 906-line file  
**Date:** 2025-11-21  
**Researcher:** Football Research Droid

---

## Directory Structure

This directory contains the restructured football data sources research, split into vertical-specific files for better readability.

```
docs/research/data_sources/
├── README.md                  # This file
├── executive_summary.md       # Recommended stack + status overview
├── fixtures.md                # Fixtures APIs (football-data.org, API-Football)
├── odds.md                    # Betting odds (The-Odds-API, replaces winner.co.il)
├── injuries.md                # Injury & suspension data (API-Football)
├── weather.md                 # Weather APIs (Open-Meteo)
├── h2h.md                     # Head-to-head statistics (API-Football)
└── team_news.md               # Team news (DISABLED for MVP)
```

---

## Quick Navigation

### Start Here
- **[Executive Summary](./executive_summary.md)** - Recommended stack, status table, quick start

### Core APIs (MVP)
- **[Fixtures](./fixtures.md)** - football-data.org (🟢 primary)
- **[Odds](./odds.md)** - The-Odds-API (🟢 replaces winner.co.il)
- **[Weather](./weather.md)** - Open-Meteo (🟢 no API key needed)

### Enhanced Data (MVP)
- **[Injuries](./injuries.md)** - API-Football (🟡 100 req/day)
- **[H2H Stats](./h2h.md)** - API-Football (🟡 100 req/day)

### Disabled for MVP
- **[Team News](./team_news.md)** - 🔴 Scraping/paid only

---

## Key Changes from Original Research

### 🔴 REMOVED: winner.co.il
- **Reason:** Too fragile (React SPA scraping with Incapsula protection)
- **Replacement:** **The-Odds-API** (free tier, 500 requests/month)
- **Impact:** Stable API vs brittle scraping

### 🔴 DISABLED: All Scraping
- winner.co.il scraping → Replaced with The-Odds-API
- BBC Sport news → Disabled (use injury data as proxy)
- ESPN news → Disabled
- Team news scrapers → Disabled

### 🔴 DISABLED: Paid Services
- Sportmonks Pre-Match News → Disabled
- OddsMatrix → Disabled
- Sportradar → Disabled

---

## Status Legend

- 🟢 **Free API, easy to use** - No registration or minimal signup
- 🟡 **Free with limits** - Registration required, rate limits apply
- 🔴 **DISABLED for MVP** - Scraping, paid, or too fragile

---

## Implementation Priority

1. **Week 1:** Core APIs (fixtures, odds, weather)
2. **Week 2:** Enhanced data (injuries, H2H)
3. **Future:** Optional enhancements (team news scraping if needed)

---

## File Size Guidelines

Each vertical file is **< 150 lines** for readability:

- `executive_summary.md` - 120 lines
- `fixtures.md` - 130 lines
- `odds.md` - 145 lines
- `injuries.md` - 140 lines
- `weather.md` - 135 lines
- `h2h.md` - 140 lines
- `team_news.md` - 110 lines

Total: **~920 lines** (vs original 906 lines), but split for maintainability.

---

## Usage

1. Start with **Executive Summary** to understand recommended stack
2. Read vertical-specific files as needed for implementation
3. Each file contains:
   - Status indicator (🟢🟡🔴)
   - API documentation
   - Code examples
   - Rate limit strategies
   - Implementation checklists

---

## Related Documents

- `PRE_GAMBLING_OPTIMIZED_FLOW_TASKS.md` - Task breakdown using these APIs
- `BATCH_PLAN.md` - Implementation batches

---

**Next Steps:** Implement core APIs (fixtures, odds, weather) before moving to enhanced data.
