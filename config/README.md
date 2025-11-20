# SoccerSmartBet Configuration Guide

This directory contains the configuration management system for SoccerSmartBet.

## Overview

The configuration system uses a two-tier approach:
1. **`config.yaml`** - Non-sensitive application settings (thresholds, timeouts, feature flags)
2. **`.env`** - Sensitive credentials (API keys, database passwords)

This separation ensures security best practices: sensitive data never gets committed to git.

## Quick Start

### 1. Set Up Environment Variables

```bash
# Copy the example file
cp config/.env.example config/.env

# Edit .env with your actual credentials
nano config/.env  # or use your preferred editor
```

**Required credentials:**
- `OPENAI_API_KEY` - For LLM models (gpt-4o-mini)
- `LANGSMITH_API_KEY` - For tracing and observability
- `DB_STAGING_PASSWORD` - Staging database password
- `DB_PROD_PASSWORD` - Production database password
- `WEATHER_API_KEY` - For weather data

**Optional (after Task 0.1 research):**
- Football data API keys (depends on chosen provider)
- News API keys for team news

### 2. Verify Configuration

```bash
# Load and validate configuration
python -c "import yaml; print(yaml.safe_load(open('config/config.yaml')))"

# Check environment variables are loaded
python -c "from dotenv import load_dotenv; load_dotenv('config/.env'); import os; print('OK' if os.getenv('OPENAI_API_KEY') else 'MISSING')"
```

### 3. Customize Settings

Edit `config/config.yaml` to adjust:
- Betting thresholds (`betting.min_odds_threshold`)
- Number of daily games (`betting.max_daily_games`)
- Scheduling times (`scheduling.pre_gambling_cron`)
- Model selection (`models.default`)
- Feature flags (`features.*`)

## Configuration Structure

### Betting Configuration

```yaml
betting:
  min_odds_threshold: 1.5      # Filter out games below this odds level
  max_daily_games: 3           # Select up to 3 games per day
  stake_per_game: 100          # Simulated stake in NIS
```

**When to adjust:**
- Increase `min_odds_threshold` to focus on higher-risk, higher-reward games
- Decrease `max_daily_games` during testing or to reduce LLM costs
- `stake_per_game` is for P&L calculations only (simulated betting)

### Scheduling Configuration

```yaml
scheduling:
  pre_gambling_cron: "0 14 * * *"  # Daily at 14:00 (2 PM)
  timezone: "Asia/Jerusalem"
  post_games_delay_hours: 3        # Wait 3 hours after kickoff
  auto_schedule_enabled: true
```

**Cron format:** `"minute hour * * *"`
- `"0 14 * * *"` = 14:00 daily
- `"30 13 * * *"` = 13:30 daily
- `"0 10 * * 6"` = 10:00 on Saturdays only

### Database Configuration

```yaml
database:
  staging:
    host: "localhost"
    port: 5432
    pool_size: 10
  production:
    host: "localhost"
    port: 5433
    pool_size: 20
```

**Environment selection:**
Set `environment: "staging"` or `"production"` at the bottom of config.yaml.

Credentials are loaded from `.env`:
```bash
DB_STAGING_USER=postgres
DB_STAGING_PASSWORD=your_password
```

### Model Configuration

```yaml
models:
  default: "gpt-4o-mini"           # Cost-efficient default
  smart_picker: "gpt-4o-mini"      # Game selection agent
  game_agent: "gpt-4o-mini"        # Game intelligence agent
  team_agent: "gpt-4o-mini"        # Team intelligence agent
  temperature: 0.7
  max_tokens: 2000
```

**Model options:**
- `gpt-4o-mini` - Recommended for cost (~$0.15/$0.60 per 1M tokens)
- `gpt-4o` - More capable but more expensive
- `gpt-4-turbo` - Alternative high-performance option

**When to upgrade models:**
- If agent analysis quality is insufficient, upgrade specific agents
- Example: Use `gpt-4o` for `smart_picker` but keep `gpt-4o-mini` for others

### API Configuration

```yaml
apis:
  fixtures:
    enabled: true
    timeout_seconds: 30
    retry_attempts: 3
  odds:
    source: "winner.co.il"
    use_scraping: true
```

API keys are loaded from `.env`. Provider-specific settings will be added after Task 0.1 research.

### Feature Flags

```yaml
features:
  parallel_subgraphs: true              # Enable parallel execution
  strict_structured_outputs: true        # Enforce Pydantic validation
  tolerate_partial_data: true           # Continue if some tools fail
  smart_game_selection: true            # Use AI picker vs. simple filter
```

**Toggle for testing:**
- Set `parallel_subgraphs: false` to debug issues sequentially
- Set `tolerate_partial_data: false` to require complete data

### Logging Configuration

```yaml
logging:
  level: "INFO"                    # DEBUG | INFO | WARNING | ERROR
  format: "json"                   # json | text
  file_path: "logs/soccersmartbet.log"
  rotation: "daily"
  retention_days: 30
```

**Log levels:**
- `DEBUG` - Verbose output for development
- `INFO` - Standard production logging (recommended)
- `WARNING` - Only warnings and errors
- `ERROR` - Only errors

## Loading Configuration in Code

### Python Example

```python
import yaml
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv('config/.env')

# Load YAML configuration
with open('config/config.yaml', 'r') as f:
    config = yaml.safe_load(f)

# Access settings
min_odds = config['betting']['min_odds_threshold']
db_host = config['database'][os.getenv('ENVIRONMENT', 'staging')]['host']
openai_key = os.getenv('OPENAI_API_KEY')
```

### Configuration Helper (Recommended)

Create a `src/config.py` module:

```python
import yaml
import os
from dotenv import load_dotenv
from pathlib import Path

class Config:
    def __init__(self):
        # Load .env
        load_dotenv(Path(__file__).parent.parent / 'config' / '.env')
        
        # Load YAML
        config_path = Path(__file__).parent.parent / 'config' / 'config.yaml'
        with open(config_path) as f:
            self._config = yaml.safe_load(f)
        
        self.env = os.getenv('ENVIRONMENT', 'staging')
    
    def get(self, key_path: str, default=None):
        """Get config value by dot-separated path"""
        keys = key_path.split('.')
        value = self._config
        for key in keys:
            if isinstance(value, dict):
                value = value.get(key)
            else:
                return default
        return value if value is not None else default
    
    def get_env(self, key: str, default=None):
        """Get environment variable"""
        return os.getenv(key, default)
    
    @property
    def db_url(self):
        """Get current environment's database URL"""
        db_config = self._config['database'][self.env]
        user = self.get_env(f'DB_{self.env.upper()}_USER')
        password = self.get_env(f'DB_{self.env.upper()}_PASSWORD')
        return f"postgresql://{user}:{password}@{db_config['host']}:{db_config['port']}/{db_config['database']}"

# Singleton instance
config = Config()
```

Usage:
```python
from config import config

min_odds = config.get('betting.min_odds_threshold')
db_url = config.db_url
openai_key = config.get_env('OPENAI_API_KEY')
```

## Security Best Practices

### ✅ DO:
- Keep `.env` file in `.gitignore`
- Use separate credentials for staging and production
- Rotate API keys regularly
- Use environment variables for all secrets
- Review `.env.example` when adding new secrets

### ❌ DON'T:
- Commit `.env` file to git
- Hardcode API keys in code
- Share production credentials in Slack/email
- Use production credentials in staging
- Commit real values to `config.yaml`

## Environment-Specific Overrides

For different environments, you can:

1. **Use separate .env files:**
```bash
cp config/.env config/.env.staging
cp config/.env config/.env.production
```

2. **Load specific env file:**
```python
env = os.getenv('ENVIRONMENT', 'staging')
load_dotenv(f'config/.env.{env}')
```

3. **Override via environment variables:**
```bash
export ENVIRONMENT=production
export DB_PROD_PASSWORD=different_password
python main.py
```

## Validation

The configuration system should validate on startup:

```python
def validate_config():
    """Validate required configuration is present"""
    required_env_vars = [
        'OPENAI_API_KEY',
        'LANGSMITH_API_KEY',
        'DB_STAGING_PASSWORD',
        'DB_PROD_PASSWORD'
    ]
    
    missing = [var for var in required_env_vars if not os.getenv(var)]
    
    if missing:
        raise ValueError(f"Missing required environment variables: {', '.join(missing)}")
    
    # Validate YAML structure
    required_config_keys = ['betting', 'database', 'models', 'scheduling']
    for key in required_config_keys:
        if key not in config._config:
            raise ValueError(f"Missing required config section: {key}")
    
    print("✅ Configuration validated successfully")

# Run on startup
validate_config()
```

## Troubleshooting

### Configuration not loading
```bash
# Check file exists
ls -la config/config.yaml
ls -la config/.env

# Validate YAML syntax
python -c "import yaml; yaml.safe_load(open('config/config.yaml'))"
```

### Environment variables not set
```bash
# Check .env file is being loaded
python -c "from dotenv import load_dotenv; load_dotenv('config/.env'); import os; print(os.environ.get('OPENAI_API_KEY', 'NOT SET'))"

# Ensure .env path is correct
python -c "from pathlib import Path; print(Path('config/.env').absolute())"
```

### Database connection fails
```bash
# Test database connection
psql -U postgres -h localhost -p 5432 -d soccersmartbet_staging

# Check credentials match .env
grep DB_STAGING config/.env
```

## Next Steps

After setting up configuration:

1. **Task 1.1:** Ensure database schema matches the database configuration
2. **Task 0.1:** Add API provider details to `apis` section after research
3. **Task 1.4:** Use config in docker-compose for database initialization
4. **Task 2.5:** Tools will use API keys from environment variables

## File Structure

```
config/
├── README.md           # This file
├── config.yaml         # Main configuration (non-sensitive)
├── .env.example        # Template for credentials
└── .env               # Your actual credentials (git-ignored)
```

## Support

For questions or issues with configuration:
1. Check this README
2. Review `.env.example` for required variables
3. Validate YAML syntax in `config.yaml`
4. Ensure all required environment variables are set
