# FotMob API (via mobfot)

**Package:** `pip install mobfot`
**Cost:** FREE (no API key)
**Rate Limits:** None observed

## What It Provides
- Team form (W/D/L with scores)
- League standings (ALL teams, not just top 5)
- Venue info (name, city, capacity)
- Injuries (via match lineup)
- Last/next match dates

## Usage
```python
from mobfot import MobFot
client = MobFot()

# League standings
league = client.get_league(47)  # Premier League

# Team data (form, venue, lastMatch)
team = client.get_team(8650)  # Man City

# Match details (injuries in lineup)
match = client.get_match_details(4837260)
```

## League IDs
- Premier League: 47
- La Liga: 87
- Serie A: 55
- Bundesliga: 54
- Ligue 1: 53

## Limitations
- Unofficial API (could change)
- No individual player stats
- Position IDs in injury data are unreliable
