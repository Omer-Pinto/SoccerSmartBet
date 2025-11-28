# API Integration Tests (Batch 2 - Task 0.4)

This directory contains integration tests for all football data APIs used in SoccerSmartBet.

## Prerequisites

Before running these tests, you must:

1. **Register for API keys** from the following services:
   - [football-data.org](https://www.football-data.org/client/register) → `FOOTBALL_DATA_API_KEY`
   - [The Odds API](https://the-odds-api.com/) → `ODDS_API_KEY`
   - [apifootball.com](https://apifootball.com/) → `APIFOOTBALL_API_KEY`

2. **Create `.env` file** in the project root:
   ```bash
   cp .env.example .env
   ```

3. **Add your API keys** to `.env` file (see `.env.example` for template)

## Test Coverage

**Total: 24 tests across 4 APIs** (All passing ✅)

### What Each Test Validates

| Vertical | API | Test | Validates |
|----------|-----|------|-----------|
| **Fixtures** | football-data.org | test_get_upcoming_fixtures | Matches >= today (NOT 2021-2023 data) |
| **H2H** | football-data.org | test_get_h2h_last_5_matches_only | Last 5 meetings between 2 teams only |
| **H2H (Backup)** | apifootball | test_get_h2h_between_two_teams | get_H2H action for 2 specific teams |
| **Odds** | The Odds API | test_get_current_soccer_odds | Odds >= yesterday (dynamic date check) |
| **Odds Format** | The Odds API | test_odds_decimal_format | Israeli decimal format |
| **Odds Market** | The Odds API | test_h2h_market | 3 outcomes (1/X/2) |
| **Injuries** | apifootball | test_get_current_team_injuries | Current season injury status |
| **Team Form** | apifootball | test_get_last_5_team_matches | Last 30 days matches |
| **Player Stats** | apifootball | test_get_current_top_scorers | Current season goals |
| **Weather** | Open-Meteo | 10 weather tests | Current/future forecasts |
| **Error Handling** | All APIs | test_invalid_api_key | Proper error responses |

### Test Files Breakdown

- `test_football_data_org.py` - **3 tests** (fixtures, H2H, error handling)
- `test_odds_api.py` - **5 tests** (odds retrieval, format, market, sports list, error handling)
- `test_apifootball.py` - **5 tests** (injuries, H2H, team form, top scorers, error handling)
- `test_open_meteo.py` - **10 tests** (weather variables, date/time handling, no auth verification)

## Running Tests

**Note:** This project uses `uv` for package management. Run tests through your IDE's test runner or uv.

```bash
# Run all API integration tests
uv run pytest tests/api_integration/ -v

# Run specific API test
uv run pytest tests/api_integration/test_football_data_org.py -v

# Run with verbose output (show API responses)
uv run pytest tests/api_integration/ -v -s
```

## Rate Limits

**Important:** These tests make real API calls. Be mindful of rate limits:

| API | Free Tier Limit | Test Impact |
|-----|-----------------|-------------|
| football-data.org | 10 req/min | Low - 2-3 tests |
| The Odds API | 500 credits/month | Medium - ~5 credits per test run |
| apifootball.com | 180 req/hour (6,480/day) | Low - 5-10 tests |
| Open-Meteo | 10k req/day | Negligible |

**Recommendation:** Run tests sparingly during development, use mocks for frequent testing.

## Test Design Principles

All tests follow these rules:
1. ✅ **Current data only** - No hardcoded dates, all dates calculated dynamically
2. ✅ **Smart H2H queries** - Use dedicated H2H endpoints (limit=5), NOT date range filtering
3. ✅ **No rate limit hammering** - Tests don't intentionally trigger rate limits
4. ✅ **Focused on app needs** - Test what the betting app requires, not API infrastructure
5. ✅ **Verify data currency** - Fixtures >= today, odds >= yesterday, injuries current season

## Troubleshooting

### "API key not found" error
- Ensure `.env` file exists in project root
- Verify API key variable names match `.env.example`
- Check for typos in API keys

### Rate limit exceeded
- Wait for rate limit window to reset
- Reduce test frequency
- Consider implementing API response caching

### Connection timeout
- Check internet connection
- Verify API service is operational (check status pages)
- Increase timeout values in test configuration

## References

- [Data Sources Executive Summary](../../docs/research/data_sources/executive_summary.md)
- [football-data.org API Docs](../../docs/research/data_sources/sources/football-data.org.md)
- [The Odds API Docs](../../docs/research/data_sources/sources/the-odds-api.md)
- [apifootball.com API Docs](../../docs/research/data_sources/sources/apifootball.md)
- [Open-Meteo API Docs](../../docs/research/data_sources/sources/open-meteo.md)
