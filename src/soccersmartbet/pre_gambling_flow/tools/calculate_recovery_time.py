"""
Calculate Recovery Time Tool - Pure Python Date Arithmetic

This is a "dumb fetcher" tool that calculates the number of days between
a team's last match and their upcoming match. The Team Intelligence Agent
uses this data to assess fatigue/freshness levels.

NO AI analysis - just pure Python date calculation and status classification.
"""

from datetime import datetime
from typing import Literal


RecoveryStatus = Literal["Short", "Normal", "Extended"]


def calculate_recovery_time(
    last_match_date: str,
    upcoming_match_date: str
) -> dict[str, str | int]:
    """
    Calculate days between team's last match and upcoming match.

    This tool performs pure Python date arithmetic to determine recovery time.
    The Team Intelligence Agent interprets this data for fatigue assessment:
    - Short recovery (<3 days): High fatigue risk
    - Normal recovery (3-7 days): Standard rest period
    - Extended recovery (>7 days): Extra rest, possible rhythm concerns

    Args:
        last_match_date: ISO date of team's last match (YYYY-MM-DD, e.g., "2024-11-10")
        upcoming_match_date: ISO date of upcoming match (YYYY-MM-DD, e.g., "2024-11-15")

    Returns:
        Dictionary with recovery calculation:
        {
            "recovery_days": 5,
            "last_match_date": "2024-11-10",
            "upcoming_match_date": "2024-11-15",
            "recovery_status": "Normal"
        }

    Raises:
        ValueError: If date formats are invalid or upcoming_match_date is before last_match_date

    Example:
        >>> calculate_recovery_time("2024-11-10", "2024-11-15")
        {
            "recovery_days": 5,
            "last_match_date": "2024-11-10",
            "upcoming_match_date": "2024-11-15",
            "recovery_status": "Normal"
        }

        >>> calculate_recovery_time("2024-11-12", "2024-11-14")
        {
            "recovery_days": 2,
            "last_match_date": "2024-11-12",
            "upcoming_match_date": "2024-11-14",
            "recovery_status": "Short"
        }
    """
    try:
        # Parse ISO date strings
        last_match = datetime.fromisoformat(last_match_date)
        upcoming_match = datetime.fromisoformat(upcoming_match_date)
    except (ValueError, TypeError) as e:
        raise ValueError(
            f"Invalid date format. Expected ISO format (YYYY-MM-DD). "
            f"Got last_match_date='{last_match_date}', upcoming_match_date='{upcoming_match_date}'. "
            f"Error: {e}"
        ) from e

    # Calculate days difference
    delta = upcoming_match - last_match
    recovery_days = delta.days

    # Validate logical date order
    if recovery_days < 0:
        raise ValueError(
            f"Invalid date order: upcoming_match_date ({upcoming_match_date}) "
            f"is before last_match_date ({last_match_date}). "
            f"Calculated negative recovery: {recovery_days} days."
        )

    # Classify recovery status based on day count
    if recovery_days < 3:
        recovery_status: RecoveryStatus = "Short"
    elif recovery_days <= 7:
        recovery_status = "Normal"
    else:
        recovery_status = "Extended"

    return {
        "recovery_days": recovery_days,
        "last_match_date": last_match_date,
        "upcoming_match_date": upcoming_match_date,
        "recovery_status": recovery_status
    }
