# APIfootball.com

**Website:** https://apifootball.com  
**Type:** REST API  
**Cost:** FREE (180 requests/hour)  
**Status:** ✅ Primary source for [Injuries/Suspensions](../verticals/injuries_suspensions.md), [H2H](../verticals/h2h.md), and [Team Form](../verticals/team_form.md)

**⚠️ NOTE:** This is **NOT** api-football.com (the fraudulent service with 2021-2023 data only). This is apifootball.com - a completely different, legitimate FREE API.

---

## Overview

APIfootball.com provides comprehensive football data including injuries, team form, H2H statistics, and live scores. It's a **primary alternative source** after the discovery that api-football.com is fraudulent (only provides 2021-2023 data for free users).

---

## Features

- ✅ 180 requests/hour FREE (6,480 requests/day!)
- ✅ Live scores and events
- ✅ **Injuries tracking** (`player_injured` field in player data)
- ✅ Head-to-head statistics (via event filtering)
- ✅ Team form (recent matches per team)
- ✅ Player statistics
- ✅ Fixtures, standings, lineups
- ✅ JSON format

---

## Rate Limits

- **Free Plan**: 180 requests/hour, ~6,480 requests/day
- **Coverage**: England Championship, France Ligue 2, and more

**For SoccerSmartBet:**
- 3-5 games/day × 2 teams = 6-10 requests for injuries
- ~3-5 requests for H2H
- ~6-10 requests for recent matches (team form)
- **Total:** ~20-30 requests/day (well under 6,480 limit)

---

## Registration

1. Visit: https://apifootball.com/
2. Create account and get API key
3. Add to `.env`:
   ```bash
   APIFOOTBALL_API_KEY=your_api_key_here
   ```

---

## API Endpoints

### 1. Get Teams with Players (Includes Injuries)

**Endpoint:**
```http
GET https://apiv3.apifootball.com/?action=get_teams&league_id=302&APIkey=YOUR_API_KEY
```

**Parameters:**
- `action`: `get_teams`
- `league_id`: League ID (required)
- `APIkey`: Your API key

**Response (Injuries):**
```json
{
  "team_key": "73",
  "team_name": "Atletico Madrid",
  "players": [
    {
      "player_name": "K. Benzema",
      "player_injured": "Yes",
      "player_type": "Forwards",
      "player_match_played": "23",
      "player_goals": "18"
    },
    {
      "player_name": "J. Oblak",
      "player_injured": "No",
      "player_type": "Goalkeepers"
    }
  ]
}
```

**Injury Detection:**
- Check `player_injured` field: "Yes" or "No"
- Cross-reference with `player_type` to determine starter vs bench
- Use `player_match_played` and `player_goals` to assess importance

---

### 2. Get Events (For H2H and Team Form)

**Endpoint:**
```http
GET https://apiv3.apifootball.com/?action=get_events&from=2024-01-01&to=2024-12-31&team_id=76&APIkey=YOUR_API_KEY
```

**Parameters:**
- `action`: `get_events`
- `from`: Start date (yyyy-mm-dd)
- `to`: End date (yyyy-mm-dd)
- `team_id`: Team ID (optional - for team-specific matches)
- `match_id`: Match ID (optional - for specific match)
- `APIkey`: Your API key

**Response:**
```json
[
  {
    "match_id": "112282",
    "match_date": "2023-04-05",
    "match_status": "Finished",
    "match_hometeam_name": "West Ham United",
    "match_awayteam_name": "Newcastle United",
    "match_hometeam_score": "1",
    "match_awayteam_score": "5",
    "match_stadium": "London Stadium (London)"
  }
]
```

**Use Cases:**
- **Team Form:** Get last 5 matches for a team by filtering by `team_id`
- **H2H:** Get historical matches between two teams (filter results by both team names)

---

## Python Code Example

```python
import requests
from typing import List, Dict

class APIFootballFetcher:
    """Fetches data from APIfootball.com (NOT api-football.com!)"""
    
    BASE_URL = "https://apiv3.apifootball.com/"
    
    def __init__(self, api_key: str):
        self.api_key = api_key
    
    def get_team_with_injuries(self, league_id: int, team_name: str) -> Dict:
        """
        Fetch team data including player injury status
        
        Args:
            league_id: League ID
            team_name: Team name to filter
        
        Returns:
            Team data with player list and injury status
        """
        params = {
            "action": "get_teams",
            "league_id": league_id,
            "APIkey": self.api_key
        }
        response = requests.get(self.BASE_URL, params=params, timeout=30)
        response.raise_for_status()
        
        teams = response.json()
        
        # Find specific team
        for team in teams:
            if team["team_name"].lower() == team_name.lower():
                return team
        
        return None
    
    def get_injured_players(self, league_id: int, team_name: str) -> List[Dict]:
        """
        Get list of injured players for a team
        
        Returns:
            List of injured players with their details
        """
        team = self.get_team_with_injuries(league_id, team_name)
        
        if not team:
            return []
        
        injured = [
            p for p in team.get("players", [])
            if p.get("player_injured") == "Yes"
        ]
        
        return injured
    
    def get_team_recent_matches(self, team_id: int, limit: int = 5) -> List[Dict]:
        """
        Fetch recent matches for a team (for form analysis)
        
        Args:
            team_id: Team ID
            limit: Number of recent matches (default: 5)
        
        Returns:
            List of recent matches
        """
        from datetime import datetime, timedelta
        
        # Get matches from last 60 days
        to_date = datetime.now().strftime("%Y-%m-%d")
        from_date = (datetime.now() - timedelta(days=60)).strftime("%Y-%m-%d")
        
        params = {
            "action": "get_events",
            "from": from_date,
            "to": to_date,
            "team_id": team_id,
            "APIkey": self.api_key
        }
        response = requests.get(self.BASE_URL, params=params, timeout=30)
        response.raise_for_status()
        
        matches = response.json()
        
        # Return most recent matches (sorted by date)
        matches_sorted = sorted(
            matches,
            key=lambda x: x.get("match_date", ""),
            reverse=True
        )
        
        return matches_sorted[:limit]
    
    def get_h2h_matches(self, team1_name: str, team2_name: str, limit: int = 10) -> List[Dict]:
        """
        Fetch head-to-head matches between two teams
        
        Args:
            team1_name: First team name
            team2_name: Second team name
            limit: Number of recent H2H matches
        
        Returns:
            List of H2H matches
        """
        from datetime import datetime, timedelta
        
        # Get matches from last 3 years
        to_date = datetime.now().strftime("%Y-%m-%d")
        from_date = (datetime.now() - timedelta(days=1095)).strftime("%Y-%m-%d")
        
        params = {
            "action": "get_events",
            "from": from_date,
            "to": to_date,
            "APIkey": self.api_key
        }
        response = requests.get(self.BASE_URL, params=params, timeout=30)
        response.raise_for_status()
        
        all_matches = response.json()
        
        # Filter for matches between these two teams
        h2h_matches = [
            m for m in all_matches
            if (m.get("match_hometeam_name") == team1_name and m.get("match_awayteam_name") == team2_name) or
               (m.get("match_hometeam_name") == team2_name and m.get("match_awayteam_name") == team1_name)
        ]
        
        # Sort by date (most recent first)
        h2h_matches_sorted = sorted(
            h2h_matches,
            key=lambda x: x.get("match_date", ""),
            reverse=True
        )
        
        return h2h_matches_sorted[:limit]


# Example usage
if __name__ == "__main__":
    import os
    
    api_key = os.getenv("APIFOOTBALL_API_KEY")
    fetcher = APIFootballFetcher(api_key)
    
    # Get injuries for Real Madrid (league_id=302 for La Liga)
    injured_players = fetcher.get_injured_players(league_id=302, team_name="Real Madrid")
    
    print("Real Madrid - Injured Players:")
    for player in injured_players:
        name = player.get("player_name")
        position = player.get("player_type")
        games = player.get("player_match_played", "0")
        print(f"  {name} ({position}): {games} games played")
    
    # Get recent form for team_id=76 (Real Madrid)
    recent_matches = fetcher.get_team_recent_matches(team_id=76, limit=5)
    
    print("\nReal Madrid - Last 5 Matches:")
    for match in recent_matches:
        home = match.get("match_hometeam_name")
        away = match.get("match_awayteam_name")
        score = f"{match.get('match_hometeam_score')}-{match.get('match_awayteam_score')}"
        date = match.get("match_date")
        print(f"  {date}: {home} {score} {away}")
    
    # Get H2H between Real Madrid and Barcelona
    h2h = fetcher.get_h2h_matches(team1_name="Real Madrid", team2_name="Barcelona", limit=5)
    
    print("\nReal Madrid vs Barcelona - Last 5 H2H:")
    for match in h2h:
        home = match.get("match_hometeam_name")
        away = match.get("match_awayteam_name")
        score = f"{match.get('match_hometeam_score')}-{match.get('match_awayteam_score')}"
        date = match.get("match_date")
        print(f"  {date}: {home} {score} {away}")
```

---

## Team/League ID Mapping

**Note:** APIfootball uses internal team/league IDs. Must map names to IDs.

### Common League IDs
| League | ID |
|------|-----|
| Premier League | 152 |
| La Liga | 302 |
| Serie A | 207 |
| Bundesliga | 175 |
| Ligue 1 | 168 |

**Full mapping:** Call `get_leagues` endpoint or maintain lookup table in DB.

---

## Implementation Notes

### For Team Intelligence Agent

1. **Fetch injuries per team:**
   - Call `get_teams(league_id)` to get all teams with player data
   - Filter for specific team
   - Check `player_injured` field for each player
   - **2 requests per game** (6-10 requests/day for 3-5 games)

2. **AI Analysis Required:**
   - Raw injury list NOT sufficient for betting
   - Agent must determine if injured players are starters vs bench warmers
   - Cross-reference with `player_match_played`, `player_goals`, `player_type`

### For Game Intelligence Agent

1. **Fetch H2H:**
   - Call `get_events(from, to)` to get historical matches
   - Filter results for matches between two specific teams
   - **1 request per game** (covers both teams)

2. **Fetch Team Form:**
   - Call `get_events(team_id, from, to)` per team
   - Get last 5 matches for form analysis
   - **2 requests per game** (one per team)

### Quota Management

**Daily Usage Estimate:**
- Injuries: 6-10 requests (2 per game × 3-5 games)
- H2H: 3-5 requests (1 per game)
- Team Form: 6-10 requests (2 per game × 3-5 games)
- **Total:** 15-25 requests/day (buffer: 6,455 requests/day remaining)

**Rate:** 180 requests/hour = 3 requests/minute - more than sufficient

---

## Advantages Over api-football.com

1. **Actually FREE for 2025 data** (api-football.com is limited to 2021-2023 for free users)
2. **Higher rate limit** (180 req/hour vs 100 req/day)
3. **Simpler API** - less nested JSON structures
4. **No authentication headers** - just API key in URL
5. **Covers injuries, H2H, and team form** - one API for multiple verticals

---

## See Also

- [Injuries/Suspensions Vertical](../verticals/injuries_suspensions.md) - Use case for player injury data
- [H2H Vertical](../verticals/h2h.md) - Use case for H2H statistics
- [Team Intelligence Agent](../../../../status/pre_gambling_flow/PRE_GAMBLING_FLOW_TASKS.md#52-team-intelligence-agent-node) - Uses injury data
- [Game Intelligence Agent](../../../../status/pre_gambling_flow/PRE_GAMBLING_FLOW_TASKS.md#42-game-intelligence-agent-node) - Uses H2H data
- [Official API Docs](https://apifootball.com/documentation/)
