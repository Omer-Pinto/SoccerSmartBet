"""
Fetch team's current league position using BBC Sport web scraping.

Uses Playwright for headless browser scraping.
FREE, no API key needed, works for ALL teams.
"""

from typing import Dict, Any
from playwright.sync_api import sync_playwright
import re

TIMEOUT = 15000  # 15 seconds in milliseconds

# BBC Sport league URLs
BBC_LEAGUES = {
    "Premier League": "https://www.bbc.com/sport/football/premier-league/table",
    "La Liga": "https://www.bbc.com/sport/football/spanish-la-liga/table",
    "Serie A": "https://www.bbc.com/sport/football/italian-serie-a/table",
    "Bundesliga": "https://www.bbc.com/sport/football/german-bundesliga/table",
    "Ligue 1": "https://www.bbc.com/sport/football/french-ligue-one/table",
}


def fetch_league_position(team_name: str) -> Dict[str, Any]:
    """
    Fetch team's current league position by scraping BBC Sport.
    
    Searches across all major leagues to find the team.
    Uses Playwright headless browser.
    
    Args:
        team_name: Team name (e.g., "Osasuna", "Barcelona")
    
    Returns:
        {
            "team_name": "Osasuna",
            "league_name": "La Liga",
            "position": 15,
            "played": 15,
            "won": 4,
            "draw": 3,
            "lost": 8,
            "goals_for": 14,
            "goals_against": 18,
            "goal_difference": -4,
            "points": 15,
            "form": "LDDL",  # Last few results
            "error": None
        }
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
                    page.wait_for_timeout(2000)  # Wait 2 seconds for JS
                    
                    # Get page text
                    text = page.inner_text('body')
                    
                    # Check if team is in this league
                    if team_lower not in text.lower():
                        continue
                    
                    # Parse the standings
                    result = _parse_bbc_standings(text, team_name, league_name)
                    if result:
                        browser.close()
                        return result
                
                except Exception:
                    continue
            
            browser.close()
            
            # Team not found in any league
            return _error_response(team_name, f"Team '{team_name}' not found in any supported league")
    
    except Exception as e:
        return _error_response(team_name, f"Scraping error: {str(e)}")


def _parse_bbc_standings(text: str, team_name: str, league_name: str) -> Dict[str, Any]:
    """
    Parse BBC Sport standings text to extract team data.
    
    BBC format:
    Position
    Team Name
    Played Won Draw Lost GF GA GD Points
    Form indicators (W/D/L)
    """
    lines = text.split('\n')
    team_lower = team_name.lower()
    
    for i, line in enumerate(lines):
        if team_lower in line.lower() and len(line.strip()) < 50:  # Team name line
            try:
                # Previous line should be position
                position = int(lines[i-1].strip())
                
                # Next line should have stats: Played W D L GF GA GD Points
                stats_line = lines[i+1].strip()
                stats = stats_line.split()
                
                # Filter to only numbers (removes tabs, etc)
                numbers = [s for s in stats if re.match(r'^-?\d+$', s)]
                
                if len(numbers) >= 8:
                    # Parse: Played, Won, Draw, Lost, GF, GA, GD, Points
                    played = int(numbers[0])
                    won = int(numbers[1])
                    draw = int(numbers[2])
                    lost = int(numbers[3])
                    gf = int(numbers[4])
                    ga = int(numbers[5])
                    gd = int(numbers[6])
                    points = int(numbers[7])
                    
                    # Try to extract form (W/D/L letters after stats)
                    form_letters = []
                    for j in range(i+2, min(i+15, len(lines))):
                        if lines[j].strip() in ['W', 'D', 'L']:
                            form_letters.append(lines[j].strip())
                        if len(form_letters) >= 5:
                            break
                    
                    form = ''.join(form_letters[-5:]) if form_letters else None
                    
                    return {
                        "team_name": team_name,
                        "league_name": league_name,
                        "position": position,
                        "played": played,
                        "won": won,
                        "draw": draw,
                        "lost": lost,
                        "goals_for": gf,
                        "goals_against": ga,
                        "goal_difference": gd,
                        "points": points,
                        "form": form,
                        "error": None
                    }
            
            except (ValueError, IndexError):
                continue
    
    return None


def _error_response(team_name: str, error_msg: str) -> Dict[str, Any]:
    """Return error response."""
    return {
        "team_name": team_name,
        "league_name": None,
        "position": None,
        "played": None,
        "won": None,
        "draw": None,
        "lost": None,
        "goals_for": None,
        "goals_against": None,
        "goal_difference": None,
        "points": None,
        "form": None,
        "error": error_msg
    }
