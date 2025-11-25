# Weather Vertical

**Purpose:** Assess weather-related cancellation risk and draw probability impact (rain/snow → defensive play)

---

## Requirements

- Weather forecast for match kickoff time
- Temperature, precipitation, wind speed
- Venue coordinates (stadium lat/lon)
- Hourly forecast precision

---

## Primary Source: Open-Meteo

**Status:** ✅ Enabled  
**Type:** REST API, Free (no API key required)  
**Details:** See [sources/open-meteo.md](../sources/open-meteo.md)

### Key Features
- **No API key required** (instant use)
- 10,000 requests/day free
- Hourly forecasts up to 7 days ahead
- 1-11km resolution
- Historical weather (80+ years)

### Data Fields Provided
```json
{
  "hourly": {
    "time": ["2025-11-20T15:00"],
    "temperature_2m": [12.5],
    "precipitation": [0.0],
    "windspeed_10m": [15.3]
  }
}
```

---

## AI Analysis Requirement

The **Game Intelligence Agent** uses weather data to assess:
- **Cancellation risk:** Heavy snow/ice → match cancelled → auto-draw bet?
- **Draw probability increase:** Rain → defensive play → more draws
- **Extreme conditions:** Very high wind → unpredictable ball movement

**Tool:** `fetch_weather(lat, lon, match_time)` returns forecast  
**AI Agent:** Interprets impact on betting decision

---

## Venue Coordinates

**Note:** Stadium coordinates must be mapped from fixture venue names.

### Example Stadium Coordinates
```python
STADIUM_COORDS = {
    "Old Trafford": (53.4631, -2.2913),
    "Anfield": (53.4308, -2.9608),
    "Emirates Stadium": (51.5549, -0.1084),
    "Santiago Bernabéu": (40.4530, -3.6883),
    "Camp Nou": (41.3809, 2.1228)
}
```

**Implementation:** Maintain a DB table of stadium names → (lat, lon)

---

## Implementation Notes

1. **Fetch Strategy:** After fixture selection, lookup venue coordinates
2. **Quota:** ~3-5 requests/day for filtered games (negligible vs 10k limit)
3. **Timing:** Fetch forecast 1-2 hours before kickoff for accuracy
4. **Caching:** Weather changes, re-fetch if game moved/postponed
5. **Unknown Stadium:** If venue not in DB, skip weather analysis (non-critical data)

---

## See Also
- [Game Intelligence Agent](../../../../PRE_GAMBLING_OPTIMIZED_FLOW_TASKS.md#42-game-intelligence-agent-node) - uses weather for risk assessment
- [Open-Meteo Source](../sources/open-meteo.md) - API details and code examples
