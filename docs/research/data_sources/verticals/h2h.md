# Head-to-Head (H2H) Statistics Vertical

**Purpose:** Analyze recent encounters between two teams to identify patterns (home dominance, high-scoring trends, defensive patterns)

---

## Requirements

- Last 5-10 matches between two teams
- Results (home/away scores)
- Match dates and venues
- Competition context (league vs cup)

---

## Primary Source: API-Football H2H Endpoint

**Status:** ✅ Enabled  
**Type:** REST API, Free tier (included in 100 req/day)  
**Details:** See [sources/api-football.md#h2h](../sources/api-football.md)

### Key Features
- Included in API-Football free tier
- Returns last N matches between two teams
- Full match details (scores, date, venue, competition)
- Same API as injuries (efficient quota usage)

### Data Fields Provided
```json
{
  "fixture": {
    "id": 123456,
    "date": "2024-10-06T14:00:00+00:00",
    "venue": {"name": "Old Trafford"}
  },
  "teams": {
    "home": {"id": 33, "name": "Manchester United", "winner": true},
    "away": {"id": 34, "name": "Newcastle", "winner": false}
  },
  "goals": {"home": 3, "away": 0}
}
```

---

## AI Analysis Requirement

**⚠️ IMPORTANT:** H2H data is NOT just win/loss counts.

The **Game Intelligence Agent** must extract patterns:
- **Home dominance:** "Man United wins 80% of home fixtures vs Newcastle"
- **High-scoring:** "Last 5 meetings averaged 4.2 goals"
- **Defensive patterns:** "3 of last 4 were under 2.5 goals"
- **Recent trend:** "Liverpool won last 3 encounters after 10-year drought"

**Tool:** `fetch_h2h()` returns raw match list  
**AI Agent:** Synthesizes patterns into betting-relevant insights

---

## Implementation Notes

1. **Fetch per game:** 1 request per selected game (after Smart Game Picker)
2. **Quota:** ~3-5 requests/day for filtered games
3. **Caching:** H2H history changes slowly, cache for 1 week
4. **Limit:** Request last 10 matches max (sufficient for pattern analysis)

---

## See Also
- [Game Intelligence Agent](../../../../PRE_GAMBLING_OPTIMIZED_FLOW_TASKS.md#42-game-intelligence-agent-node) - performs H2H pattern analysis
- [API-Football Source](../sources/api-football.md#h2h) - API details and code examples
