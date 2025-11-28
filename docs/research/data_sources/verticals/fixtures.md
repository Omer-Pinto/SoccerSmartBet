# Fixtures Vertical

**Purpose:** Fetch daily football fixtures to select interesting games for betting

---

## Requirements

- List of today's football matches across major leagues
- Match metadata: teams, kickoff time, venue, competition
- Coverage: Premier League, La Liga, Bundesliga, Serie A, Ligue 1, Champions League
- Update frequency: Once daily (morning)

---

## Primary Source: football-data.org

**Status:** ✅ Enabled  
**Type:** REST API, Free tier  
**Details:** See [sources/football-data.org.md](../sources/football-data.org.md)

### Key Features
- 12 major competitions included
- 10 requests/minute, 100 requests/day
- Well-documented, reliable
- Delayed live scores (use for pre-match only)

### Data Fields Provided
- Fixture ID
- Home/Away teams
- Kickoff time (UTC)
- Competition/league
- Venue (stadium name)
- Status (scheduled, postponed, cancelled)

---

## Implementation Notes

1. **Fetch Strategy:** Call once daily at configured time (e.g., 14:00 UTC)
2. **Caching:** Store fixtures in DB, no re-fetching same day
3. **Filtering:** Filter to interesting games per Smart Game Picker logic
4. **Coverage:** 12 major competitions sufficient for MVP

---

## See Also
- [Game Intelligence Agent](../../../../status/pre_gambling_flow/PRE_GAMBLING_FLOW_TASKS.md#4-game-intelligence-agent-subgraph) - uses fixture data
- [Smart Game Picker](../../../../status/pre_gambling_flow/PRE_GAMBLING_FLOW_TASKS.md#32-smart-game-picker-node) - selects from fixtures
