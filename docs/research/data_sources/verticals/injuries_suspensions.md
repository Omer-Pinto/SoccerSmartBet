# Injuries & Suspensions Vertical

**Purpose:** Identify missing players (injuries, suspensions) to assess team strength impact

---

## Requirements

- Current injury list with player names, injury type, expected return date
- Suspension list (red cards, yellow accumulation) with duration
- **Critical:** Flag if injured/suspended players are starters vs bench warmers
- Team-level data (fetch for both home and away teams)

---

## Primary Source: API-Football Sidelined Endpoint

**Status:** ✅ Enabled  
**Type:** REST API, Free tier (included in 100 req/day)  
**Details:** See [sources/api-football.md#sidelined](../sources/api-football.md)

### Key Features
- Included in API-Football free tier
- Injury type and severity
- Expected return date
- Suspension type (red card, yellow accumulation)
- Player identification (name, ID)

### Data Fields Provided
```json
{
  "type": "Knee Injury",
  "start": "2025-10-15",
  "end": "2025-12-01",
  "player": {
    "id": 276,
    "name": "Bruno Fernandes"
  }
}
```

---

## AI Analysis Requirement

**⚠️ IMPORTANT:** Raw injury lists are NOT enough for betting decisions.

The **Team Intelligence Agent** must analyze whether missing players are critical:
- **For known teams (e.g., Man United):** User may know Bruno Fernandes is key
- **For unknown teams (e.g., Napoli, Atalanta):** AI must identify if injured players are starters

**Tool:** `fetch_injuries()` returns raw list  
**AI Agent:** Analyzes impact → "critical starters missing" vs "minor depth issues"

---

## Implementation Notes

1. **Fetch per team:** Call API-Football sidelined endpoint with team ID
2. **Cache:** Store in DB, update daily (injuries change slowly)
3. **AI Processing:** Team Intelligence Agent must cross-reference with lineup/form data
4. **Quota:** 2 requests per game (home + away teams), ~6-10 requests/day for 3-5 games

---

## See Also
- [Team Intelligence Agent](../../../../PRE_GAMBLING_OPTIMIZED_FLOW_TASKS.md#5-team-intelligence-agent-subgraph) - uses injury data for impact assessment
- [API-Football Source](../sources/api-football.md#sidelined) - API details and code examples
