"""
Integration tests for Open-Meteo Weather API

Tests weather data retrieval for match venues.
NO API KEY REQUIRED (free, no signup needed)

API Docs: https://open-meteo.com/en/docs
Rate Limit: 10,000 requests/day (free tier)
"""

import pytest


# API Configuration (no key needed)
BASE_URL = "https://api.open-meteo.com/v1"


class TestWeatherEndpoint:
    """Test weather data retrieval"""

    def test_get_weather_by_coordinates(self):
        """Test retrieving weather for specific lat/lon coordinates"""
        import requests
        
        # Old Trafford coordinates
        latitude = 53.4631
        longitude = -2.2913
        
        params = {
            "latitude": latitude,
            "longitude": longitude,
            "hourly": "temperature_2m,precipitation,windspeed_10m"
        }
        
        response = requests.get(f"{BASE_URL}/forecast", params=params, timeout=10)
        
        assert response.status_code == 200
        data = response.json()
        
        # Validate response structure
        assert "latitude" in data
        assert "longitude" in data
        assert "hourly" in data
        assert "temperature_2m" in data["hourly"]
        assert "precipitation" in data["hourly"]
        assert "windspeed_10m" in data["hourly"]

    def test_weather_hourly_forecast(self):
        """Test retrieving hourly weather forecast"""
        import requests
        
        # London coordinates
        latitude = 51.5074
        longitude = -0.1278
        
        params = {
            "latitude": latitude,
            "longitude": longitude,
            "hourly": "temperature_2m",
            "forecast_days": 3
        }
        
        response = requests.get(f"{BASE_URL}/forecast", params=params, timeout=10)
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify hourly data
        assert "hourly" in data
        assert "time" in data["hourly"]
        assert "temperature_2m" in data["hourly"]
        
        # Should have multiple hours (at least 24 hours × 3 days)
        assert len(data["hourly"]["time"]) >= 72

    def test_precipitation_probability(self):
        """Test retrieving precipitation probability"""
        import requests
        
        # Paris coordinates
        latitude = 48.8566
        longitude = 2.3522
        
        params = {
            "latitude": latitude,
            "longitude": longitude,
            "hourly": "precipitation_probability,precipitation"
        }
        
        response = requests.get(f"{BASE_URL}/forecast", params=params, timeout=10)
        
        assert response.status_code == 200
        data = response.json()
        
        assert "hourly" in data
        assert "precipitation_probability" in data["hourly"]
        assert "precipitation" in data["hourly"]
        
        # Check values are in valid range
        if data["hourly"]["precipitation_probability"]:
            for prob in data["hourly"]["precipitation_probability"][:10]:
                if prob is not None:
                    assert 0 <= prob <= 100


class TestWeatherVariables:
    """Test specific weather variables for match conditions"""

    def test_temperature(self):
        """Test retrieving temperature data"""
        import requests
        
        params = {
            "latitude": 51.5074,
            "longitude": -0.1278,
            "hourly": "temperature_2m"
        }
        
        response = requests.get(f"{BASE_URL}/forecast", params=params, timeout=10)
        
        assert response.status_code == 200
        data = response.json()
        
        assert "hourly" in data
        assert "temperature_2m" in data["hourly"]
        
        # Check that temperatures are reasonable (in Celsius)
        temps = data["hourly"]["temperature_2m"]
        if temps and temps[0] is not None:
            # Should be in reasonable range for Earth (-50 to 50°C)
            assert -50 <= temps[0] <= 50

    def test_wind_speed(self):
        """Test retrieving wind speed data"""
        import requests
        
        params = {
            "latitude": 51.5074,
            "longitude": -0.1278,
            "hourly": "windspeed_10m"
        }
        
        response = requests.get(f"{BASE_URL}/forecast", params=params, timeout=10)
        
        assert response.status_code == 200
        data = response.json()
        
        assert "hourly" in data
        assert "windspeed_10m" in data["hourly"]
        
        # Wind speed should be non-negative
        speeds = data["hourly"]["windspeed_10m"]
        if speeds and speeds[0] is not None:
            assert speeds[0] >= 0

    def test_precipitation(self):
        """Test retrieving precipitation data"""
        import requests
        
        params = {
            "latitude": 51.5074,
            "longitude": -0.1278,
            "hourly": "precipitation"
        }
        
        response = requests.get(f"{BASE_URL}/forecast", params=params, timeout=10)
        
        assert response.status_code == 200
        data = response.json()
        
        assert "hourly" in data
        assert "precipitation" in data["hourly"]
        
        # Precipitation should be non-negative (in mm)
        precip = data["hourly"]["precipitation"]
        if precip and precip[0] is not None:
            assert precip[0] >= 0


class TestDateTimeHandling:
    """Test date/time filtering for match kickoff times"""

    def test_specific_datetime_forecast(self):
        """Test retrieving weather for specific match kickoff time"""
        import requests
        from datetime import datetime, timedelta
        
        # Get forecast for tomorrow
        tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        
        params = {
            "latitude": 51.5074,
            "longitude": -0.1278,
            "hourly": "temperature_2m",
            "start_date": tomorrow,
            "end_date": tomorrow
        }
        
        response = requests.get(f"{BASE_URL}/forecast", params=params, timeout=10)
        
        assert response.status_code == 200
        data = response.json()
        
        assert "hourly" in data
        assert "time" in data["hourly"]
        
        # Check that times are for tomorrow
        if data["hourly"]["time"]:
            first_time = data["hourly"]["time"][0]
            assert tomorrow in first_time

    def test_timezone_handling(self):
        """Test timezone parameter for international matches"""
        import requests
        
        params = {
            "latitude": 51.5074,
            "longitude": -0.1278,
            "hourly": "temperature_2m",
            "timezone": "Europe/London"
        }
        
        response = requests.get(f"{BASE_URL}/forecast", params=params, timeout=10)
        
        assert response.status_code == 200
        data = response.json()
        
        assert "timezone" in data
        # Verify timezone is as requested
        assert "Europe/London" in data["timezone"] or data["timezone"] in ["GMT", "BST"]


class TestErrorHandling:
    """Test API error handling"""

    def test_invalid_coordinates(self):
        """Test behavior with invalid lat/lon coordinates"""
        import requests
        
        # Invalid latitude (> 90)
        params = {
            "latitude": 999,
            "longitude": 0,
            "hourly": "temperature_2m"
        }
        
        response = requests.get(f"{BASE_URL}/forecast", params=params, timeout=10)
        
        # Should return 400 for invalid coordinates
        assert response.status_code == 400

    def test_invalid_parameters(self):
        """Test behavior with invalid parameters"""
        import requests
        
        params = {
            "latitude": 51.5074,
            "longitude": -0.1278,
            "hourly": "invalid_weather_variable_xyz"
        }
        
        response = requests.get(f"{BASE_URL}/forecast", params=params, timeout=10)
        
        # Should return error for invalid parameter
        assert response.status_code == 400


class TestNoAuthRequired:
    """Test that no authentication is required"""

    def test_request_without_api_key(self):
        """Test that requests work without API key"""
        import requests
        
        # Make request without any API key or authentication
        params = {
            "latitude": 51.5074,
            "longitude": -0.1278,
            "hourly": "temperature_2m"
        }
        
        response = requests.get(f"{BASE_URL}/forecast", params=params, timeout=10)
        
        # Should succeed without any authentication
        assert response.status_code == 200
        data = response.json()
        
        # Verify we got actual weather data
        assert "hourly" in data
        assert "temperature_2m" in data["hourly"]
