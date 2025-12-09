"""Test Open-Meteo API availability for weather data."""

import requests
from datetime import datetime


def test_weather_api_available():
    """Test that Open-Meteo API is accessible."""
    tomorrow = datetime.now().strftime("%Y-%m-%d")
    
    response = requests.get(
        "https://api.open-meteo.com/v1/forecast",
        params={
            "latitude": 51.5074,
            "longitude": -0.1278,
            "hourly": "temperature_2m",
            "start_date": tomorrow,
            "end_date": tomorrow
        },
        timeout=10
    )
    
    if response.status_code != 200:
        print(f"❌ API error: {response.status_code}")
        return False
    
    data = response.json()
    
    print(f"✅ API accessible - Weather data available")
    return True


if __name__ == "__main__":
    test_weather_api_available()
