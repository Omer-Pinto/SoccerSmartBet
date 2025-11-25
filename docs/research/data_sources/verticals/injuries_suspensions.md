# Injuries & Suspensions Vertical

**Purpose:** Identify missing players (injuries, suspensions) to assess team strength impact

---

## Requirements

- Current injury list with player names, injury type, games played
- Suspension list (red cards, yellow accumulation) with duration
- **Critical:** Flag if injured/suspended players are starters vs bench warmers
- Team-level data (fetch for both home and away teams)

---

## Primary Source: apifootball.com

**Status:** ✅ Enabled  
**Type:** REST API, Free tier (180 requests/hour = 6,480 requests/day)  
**Details:** See [sources/apifootball.md](../sources/apifootball.md)

**⚠️ NOTE:** This replaces api-football.com, which was discovered to be fraudulent (only provides 2021-2023 data for free users).

### Key Features
- 180 requests/hour FREE (6,480 requests/day)
- `player_injured` field in player data ("Yes"/"No")
- Player statistics (games played, goals, assists) to assess importance
- Player type (Goalkeepers, Defenders, Midfielders, Forwards)
- No complex authentication - just API key in URL

### Data Fields Provided
```json
{
  "team_name": "Atletico Madrid",
  "players": [
    {
      "player_name": "K. Benzema",
      "player_injured": "Yes",
      "player_type": "Forwards",
      "player_match_played": "23",
      "player_goals": "18",
      "player_yellow_cards": "1",
      "player_red_cards": "0",
      "player_assists": "3"
    }
  ]
}
```

---

## Backup Source: TheSportsDB.com

**Status:** 🟡 Backup  
**Type:** REST API, Free tier (100 requests/minute)  
**Details:** https://www.thesportsdb.com/api.php

### Key Features
- Free API with higher rate limit
- Player injury tracking
- Team and player statistics

### When to Use
- If apifootball.com quota exhausted (unlikely at 6,480 req/day)
- As a validation source for critical injuries

---

## AI Analysis Requirement

**⚠️ IMPORTANT:** Raw injury lists are NOT enough for betting decisions.

The **Team Intelligence Agent** must analyze whether missing players are critical:
- **For known teams (e.g., Man United):** User may know Bruno Fernandes is key
- **For unknown teams (e.g., Napoli, Atalanta):** AI must identify if injured players are starters

**Tool:** `fetch_injuries()` returns raw list  
**AI Agent:** Analyzes impact → "critical starters missing" vs "minor depth issues"

### AI Analysis Steps
1. **Check player statistics:**
   - `player_match_played` > 20 → likely starter
   - `player_goals` or `player_assists` > 5 → key offensive contributor
   - `player_type` = "Goalkeepers" and injured → critical (no backup goalkeeper as good)

2. **Cross-reference with team context:**
   - Team in top half of table + star player injured → bigger impact
   - Defensive player injured + team has weak defense → bigger impact

3. **Output assessment:**
   - "Critical starters missing: [Name] (23 games, 18 goals) - key striker injured"
   - "Minor depth issues: [Name] (3 games, 0 goals) - backup defender injured"

---

## Implementation Notes

1. **Fetch per team:** Call apifootball.com `get_teams` endpoint with league ID, filter for specific team
2. **Cache:** Store in DB, update daily (injuries change slowly, but update daily for accuracy)
3. **AI Processing:** Team Intelligence Agent must cross-reference with lineup/form data
4. **Quota:** 2 requests per game (home + away teams), ~6-10 requests/day for 3-5 games

### API Request Strategy
```python
# Fetch team with all players (includes injury status)
GET https://apiv3.apifootball.com/?action=get_teams&league_id=302&APIkey=YOUR_KEY

# Filter for specific team in response
# Check each player's "player_injured" field
# Cross-reference with player_match_played, player_goals, player_type
```

---

## Why Not api-football.com?

**⚠️ FRAUD ALERT:** api-football.com (with hyphen) was initially recommended but discovered to be fraudulent.

**The Problem:**
- Free tier **only provides 2021-2023 data**
- No 2024-2025 season data
- No current injuries
- Completely useless for live betting

**See:** [sources/NON_VIABLE_SOURCES.md](../sources/NON_VIABLE_SOURCES.md) for full details.

---

## See Also
- [Team Intelligence Agent](../../../../PRE_GAMBLING_OPTIMIZED_FLOW_TASKS.md#5-team-intelligence-agent-subgraph) - uses injury data for impact assessment
- [apifootball.com Source](../sources/apifootball.md) - API details and code examples
- [NON_VIABLE_SOURCES.md](../sources/NON_VIABLE_SOURCES.md) - Why api-football.com is fraudulent
