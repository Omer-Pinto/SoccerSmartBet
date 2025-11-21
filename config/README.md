# SoccerSmartBet Configuration Guide - MVP

This directory contains the minimal configuration system for SoccerSmartBet MVP.

## Overview

The configuration uses a simple two-file approach:
1. **`config.yaml`** - Non-sensitive settings (betting thresholds, database connection, model)
2. **`.env`** - Sensitive credentials (API keys, passwords)

## Quick Start

### 1. Set Up Environment Variables

```bash
# Copy the example file
cp config/.env.example config/.env

# Edit .env with your actual credentials
nano config/.env  # or use your preferred editor
```

**Required:**
- `OPENAI_API_KEY` - For LLM models (gpt-4o-mini)
- `DB_USER` and `DB_PASSWORD` - Database credentials

**Optional:**
- `LANGSMITH_API_KEY` - For LangGraph tracing (commented out in .env.example)

### 2. Customize Settings (Optional)

Edit `config/config.yaml` to adjust:
- `betting.min_odds_threshold` - Minimum odds to consider (default: 1.5)
- `betting.max_daily_games` - Max games per day (default: 3)
- `betting.stake_per_game` - Simulated stake in NIS (default: 100)
- `database.*` - Database connection settings
- `models.default` - LLM model to use (default: gpt-4o-mini)

## Configuration Files

### config.yaml

Minimal MVP configuration with only essential settings:

```yaml
# Betting
betting:
  min_odds_threshold: 1.5
  max_daily_games: 3
  stake_per_game: 100

# Database
database:
  host: localhost
  port: 5432
  name: soccersmartbet

# Models
models:
  default: gpt-4o-mini
```

### .env

Single environment file for MVP. Future versions may use `.env.staging` and `.env.production` for separate environments.

```bash
# Database
DB_USER=postgres
DB_PASSWORD=your_password_here

# OpenAI (Required)
OPENAI_API_KEY=your_openai_api_key_here

# LangSmith (Optional - commented out by default)
# LANGSMITH_API_KEY=your_key
# LANGSMITH_TRACING=true
# LANGSMITH_PROJECT=SoccerSmartBet
```

## Loading Configuration in Code

Simple Python example:

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
db_host = config['database']['host']
db_name = config['database']['name']
openai_key = os.getenv('OPENAI_API_KEY')
db_user = os.getenv('DB_USER')
db_password = os.getenv('DB_PASSWORD')

# Build database URL
db_url = f"postgresql://{db_user}:{db_password}@{db_host}:5432/{db_name}"
```

## Security Best Practices

### ✅ DO:
- Keep `.env` file in `.gitignore` (already configured)
- Use environment variables for all secrets
- Never commit `.env` to git

### ❌ DON'T:
- Commit `.env` file to git
- Hardcode API keys in code
- Commit real credentials to `config.yaml`

## Future: Multiple Environments

For production deployment, you can create separate .env files:

```bash
# Create environment-specific files
cp config/.env config/.env.staging
cp config/.env config/.env.production

# Load specific env file in code
from dotenv import load_dotenv
load_dotenv('config/.env.production')
```

## File Structure

```
config/
├── README.md           # This guide
├── config.yaml         # MVP configuration (31 lines)
├── .env.example        # Template for credentials (23 lines)
└── .env               # Your actual credentials (git-ignored)
```

## What Changed from Previous Version

This is a **drastically simplified MVP** configuration:
- **Before:** 230 lines of config.yaml with extensive sections
- **After:** 31 lines with only essential settings
- **Removed:** Performance tuning, data quality, feature flags, detailed logging, scheduling
- **Kept:** Betting thresholds, database connection, model selection
- **Philosophy:** Start minimal, add complexity only when needed

## Next Steps

1. Copy `.env.example` to `.env` and fill in credentials
2. Adjust `config.yaml` if needed (usually defaults are fine)
3. Build the actual application that uses this config
