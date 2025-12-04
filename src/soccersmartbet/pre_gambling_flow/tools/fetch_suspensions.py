"""
Fetch team suspensions from apifootball.com API.

This is a "dumb fetcher" tool that retrieves raw suspension data without analysis.
The Team Intelligence Agent will analyze the impact of suspensions on lineup strength.

Data Source: apifootball.com (180 requests/hour free tier)
API Docs: https://apifootball.com/documentation/

NOTE: apifootball.com does NOT provide explicit suspension status data.
This tool returns an empty list with a note explaining the API limitation.
For production use, switch to a data source that provides actual suspension tracking
(e.g., official league APIs or specialized sports data providers).
"""

import os
from typing import Dict, Any
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# API Configuration
API_KEY = os.getenv("APIFOOTBALL_API_KEY")


def fetch_suspensions(team_id: int, league_id: int) -> Dict[str, Any]:
    """
    Fetch current suspension list for a team.
    
    NOTE: apifootball.com does NOT provide explicit suspension status.
    This tool returns an empty list with a note explaining the limitation.
    
    For production, use a data source that provides actual suspension tracking
    (e.g., official league APIs or specialized sports data providers).
    
    Parameters
    ----------
    team_id : int
        apifootball.com team ID (e.g., 33 for Manchester City)
    league_id : int
        apifootball.com league ID (e.g., 152 for Premier League)
    
    Returns
    -------
    dict
        Suspension data in the format:
        {
            "suspensions": [],  # Always empty - API doesn't provide this data
            "total_suspensions": 0,
            "note": <explanation of API limitation>,
            "error": <error message if API key missing, else None>
        }
    
    Examples
    --------
    >>> fetch_suspensions(team_id=33, league_id=152)
    {
        "suspensions": [],
        "total_suspensions": 0,
        "note": "apifootball.com does not provide explicit suspension status...",
        "error": None
    }
    
    Notes
    -----
    - This tool does NOT infer suspensions from card data (unreliable)
    - Red card suspensions vary by offense (1-3+ games)
    - Yellow card thresholds vary by competition
    - Card data cannot indicate if suspension was already served
    - For accurate data, use official league APIs or specialized providers
    """
    # Validate API key
    if not API_KEY:
        return {
            "suspensions": [],
            "total_suspensions": 0,
            "note": "apifootball.com does not provide explicit suspension status. "
                    "Card data (red/yellow) cannot reliably indicate current suspensions "
                    "because: (1) red cards can be 1-3+ games depending on offense, "
                    "(2) yellow thresholds vary by competition, "
                    "(3) we can't know if suspension was already served. "
                    "For production, use official league APIs or specialized suspension tracking.",
            "error": "APIFOOTBALL_API_KEY not found in environment variables"
        }
    
    # Note: We could call the API to verify team exists, but since
    # apifootball.com doesn't provide suspension data, we just return
    # a note explaining the limitation.
    
    return {
        "suspensions": [],
        "total_suspensions": 0,
        "note": "apifootball.com does not provide explicit suspension status. "
                "Card data (red/yellow) cannot reliably indicate current suspensions "
                "because: (1) red cards can be 1-3+ games depending on offense, "
                "(2) yellow thresholds vary by competition, "
                "(3) we can't know if suspension was already served. "
                "For production, use official league APIs or specialized suspension tracking.",
        "error": None
    }
