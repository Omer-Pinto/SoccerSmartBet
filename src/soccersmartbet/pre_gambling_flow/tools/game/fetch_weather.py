"""
Fetch weather forecast for match between two teams.

Uses fetch_venue to get venue city, then Open-Meteo for weather.
NO dependency on APIfootball!
"""

from datetime import datetime
from typing import Dict, Any
import requests

from .fetch_venue import fetch_venue

TIMEOUT = 10


def fetch_weather(home_team_name: str, away_team_name: str, match_datetime: str) -> Dict[str, Any]:
    """
    Fetch weather forecast for match.
    
    Uses fetch_venue to get the city, then queries Open-Meteo.
    
    Args:
        home_team_name: Home team name
        away_team_name: Away team name  
        match_datetime: Match datetime in ISO format (e.g., "2024-12-10T15:00:00")
    
    Returns:
        Weather forecast dict with temperature, precipitation, wind, etc.
    """
    # Step 1: Get venue city using fetch_venue
    venue_result = fetch_venue(home_team_name, away_team_name)
    
    if venue_result.get("error"):
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
            "error": f"Could not find venue: {venue_result['error']}"
        }
    
    venue_city = venue_result.get("venue_city")
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
            "error": "Venue city not available"
        }
    
    # Step 2: Geocode the city using Nominatim
    try:
        geocode_url = "https://nominatim.openstreetmap.org/search"
        geocode_response = requests.get(
            geocode_url,
            params={"q": venue_city, "format": "json", "limit": 1},
            headers={"User-Agent": "SoccerSmartBet/1.0"},
            timeout=TIMEOUT
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
                "error": f"Geocoding error: {geocode_response.status_code}"
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
                "error": f"City '{venue_city}' not found"
            }
        
        latitude = float(geocode_data[0]["lat"])
        longitude = float(geocode_data[0]["lon"])
        
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
            "error": f"Geocoding failed: {str(e)}"
        }
    
    # Step 3: Parse match datetime
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
            "error": "Invalid datetime format"
        }
    
    match_date = match_dt.strftime("%Y-%m-%d")
    match_hour = match_dt.strftime("%Y-%m-%dT%H:00")
    
    # Check if match is too far in future (Open-Meteo limit: 16 days)
    from datetime import datetime as dt
    days_until_match = (match_dt.replace(tzinfo=None) - dt.now()).days
    
    if days_until_match > 16:
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
            "error": f"Match is {days_until_match} days away - weather forecasts only available for next 16 days"
        }
    
    # Step 4: Get weather from Open-Meteo
    try:
        weather_response = requests.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": latitude,
                "longitude": longitude,
                "hourly": "temperature_2m,precipitation,precipitation_probability,windspeed_10m",
                "start_date": match_date,
                "end_date": match_date
            },
            timeout=TIMEOUT
        )
        weather_response.raise_for_status()
        
        weather_data = weather_response.json()
        hourly = weather_data.get("hourly", {})
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
                "error": "Match time not in forecast"
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
            "error": f"Weather API error: {str(e)}"
        }
