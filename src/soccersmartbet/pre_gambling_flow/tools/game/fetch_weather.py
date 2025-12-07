"""
Fetch weather forecast for match between two teams.

Clean interface: Accepts both team names, finds venue city, gets weather.
"""

import os
from datetime import datetime
from typing import Dict, Any, Optional, Tuple
import requests
from dotenv import load_dotenv

load_dotenv()

APIFOOTBALL_API_KEY = os.getenv("APIFOOTBALL_API_KEY")
APIFOOTBALL_BASE_URL = "https://apiv3.apifootball.com"
TIMEOUT = 10

# Major European leagues
MAJOR_LEAGUES = [152, 302, 207, 175, 168]  # PL, La Liga, Serie A, Bundesliga, Ligue 1


def _find_team_league(team_name: str) -> Tuple[Optional[str], Optional[int], Optional[str]]:
    """
    Search for team across all major leagues.
    
    Args:
        team_name: Team name to search for
    
    Returns:
        Tuple of (team_id, league_id, actual_team_name) or (None, None, None) if not found
    """
    if not APIFOOTBALL_API_KEY:
        return (None, None, None)
    
    for league_id in MAJOR_LEAGUES:
        try:
            response = requests.get(
                APIFOOTBALL_BASE_URL,
                params={"action": "get_teams", "league_id": league_id, "APIkey": APIFOOTBALL_API_KEY},
                timeout=TIMEOUT
            )
            
            if response.status_code != 200:
                continue
            
            teams = response.json()
            for team in teams:
                if team_name.lower() in team.get("team_name", "").lower():
                    return (team["team_key"], league_id, team["team_name"])
        except Exception:
            continue
    
    return (None, None, None)


def fetch_weather(home_team_name: str, away_team_name: str, match_datetime: str) -> Dict[str, Any]:
    """
    Fetch weather forecast for match between two teams.
    
    Automatically looks up home team's venue city and gets weather.
    Searches across all major European leagues.
    
    Args:
        home_team_name: Home team name (e.g., "Manchester City")
        away_team_name: Away team name (e.g., "Tottenham")
        match_datetime: Match datetime ISO format (e.g., "2025-12-15T15:00:00") - REQUIRED
    
    Returns:
        {
            "home_team": "Manchester City",
            "away_team": "Tottenham",
            "venue_city": "Manchester",
            "match_datetime": "2025-12-15T15:00:00",
            "temperature_celsius": 12.5,
            "precipitation_mm": 0.0,
            "precipitation_probability": 20,
            "wind_speed_kmh": 15.3,
            "conditions": "Clear" | "Rain" | "Heavy Rain" | "Snow",
            "error": None
        }
    """
    # Step 1: Get home team's venue city
    if not APIFOOTBALL_API_KEY:
        return {
            "home_team": home_team_name,
            "away_team": away_team_name,
            "venue_city": None,
            "match_datetime": match_datetime,
            "temperature_celsius": None,
            "precipitation_mm": None,
            "precipitation_probability": None,
            "wind_speed_kmh": None,
            "conditions": None,
            "error": "APIFOOTBALL_API_KEY not found"
        }
    
    try:
        # Find home team across all major leagues
        team_id, league_id, actual_name = _find_team_league(home_team_name)
        
        if not team_id:
            return {
                "home_team": home_team_name,
                "away_team": away_team_name,
                "venue_city": None,
                "match_datetime": match_datetime,
                "temperature_celsius": None,
                "precipitation_mm": None,
                "precipitation_probability": None,
                "wind_speed_kmh": None,
                "conditions": None,
                "error": f"Team '{home_team_name}' not found in any major league"
            }
        
        # Get team's venue data
        teams_response = requests.get(
            APIFOOTBALL_BASE_URL,
            params={"action": "get_teams", "league_id": league_id, "APIkey": APIFOOTBALL_API_KEY},
            timeout=TIMEOUT
        )
        
        if teams_response.status_code != 200:
            return {
                "home_team": home_team_name,
                "away_team": away_team_name,
                "venue_city": None,
                "match_datetime": match_datetime,
                "temperature_celsius": None,
                "precipitation_mm": None,
                "precipitation_probability": None,
                "wind_speed_kmh": None,
                "conditions": None,
                "error": f"Teams API error: {teams_response.status_code}"
            }
        
        teams = teams_response.json()
        venue_city = None
        
        for team in teams:
            if team["team_key"] == team_id:
                venue_city = team.get("venue", {}).get("venue_city")
                break
        
        if not venue_city:
            return {
                "home_team": home_team_name,
                "away_team": away_team_name,
                "venue_city": None,
                "match_datetime": match_datetime,
                "temperature_celsius": None,
                "precipitation_mm": None,
                "precipitation_probability": None,
                "wind_speed_kmh": None,
                "conditions": None,
                "error": f"Venue city not found for team '{home_team_name}'"
            }
    
    except Exception as e:
        return {
            "home_team": home_team_name,
            "away_team": away_team_name,
            "venue_city": None,
            "match_datetime": match_datetime,
            "temperature_celsius": None,
            "precipitation_mm": None,
            "precipitation_probability": None,
            "wind_speed_kmh": None,
            "conditions": None,
            "error": f"Error fetching venue: {str(e)}"
        }
    
    # Step 2: Use geocoding API to get coordinates for ANY city worldwide
    try:
        # Use OpenStreetMap Nominatim API (free, no API key required)
        geocode_url = "https://nominatim.openstreetmap.org/search"
        geocode_params = {
            "q": venue_city,
            "format": "json",
            "limit": 1
        }
        geocode_headers = {
            "User-Agent": "SoccerSmartBet/1.0"  # Required by Nominatim
        }
        
        geocode_response = requests.get(
            geocode_url,
            params=geocode_params,
            headers=geocode_headers,
            timeout=10
        )
        
        if geocode_response.status_code != 200:
            return {
                "home_team": home_team_name,
                "away_team": away_team_name,
                "venue_city": venue_city,
                "match_datetime": match_datetime,
                "temperature_celsius": None,
                "precipitation_mm": None,
                "precipitation_probability": None,
                "wind_speed_kmh": None,
                "conditions": None,
                "error": f"Geocoding API error: {geocode_response.status_code}"
            }
        
        geocode_data = geocode_response.json()
        
        if not geocode_data:
            return {
                "home_team": home_team_name,
                "away_team": away_team_name,
                "venue_city": venue_city,
                "match_datetime": match_datetime,
                "temperature_celsius": None,
                "precipitation_mm": None,
                "precipitation_probability": None,
                "wind_speed_kmh": None,
                "conditions": None,
                "error": f"City '{venue_city}' not found by geocoding service"
            }
        
        latitude = float(geocode_data[0]["lat"])
        longitude = float(geocode_data[0]["lon"])
        
        # Parse match datetime
        try:
            match_dt = datetime.fromisoformat(match_datetime.replace('Z', '+00:00'))
        except ValueError:
            return {
                "home_team": home_team_name,
                "away_team": away_team_name,
                "venue_city": venue_city,
                "match_datetime": match_datetime,
                "temperature_celsius": None,
                "precipitation_mm": None,
                "precipitation_probability": None,
                "wind_speed_kmh": None,
                "conditions": None,
                "error": f"Invalid datetime format"
            }
        
        match_date = match_dt.strftime("%Y-%m-%d")
        match_hour = match_dt.strftime("%Y-%m-%dT%H:00")
        
        # Call Open-Meteo API
        base_url = "https://api.open-meteo.com/v1/forecast"
        params = {
            "latitude": latitude,
            "longitude": longitude,
            "hourly": "temperature_2m,precipitation,precipitation_probability,windspeed_10m",
            "start_date": match_date,
            "end_date": match_date
        }
        
        response = requests.get(base_url, params=params, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        hourly = data.get("hourly", {})
        times = hourly.get("time", [])
        temperatures = hourly.get("temperature_2m", [])
        precipitation_values = hourly.get("precipitation", [])
        precipitation_probs = hourly.get("precipitation_probability", [])
        wind_speeds = hourly.get("windspeed_10m", [])
        
        # Find index for match hour
        try:
            hour_index = times.index(match_hour)
        except ValueError:
            return {
                "home_team": home_team_name,
                "away_team": away_team_name,
                "venue_city": venue_city,
                "match_datetime": match_datetime,
                "temperature_celsius": None,
                "precipitation_mm": None,
                "precipitation_probability": None,
                "wind_speed_kmh": None,
                "conditions": None,
                "error": f"Match time not in forecast"
            }
        
        temperature = temperatures[hour_index]
        precipitation = precipitation_values[hour_index]
        precip_prob = precipitation_probs[hour_index] if hour_index < len(precipitation_probs) else 0
        wind_speed = wind_speeds[hour_index]
        
        # Determine conditions
        if precipitation >= 5.0:
            conditions = "Heavy Rain"
        elif precipitation >= 0.5:
            conditions = "Rain"
        elif temperature < 0 and precipitation > 0:
            conditions = "Snow"
        else:
            conditions = "Clear"
        
        return {
            "home_team": home_team_name,
            "away_team": away_team_name,
            "venue_city": venue_city,
            "match_datetime": match_datetime,
            "temperature_celsius": temperature,
            "precipitation_mm": precipitation,
            "precipitation_probability": precip_prob,
            "wind_speed_kmh": wind_speed,
            "conditions": conditions,
            "error": None
        }
    
    except requests.Timeout:
        return {
            "home_team": home_team_name,
            "away_team": away_team_name,
            "venue_city": venue_city,
            "match_datetime": match_datetime,
            "temperature_celsius": None,
            "precipitation_mm": None,
            "precipitation_probability": None,
            "wind_speed_kmh": None,
            "conditions": None,
            "error": "API timeout"
        }
    except Exception as e:
        return {
            "home_team": home_team_name,
            "away_team": away_team_name,
            "venue_city": venue_city,
            "match_datetime": match_datetime,
            "temperature_celsius": None,
            "precipitation_mm": None,
            "precipitation_probability": None,
            "wind_speed_kmh": None,
            "conditions": None,
            "error": f"Error: {str(e)}"
        }
