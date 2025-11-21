# Team News & Match Previews

**Status:** 🔴 **DISABLED FOR MVP**

---

## Why Team News is Disabled

All viable team news sources fall into one of these categories:

1. **🔴 Paid APIs** (Sportmonks, etc.) - Not suitable for MVP
2. **🔴 Scraping Required** (BBC Sport, ESPN, etc.) - Too fragile
3. **🔴 Unreliable** (Inconsistent data, frequent site changes)

**MVP Strategy:** Use **injuries + form data** as proxy for team news. Add news scraping later if needed.

---

## 🔴 DISABLED: Sportmonks Pre-Match News API

**Website:** https://www.sportmonks.com  
**Type:** RESTful API  
**Cost:** Paid subscription required  
**Status:** 🔴 DISABLED

### Why It's Disabled
- ❌ Paid plans only (no free tier)
- ❌ Expensive for small project
- ✅ High quality data (but not worth cost for MVP)

### Features (for reference)
- Match previews written 48+ hours before kickoff
- Scout-analyzed team news
- League coverage: Premier League, Champions League, La Liga, Serie A, Bundesliga, Ligue 1

---

## 🔴 DISABLED: Web Scraping News Sites

**Status:** 🔴 DISABLED  
**Reason:** Too fragile for MVP

### Scraping Candidates (NOT IMPLEMENTED)

| Source | URL | Coverage | Difficulty | Status |
|--------|-----|----------|------------|--------|
| BBC Sport | bbc.com/sport/football | Premier League | Medium | 🔴 DISABLED |
| Sky Sports | skysports.com | Multi-league | Medium | 🔴 DISABLED |
| ESPN FC | espn.com/soccer | Global | Easy | 🔴 DISABLED |
| The Athletic | theathletic.com | Premium | Hard (paywall) | 🔴 DISABLED |

### Why Scraping is Problematic
1. **Site layout changes break scrapers** - Requires constant maintenance
2. **No standardized data format** - Each site structured differently
3. **Potential ToS violations** - Legal risk
4. **Anti-bot measures** - Rate limiting, Cloudflare protection
5. **Low reliability** - One change breaks entire pipeline

---

## Alternative: Data-Driven Approach (MVP)

Instead of scraping news, use **structured data as proxy**:

### 1. Injury Impact (API-Football)
```python
# Replace "team news" with injury analysis
injuries = get_team_injuries(team_id)

# AI Agent analyzes:
# - Are key starters missing?
# - How many players out?
# - Severity of injuries
```

### 2. Recent Form (API-Football)
```python
# Last 5 games trend
form = get_recent_form(team_id)

# AI Agent extracts:
# - Winning/losing streak
# - Goals scored/conceded trend
# - Home vs away performance
```

### 3. Fixture Congestion (API-Football)
```python
# Upcoming fixtures
upcoming = get_upcoming_fixtures(team_id)

# AI Agent infers:
# - Rotation risk (Champions League in 3 days?)
# - Player fatigue
# - Prioritization
```

### 4. Suspension List (API-Football)
```python
# Red cards, yellow accumulation
suspensions = get_suspensions(team_id)

# AI Agent flags:
# - Key players missing
# - Depth issues
```

### Combined AI Analysis
```python
def generate_team_news_proxy(team_id: int) -> str:
    """
    Generate team news proxy from structured data.
    
    AI Agent synthesizes:
    - Injuries
    - Form
    - Fixture congestion
    - Suspensions
    
    Into betting-relevant summary.
    """
    injuries = get_team_injuries(team_id)
    form = get_recent_form(team_id)
    fixtures = get_upcoming_fixtures(team_id)
    suspensions = get_suspensions(team_id)
    
    # AI prompt:
    prompt = f"""
    Analyze team status for betting purposes:
    
    Injuries: {injuries}
    Recent form: {form}
    Upcoming fixtures: {fixtures}
    Suspensions: {suspensions}
    
    Provide:
    1. Key player availability
    2. Rotation risk
    3. Team morale indicators
    4. Betting-relevant concerns
    """
    
    return ai_agent.generate(prompt)
```

---

## Future Enhancement: Selective Scraping

**IF** scraping becomes necessary later:

### 1. Target Only Critical News
- Don't scrape everything
- Focus on: lineup announcements, major injuries, coach statements

### 2. Use MCP Browser
- Sandbox scraping in MCP server
- Easier to maintain than custom scrapers

### 3. Fallback Gracefully
- If scraping fails, proceed with proxy data
- Don't block entire pipeline

### Example Implementation (Future)
```python
def scrape_team_news_optional(team_name: str) -> Optional[str]:
    """
    Optional news scraping with graceful fallback.
    
    Returns None if scraping fails - system continues.
    """
    try:
        # Try MCP browser scraping
        news = mcp_browser.scrape(
            url=f"https://www.bbc.com/sport/football/teams/{team_name}",
            selector=".news-article"
        )
        return news
    except Exception as e:
        logging.warning(f"News scraping failed for {team_name}: {e}")
        return None  # Graceful fallback

# In main flow:
news = scrape_team_news_optional("manchester-united")
if news:
    # Use scraped news
    team_report.add_news(news)
else:
    # Continue with proxy data
    pass
```

---

## MVP Recommendation

**DON'T** implement team news scraping for MVP.

**INSTEAD:**
1. Use API-Football for injuries, suspensions, form
2. Let AI Agent synthesize these into "team status"
3. Focus on **data quality over data quantity**
4. Add scraping only if MVP shows it's truly needed

**Rationale:**
- Scraping adds fragility
- Structured data (injuries, form) captures 80% of betting value
- News articles often contain fluff
- Can always add later if needed

---

## Status Summary

| Feature | Status | MVP Alternative |
|---------|--------|-----------------|
| **Team morale** | 🔴 DISABLED | Infer from form trend |
| **Coach pressure** | 🔴 DISABLED | Not critical for MVP |
| **Lineup announcements** | 🔴 DISABLED | Use injury list |
| **Training reports** | 🔴 DISABLED | Not critical |
| **Transfer rumors** | 🔴 DISABLED | Not betting-relevant |

---

## Implementation Checklist (MVP)

- [ ] ~~Register for news APIs~~ (SKIPPED)
- [ ] ~~Build news scrapers~~ (SKIPPED)
- [x] Use injuries as proxy for team news
- [x] Use form as proxy for morale
- [x] Use fixture congestion for rotation risk
- [ ] Create AI prompt for synthesizing proxy data
- [ ] Test AI-generated "team status" summary
- [ ] Validate betting value vs. actual news articles

---

**Next Steps:** Focus on core APIs (fixtures, odds, injuries, weather, H2H) before considering news scraping.
