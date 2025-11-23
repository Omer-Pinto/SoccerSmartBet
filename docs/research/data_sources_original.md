# SoccerSmartBet - Football Data Sources Research

**Date:** 2025-11-20  
**Researcher:** Football Research Droid  
**Purpose:** Catalog free football APIs, MCP servers, and data sources for Pre-Gambling Flow

---

## Executive Summary

### Recommended Data Stack

| Category | Primary Source | Backup Source | Notes |
|----------|---------------|---------------|-------|
| **Fixtures** | football-data.org | API-Football | 12 competitions free, reliable |
| **Odds (CRITICAL)** | **winner.co.il** | None | Mandatory, requires scraping |
| **Injuries/Suspensions** | API-Football | Sportmonks | Included in free tier |
| **Team News** | Sportmonks Pre-Match News | Manual scraping | Paid feature, may need workaround |
| **Weather** | Open-Meteo | OpenWeatherMap | No API key needed |
| **H2H Stats** | API-Football | football-data.org | Available in most APIs |
| **MCP Tools** | mcp-soccer-data | Browser MCP | For external integration only |

### Key Risks & Concerns
1. **🔴 CRITICAL**: winner.co.il is React SPA requiring Selenium/Playwright for scraping
2. **🟡 MEDIUM**: Team news/match previews are paid features in most APIs
3. **🟡 MEDIUM**: Free tier rate limits require careful request management
4. **🟢 LOW**: Weather and H2H data widely available

---

## 1. Fixtures APIs

### 1.1 football-data.org ⭐ **RECOMMENDED**

**Website:** https://www.football-data.org  
**Type:** RESTful API  
**Cost:** FREE (12 competitions)

#### Features
- ✅ 12 major competitions (Premier League, La Liga, Bundesliga, etc.)
- ✅ Fixtures, results, standings, teams
- ✅ 10 API calls per minute
- ✅ Well-documented, reliable
- ❌ Delayed scores on free tier (use for pre-match only)

#### Rate Limits
- **Free Plan**: 10 requests/minute, 100 requests/day (non-authenticated)
- **Free Registered**: 10 requests/minute (authenticated)

#### Registration
```bash
# Sign up at: https://www.football-data.org/client/register
# Get API key immediately - no credit card required
```

#### Example API Call
```python
import requests

API_KEY = "your_api_key"
BASE_URL = "https://api.football-data.org/v4"

# Get today's fixtures
headers = {"X-Auth-Token": API_KEY}
response = requests.get(f"{BASE_URL}/matches", headers=headers)

# Example response structure:
{
  "matches": [
    {
      "id": 327105,
      "utcDate": "2025-11-20T19:45:00Z",
      "status": "SCHEDULED",
      "homeTeam": {"id": 65, "name": "Manchester City"},
      "awayTeam": {"id": 66, "name": "Manchester United"},
      "competition": {"id": 2021, "name": "Premier League"}
    }
  ]
}
```

#### Coverage
- English Premier League
- Spanish La Liga
- German Bundesliga
- Italian Serie A
- French Ligue 1
- UEFA Champions League
- European Championship
- World Cup
- + 4 more

---

### 1.2 API-Football (RapidAPI)

**Website:** https://www.api-football.com  
**Type:** RESTful API  
**Cost:** FREE (100 requests/day)

#### Features
- ✅ 1,200+ leagues and cups
- ✅ Live scores (15-second updates)
- ✅ Fixtures, standings, H2H, events
- ✅ Injuries, suspensions included
- ✅ Pre-match and live odds
- ✅ Player statistics

#### Rate Limits
- **Free Plan**: 100 requests/day, 10 requests/minute
- **Pro Plan**: $19/month for 7,500 requests/day

#### Registration
```bash
# Sign up at: https://dashboard.api-football.com/register
# OR via RapidAPI: https://rapidapi.com/api-sports/api/api-football
```

#### Example API Call
```python
import requests

API_KEY = "your_rapidapi_key"
BASE_URL = "https://v3.football.api-sports.io"

headers = {
    "x-rapidapi-host": "v3.football.api-sports.io",
    "x-rapidapi-key": API_KEY
}

# Get fixtures for today
params = {"date": "2025-11-20"}
response = requests.get(f"{BASE_URL}/fixtures", headers=headers, params=params)

# Example response:
{
  "response": [
    {
      "fixture": {
        "id": 1234567,
        "date": "2025-11-20T19:45:00+00:00",
        "venue": {"name": "Old Trafford", "city": "Manchester"}
      },
      "teams": {
        "home": {"id": 33, "name": "Manchester United"},
        "away": {"id": 34, "name": "Newcastle"}
      },
      "league": {"id": 39, "name": "Premier League"}
    }
  ]
}
```

#### Coverage
- Global coverage: 1,200+ leagues
- Major European leagues
- International tournaments
- Lower-tier divisions

---

### 1.3 TheSportsDB

**Website:** https://www.thesportsdb.com  
**Type:** RESTful JSON API  
**Cost:** FREE (limited), $9/month (premium)

#### Features
- ✅ Completely free basic tier
- ✅ Fixtures, teams, players, events
- ✅ 255,300+ players in database
- ❌ Some methods rate-limited due to demand
- ❌ No official injury/suspension data

#### API Key
```bash
# Free development key: 3
# Production key (Patreon): $9/month
```

#### Example API Call
```python
import requests

# Get fixtures for a specific league
LEAGUE_ID = "4328"  # Premier League
response = requests.get(
    f"https://www.thesportsdb.com/api/v1/json/3/eventsnextleague.php?id={LEAGUE_ID}"
)

# Example response:
{
  "events": [
    {
      "idEvent": "1234567",
      "strEvent": "Manchester United vs Liverpool",
      "dateEvent": "2025-11-20",
      "strTime": "15:00:00",
      "strHomeTeam": "Manchester United",
      "strAwayTeam": "Liverpool",
      "strLeague": "English Premier League"
    }
  ]
}
```

---

## 2. Odds Sources (CRITICAL)

### 2.1 winner.co.il 🔴 **MANDATORY PRIMARY SOURCE**

**Website:** https://www.winner.co.il  
**Type:** Israeli Toto (Government Monopoly)  
**Access Method:** Web Scraping (NO PUBLIC API)

#### Site Structure
- **Technology**: React Single Page Application (SPA)
- **Language**: Hebrew (he-IL)
- **Dynamic Loading**: JavaScript-rendered content
- **Anti-Scraping**: Incapsula CDN protection detected

#### HTML Analysis
```html
<!DOCTYPE html>
<html lang="he">
  <head>
    <meta charset="utf-8" />
    <title>אתר Winner החדש</title>
    <!-- Incapsula protection detected -->
    <script src="/_Incapsula_Resource?..."></script>
  </head>
  <body>
    <div id="root"></div>
    <!-- React app loads here -->
  </body>
</html>
```

#### Scraping Strategy

**Option 1: Selenium/Playwright (RECOMMENDED)**
```python
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def scrape_winner_odds():
    driver = webdriver.Chrome()
    driver.get("https://www.winner.co.il")
    
    # Wait for React app to load
    wait = WebDriverWait(driver, 10)
    
    # Find odds elements (selectors need to be discovered)
    # Look for classes/IDs containing: "odds", "line", "toto", etc.
    odds_elements = wait.until(
        EC.presence_of_all_elements_located((By.CLASS_NAME, "match-odds"))
    )
    
    for element in odds_elements:
        match_name = element.find_element(By.CLASS_NAME, "match-name").text
        home_odd = element.find_element(By.CLASS_NAME, "odd-1").text
        draw_odd = element.find_element(By.CLASS_NAME, "odd-x").text
        away_odd = element.find_element(By.CLASS_NAME, "odd-2").text
        
        print(f"{match_name}: 1={home_odd}, X={draw_odd}, 2={away_odd}")
    
    driver.quit()
```

**Option 2: MCP Browser Server**
```bash
# Use existing MCP browser for sandboxed scraping
# Install: npx @modelcontextprotocol/browser
# Configure to target winner.co.il
```

#### Data Structure (Expected)
```python
{
  "match_id": "winner_20251120_001",
  "home_team": "Manchester United",
  "away_team": "Liverpool",
  "kickoff_time": "2025-11-20T15:00:00Z",
  "odds": {
    "1": 2.10,  # Home win (n1)
    "X": 3.40,  # Draw (nx)
    "2": 3.50   # Away win (n2)
  },
  "source": "winner.co.il",
  "scraped_at": "2025-11-20T10:00:00Z"
}
```

#### Challenges & Mitigations
| Challenge | Mitigation |
|-----------|------------|
| **Incapsula Protection** | Use Selenium with real browser, randomize user agents |
| **Hebrew Language** | Use UTF-8 encoding, translate team names to English |
| **Dynamic Content** | Wait for elements to load, use explicit waits |
| **Rate Limiting** | Scrape once daily (morning), cache results |
| **Site Changes** | Monitor for layout changes, alert on scraping failures |

#### Selector Discovery Strategy
1. Inspect page with browser DevTools (F12)
2. Look for elements containing:
   - Match names (teams)
   - Numeric values (odds)
   - Date/time information
3. Common class patterns in Hebrew sites:
   - `.match`, `.game`, `.event`
   - `.odds`, `.line`, `.coefficient`
   - `.home`, `.away`, `.draw`

#### Backup Plan
If winner.co.il becomes unscrappable:
1. **Manual Entry**: User inputs odds from winner.co.il daily
2. **OCR**: Screenshot + Tesseract OCR (less reliable)
3. **Contact ISBB**: Request official API access (unlikely)

---

### 2.2 Backup Odds Sources (NOT RECOMMENDED)

#### OddsMatrix (Commercial)
- **Website**: https://oddsmatrix.com
- **Cost**: Paid only
- **Coverage**: 3,000+ competitions
- ❌ **Not suitable**: Paid service, not Israeli odds

#### Sportradar Odds Comparison (Commercial)
- **Website**: https://developer.sportradar.com/odds
- **Cost**: Paid only
- ❌ **Not suitable**: Enterprise pricing

**⚠️ NOTE**: Only winner.co.il odds are acceptable for this project.

---

## 3. Injury & Suspension Data

### 3.1 API-Football Sidelined Endpoint

**Included in free tier!**

```python
# Get injuries for a team
params = {"team": 33}  # Manchester United
response = requests.get(
    f"{BASE_URL}/sidelined",
    headers=headers,
    params=params
)

# Example response:
{
  "response": [
    {
      "type": "Knee Injury",
      "start": "2025-10-15",
      "end": "2025-12-01",
      "player": {
        "id": 276,
        "name": "Bruno Fernandes"
      }
    },
    {
      "type": "Red Card",
      "start": "2025-11-10",
      "end": "2025-11-24",
      "player": {
        "id": 1456,
        "name": "Casemiro"
      }
    }
  ]
}
```

**Data Includes:**
- Injury type and severity
- Expected return date
- Suspension type (red card, yellow accumulation)
- Player identification

---

### 3.2 Sportmonks Injury Reports (Paid)

**Website:** https://www.sportmonks.com  
**Cost:** Paid plans only  
**Features:**
- Detailed injury epidemiology
- Lower extremity injury tracking
- ACL injury statistics
- ❌ **Not suitable for free tier**

---

### 3.3 Manual Scraping Options

**premierleagueinjuries.com** (Premier League only)
```python
# Free daily updates, no API
# Scrape: https://www.premierleagueinjuries.com/
# Contains: Player status, estimated return dates
```

**sportsgambler.com/injuries/football**
```python
# Free injury lists by league
# Scrape: https://www.sportsgambler.com/injuries/football/
# Contains: Matches played, goals, assists, return dates
```

---

## 4. Team News & Match Previews

### 4.1 Sportmonks Pre-Match News API (Paid) ⚠️

**Website:** https://www.sportmonks.com  
**Cost:** Paid subscription required  
**Features:**
- Match previews written 48+ hours before kickoff
- Scout-analyzed team news
- League coverage: Premier League, Champions League, La Liga, Serie A, Bundesliga, Ligue 1

#### Example Endpoint
```python
# GET Pre-Match News by Season
response = requests.get(
    f"https://api.sportmonks.com/v3/football/news/pre-match/seasons/21646",
    params={"api_token": "YOUR_TOKEN"}
)

# Example response:
{
  "data": [
    {
      "id": 12345,
      "fixture_id": 98765,
      "league_id": 2,
      "title": "Roma vs. Juventus - Match Preview",
      "subtitle": "Tactical analysis and team news",
      "type": "prematch",
      "published_at": "2025-11-18T08:00:00Z"
    }
  ]
}
```

**❌ PROBLEM**: Paid only, expensive for small project

---

### 4.2 Alternative: Web Scraping News Sites

**Free News Sources to Scrape:**

| Source | URL | Coverage | Difficulty |
|--------|-----|----------|------------|
| BBC Sport | bbc.com/sport/football | Premier League | Medium |
| Sky Sports | skysports.com | Multi-league | Medium |
| ESPN FC | espn.com/soccer | Global | Easy |
| The Athletic | theathletic.com | Premium (paywall) | Hard |

**Scraping Strategy:**
```python
import requests
from bs4 import BeautifulSoup

def scrape_team_news(team_name):
    # Example: BBC Sport team news
    url = f"https://www.bbc.com/sport/football/teams/{team_name.lower()}"
    response = requests.get(url)
    soup = BeautifulSoup(response.content, 'html.parser')
    
    # Find news articles
    articles = soup.find_all('article', class_='news-article')
    
    team_news = []
    for article in articles:
        title = article.find('h3').text
        summary = article.find('p').text
        team_news.append({"title": title, "summary": summary})
    
    return team_news
```

**⚠️ CHALLENGES**:
- Site layout changes break scrapers
- No standardized data format
- Potential legal issues (ToS violations)

---

### 4.3 Recommendation: Hybrid Approach

1. **Use API-Football for injuries/suspensions** (included in free tier)
2. **Scrape 2-3 reliable news sources** for team news
3. **Implement fallback**: If scraping fails, proceed with partial data

---

## 5. Weather APIs

### 5.1 Open-Meteo ⭐ **RECOMMENDED**

**Website:** https://open-meteo.com  
**Type:** Free, No API Key Required  
**Cost:** FREE

#### Features
- ✅ No API key needed
- ✅ 10,000 requests/day free
- ✅ Hourly forecasts
- ✅ Historical weather (80+ years)
- ✅ 1-11km resolution

#### Example API Call
```python
import requests

def get_match_weather(lat, lon, match_time):
    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": "temperature_2m,precipitation,windspeed_10m",
        "timezone": "auto"
    }
    
    response = requests.get(
        "https://api.open-meteo.com/v1/forecast",
        params=params
    )
    
    data = response.json()
    return data["hourly"]

# Example: Manchester (Old Trafford)
weather = get_match_weather(53.4631, -2.2913, "2025-11-20T15:00:00")

# Example response:
{
  "hourly": {
    "time": ["2025-11-20T15:00"],
    "temperature_2m": [12.5],
    "precipitation": [0.0],
    "windspeed_10m": [15.3]
  }
}
```

#### Venue Coordinates (Examples)
```python
STADIUM_COORDS = {
    "Old Trafford": (53.4631, -2.2913),
    "Anfield": (53.4308, -2.9608),
    "Emirates Stadium": (51.5549, -0.1084),
    "Santiago Bernabéu": (40.4530, -3.6883),
    "Camp Nou": (41.3809, 2.1228)
}
```

---

### 5.2 OpenWeatherMap (Backup)

**Website:** https://openweathermap.org  
**Type:** Free tier available  
**Cost:** FREE (1,000 calls/day)

#### Features
- ✅ 1,000 API calls/day free
- ✅ Current weather + forecasts
- ✅ Minute-by-minute (1 hour), hourly (48h), daily (8 days)
- ❌ Requires API key signup

#### Example API Call
```python
API_KEY = "your_openweather_key"
lat, lon = 53.4631, -2.2913  # Old Trafford

response = requests.get(
    f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={API_KEY}"
)

# Example response:
{
  "weather": [{"main": "Rain", "description": "light rain"}],
  "main": {"temp": 285.5, "humidity": 78},
  "wind": {"speed": 4.12},
  "dt": 1700490000
}
```

---

## 6. Head-to-Head (H2H) Statistics

### 6.1 API-Football H2H Endpoint

**Included in free tier!**

```python
# Get head-to-head between two teams
params = {
    "h2h": "33-34"  # Man United (33) vs Newcastle (34)
}

response = requests.get(
    f"{BASE_URL}/fixtures/headtohead",
    headers=headers,
    params=params
)

# Example response:
{
  "response": [
    {
      "fixture": {
        "id": 123456,
        "date": "2024-10-06T14:00:00+00:00"
      },
      "teams": {
        "home": {"id": 33, "name": "Manchester United", "winner": true},
        "away": {"id": 34, "name": "Newcastle", "winner": false}
      },
      "goals": {"home": 3, "away": 0},
      "score": {
        "fulltime": {"home": 3, "away": 0}
      }
    }
  ]
}
```

---

### 6.2 football-data.org H2H

```python
# Get head-to-head via match history
# Find common fixtures between two teams
team1_matches = requests.get(f"{BASE_URL}/teams/65/matches", headers=headers)
team2_matches = requests.get(f"{BASE_URL}/teams/66/matches", headers=headers)

# Filter for matches where both teams played each other
```

---

### 6.3 AllSportsAPI (Alternative)

**Website:** https://allsportsapi.com  
**Cost:** FREE (260 calls/hour)  
**Features:**
- H2H included in free tier
- 2 random leagues per year
- Good for testing

---

## 7. MCP Servers (External Integration)

### 7.1 mcp-soccer-data (yeonupark) ⭐

**GitHub:** https://github.com/yeonupark/mcp-soccer-data  
**Type:** Model Context Protocol Server  
**Data Source:** SoccerDataAPI

#### Features
- ✅ Real-time football match data
- ✅ Natural language queries via LLM
- ✅ Live match listings
- ✅ Match details (lineups, events, odds)
- ✅ MIT License

#### Installation
```bash
npx -y @smithery/cli install @yeonupark/mcp-soccer-data --client claude
```

#### Configuration (Claude Desktop)
```json
{
  "mcpServers": {
    "soccerdata": {
      "command": "npx",
      "args": ["-y", "@yeonupark/mcp-soccer-data"],
      "env": {
        "SOCCER_API_KEY": "your_soccerdata_api_key"
      }
    }
  }
}
```

**⚠️ NOTE**: MCPs are for **external AI clients** (like Claude Desktop), not our internal Python tools.

---

### 7.2 soccer-mcp-server (obinopaul)

**GitHub:** https://github.com/obinopaul/soccer-mcp-server  
**Type:** Python MCP Server  
**Data Source:** API-Football (RapidAPI)

#### Features
- ✅ League data, standings, fixtures
- ✅ Team and player information
- ✅ Live match data
- ✅ Python-based

#### Setup
```bash
git clone https://github.com/obinopaul/soccer-mcp-server
cd soccer-mcp-server
pip install -r requirements.txt

# Set API key
export RAPIDAPI_KEY="your_rapidapi_key"

# Run server
python main.py
```

---

### 7.3 MCP Browser (General Purpose)

**Use Case:** Scraping winner.co.il

```bash
# Install MCP browser server
npx @modelcontextprotocol/browser

# Configure for winner.co.il scraping
# Navigate, extract odds data
```

**⚠️ NOTE**: We will write **Python scraping tools** directly, not custom MCPs.

---

## 8. Data Gaps & Concerns

### 8.1 Critical Issues

| Issue | Severity | Impact | Mitigation |
|-------|----------|--------|------------|
| **winner.co.il scraping** | 🔴 HIGH | System unusable without odds | Robust Selenium setup, daily monitoring |
| **Team news is paid** | 🟡 MEDIUM | Less informed betting | Scrape free sources (BBC, ESPN) |
| **Free tier rate limits** | 🟡 MEDIUM | Request failures | Cache data, optimize requests |

### 8.2 Missing Data

- **Player form**: Not available in free tiers (goals/assists available, but not "form" metric)
- **Morale/coach pressure**: News scraping only, no structured data
- **Training reports**: News scraping only
- **Rotation policy**: News scraping only

### 8.3 Recommendations

1. **Prioritize API-Football**: Best coverage for free tier (fixtures, injuries, H2H, odds)
2. **football-data.org**: Backup for fixtures if API-Football quota exhausted
3. **Open-Meteo**: Weather (no key required)
4. **winner.co.il**: Build robust scraper FIRST (most critical)
5. **News scraping**: Start with 1-2 sources, expand if needed

---

## 9. Implementation Checklist

- [ ] Register for football-data.org API key
- [ ] Register for API-Football (RapidAPI) key
- [ ] Test fixtures endpoint (both APIs)
- [ ] Build winner.co.il Selenium scraper
- [ ] Test scraper on multiple match days
- [ ] Implement Open-Meteo weather fetcher
- [ ] Test API-Football injuries endpoint
- [ ] Test API-Football H2H endpoint
- [ ] Explore BBC Sport scraping for team news
- [ ] Set up error handling for all scrapers
- [ ] Implement rate limit tracking
- [ ] Create data validation layer (detect missing/stale data)

---

## 10. Example Python Tool Structure

```python
# tools/fetch_fixtures.py

import requests
from typing import List, Dict
from datetime import date

class FixtureFetcher:
    def __init__(self, api_key: str, provider: str = "football-data"):
        self.api_key = api_key
        self.provider = provider
        
    def get_todays_fixtures(self) -> List[Dict]:
        if self.provider == "football-data":
            return self._fetch_football_data()
        elif self.provider == "api-football":
            return self._fetch_api_football()
        
    def _fetch_football_data(self) -> List[Dict]:
        headers = {"X-Auth-Token": self.api_key}
        response = requests.get(
            "https://api.football-data.org/v4/matches",
            headers=headers
        )
        return response.json()["matches"]
    
    def _fetch_api_football(self) -> List[Dict]:
        headers = {
            "x-rapidapi-host": "v3.football.api-sports.io",
            "x-rapidapi-key": self.api_key
        }
        params = {"date": str(date.today())}
        response = requests.get(
            "https://v3.football.api-sports.io/fixtures",
            headers=headers,
            params=params
        )
        return response.json()["response"]


# tools/scrape_winner_odds.py

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from typing import List, Dict

class WinnerOddsScraper:
    def __init__(self):
        self.url = "https://www.winner.co.il"
        
    def scrape_odds(self) -> List[Dict]:
        driver = webdriver.Chrome()
        driver.get(self.url)
        
        # Wait for dynamic content
        wait = WebDriverWait(driver, 10)
        
        # Scrape odds (selectors TBD after inspection)
        odds_data = []
        
        # TODO: Discover actual selectors
        # matches = driver.find_elements(By.CLASS_NAME, "match")
        # for match in matches:
        #     home_team = match.find_element(...).text
        #     odds = {...}
        #     odds_data.append(...)
        
        driver.quit()
        return odds_data
```

---

## Appendix A: API Comparison Matrix

| Feature | football-data.org | API-Football | TheSportsDB | Sportmonks |
|---------|------------------|--------------|-------------|------------|
| **Cost** | Free | Free (100/day) | Free | Paid |
| **Fixtures** | ✅ | ✅ | ✅ | ✅ |
| **Live Scores** | ❌ (paid) | ✅ | ✅ (limited) | ✅ |
| **Injuries** | ❌ | ✅ | ❌ | ✅ |
| **H2H** | ✅ | ✅ | ✅ | ✅ |
| **Odds** | ❌ | ✅ | ❌ | ✅ |
| **Team News** | ❌ | ❌ | ❌ | ✅ (paid) |
| **Rate Limit** | 10/min | 10/min | Varies | Varies |
| **Documentation** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ |
| **Reliability** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ |

---

## Appendix B: winner.co.il Scraping Checklist

- [ ] Inspect page with DevTools
- [ ] Identify odds container elements
- [ ] Map Hebrew team names to English
- [ ] Extract match date/time
- [ ] Extract home/away team names
- [ ] Extract 1/X/2 odds values
- [ ] Handle Incapsula protection
- [ ] Implement retry logic
- [ ] Log scraping errors
- [ ] Validate scraped data
- [ ] Store in database with timestamp
- [ ] Schedule daily execution (cron)
- [ ] Monitor for site layout changes
- [ ] Alert on scraping failures

---

**End of Research Document**  
**Next Steps:** Begin implementation of tools as per PRE_GAMBLING_OPTIMIZED_FLOW_TASKS.md
