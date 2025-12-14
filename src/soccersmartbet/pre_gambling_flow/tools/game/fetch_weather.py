"""
Fetch weather forecast for match between two teams.

Uses FotMob for venue city lookup, then Open-Meteo for weather data.
Clean interface: Accepts both team names, finds venue city, gets weather.
NO API KEY REQUIRED.
"""

from datetime import datetime
from typing import Dict, Any

import requests

from ..fotmob_client import get_fotmob_client

TIMEOUT = 10


def fetch_weather(home_team_name: str, away_team_name: str, match_datetime: str) -> Dict[str, Any]:
    """
    Fetch weather forecast for match between two teams.

    Automatically looks up home team's venue city via FotMob and gets weather from Open-Meteo.

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
    # Step 1: Get venue city from FotMob
    try:
        client = get_fotmob_client()

        team_info = client.find_team(home_team_name)

        if not team_info:
            return _error_response(
                home_team_name,
                away_team_name,
                None,
                match_datetime,
                f"Team '{home_team_name}' not found in any major league",
            )

        team_data = client.get_team_data(team_info["id"])

        if not team_data:
            return _error_response(
                home_team_name,
                away_team_name,
                None,
                match_datetime,
                f"Could not fetch team data for '{home_team_name}'",
            )

        overview = team_data.get("overview", {})
        venue = overview.get("venue", {})
        widget = venue.get("widget", {})
        venue_city = widget.get("city")

        if not venue_city:
            return _error_response(
                home_team_name,
                away_team_name,
                None,
                match_datetime,
                f"Venue city not found for team '{home_team_name}'",
            )

    except Exception as e:
        return _error_response(
            home_team_name,
            away_team_name,
            None,
            match_datetime,
            f"Error fetching venue: {str(e)}",
        )

    # Step 2: Get coordinates using Nominatim geocoding
    try:
        geocode_url = "https://nominatim.openstreetmap.org/search"
        geocode_params = {"q": venue_city, "format": "json", "limit": 1}
        geocode_headers = {"User-Agent": "SoccerSmartBet/1.0"}

        geocode_response = requests.get(
            geocode_url,
            params=geocode_params,
            headers=geocode_headers,
            timeout=TIMEOUT,
        )

        if geocode_response.status_code != 200:
            return _error_response(
                home_team_name,
                away_team_name,
                venue_city,
                match_datetime,
                f"Geocoding API error: {geocode_response.status_code}",
            )

        geocode_data = geocode_response.json()

        if not geocode_data:
            return _error_response(
                home_team_name,
                away_team_name,
                venue_city,
                match_datetime,
                f"City '{venue_city}' not found by geocoding service",
            )

        latitude = float(geocode_data[0]["lat"])
        longitude = float(geocode_data[0]["lon"])

    except requests.Timeout:
        return _error_response(
            home_team_name,
            away_team_name,
            venue_city,
            match_datetime,
            "Geocoding API timeout",
        )
    except Exception as e:
        return _error_response(
            home_team_name,
            away_team_name,
            venue_city,
            match_datetime,
            f"Geocoding error: {str(e)}",
        )

    # Step 3: Parse match datetime
    try:
        match_dt = datetime.fromisoformat(match_datetime.replace("Z", "+00:00"))
    except ValueError:
        return _error_response(
            home_team_name,
            away_team_name,
            venue_city,
            match_datetime,
            "Invalid datetime format",
        )

    match_date = match_dt.strftime("%Y-%m-%d")
    match_hour = match_dt.strftime("%Y-%m-%dT%H:00")

    # Step 4: Get weather from Open-Meteo
    try:
        weather_url = "https://api.open-meteo.com/v1/forecast"
        weather_params = {
            "latitude": latitude,
            "longitude": longitude,
            "hourly": "temperature_2m,precipitation,precipitation_probability,windspeed_10m",
            "start_date": match_date,
            "end_date": match_date,
        }

        weather_response = requests.get(weather_url, params=weather_params, timeout=TIMEOUT)
        weather_response.raise_for_status()

        data = weather_response.json()
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
            return _error_response(
                home_team_name,
                away_team_name,
                venue_city,
                match_datetime,
                f"Match time {match_hour} not in forecast",
            )

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
            "error": None,
        }

    except requests.Timeout:
        return _error_response(
            home_team_name,
            away_team_name,
            venue_city,
            match_datetime,
            "Weather API timeout",
        )
    except Exception as e:
        return _error_response(
            home_team_name,
            away_team_name,
            venue_city,
            match_datetime,
            f"Weather API error: {str(e)}",
        )


def _error_response(
    home_team: str,
    away_team: str,
    venue_city: str | None,
    match_datetime: str,
    error: str,
) -> Dict[str, Any]:
    """Return error response with all fields."""
    return {
        "home_team": home_team,
        "away_team": away_team,
        "venue_city": venue_city,
        "match_datetime": match_datetime,
        "temperature_celsius": None,
        "precipitation_mm": None,
        "precipitation_probability": None,
        "wind_speed_kmh": None,
        "conditions": None,
        "error": error,
    }
