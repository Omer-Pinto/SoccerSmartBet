"""
Weather Fetcher Tool for Game Intelligence Agent

Fetches weather forecast for match location and time using Open-Meteo API.
This is a "dumb fetcher" - no AI analysis, just raw weather data retrieval.

API: Open-Meteo (https://open-meteo.com/en/docs)
Authentication: None required (free tier)
Rate Limit: 10,000 requests/day
"""

from datetime import datetime
from typing import Any

import requests


def fetch_weather(
    latitude: float,
    longitude: float,
    match_datetime: str
) -> dict[str, Any]:
    """
    Fetch weather forecast for match venue and kickoff time.

    This tool retrieves temperature, precipitation, wind speed, and conditions
    from Open-Meteo API. Returns empty dict with error message on failure.

    Args:
        latitude: Venue latitude coordinate
        longitude: Venue longitude coordinate
        match_datetime: ISO format datetime of match kickoff (e.g., "2024-11-15T15:00:00")

    Returns:
        dict with structure:
        {
            "temperature_celsius": 12.5,
            "precipitation_mm": 0.0,
            "precipitation_probability": 20,
            "wind_speed_kmh": 15.3,
            "conditions": "Clear" | "Rain" | "Heavy Rain" | "Snow"
        }
        
        On error, returns:
        {
            "error": "Error message description"
        }

    Example:
        >>> fetch_weather(53.4631, -2.2913, "2024-11-15T15:00:00")
        {
            "temperature_celsius": 8.2,
            "precipitation_mm": 0.5,
            "precipitation_probability": 40,
            "wind_speed_kmh": 18.5,
            "conditions": "Rain"
        }
    """
    try:
        # Parse match datetime to determine forecast time
        try:
            match_dt = datetime.fromisoformat(match_datetime.replace('Z', '+00:00'))
        except ValueError as e:
            return {"error": f"Invalid match_datetime format: {match_datetime}. Expected ISO format. {e}"}

        # Format dates for API request
        match_date = match_dt.strftime("%Y-%m-%d")
        match_hour = match_dt.strftime("%Y-%m-%dT%H:00")  # Open-Meteo uses hourly data

        # Prepare API request
        base_url = "https://api.open-meteo.com/v1/forecast"
        params = {
            "latitude": latitude,
            "longitude": longitude,
            "hourly": "temperature_2m,precipitation,precipitation_probability,windspeed_10m",
            "start_date": match_date,
            "end_date": match_date
        }

        # Make API request (10 second timeout)
        response = requests.get(base_url, params=params, timeout=10)
        response.raise_for_status()

        data = response.json()

        # Extract hourly data arrays
        hourly = data.get("hourly", {})
        times = hourly.get("time", [])
        temperatures = hourly.get("temperature_2m", [])
        precipitation_values = hourly.get("precipitation", [])
        precipitation_probs = hourly.get("precipitation_probability", [])
        wind_speeds = hourly.get("windspeed_10m", [])

        # Find the index matching the match hour
        try:
            hour_index = times.index(match_hour)
        except ValueError:
            # If exact hour not found, return error
            return {
                "error": f"Match time {match_hour} not found in forecast. Available times: {times[:3]}..."
            }

        # Extract weather values at match time
        temperature = temperatures[hour_index] if hour_index < len(temperatures) else None
        precipitation = precipitation_values[hour_index] if hour_index < len(precipitation_values) else None
        precip_prob = precipitation_probs[hour_index] if hour_index < len(precipitation_probs) else None
        wind_speed = wind_speeds[hour_index] if hour_index < len(wind_speeds) else None

        # Handle None values
        if temperature is None or precipitation is None or wind_speed is None:
            return {"error": "Incomplete weather data returned from API"}

        # Determine weather conditions based on precipitation
        if precipitation >= 5.0:
            conditions = "Heavy Rain"
        elif precipitation >= 0.5:
            conditions = "Rain"
        elif temperature < 0 and precipitation > 0:
            conditions = "Snow"
        else:
            conditions = "Clear"

        return {
            "temperature_celsius": temperature,
            "precipitation_mm": precipitation,
            "precipitation_probability": precip_prob if precip_prob is not None else 0,
            "wind_speed_kmh": wind_speed,
            "conditions": conditions
        }

    except requests.exceptions.Timeout:
        return {"error": "API request timed out after 10 seconds"}
    except requests.exceptions.HTTPError as e:
        return {"error": f"HTTP error from API: {e.response.status_code} - {e.response.text}"}
    except requests.exceptions.RequestException as e:
        return {"error": f"Network error: {str(e)}"}
    except Exception as e:
        return {"error": f"Unexpected error: {str(e)}"}
