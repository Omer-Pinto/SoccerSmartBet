"""
Calculate days since team's last match (recovery time).

Uses fetch_form to get last match date.
"""

from datetime import datetime
from typing import Dict, Any

from .fetch_form import fetch_form


def calculate_recovery_time(team_name: str, upcoming_match_date: str) -> Dict[str, Any]:
    """
    Calculate days between team's last match and upcoming match.
    
    Args:
        team_name: Team name (e.g., "Manchester City")
        upcoming_match_date: Upcoming match date in YYYY-MM-DD format
    
    Returns:
        {
            "team_name": "Manchester City",
            "last_match_date": "2025-12-01",
            "upcoming_match_date": "2025-12-08",
            "recovery_days": 7,
            "recovery_status": "Normal",
            "error": None
        }
    """
    # Get team's recent form to find last match
    form_result = fetch_form(team_name, limit=1)
    
    if form_result.get("error"):
        return {
            "team_name": team_name,
            "last_match_date": None,
            "upcoming_match_date": upcoming_match_date,
            "recovery_days": None,
            "recovery_status": None,
            "error": f"Could not get team form: {form_result['error']}"
        }
    
    matches = form_result.get("matches", [])
    if not matches:
        return {
            "team_name": team_name,
            "last_match_date": None,
            "upcoming_match_date": upcoming_match_date,
            "recovery_days": None,
            "recovery_status": None,
            "error": "No recent matches found"
        }
    
    last_match_date = matches[0].get("date")
    if not last_match_date:
        return {
            "team_name": team_name,
            "last_match_date": None,
            "upcoming_match_date": upcoming_match_date,
            "recovery_days": None,
            "recovery_status": None,
            "error": "Last match date not available"
        }
    
    # Calculate recovery days
    try:
        last_dt = datetime.strptime(last_match_date, "%Y-%m-%d")
        upcoming_dt = datetime.strptime(upcoming_match_date, "%Y-%m-%d")
        recovery_days = (upcoming_dt - last_dt).days
        
        # Determine recovery status
        if recovery_days < 3:
            status = "Short"
        elif recovery_days <= 7:
            status = "Normal"
        else:
            status = "Extended"
        
        return {
            "team_name": team_name,
            "last_match_date": last_match_date,
            "upcoming_match_date": upcoming_match_date,
            "recovery_days": recovery_days,
            "recovery_status": status,
            "error": None
        }
    
    except ValueError as e:
        return {
            "team_name": team_name,
            "last_match_date": last_match_date,
            "upcoming_match_date": upcoming_match_date,
            "recovery_days": None,
            "recovery_status": None,
            "error": f"Invalid date format: {str(e)}"
        }
    except Exception as e:
        return {
            "team_name": team_name,
            "last_match_date": last_match_date,
            "upcoming_match_date": upcoming_match_date,
            "recovery_days": None,
            "recovery_status": None,
            "error": f"Unexpected error: {str(e)}"
        }
