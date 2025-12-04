"""
Fetch venue information for a soccer match.

This is a "dumb fetcher" tool - retrieves raw venue data from football-data.org
without any AI analysis or intelligence. The Game Intelligence Agent uses this
data to generate venue-based betting insights.

Data Source: football-data.org API
Rate Limit: 10 requests/minute (free tier)
API Docs: https://www.football-data.org/documentation/quickstart
"""

import os
import requests
from typing import Dict, Any
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# API Configuration
API_KEY = os.getenv("FOOTBALL_DATA_API_KEY")
BASE_URL = "https://api.football-data.org/v4"
DEFAULT_TIMEOUT = 10  # seconds


def fetch_venue(match_id: int) -> Dict[str, Any]:
    """
    Fetch venue information for a specific match.

    This is a pure data fetcher - no AI analysis, just retrieves raw venue
    information from football-data.org API.

    Args:
        match_id: football-data.org match ID (integer)

    Returns:
        Dictionary with venue information:
        {
            "venue_name": "Old Trafford",
            "capacity": 74879,
            "city": "Manchester",
            "country": "England"
        }

        On error or missing data, returns:
        {
            "venue_name": None,
            "capacity": None,
            "city": None,
            "country": None,
            "error": "Error message"
        }

    Example:
        >>> venue_data = fetch_venue(12345)
        >>> print(venue_data["venue_name"])
        "Etihad Stadium"
    """
    # Check if API key is available
    if not API_KEY:
        return {
            "venue_name": None,
            "capacity": None,
            "city": None,
            "country": None,
            "error": "FOOTBALL_DATA_API_KEY not found in environment variables"
        }

    # Prepare headers
    headers = {"X-Auth-Token": API_KEY}

    try:
        # Make API request to matches endpoint
        response = requests.get(
            f"{BASE_URL}/matches/{match_id}",
            headers=headers,
            timeout=DEFAULT_TIMEOUT
        )

        # Check response status
        if response.status_code != 200:
            return {
                "venue_name": None,
                "capacity": None,
                "city": None,
                "country": None,
                "error": f"API returned status code {response.status_code}"
            }

        # Parse response JSON
        data = response.json()

        # Extract venue information from match data
        # football-data.org returns venue info nested in the match object
        venue_name = data.get("venue")
        
        # Extract additional venue details if available
        # Note: football-data.org may not provide all fields for all matches
        area = data.get("area", {})
        competition = data.get("competition", {})
        
        return {
            "venue_name": venue_name,
            "capacity": None,  # football-data.org doesn't provide capacity in match endpoint
            "city": None,  # Would need to fetch from team endpoint or separate venue API
            "country": area.get("name") if area else None
        }

    except requests.exceptions.Timeout:
        return {
            "venue_name": None,
            "capacity": None,
            "city": None,
            "country": None,
            "error": f"Request timeout after {DEFAULT_TIMEOUT} seconds"
        }

    except requests.exceptions.RequestException as e:
        return {
            "venue_name": None,
            "capacity": None,
            "city": None,
            "country": None,
            "error": f"Request failed: {str(e)}"
        }

    except (KeyError, ValueError, TypeError) as e:
        return {
            "venue_name": None,
            "capacity": None,
            "city": None,
            "country": None,
            "error": f"Failed to parse API response: {str(e)}"
        }
