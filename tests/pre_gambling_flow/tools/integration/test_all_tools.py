"""
Integration test: Run ALL tools for a single match.

User provides two team names, test runs all 7 tools and reports results.
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent / "src"))

from soccersmartbet.pre_gambling_flow.tools.game import (
    fetch_h2h,
    fetch_venue,
    fetch_weather,
)
from soccersmartbet.pre_gambling_flow.tools.team import (
    fetch_form,
    fetch_injuries,
    fetch_key_players_form,
    calculate_recovery_time,
)


def print_section(title):
    """Print section header."""
    print("\n" + "=" * 70)
    print(f" {title}")
    print("=" * 70)


def print_result(tool_name, result, success_key=None):
    """Print tool result with pass/fail status."""
    has_error = result.get("error") is not None
    
    if has_error:
        status = "❌ FAILED"
        print(f"\n{tool_name}: {status}")
        print(f"  Error: {result['error']}")
    else:
        # Check if we got actual data
        if success_key:
            has_data = result.get(success_key) is not None and len(result.get(success_key, [])) > 0
        else:
            has_data = True
        
        status = "✅ PASSED" if has_data else "⚠️  NO DATA"
        print(f"\n{tool_name}: {status}")
        
        # Print key fields
        for key, value in result.items():
            if key == "error":
                continue
            if isinstance(value, list):
                print(f"  {key}: {len(value)} items")
                # Show all items (or first 5 if more than 5)
                items_to_show = value[:5] if len(value) > 5 else value
                for item in items_to_show:
                    print(f"    - {item}")
                if len(value) > 5:
                    print(f"    ... and {len(value) - 5} more")
            elif isinstance(value, dict):
                print(f"  {key}: {value}")
            else:
                print(f"  {key}: {value}")
    
    return not has_error


def test_all_tools(home_team, away_team):
    """
    Run all 7 tools for a match and report results.
    
    Args:
        home_team: Home team name
        away_team: Away team name
    """
    print_section(f"INTEGRATION TEST: {home_team} vs {away_team}")
    print(f"Testing all 7 tools with team names only (no league_id)")
    
    results = {
        "passed": [],
        "failed": [],
        "no_data": []
    }
    
    # GAME TOOLS (3 tools - called once per match)
    print_section("GAME TOOLS")
    
    # 1. H2H
    print("\n[1/11] fetch_h2h...")
    h2h_result = fetch_h2h(home_team, away_team, limit=5)
    success = print_result("fetch_h2h", h2h_result, success_key="h2h_matches")
    
    if success:
        if h2h_result.get("total_h2h", 0) > 0:
            results["passed"].append("fetch_h2h")
        else:
            results["no_data"].append("fetch_h2h")
    else:
        results["failed"].append("fetch_h2h")
    
    # Extract match date for later tools
    upcoming_match_date = h2h_result.get("upcoming_match_date")
    if not upcoming_match_date:
        upcoming_match_date = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
        print(f"  ⚠️  Using estimated match date: {upcoming_match_date}")
    
    # 2. Venue
    print(f"\n[2/11] fetch_venue...")
    venue_result = fetch_venue(home_team, away_team)
    success = print_result("fetch_venue", venue_result)
    (results["passed"] if success else results["failed"]).append("fetch_venue")
    
    # 3. Weather
    print(f"\n[3/11] fetch_weather...")
    match_datetime = f"{upcoming_match_date}T15:00:00"
    weather_result = fetch_weather(home_team, away_team, match_datetime)
    success = print_result("fetch_weather", weather_result)
    (results["passed"] if success else results["failed"]).append("fetch_weather")
    
    # TEAM TOOLS - HOME TEAM (4 tools)
    print_section(f"TEAM TOOLS - {home_team}")
    
    # 4. Form
    print(f"\n[4/11] fetch_form...")
    form_result = fetch_form(home_team, limit=5)
    success = print_result("fetch_form", form_result, success_key="matches")
    
    if success:
        if form_result.get("matches"):
            results["passed"].append(f"fetch_form({home_team})")
        else:
            results["no_data"].append(f"fetch_form({home_team})")
    else:
        results["failed"].append(f"fetch_form({home_team})")
    
    # 5. Injuries
    print(f"\n[5/11] fetch_injuries...")
    injuries_result = fetch_injuries(home_team)
    success = print_result("fetch_injuries", injuries_result)
    (results["passed"] if success else results["failed"]).append(f"fetch_injuries({home_team})")
    
    # 6. Key Players
    print(f"\n[6/11] fetch_key_players_form...")
    key_players_result = fetch_key_players_form(home_team, top_n=5)
    success = print_result("fetch_key_players_form", key_players_result, success_key="top_players")
    
    if success:
        if key_players_result.get("total_players", 0) > 0:
            results["passed"].append(f"fetch_key_players_form({home_team})")
        else:
            results["no_data"].append(f"fetch_key_players_form({home_team})")
    else:
        results["failed"].append(f"fetch_key_players_form({home_team})")
    
    # 7. Recovery Time
    print(f"\n[7/11] calculate_recovery_time...")
    recovery_result = calculate_recovery_time(home_team, upcoming_match_date)
    success = print_result("calculate_recovery_time", recovery_result)
    (results["passed"] if success else results["failed"]).append(f"calculate_recovery_time({home_team})")
    
    # TEAM TOOLS - AWAY TEAM (4 tools)
    print_section(f"TEAM TOOLS - {away_team}")
    
    # 8. Form
    print(f"\n[8/11] fetch_form...")
    away_form = fetch_form(away_team, limit=5)
    success = print_result("fetch_form", away_form, success_key="matches")
    if success:
        if away_form.get("matches"):
            results["passed"].append(f"fetch_form({away_team})")
        else:
            results["no_data"].append(f"fetch_form({away_team})")
    else:
        results["failed"].append(f"fetch_form({away_team})")
    
    # 9. Injuries
    print(f"\n[9/11] fetch_injuries...")
    away_injuries = fetch_injuries(away_team)
    success = print_result("fetch_injuries", away_injuries)
    (results["passed"] if success else results["failed"]).append(f"fetch_injuries({away_team})")
    
    # 10. Key Players
    print(f"\n[10/11] fetch_key_players_form...")
    away_players = fetch_key_players_form(away_team, top_n=5)
    success = print_result("fetch_key_players_form", away_players, success_key="top_players")
    if success:
        if away_players.get("total_players", 0) > 0:
            results["passed"].append(f"fetch_key_players_form({away_team})")
        else:
            results["no_data"].append(f"fetch_key_players_form({away_team})")
    else:
        results["failed"].append(f"fetch_key_players_form({away_team})")
    
    # 11. Recovery Time
    print(f"\n[11/11] calculate_recovery_time...")
    away_recovery = calculate_recovery_time(away_team, upcoming_match_date)
    success = print_result("calculate_recovery_time", away_recovery)
    (results["passed"] if success else results["failed"]).append(f"calculate_recovery_time({away_team})")
    
    # FINAL REPORT
    print_section("FINAL REPORT")
    
    total_tools = len(results["passed"]) + len(results["failed"]) + len(results["no_data"])
    passed_count = len(results["passed"])
    failed_count = len(results["failed"])
    no_data_count = len(results["no_data"])
    
    print(f"\nTotal tools tested: {total_tools}")
    print(f"✅ Passed: {passed_count}")
    print(f"⚠️  No data: {no_data_count}")
    print(f"❌ Failed: {failed_count}")
    
    if results["passed"]:
        print("\n✅ PASSED:")
        for tool in results["passed"]:
            print(f"  - {tool}")
    
    if results["no_data"]:
        print("\n⚠️  NO DATA (tool works but returned empty):")
        for tool in results["no_data"]:
            print(f"  - {tool}")
    
    if results["failed"]:
        print("\n❌ FAILED:")
        for tool in results["failed"]:
            print(f"  - {tool}")
    
    print("\n" + "=" * 70)
    
    if failed_count == 0:
        print("✅ ALL TOOLS WORKING")
    else:
        print(f"⚠️  {failed_count} TOOLS BROKEN")
    
    print("=" * 70)
    
    return failed_count == 0


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 3:
        print("Usage: python test_all_tools.py <home_team> <away_team>")
        print("Example: python test_all_tools.py 'Manchester City' 'Tottenham'")
        print("         python test_all_tools.py 'Barcelona' 'Real Madrid'")
        sys.exit(1)
    
    home_team = sys.argv[1]
    away_team = sys.argv[2]
    
    success = test_all_tools(home_team, away_team)
    sys.exit(0 if success else 1)
