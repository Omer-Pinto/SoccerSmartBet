"""Test calculate_recovery_time functionality with real data."""

import sys
from pathlib import Path
from datetime import datetime, timedelta

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent / "src"))

from soccersmartbet.pre_gambling_flow.tools.team import calculate_recovery_time


def test_calculate_recovery():
    """Test recovery time calculation for team."""
    next_week = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
    
    result = calculate_recovery_time("Manchester City", next_week)
    
    assert "error" in result
    assert "recovery_days" in result
    assert "recovery_status" in result
    
    if result["error"]:
        print(f"Error: {result['error']}")
    else:
        print(f"✅ {result['team_name']}:")
        print(f"   Last match: {result['last_match_date']}")
        print(f"   Recovery: {result['recovery_days']} days ({result['recovery_status']})")


if __name__ == "__main__":
    test_calculate_recovery()
