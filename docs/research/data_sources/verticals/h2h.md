# Head-to-Head (H2H) Statistics Vertical

**Purpose:** Analyze recent encounters between two teams to identify patterns (home dominance, high-scoring trends, defensive patterns)

---

## Requirements

- Last 5-10 matches between two teams
- Results (home/away scores)
- Match dates and venues
- Competition context (league vs cup)

---

## Primary Source: football-data.org /matches/{id}/head2head

**Status:** ✅ Enabled  
**Type:** REST API, Free tier (10 requests/minute)  
**Details:** See [sources/football-data.org.md](../sources/football-data.org.md)

**Why:** Already using football-data.org for fixtures - adding H2H endpoint is zero additional cost.

### Key Features
- Included in football-data.org free tier (already using for fixtures)
- H2H subresource: `/matches/{match_id}/head2head`
- Returns previous encounters between two teams
- Full match details (scores, date, venue, competition)

### Data Fields Provided
```json
{
  "matches": [
    {
      "id": 330299,
      "utcDate": "2022-02-27T16:05:00Z",
      "status": "FINISHED",
      "homeTeam": {
        "id": 531,
        "name": "ES Troyes AC"
      },
      "awayTeam": {
        "id": 516,
        "name": "Olympique de Marseille"
      },
      "score": {
        "fullTime": {
          "home": 1,
          "away": 1
        }
      },
      "venue": "Stade de l'Aube"
    }
  ]
}
```

### API Request
```bash
curl -XGET 'https://api.football-data.org/v4/matches/{match_id}/head2head' \
  -H "X-Auth-Token: YOUR_TOKEN"
```

**Filters Available:**
- `limit` - number of past encounters to return (default: all)
- `dateFrom` - start date for H2H history
- `dateTo` - end date for H2H history

---

## Backup Source: apifootball.com

**Status:** ✅ Backup  
**Type:** REST API, Free tier (180 requests/hour = 6,480 requests/day)  
**Details:** See [sources/apifootball.md](../sources/apifootball.md)

### Key Features
- 180 requests/hour FREE
- Get all matches via `get_events` endpoint
- Filter results for matches between two specific teams
- Good backup if football-data.org quota exhausted

### API Request Strategy
```python
# Fetch events from last 3 years
GET https://apiv3.apifootball.com/?action=get_events&from=2022-01-01&to=2025-11-25&APIkey=YOUR_KEY

# Filter for matches between Team A and Team B
# (match_hometeam_name == Team A AND match_awayteam_name == Team B) OR
# (match_hometeam_name == Team B AND match_awayteam_name == Team A)
```

---

## AI Analysis Requirement

**⚠️ IMPORTANT:** H2H data is NOT just win/loss counts.

The **Game Intelligence Agent** must extract patterns:
- **Home dominance:** "Man United wins 80% of home fixtures vs Newcastle"
- **High-scoring:** "Last 5 meetings averaged 4.2 goals"
- **Defensive patterns:** "3 of last 4 were under 2.5 goals"
- **Recent trend:** "Liverpool won last 3 encounters after 10-year drought"

**Tool:** `fetch_h2h()` returns raw match list  
**AI Agent:** Synthesizes patterns into betting-relevant insights

### AI Pattern Extraction Examples

```python
# Example H2H analysis by AI
{
  "h2h_insights": """
  Last 5 encounters show clear home dominance:
  - Man United won 4 of 5 home games vs Newcastle (1 draw)
  - Average score at Old Trafford: 2.6 - 0.4
  - Newcastle hasn't won at Old Trafford since 2019
  
  Betting implications:
  - Home win (1) likely outcome
  - Under 2.5 goals unlikely (high-scoring trend)
  - Draw (X) very unlikely based on historical pattern
  """,
  "home_dominance_pct": 80,
  "avg_goals_per_game": 3.0,
  "recent_trend": "improving for home team"
}
```

---

## Implementation Notes

1. **Fetch per game:** 1 request per selected game (after Smart Game Picker)
   - Primary: football-data.org `/matches/{match_id}/head2head`
   - Backup: apifootball.com `get_events` + filter

2. **Quota:** 
   - football-data.org: ~3-5 requests/day for filtered games (well under 10 req/min limit)
   - apifootball.com: 1 request to get all events (if backup needed)

3. **Caching:** H2H history changes slowly, cache for 1 week

4. **Limit:** Request last 10 matches max (sufficient for pattern analysis)

### Request Strategy
```python
# Primary: football-data.org H2H endpoint
def fetch_h2h_primary(match_id: int) -> List[Dict]:
    """Fetch H2H using football-data.org (already using this API)"""
    url = f"https://api.football-data.org/v4/matches/{match_id}/head2head"
    headers = {"X-Auth-Token": os.getenv("FOOTBALL_DATA_API_KEY")}
    params = {"limit": 10}  # Last 10 encounters
    
    response = requests.get(url, headers=headers, params=params)
    return response.json()["matches"]

# Backup: apifootball.com event filtering
def fetch_h2h_backup(team1_name: str, team2_name: str) -> List[Dict]:
    """Backup H2H fetcher using apifootball.com"""
    # Implementation in sources/apifootball.md
    pass
```

---

## Why Not api-football.com?

**⚠️ FRAUD ALERT:** api-football.com (with hyphen) was initially recommended but discovered to be fraudulent.

**The Problem:**
- Free tier **only provides 2021-2023 data**
- No 2024-2025 season data
- No recent H2H matches for current season
- Completely useless for live betting

**Better Alternatives:**
1. **football-data.org** - already using it, H2H endpoint included
2. **apifootball.com** (no hyphen) - legitimate 180 req/hour FREE

**See:** [sources/NON_VIABLE_SOURCES.md](../sources/NON_VIABLE_SOURCES.md) for full details.

---

## See Also
- [Game Intelligence Agent](../../../../status/pre_gambling_flow/PRE_GAMBLING_FLOW_TASKS.md#42-game-intelligence-agent-node) - performs H2H pattern analysis
- [football-data.org Source](../sources/football-data.org.md) - Primary H2H source
- [apifootball.com Source](../sources/apifootball.md) - Backup H2H source
- [NON_VIABLE_SOURCES.md](../sources/NON_VIABLE_SOURCES.md) - Why api-football.com is fraudulent
