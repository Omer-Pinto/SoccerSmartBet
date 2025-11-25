# Open-Meteo

**Website:** https://open-meteo.com  
**Type:** REST API  
**Cost:** FREE (no API key required)  
**Status:** ✅ Primary source for [Weather](../verticals/weather.md)

---

## Overview

Open-Meteo provides free weather forecasts with no API key required. It's the **primary source for weather-based cancellation risk assessment** in SoccerSmartBet.

---

## Features

- ✅ **No API key required** (instant use, no signup)
- ✅ 10,000 requests/day free
- ✅ Hourly forecasts up to 7 days ahead
- ✅ 1-11km resolution
- ✅ Historical weather (80+ years)
- ✅ Temperature, precipitation, wind speed
- ✅ JSON format

---

## API Endpoint

**Base URL:**
```http
GET https://api.open-meteo.com/v1/forecast
```

**Parameters:**
- `latitude`: Venue latitude (required)
- `longitude`: Venue longitude (required)
- `hourly`: Comma-separated list of weather variables (required)
- `timezone`: Timezone (e.g., "auto", "Europe/London")
- `forecast_days`: Number of days ahead (default: 7)

**Example Request:**
```http
GET https://api.open-meteo.com/v1/forecast
  ?latitude=53.4631
  &longitude=-2.2913
  &hourly=temperature_2m,precipitation,windspeed_10m
  &timezone=auto
```

**Response:**
```json
{
  "latitude": 53.46,
  "longitude": -2.29,
  "generationtime_ms": 0.123,
  "utc_offset_seconds": 0,
  "timezone": "GMT",
  "timezone_abbreviation": "GMT",
  "elevation": 30.0,
  "hourly_units": {
    "time": "iso8601",
    "temperature_2m": "°C",
    "precipitation": "mm",
    "windspeed_10m": "km/h"
  },
  "hourly": {
    "time": [
      "2025-11-20T00:00",
      "2025-11-20T01:00",
      "2025-11-20T02:00",
      ...,
      "2025-11-20T15:00",
      ...
    ],
    "temperature_2m": [10.2, 10.0, 9.8, ..., 12.5, ...],
    "precipitation": [0.0, 0.0, 0.2, ..., 0.0, ...],
    "windspeed_10m": [12.5, 13.0, 14.2, ..., 15.3, ...]
  }
}
```

---

## Python Code Example

```python
import requests
from datetime import datetime
from typing import Dict, Optional

class OpenMeteoFetcher:
    """Fetches weather data from Open-Meteo API"""
    
    BASE_URL = "https://api.open-meteo.com/v1/forecast"
    
    def get_match_weather(
        self,
        latitude: float,
        longitude: float,
        match_time: str,
        timezone: str = "auto"
    ) -> Optional[Dict]:
        """
        Fetch weather forecast for match kickoff time
        
        Args:
            latitude: Venue latitude
            longitude: Venue longitude
            match_time: Kickoff time in ISO format (e.g., "2025-11-20T15:00:00Z")
            timezone: Timezone (default: "auto")
        
        Returns:
            Weather data for the specific hour, or None if not available
        """
        params = {
            "latitude": latitude,
            "longitude": longitude,
            "hourly": "temperature_2m,precipitation,windspeed_10m,weathercode",
            "timezone": timezone
        }
        
        response = requests.get(self.BASE_URL, params=params)
        response.raise_for_status()
        
        data = response.json()
        
        # Find weather for match time
        match_hour = match_time[:13]  # "2025-11-20T15"
        
        try:
            index = data["hourly"]["time"].index(match_hour)
            return {
                "time": data["hourly"]["time"][index],
                "temperature_c": data["hourly"]["temperature_2m"][index],
                "precipitation_mm": data["hourly"]["precipitation"][index],
                "windspeed_kmh": data["hourly"]["windspeed_10m"][index],
                "weather_code": data["hourly"]["weathercode"][index]
            }
        except (ValueError, IndexError):
            return None
    
    def get_stadium_coords(self, stadium_name: str) -> Optional[tuple]:
        """
        Get coordinates for a known stadium
        
        Args:
            stadium_name: Stadium name (e.g., "Old Trafford")
        
        Returns:
            (latitude, longitude) tuple, or None if unknown
        """
        # Lookup table of major stadiums
        STADIUM_COORDS = {
            "Old Trafford": (53.4631, -2.2913),
            "Anfield": (53.4308, -2.9608),
            "Emirates Stadium": (51.5549, -0.1084),
            "Stamford Bridge": (51.4816, -0.1909),
            "Etihad Stadium": (53.4831, -2.2004),
            "Tottenham Hotspur Stadium": (51.6042, -0.0662),
            "St James' Park": (54.9756, -1.6217),
            "Santiago Bernabéu": (40.4530, -3.6883),
            "Camp Nou": (41.3809, 2.1228),
            "Allianz Arena": (48.2188, 11.6247),
            "San Siro": (45.4781, 9.1240),
            "Parc des Princes": (48.8414, 2.2530)
        }
        
        return STADIUM_COORDS.get(stadium_name)
    
    def interpret_weather_code(self, code: int) -> str:
        """
        Interpret WMO weather code
        
        Args:
            code: WMO weather code (0-99)
        
        Returns:
            Human-readable description
        """
        codes = {
            0: "Clear sky",
            1: "Mainly clear",
            2: "Partly cloudy",
            3: "Overcast",
            45: "Fog",
            48: "Depositing rime fog",
            51: "Light drizzle",
            61: "Slight rain",
            63: "Moderate rain",
            65: "Heavy rain",
            71: "Slight snow",
            73: "Moderate snow",
            75: "Heavy snow",
            95: "Thunderstorm"
        }
        return codes.get(code, f"Unknown ({code})")


# Example usage
if __name__ == "__main__":
    fetcher = OpenMeteoFetcher()
    
    # Get weather for Old Trafford
    stadium_name = "Old Trafford"
    coords = fetcher.get_stadium_coords(stadium_name)
    
    if coords:
        lat, lon = coords
        match_time = "2025-11-20T15:00"
        
        weather = fetcher.get_match_weather(lat, lon, match_time)
        
        if weather:
            print(f"Weather for {stadium_name} at {weather['time']}:")
            print(f"  Temperature: {weather['temperature_c']}°C")
            print(f"  Precipitation: {weather['precipitation_mm']} mm")
            print(f"  Wind Speed: {weather['windspeed_kmh']} km/h")
            print(f"  Conditions: {fetcher.interpret_weather_code(weather['weather_code'])}")
            
            # AI Analysis would assess:
            if weather['precipitation_mm'] > 5:
                print("  ⚠️ Heavy rain - increased draw probability")
            if weather['windspeed_kmh'] > 40:
                print("  ⚠️ High winds - unpredictable ball movement")
            if weather['weather_code'] >= 71:
                print("  🔴 Snow - match cancellation risk")
```

---

## Weather Variables

### Available Hourly Variables
- `temperature_2m`: Temperature at 2 meters (°C)
- `precipitation`: Total precipitation (rain + snow) (mm)
- `rain`: Rain only (mm)
- `snowfall`: Snowfall (cm)
- `weathercode`: WMO weather code (0-99)
- `windspeed_10m`: Wind speed at 10 meters (km/h)
- `winddirection_10m`: Wind direction (°)
- `cloudcover`: Cloud cover percentage (%)

### Weather Codes (WMO)
- **0-3**: Clear to cloudy (safe)
- **45-48**: Fog (moderate risk)
- **51-65**: Rain (increased draw probability)
- **71-75**: Snow (cancellation risk)
- **95-99**: Thunderstorm (cancellation risk)

---

## Venue Coordinates Database

**Implementation:** Maintain a database table of stadiums with coordinates.

### Schema
```sql
CREATE TABLE stadiums (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) UNIQUE NOT NULL,
    city VARCHAR(255),
    country VARCHAR(100),
    latitude DECIMAL(9, 6),
    longitude DECIMAL(9, 6)
);
```

### Seed Data (Major European Stadiums)
```sql
INSERT INTO stadiums (name, city, country, latitude, longitude) VALUES
('Old Trafford', 'Manchester', 'England', 53.4631, -2.2913),
('Anfield', 'Liverpool', 'England', 53.4308, -2.9608),
('Emirates Stadium', 'London', 'England', 51.5549, -0.1084),
('Santiago Bernabéu', 'Madrid', 'Spain', 40.4530, -3.6883),
('Camp Nou', 'Barcelona', 'Spain', 41.3809, 2.1228),
('Allianz Arena', 'Munich', 'Germany', 48.2188, 11.6247),
('San Siro', 'Milan', 'Italy', 45.4781, 9.1240),
('Parc des Princes', 'Paris', 'France', 48.8414, 2.2530);
```

---

## Implementation Notes

### For Game Intelligence Agent

1. **Fetch Strategy:**
   - After fixture selection, lookup venue coordinates from stadiums table
   - Call Open-Meteo API with venue coords and match kickoff time
   - Extract weather for specific hour

2. **AI Weather Impact Analysis:**
   - **Cancellation Risk:** Snow (code 71-75) or severe thunderstorm (code 95+)
   - **Draw Probability Increase:** Heavy rain (precipitation > 5mm), high wind (> 40 km/h)
   - **Normal Conditions:** Clear/cloudy, light rain

3. **Quota:** ~3-5 requests/day (one per filtered game), negligible vs 10k limit

### Error Handling

**Unknown Stadium:**
- If venue not in database, skip weather analysis (non-critical data)
- Log warning for manual coordinate addition later

**API Failure:**
- Weather is non-critical, continue without it
- AI agent should note "weather data unavailable" in report

---

## See Also

- [Weather Vertical](../verticals/weather.md) - Why weather matters for betting
- [Game Intelligence Agent](../../../../PRE_GAMBLING_OPTIMIZED_FLOW_TASKS.md#42-game-intelligence-agent-node) - Uses weather for risk assessment
- [Official API Docs](https://open-meteo.com/en/docs)
