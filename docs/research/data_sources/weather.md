# Weather APIs

**Status:** 🟢 **FREE - NO API KEY REQUIRED**

---

## Primary: Open-Meteo ⭐ **RECOMMENDED**

**Website:** https://open-meteo.com  
**Type:** Free Weather API  
**Cost:** FREE (10,000 requests/day)  
**Status:** 🟢

### Features
- ✅ **No API key needed**
- ✅ 10,000 requests/day free
- ✅ Hourly forecasts
- ✅ Historical weather (80+ years)
- ✅ 1-11km resolution
- ✅ Precipitation, temperature, wind speed
- ✅ Global coverage

### Example API Call
```python
import requests
from datetime import datetime

def get_match_weather(lat: float, lon: float, match_time: str):
    """
    Fetch weather for match location and time.
    
    Args:
        lat: Stadium latitude
        lon: Stadium longitude
        match_time: ISO format datetime (e.g., "2025-11-20T15:00")
    """
    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": "temperature_2m,precipitation,windspeed_10m,weathercode",
        "timezone": "auto"
    }
    
    response = requests.get(
        "https://api.open-meteo.com/v1/forecast",
        params=params
    )
    
    return response.json()

# Example: Manchester (Old Trafford)
weather = get_match_weather(53.4631, -2.2913, "2025-11-20T15:00:00")

# Example response:
{
  "hourly": {
    "time": ["2025-11-20T15:00"],
    "temperature_2m": [12.5],        # Celsius
    "precipitation": [0.0],          # mm
    "windspeed_10m": [15.3],         # km/h
    "weathercode": [3]               # 0=clear, 3=overcast, 61=rain
  }
}
```

---

## Stadium Coordinates Database

```python
STADIUM_COORDS = {
    # England - Premier League
    "Old Trafford": (53.4631, -2.2913),
    "Anfield": (53.4308, -2.9608),
    "Emirates Stadium": (51.5549, -0.1084),
    "Stamford Bridge": (51.4817, -0.1910),
    "Etihad Stadium": (53.4831, -2.2004),
    "Tottenham Hotspur Stadium": (51.6043, -0.0664),
    
    # Spain - La Liga
    "Santiago Bernabéu": (40.4530, -3.6883),
    "Camp Nou": (41.3809, 2.1228),
    "Wanda Metropolitano": (40.4362, -3.5995),
    
    # Italy - Serie A
    "San Siro": (45.4781, 9.1240),
    "Stadio Olimpico": (41.9338, 12.4547),
    
    # Germany - Bundesliga
    "Allianz Arena": (48.2188, 11.6247),
    "Signal Iduna Park": (51.4925, 7.4517)
}

def get_stadium_coords(venue_name: str) -> tuple:
    """
    Get coordinates for a stadium.
    
    Returns (lat, lon) or None if not found.
    """
    return STADIUM_COORDS.get(venue_name)
```

---

## Weather Code Interpretation

```python
WEATHER_CODES = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Depositing rime fog",
    51: "Light drizzle",
    53: "Moderate drizzle",
    55: "Dense drizzle",
    61: "Slight rain",
    63: "Moderate rain",
    65: "Heavy rain",
    71: "Slight snow",
    73: "Moderate snow",
    75: "Heavy snow",
    77: "Snow grains",
    80: "Slight rain showers",
    81: "Moderate rain showers",
    82: "Violent rain showers",
    85: "Slight snow showers",
    86: "Heavy snow showers",
    95: "Thunderstorm",
    96: "Thunderstorm with slight hail",
    99: "Thunderstorm with heavy hail"
}

def interpret_weather(weather_code: int) -> dict:
    """
    Interpret weather impact on match.
    
    Returns:
        - description: Human-readable description
        - cancellation_risk: low, medium, high
        - draw_probability_impact: float (-0.1 to +0.2)
    """
    if weather_code in [95, 96, 99]:  # Thunderstorm
        return {
            "description": WEATHER_CODES[weather_code],
            "cancellation_risk": "high",
            "draw_probability_impact": 0.15
        }
    elif weather_code in [63, 65, 82]:  # Heavy rain
        return {
            "description": WEATHER_CODES[weather_code],
            "cancellation_risk": "medium",
            "draw_probability_impact": 0.10
        }
    elif weather_code in [73, 75, 86]:  # Heavy snow
        return {
            "description": WEATHER_CODES[weather_code],
            "cancellation_risk": "high",
            "draw_probability_impact": 0.20
        }
    elif weather_code in [61, 71, 80]:  # Light rain/snow
        return {
            "description": WEATHER_CODES[weather_code],
            "cancellation_risk": "low",
            "draw_probability_impact": 0.05
        }
    else:  # Clear/cloudy
        return {
            "description": WEATHER_CODES.get(weather_code, "Unknown"),
            "cancellation_risk": "none",
            "draw_probability_impact": 0.0
        }
```

---

## Data Structure

```python
from pydantic import BaseModel
from typing import Literal

class MatchWeather(BaseModel):
    venue: str
    latitude: float
    longitude: float
    match_time: datetime
    temperature_c: float
    precipitation_mm: float
    wind_speed_kmh: float
    weather_code: int
    weather_description: str
    cancellation_risk: Literal["none", "low", "medium", "high"]
    draw_impact: float  # -0.1 to +0.2
    
# Example usage:
weather = MatchWeather(
    venue="Old Trafford",
    latitude=53.4631,
    longitude=-2.2913,
    match_time=datetime(2025, 11, 20, 15, 0),
    temperature_c=12.5,
    precipitation_mm=2.3,
    wind_speed_kmh=15.3,
    weather_code=61,
    weather_description="Slight rain",
    cancellation_risk="low",
    draw_impact=0.05
)
```

---

## Backup: OpenWeatherMap

**Website:** https://openweathermap.org  
**Type:** Weather API  
**Cost:** FREE (1,000 calls/day)  
**Status:** 🟡

### Features
- ✅ 1,000 API calls/day free
- ✅ Current weather + forecasts
- ✅ Minute-by-minute (1 hour), hourly (48h)
- ⚠️ Requires API key signup

### Example API Call
```python
API_KEY = "your_openweather_key"
lat, lon = 53.4631, -2.2913  # Old Trafford

response = requests.get(
    f"https://api.openweathermap.org/data/2.5/weather",
    params={"lat": lat, "lon": lon, "appid": API_KEY, "units": "metric"}
)

# Example response:
{
  "weather": [{"main": "Rain", "description": "light rain"}],
  "main": {"temp": 12.5, "humidity": 78},
  "wind": {"speed": 4.12},  # m/s
  "dt": 1700490000
}
```

**Note:** OpenWeatherMap is backup only. Use Open-Meteo as primary (no key required).

---

## Implementation Checklist

- [ ] Create stadium coordinates database
- [ ] Test Open-Meteo API (no registration needed)
- [ ] Implement weather code interpretation
- [ ] Calculate draw probability impact
- [ ] Handle missing stadium coordinates gracefully
- [ ] Cache weather data for 6 hours
- [ ] Test cancellation risk logic
- [ ] Validate temperature/precipitation ranges
- [ ] Log extreme weather conditions
- [ ] Set up alerts for high cancellation risk
