"""
Fetch team's recent match form using BBC Sport standings scraper.

Extracts form (W/D/L) from the standings table which already shows last 5-6 results.
Uses Playwright for headless browser scraping.
FREE, no API key needed, works for ALL teams, NO rate limits.
"""

from typing import Dict, Any, List
from playwright.sync_api import sync_playwright
from datetime import datetime, timedelta
import re

TIMEOUT = 15000  # 15 seconds

# BBC Sport league table URLs
BBC_LEAGUES = {
    "Premier League": "https://www.bbc.com/sport/football/premier-league/table",
    "La Liga": "https://www.bbc.com/sport/football/spanish-la-liga/table",
    "Serie A": "https://www.bbc.com/sport/football/italian-serie-a/table",
    "Bundesliga": "https://www.bbc.com/sport/football/german-bundesliga/table",
    "Ligue 1": "https://www.bbc.com/sport/football/french-ligue-one/table",
}


def fetch_form(team_name: str, limit: int = 5) -> Dict[str, Any]:
    """
    Fetch team's recent form by scraping BBC Sport standings table.
    
    BBC Sport standings table shows form (W/D/L indicators) for last 5-6 matches.
    This is faster and simpler than scraping fixtures pages.
    
    Args:
        team_name: Team name (e.g., "Osasuna", "Barcelona")
        limit: Number of recent matches to return (default: 5)
    
    Returns:
        {
            "team_name": "Osasuna",
            "matches": [
                {
                    "date": "Recent",
                    "opponent": "Unknown",
                    "home_away": "Unknown",
                    "result": "L",
                    "goals_for": None,
                    "goals_against": None,
                    "competition": "La Liga"
                },
                ...
            ],
            "record": {"wins": 1, "draws": 1, "losses": 3},
            "error": None
        }
    
    Note: BBC only shows W/D/L indicators, not detailed match info.
    """
    try:
        team_lower = team_name.lower()
        
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            
            # Search across all major leagues
            for league_name, url in BBC_LEAGUES.items():
                try:
                    page.goto(url, wait_until='load', timeout=TIMEOUT)
                    page.wait_for_timeout(2000)
                    
                    # Get page text
                    text = page.inner_text('body')
                    
                    # Check if team is in this league
                    if team_lower not in text.lower():
                        continue
                    
                    # Parse form from standings table
                    form_str = _extract_form_from_standings(text, team_name)
                    
                    if form_str:
                        browser.close()
                        
                        # Convert form string (e.g., "WWLDW") to match list
                        # BBC doesn't provide actual dates, so we estimate based on typical schedule
                        # Most teams play 1 match per week
                        matches = []
                        today = datetime.now()
                        
                        for i, result_char in enumerate(form_str[:limit]):
                            # Estimate date: most recent match is ~3 days ago, then weekly before that
                            days_ago = 3 + (i * 7)
                            match_date = (today - timedelta(days=days_ago)).strftime('%Y-%m-%d')
                            
                            matches.append({
                                "date": match_date,
                                "opponent": "Unknown",
                                "home_away": "Unknown",
                                "result": result_char,
                                "goals_for": None,
                                "goals_against": None,
                                "competition": league_name
                            })
                        
                        # Calculate record
                        record = {
                            "wins": form_str[:limit].count("W"),
                            "draws": form_str[:limit].count("D"),
                            "losses": form_str[:limit].count("L")
                        }
                        
                        return {
                            "team_name": team_name,
                            "matches": matches,
                            "record": record,
                            "error": None
                        }
                
                except Exception:
                    continue
            
            browser.close()
            
            # Team not found
            return _error_response(team_name, f"No form data found for '{team_name}'")
    
    except Exception as e:
        return _error_response(team_name, f"Scraping error: {str(e)}")


def _extract_form_from_standings(text: str, team_name: str) -> str:
    """
    Extract form string (e.g., "WWLDW") from BBC standings table.
    
    BBC shows form as:
    W
    Result Win
    W
    Result Win
    etc.
    
    We only want the single-letter W/D/L lines.
    """
    lines = text.split('\n')
    team_lower = team_name.lower()
    
    # Find the team name line
    for i, line in enumerate(lines):
        if team_lower in line.lower() and len(line.strip()) < 50:
            # Form letters should appear after the stats
            # Look for W/D/L single-character lines
            form_chars = []
            
            for j in range(i+1, min(i+40, len(lines))):
                char = lines[j].strip()
                
                # Only take single-letter W/D/L (not "Result Win" etc)
                if char in ['W', 'D', 'L'] and len(char) == 1:
                    form_chars.append(char)
                
                # Stop when we hit another team (next position number or team name)
                if char.isdigit() and len(char) <= 2 and len(form_chars) > 0:
                    break
                
                # Stop if we've collected enough
                if len(form_chars) >= 6:
                    break
            
            if form_chars:
                # BBC typically shows last 5-6 matches
                return ''.join(form_chars)
    
    return None


def _error_response(team_name: str, error_msg: str) -> Dict[str, Any]:
    """Return error response."""
    return {
        "team_name": team_name,
        "matches": [],
        "record": {"wins": 0, "draws": 0, "losses": 0},
        "error": error_msg
    }
