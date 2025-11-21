# Executive Summary - Football Data Sources

**Date:** 2025-11-21  
**Researcher:** Football Research Droid  
**Purpose:** Recommended data stack for Pre-Gambling Flow (MVP - Free APIs Only)

---

## Recommended Data Stack (MVP)

| Category | Primary Source | Status | Notes |
|----------|---------------|--------|-------|
| **Fixtures** | football-data.org | 🟢 | 12 competitions free, 10 req/min |
| **Odds** | **The-Odds-API** | 🟢 | 500 requests/month free, global bookmakers |
| **Injuries/Suspensions** | API-Football | 🟡 | 100 requests/day free |
| **Weather** | Open-Meteo | 🟢 | 10,000 requests/day, no API key |
| **H2H Stats** | API-Football | 🟡 | Included in free tier |
| **Team News** | 🔴 DISABLED | 🔴 | Paid only - disable for MVP |

### Status Legend
- 🟢 **Free API, easy to use** - No registration or minimal signup required
- 🟡 **Free with limits** - Registration required, rate limits apply
- 🔴 **DISABLED for MVP** - Requires scraping, paid service, or too fragile

---

## Key Changes from Original Research

### 🔴 REMOVED: winner.co.il
**Reason:** Too fragile (React SPA requiring Selenium scraping with Incapsula protection)

**Replacement:** **The-Odds-API** (the-odds-api.com)
- ✅ Free tier: 500 requests/month
- ✅ International bookmakers (US, UK, EU, Australia)
- ✅ REST API with JSON format
- ✅ Supports decimal odds format
- ⚠️ Note: Odds format differs from Israeli (X for every 1 ILS). Python code will translate decimal odds to Israeli format.

### 🔴 DISABLED: All Scraping Sources
**Disabled for MVP:**
- winner.co.il scraping (replaced with The-Odds-API)
- BBC Sport news scraping (paid APIs only viable alternative)
- ESPN news scraping (inconsistent structure)
- Team news scrapers (too fragile)

**Strategy:** Start with API-only sources. Team morale/news can be added later if scraping proves reliable.

### 🔴 DISABLED: Paid Services
**Disabled for MVP:**
- Sportmonks Pre-Match News API (paid subscription required)
- Sportmonks Injury Reports (paid only)
- OddsMatrix (enterprise pricing)
- Sportradar (paid only)

---

## Implementation Priority

### Phase 1: Core APIs (Week 1)
1. **football-data.org** - Fixtures API
2. **The-Odds-API** - Betting odds (replaces winner.co.il)
3. **Open-Meteo** - Weather API

### Phase 2: Enhanced Data (Week 2)
4. **API-Football** - Injuries, suspensions, H2H stats

### Phase 3: Optional Enhancements (Future)
5. Team news scraping (only if needed)
6. MCP integration for external tools

---

## Data Gaps (MVP Acceptable)

| Gap | Impact | Mitigation |
|-----|--------|------------|
| **Team news/morale** | Medium | Use injury data + form as proxy |
| **Player form metrics** | Low | Goals/assists available via API-Football |
| **Coach pressure** | Low | Not critical for MVP |
| **Rotation policy** | Medium | Infer from fixture congestion |

---

## Quick Start Checklist

- [ ] Register for football-data.org API key (free, instant)
- [ ] Register for The-Odds-API key (free tier, 500 requests/month)
- [ ] Register for API-Football key (RapidAPI, 100 requests/day free)
- [ ] Test Open-Meteo (no registration needed)
- [ ] Implement rate limit tracking for all APIs
- [ ] Build odds format converter (decimal → Israeli format)

---

## Risk Assessment

| Risk | Severity | Mitigation |
|------|----------|------------|
| **The-Odds-API free tier limits** | 🟡 MEDIUM | 500 req/month ≈ 16/day. Cache daily, use wisely. |
| **API-Football 100 req/day limit** | 🟡 MEDIUM | Batch requests, cache fixture data. |
| **Missing team news** | 🟢 LOW | Acceptable for MVP. Focus on data-driven metrics. |
| **Odds format mismatch** | 🟢 LOW | Simple Python conversion function. |

---

**Next Steps:** See individual vertical docs for API details and code examples.
