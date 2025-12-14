# FotMob API (via mobfot)

**Website:** https://www.fotmob.com
**Python Package:** `mobfot` (unofficial)
**Type:** Unofficial REST API
**Cost:** FREE (no API key required)
**Status:** ✅ Primary source for team data (Batch 6)

---

## Overview

FotMob is a popular football statistics app. The `mobfot` Python package provides access to FotMob's unofficial API. It's the **primary source for team-related tools** in SoccerSmartBet after the apifootball.com trial expired.

**Why FotMob?**
- NO rate limits (tested 10+ rapid requests)
- NO API key required
- Returns ALL teams in standings (TheSportsDB only gave top 5)
- Comprehensive data: form, venue, injuries, league position, last match

---

## Features

- ✅ **No API key required** (instant use, no signup)
- ✅ **No rate limits observed** (tested extensively)
- ✅ Team form (last 5+ matches with W/D/L and scores)
- ✅ Venue information (name, city, capacity)
- ✅ League standings (ALL teams, not just top 5)
- ✅ Injuries (via match lineup.unavailable)
- ✅ Last match date (for recovery time calculation)
- ✅ 9 major leagues supported

---

## Supported Leagues

| League | FotMob ID |
|--------|-----------|
| Premier League | 47 |
| La Liga | 87 |
| Serie A | 55 |
| Bundesliga | 54 |
| Ligue 1 | 53 |
| Champions League | 42 |
| Europa League | 73 |
| Eredivisie | 57 |
| Primeira Liga | 61 |

---

## Installation

```bash
pip install mobfot
```

Or add to `pyproject.toml`:
```toml
[project]
dependencies = [
    "mobfot>=0.0.8",
]
```

---

## Python Code Examples

### Basic Usage

```python
from mobfot import MobFot

client = MobFot()

# Get league standings (returns ALL teams)
league_data = client.get_league(47)  # Premier League
table = league_data.get("table", [])
for group in table:
    for row in group.get("data", {}).get("table", {}).get("all", []):
        print(f"{row['idx']}. {row['name']} - {row['pts']} pts")

# Get team data
team_data = client.get_team(8650)  # Manchester City
overview = team_data.get("overview", {})

# Team form
team_form = overview.get("teamForm", [])
for match in team_form[:5]:
    result = match.get("result", "?")  # W, D, L
    opponent = match.get("opponent", {}).get("name", "Unknown")
    print(f"{result} vs {opponent}")

# Venue info
venue = overview.get("venue", {}).get("widget", {})
print(f"Stadium: {venue.get('name')} in {venue.get('city')}")

# Last match (for recovery time)
last_match = overview.get("lastMatch", {})
print(f"Last match ID: {last_match.get('id')}")
```

### Team Name Resolution

The main challenge is converting user-provided team names to FotMob IDs. Our `fotmob_client.py` handles this:

```python
from soccersmartbet.pre_gambling_flow.tools.fotmob_client import get_fotmob_client

client = get_fotmob_client()

# Find team by name (searches across all major leagues)
team_info = client.find_team("Manchester City")
# Returns: {"id": 8650, "name": "Manchester City", "league_id": 47, "league_name": "Premier League"}

# Get full team data
team_data = client.get_team_data(team_info["id"])
```

### Getting Injuries

Injuries are available via match lineup data:

```python
from mobfot import MobFot

client = MobFot()

# Get match data (need match ID from team's fixture list)
match_data = client.get_match(4193455)

# Injuries in lineup
lineup = match_data.get("content", {}).get("lineup", {})
home_unavailable = lineup.get("homeTeam", {}).get("unavailable", [])
away_unavailable = lineup.get("awayTeam", {}).get("unavailable", [])

for player in home_unavailable:
    name = player.get("name", "Unknown")
    reason = player.get("injuryStringShort", "Unknown")
    print(f"OUT: {name} ({reason})")
```

---

## Data Structures

### League Table Response

```json
{
  "table": [
    {
      "data": {
        "table": {
          "all": [
            {
              "idx": 1,
              "id": 8650,
              "name": "Manchester City",
              "played": 15,
              "wins": 10,
              "draws": 3,
              "losses": 2,
              "pts": 33,
              "qualColor": "#2196f3"
            }
          ]
        }
      }
    }
  ]
}
```

### Team Form Response

```json
{
  "overview": {
    "teamForm": [
      {
        "result": "W",
        "resultString": "W",
        "opponent": {
          "id": 8456,
          "name": "Liverpool"
        },
        "home": true,
        "date": "2025-12-01",
        "matchId": 4193455
      }
    ]
  }
}
```

### Venue Response

```json
{
  "overview": {
    "venue": {
      "widget": {
        "name": "Etihad Stadium",
        "city": "Manchester",
        "capacity": 55097
      }
    }
  }
}
```

---

## Implementation in SoccerSmartBet

### Tools Using FotMob

| Tool | FotMob Data Used |
|------|------------------|
| `fetch_form` | `team.overview.teamForm` |
| `fetch_venue` | `team.overview.venue.widget` |
| `fetch_injuries` | `match.content.lineup.unavailable` |
| `fetch_league_position` | `league.table` |
| `calculate_recovery_time` | `team.overview.lastMatch` |
| `fetch_weather` | `team.overview.venue.widget.city` (then Open-Meteo) |

### fotmob_client.py Architecture

```python
# Location: src/soccersmartbet/pre_gambling_flow/tools/fotmob_client.py

class FotMobClient:
    """Wrapper around mobfot with team name resolution"""

    def find_team(self, team_name: str) -> Optional[Dict]:
        """Find team by name across all major leagues"""
        # Searches league standings tables
        # Handles name normalization (accents, FC/CF prefixes)

    def get_team_data(self, team_id: int) -> Optional[Dict]:
        """Get full team data including form, venue, lastMatch"""

    def get_match_data(self, match_id: int) -> Optional[Dict]:
        """Get match details including weather, lineup, injuries"""

    def get_league_table(self, league_id: int) -> Optional[List]:
        """Get league standings with all teams"""
```

---

## Limitations

1. **Unofficial API:** Could change or be blocked without notice
2. **No individual player stats:** Cannot get goals/assists per player
3. **Injury data requires match ID:** Need to find upcoming match first
4. **No direct search endpoint:** Must iterate through league tables

---

## Error Handling

```python
from soccersmartbet.pre_gambling_flow.tools.fotmob_client import get_fotmob_client

client = get_fotmob_client()

# Team not found
team = client.find_team("Nonexistent FC")
if not team:
    return {"error": "Team not found in any major league"}

# API failure
try:
    team_data = client.get_team_data(team["id"])
except Exception as e:
    return {"error": f"FotMob API error: {str(e)}"}
```

---

## Comparison with Previous Sources

| Feature | apifootball.com | FotMob (mobfot) |
|---------|-----------------|-----------------|
| Rate Limits | 180 req/hour | None observed |
| API Key | Required (trial) | Not required |
| Standings | Full table | Full table |
| Team Form | ✅ | ✅ |
| Injuries | ✅ | ✅ (via lineup) |
| Player Stats | ✅ | ❌ |
| Trial Period | EXPIRED | N/A (unofficial) |

---

## See Also

- [Executive Summary](../executive_summary.md) - Data stack overview
- [Team Intelligence Agent](../../../../status/pre_gambling_flow/PRE_GAMBLING_FLOW_TASKS.md#52-team-intelligence-agent-node) - Uses FotMob tools
- [mobfot PyPI](https://pypi.org/project/mobfot/) - Package documentation
- [FotMob Website](https://www.fotmob.com) - Official FotMob site
