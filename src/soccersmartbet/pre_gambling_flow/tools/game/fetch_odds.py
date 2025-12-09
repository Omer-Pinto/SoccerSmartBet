"""
Fetch betting odds for a match between two teams.

Clean interface: Accepts team names, returns 1/X/2 odds in decimal format.
"""

import os
from typing import Dict, Any
import requests
from dotenv import load_dotenv

load_dotenv()

# API Configuration
ODDS_API_KEY = os.getenv("ODDS_API_KEY")
BASE_URL = "https://api.the-odds-api.com/v4"
TIMEOUT = 10

# Major soccer leagues to search
SOCCER_LEAGUES = [
    "soccer_epl",                    # Premier League
    "soccer_spain_la_liga",          # La Liga
    "soccer_italy_serie_a",          # Serie A
    "soccer_germany_bundesliga",     # Bundesliga
    "soccer_france_ligue_one",       # Ligue 1
    "soccer_uefa_champs_league",     # Champions League
    "soccer_uefa_europa_league",     # Europa League
]


def fetch_odds(home_team_name: str, away_team_name: str) -> Dict[str, Any]:
    """
    Fetch betting odds for a match between two teams.
    
    Searches across all major European leagues to find the upcoming match
    and returns decimal odds (Israeli format) for home win (1), draw (X),
    and away win (2).
    
    Args:
        home_team_name: Home team name (e.g., "Chelsea")
        away_team_name: Away team name (e.g., "Everton")
    
    Returns:
        {
            "home_team": "Chelsea",
            "away_team": "Everton",
            "match_id": "abc123def456",
            "commence_time": "2025-12-15T15:00:00Z",
            "odds_home": 2.10,      # Home win (1)
            "odds_draw": 3.40,      # Draw (X)
            "odds_away": 3.50,      # Away win (2)
            "bookmaker": "betfair",
            "error": None
        }
        
        On error:
        {
            "home_team": home_team_name,
            "away_team": away_team_name,
            "match_id": None,
            "commence_time": None,
            "odds_home": None,
            "odds_draw": None,
            "odds_away": None,
            "bookmaker": None,
            "error": "Error description"
        }
    """
    if not ODDS_API_KEY:
        return {
            "home_team": home_team_name,
            "away_team": away_team_name,
            "match_id": None,
            "commence_time": None,
            "odds_home": None,
            "odds_draw": None,
            "odds_away": None,
            "bookmaker": None,
            "error": "ODDS_API_KEY not found in environment"
        }
    
    try:
        # Search across all major leagues for upcoming match
        home_team_lower = home_team_name.lower()
        away_team_lower = away_team_name.lower()
        
        for sport_key in SOCCER_LEAGUES:
            try:
                response = requests.get(
                    f"{BASE_URL}/sports/{sport_key}/odds/",
                    params={
                        "apiKey": ODDS_API_KEY,
                        "regions": "eu",
                        "markets": "h2h",
                        "oddsFormat": "decimal"
                    },
                    timeout=TIMEOUT
                )
                
                if response.status_code != 200:
                    continue  # Try next league
                
                matches = response.json()
                
                # Find match between these two teams (fuzzy matching)
                for match in matches:
                    home = match.get("home_team", "").lower()
                    away = match.get("away_team", "").lower()
                    
                    # Check if team names match (fuzzy comparison)
                    home_matches = home_team_lower in home or home in home_team_lower
                    away_matches = away_team_lower in away or away in away_team_lower
                    
                    if home_matches and away_matches:
                        # Found the match! Extract odds
                        return _extract_odds_from_match(match, home_team_name, away_team_name)
                
            except requests.Timeout:
                continue  # Try next league
            except Exception:
                continue  # Try next league
        
        # No match found in any league
        return {
            "home_team": home_team_name,
            "away_team": away_team_name,
            "match_id": None,
            "commence_time": None,
            "odds_home": None,
            "odds_draw": None,
            "odds_away": None,
            "bookmaker": None,
            "error": f"No upcoming match found between {home_team_name} and {away_team_name}"
        }
    
    except Exception as e:
        return {
            "home_team": home_team_name,
            "away_team": away_team_name,
            "match_id": None,
            "commence_time": None,
            "odds_home": None,
            "odds_draw": None,
            "odds_away": None,
            "bookmaker": None,
            "error": f"Unexpected error: {str(e)}"
        }


def _extract_odds_from_match(match: Dict[str, Any], home_team_name: str, away_team_name: str) -> Dict[str, Any]:
    """
    Extract 1/X/2 odds from a match object.
    
    Prefers Betfair bookmaker, falls back to first available.
    """
    match_id = match.get("id")
    commence_time = match.get("commence_time")
    home_team = match.get("home_team")
    away_team = match.get("away_team")
    bookmakers = match.get("bookmakers", [])
    
    if not bookmakers:
        return {
            "home_team": home_team_name,
            "away_team": away_team_name,
            "match_id": match_id,
            "commence_time": commence_time,
            "odds_home": None,
            "odds_draw": None,
            "odds_away": None,
            "bookmaker": None,
            "error": "No bookmakers available for this match"
        }
    
    # Prefer Betfair, otherwise use first available
    preferred_bookmakers = ["betfair", "pinnacle", "bet365"]
    bookmaker = None
    
    for preferred in preferred_bookmakers:
        bookmaker = next(
            (b for b in bookmakers if b.get("key") == preferred),
            None
        )
        if bookmaker:
            break
    
    if not bookmaker:
        bookmaker = bookmakers[0]
    
    bookmaker_key = bookmaker.get("key", "unknown")
    
    # Extract h2h market
    markets = bookmaker.get("markets", [])
    h2h_market = next(
        (m for m in markets if m.get("key") == "h2h"),
        None
    )
    
    if not h2h_market:
        return {
            "home_team": home_team_name,
            "away_team": away_team_name,
            "match_id": match_id,
            "commence_time": commence_time,
            "odds_home": None,
            "odds_draw": None,
            "odds_away": None,
            "bookmaker": bookmaker_key,
            "error": "No h2h market available from bookmaker"
        }
    
    # Extract odds for home, draw, away
    outcomes = h2h_market.get("outcomes", [])
    odds_home = None
    odds_draw = None
    odds_away = None
    
    for outcome in outcomes:
        name = outcome.get("name", "").lower()
        price = outcome.get("price")
        
        if name == home_team.lower():
            odds_home = price
        elif name == away_team.lower():
            odds_away = price
        elif "draw" in name:
            odds_draw = price
    
    # Validate that we got all three odds
    if odds_home is None or odds_draw is None or odds_away is None:
        return {
            "home_team": home_team_name,
            "away_team": away_team_name,
            "match_id": match_id,
            "commence_time": commence_time,
            "odds_home": odds_home,
            "odds_draw": odds_draw,
            "odds_away": odds_away,
            "bookmaker": bookmaker_key,
            "error": "Incomplete odds data (missing home/draw/away)"
        }
    
    return {
        "home_team": home_team_name,
        "away_team": away_team_name,
        "match_id": match_id,
        "commence_time": commence_time,
        "odds_home": odds_home,
        "odds_draw": odds_draw,
        "odds_away": odds_away,
        "bookmaker": bookmaker_key,
        "error": None
    }
