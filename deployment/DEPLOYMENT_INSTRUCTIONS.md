# Docker Deployment Instructions

## Quick Start

```bash
# 1. Ensure .env configured at project root
cd /path/to/SoccerSmartBet
cp .env.example .env
# Edit .env with your passwords (POSTGRES_STAGING_PASSWORD, POSTGRES_PROD_PASSWORD)

# 2. Start staging database
cd deployment
docker-compose up -d postgres-staging

# 3. Verify running
docker-compose ps
docker logs soccersmartbet-staging
```

## Environments

- **Staging**: Port 5432, DB: `soccersmartbet_staging`
- **Production**: Port 5433, DB: `soccersmartbet_prod`

## Connect to Database

```bash
# Staging
psql -h localhost -p 5432 -U postgres -d soccersmartbet_staging

# Production
psql -h localhost -p 5433 -U postgres -d soccersmartbet_prod
```

## Schema Initialization

Schema (`db/init/001_create_schema.sql`) runs automatically on first container start.

## Management

```bash
# Stop
docker-compose down

# View logs
docker-compose logs -f postgres-staging

# Reset database (deletes all data!)
docker-compose down -v
docker-compose up -d postgres-staging
```
