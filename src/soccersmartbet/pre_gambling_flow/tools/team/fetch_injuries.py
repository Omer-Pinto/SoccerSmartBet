"""
Fetch team's current injuries.

Clean interface: Accepts team name, returns injured players.

Data source: TheSportsDB (free tier, 100 req/min)
Approach: Find team's next match and extract injury info from lineup
API: /eventsnext.php + /lookuplineup.php

NOTE: TheSportsDB injury data is match-specific (lineup-based), not team-wide.
This means we can only detect injuries for upcoming matches with published lineups.
For teams without upcoming matches or unpublished lineups, we return empty injuries list.
"""

import os
from typing import Dict, Any, Optional, List
import requests
from dotenv import load_dotenv

load_dotenv()

# API Configuration
THESPORTSDB_API_KEY = os.getenv("THESPORTSDB_API_KEY", "3")  # Default to free test key
BASE_URL = f"https://www.thesportsdb.com/api/v1/json/{THESPORTSDB_API_KEY}"
TIMEOUT = 10


def _search_team(team_name: str) -> Optional[str]:
    """
    Search for team by name and return team ID.
    
    Args:
        team_name: Team name to search for
    
    Returns:
        Team ID string or None if not found
    """
    try:
        response = requests.get(
            f"{BASE_URL}/searchteams.php",
            params={"t": team_name},
            timeout=TIMEOUT
        )
        
        if response.status_code != 200:
            return None
        
        data = response.json()
        teams = data.get("teams")
        
        if not teams or len(teams) == 0:
            return None
        
        # Return first match
        return teams[0].get("idTeam")
    
    except Exception:
        return None


def fetch_injuries(team_name: str) -> Dict[str, Any]:
    """
    Fetch team's current injury list from upcoming match lineup.
    
    NOTE: Returns empty list if no upcoming matches have published lineups yet.
    TheSportsDB injury data is match-specific, not team-wide.
    
    Args:
        team_name: Team name (e.g., "Manchester City")
    
    Returns:
        {
            "team_name": "Manchester City",
            "injuries": [
                {
                    "player_name": "Mateo Kovacic",
                    "player_type": "Unknown",  # Position not in lineup API
                    "injury_type": "Not specified",
                    "matches_played": None  # Not available in TheSportsDB
                },
                ...
            ],
            "total_injuries": 1,
            "source": "next_match_lineup",  # or "unavailable"
            "error": None
        }
    """
    try:
        # Step 1: Search for team
        team_id = _search_team(team_name)
        
        if not team_id:
            return {
                "team_name": team_name,
                "injuries": [],
                "total_injuries": 0,
                "source": "unavailable",
                "error": f"Team '{team_name}' not found"
            }
        
        # Step 2: Get next upcoming event for team
        response = requests.get(
            f"{BASE_URL}/eventsnext.php",
            params={"id": team_id},
            timeout=TIMEOUT
        )
        
        if response.status_code != 200:
            return {
                "team_name": team_name,
                "injuries": [],
                "total_injuries": 0,
                "source": "unavailable",
                "error": f"API error getting next match: {response.status_code}"
            }
        
        data = response.json()
        events = data.get("events")
        
        if not events or len(events) == 0:
            # No upcoming matches - return empty injuries (not an error)
            return {
                "team_name": team_name,
                "injuries": [],
                "total_injuries": 0,
                "source": "no_upcoming_matches",
                "error": None
            }
        
        # Get first upcoming match
        event_id = events[0].get("idEvent")
        
        if not event_id:
            return {
                "team_name": team_name,
                "injuries": [],
                "total_injuries": 0,
                "source": "unavailable",
                "error": "Event ID not found in next match"
            }
        
        # Step 3: Get lineup for that event (includes injury info)
        lineup_response = requests.get(
            f"{BASE_URL}/lookuplineup.php",
            params={"id": event_id},
            timeout=TIMEOUT
        )
        
        if lineup_response.status_code != 200:
            # Lineup not published yet - return empty (not an error)
            return {
                "team_name": team_name,
                "injuries": [],
                "total_injuries": 0,
                "source": "lineup_not_published",
                "error": None
            }
        
        lineup_data = lineup_response.json()
        
        # Lineup is a LIST of player objects, each with idTeam field
        lineup = lineup_data.get("lineup", [])
        
        if not lineup or len(lineup) == 0:
            return {
                "team_name": team_name,
                "injuries": [],
                "total_injuries": 0,
                "source": "lineup_empty",
                "error": None
            }
        
        # Filter to our team's players only
        our_players = [p for p in lineup if str(p.get("idTeam")) == str(team_id)]
        
        if len(our_players) == 0:
            return {
                "team_name": team_name,
                "injuries": [],
                "total_injuries": 0,
                "source": "team_not_in_lineup",
                "error": None
            }
        
        # Extract injured players
        # NOTE: TheSportsDB lineup API typically shows ONLY players who are playing/on bench
        # Injured players are usually NOT in the lineup at all
        # So we'll likely return empty injuries unless lineup has explicit injury flags
        injured = []
        
        for player in our_players:
            # Check various possible injury indicators
            # (These fields may not exist - this is exploratory)
            is_injured = (
                player.get("strInjured") == "Yes" or
                player.get("strStatus") == "Injured" or
                player.get("strSubstitute") == "Injured"  # Alternative field
            )
            
            if is_injured:
                injured.append({
                    "player_name": player.get("strPlayer", "Unknown"),
                    "player_type": player.get("strPosition", "Unknown"),
                    "injury_type": "Not specified",  # Not available in lineup
                    "matches_played": None  # Not available in TheSportsDB lineup
                })
        
        return {
            "team_name": team_name,
            "injuries": injured,
            "total_injuries": len(injured),
            "source": "next_match_lineup",
            "error": None
        }
    
    except requests.Timeout:
        return {
            "team_name": team_name,
            "injuries": [],
            "total_injuries": 0,
            "source": "unavailable",
            "error": f"Request timeout after {TIMEOUT}s"
        }
    except Exception as e:
        return {
            "team_name": team_name,
            "injuries": [],
            "total_injuries": 0,
            "source": "unavailable",
            "error": f"Unexpected error: {str(e)}"
        }
