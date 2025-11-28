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

### Enabled APIs (Free Tier)
- ✅ **football-data.org** - Fixtures, H2H statistics
- ✅ **The Odds API** - Betting lines
- ✅ **apifootball.com** - Injuries, suspensions, H2H backup, team form
- ✅ **Open-Meteo** - Weather data (no key required)

### Test Files
- `test_football_data_org.py` - Fixtures and H2H endpoint tests
- `test_odds_api.py` - Betting lines retrieval tests
- `test_apifootball.py` - Injuries, suspensions, team form tests
- `test_open_meteo.py` - Weather data tests

## Running Tests

```bash
# Run all API integration tests
pytest tests/api_integration/ -v

# Run specific API test
pytest tests/api_integration/test_football_data_org.py -v

# Run with verbose output (show API responses)
pytest tests/api_integration/ -v -s
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

## Expected Behavior

Each test should:
1. ✅ Connect to the API successfully
2. ✅ Return valid JSON/data structure
3. ✅ Handle errors gracefully (rate limits, invalid requests)
4. ✅ Validate data format matches expected schema

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
