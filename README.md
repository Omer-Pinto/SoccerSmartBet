# SoccerSmartBet - Docker Database Setup

This directory contains Docker Compose configuration for SoccerSmartBet PostgreSQL databases (staging and production environments).

## 📋 Overview

The Docker setup provides two isolated PostgreSQL 16 database instances:

- **Staging** (port 5432): Development and testing environment
- **Production** (port 5433): Production deployment environment

Both databases use the same schema defined in `db/init/001_create_schema.sql` (from PR #4).

## 🚀 Quick Start

### 1. Prerequisites

- Docker Engine 20.10+ and Docker Compose 2.0+
- At least 2GB free disk space for database volumes

Verify Docker installation:
```bash
docker --version
docker-compose --version
```

### 2. Configuration

Copy the environment template and configure credentials:

```bash
cp .env.example .env
```

Edit `.env` and replace placeholder passwords:
```bash
# Update these with secure passwords
POSTGRES_STAGING_PASSWORD=your_secure_staging_password
POSTGRES_PROD_PASSWORD=your_secure_production_password
```

**Security Note:** Never commit `.env` to version control. It's already in `.gitignore`.

### 3. Start Databases

#### Start staging database only:
```bash
docker-compose up -d postgres-staging
```

#### Start production database only:
```bash
docker-compose up -d postgres-production
```

#### Start both databases:
```bash
docker-compose up -d
```

### 4. Verify Health

Check container status:
```bash
docker-compose ps
```

Expected output:
```
NAME                        STATUS              PORTS
soccersmartbet-staging      Up (healthy)        0.0.0.0:5432->5432/tcp
soccersmartbet-production   Up (healthy)        0.0.0.0:5433->5432/tcp
```

View logs:
```bash
# Staging logs
docker-compose logs -f postgres-staging

# Production logs
docker-compose logs -f postgres-production
```

## 🔌 Connecting to Databases

### Connection Details

**Staging Database:**
- Host: `localhost`
- Port: `5432`
- Database: `soccersmartbet_staging`
- User: `postgres`
- Password: (from `.env`)

**Production Database:**
- Host: `localhost`
- Port: `5433`
- Database: `soccersmartbet_prod`
- User: `postgres`
- Password: (from `.env`)

### Using psql CLI

```bash
# Connect to staging
docker exec -it soccersmartbet-staging psql -U postgres -d soccersmartbet_staging

# Connect to production
docker exec -it soccersmartbet-production psql -U postgres -d soccersmartbet_prod
```

### Using pgAdmin or DBeaver

Configure a new connection with the details above. For production, remember to use port `5433`.

### Python Connection String

```python
# Staging
STAGING_DB_URL = "postgresql://postgres:your_password@localhost:5432/soccersmartbet_staging"

# Production
PROD_DB_URL = "postgresql://postgres:your_password@localhost:5433/soccersmartbet_prod"
```

## 📊 Database Schema

The schema is automatically initialized on first startup from `db/init/001_create_schema.sql`. It includes:

### Core Tables
- `teams` - Football team master data
- `players` - Player roster for injury/suspension tracking
- `games` - Match fixtures and processing status
- `betting_lines` - Odds from winner.co.il
- `game_reports` - AI-generated game analysis
- `team_reports` - AI-generated team analysis
- `unfiltered_games` - Historical snapshot of all games considered
- `bets` - User and AI betting predictions
- `results` - Match results and P&L calculations

### Test Data

Staging databases are seeded with test data from `db/init/002_seed_test_data.sql` including:
- 10 football teams (Premier League, La Liga, Bundesliga)
- 10 key players
- 3 upcoming test fixtures
- Sample betting lines, reports, and bets

**Note:** Test data is for development only. Production databases should NOT load test data.

To skip test data loading, remove or rename `002_seed_test_data.sql` before first startup.

## 🛠️ Common Operations

### Stop Databases

```bash
# Stop all
docker-compose stop

# Stop specific database
docker-compose stop postgres-staging
```

### Restart Databases

```bash
# Restart all
docker-compose restart

# Restart specific
docker-compose restart postgres-production
```

### View Database Logs

```bash
# Follow logs in real-time
docker-compose logs -f postgres-staging

# Last 100 lines
docker-compose logs --tail=100 postgres-production
```

### Execute SQL Queries

```bash
# Run a query directly
docker exec -it soccersmartbet-staging psql -U postgres -d soccersmartbet_staging -c "SELECT COUNT(*) FROM teams;"

# Run a SQL file
docker exec -i soccersmartbet-staging psql -U postgres -d soccersmartbet_staging < my_query.sql
```

### Database Shell Access

```bash
# Open psql shell in staging
docker exec -it soccersmartbet-staging psql -U postgres -d soccersmartbet_staging

# Common psql commands:
# \dt          - List tables
# \d teams     - Describe teams table
# \l           - List databases
# \q           - Quit
```

## 💾 Backup and Restore

### Backup Database

#### Full database backup:
```bash
# Staging backup
docker exec soccersmartbet-staging pg_dump -U postgres soccersmartbet_staging > staging_backup_$(date +%Y%m%d).sql

# Production backup
docker exec soccersmartbet-production pg_dump -U postgres soccersmartbet_prod > prod_backup_$(date +%Y%m%d).sql
```

#### Schema-only backup:
```bash
docker exec soccersmartbet-staging pg_dump -U postgres --schema-only soccersmartbet_staging > schema_backup.sql
```

#### Data-only backup:
```bash
docker exec soccersmartbet-staging pg_dump -U postgres --data-only soccersmartbet_staging > data_backup.sql
```

### Restore Database

```bash
# Restore to staging
docker exec -i soccersmartbet-staging psql -U postgres -d soccersmartbet_staging < staging_backup_20241121.sql

# Restore to production (BE CAREFUL!)
docker exec -i soccersmartbet-production psql -U postgres -d soccersmartbet_prod < prod_backup_20241121.sql
```

### Automated Backups

For production, consider setting up automated daily backups via cron:

```bash
# Add to crontab (crontab -e)
0 2 * * * docker exec soccersmartbet-production pg_dump -U postgres soccersmartbet_prod > /backups/prod_$(date +\%Y\%m\%d).sql
```

## 🔄 Reset Database

**Warning:** This destroys ALL data and recreates from scratch.

### Reset staging database:
```bash
docker-compose down
docker volume rm soccersmartbet-staging-data
docker-compose up -d postgres-staging
```

### Reset production database:
```bash
# ⚠️ DANGER: This deletes production data
docker-compose stop postgres-production
docker volume rm soccersmartbet-prod-data
docker-compose up -d postgres-production
```

## 🐛 Troubleshooting

### Database won't start

**Check logs:**
```bash
docker-compose logs postgres-staging
```

**Common issues:**
- Port already in use: Change `STAGING_PORT` or `PROD_PORT` in `.env`
- Permission denied: Ensure Docker has disk access permissions
- Out of disk space: Clean up Docker: `docker system prune`

### Connection refused

**Check container health:**
```bash
docker-compose ps
```

**Verify port binding:**
```bash
docker ps | grep soccersmartbet
```

**Test connection:**
```bash
docker exec soccersmartbet-staging pg_isready -U postgres
```

### Schema not initialized

If tables are missing, check init script logs:
```bash
docker-compose logs postgres-staging | grep -i init
```

Reinitialize by resetting the database (see Reset Database section).

### Performance Issues

**Check container resource usage:**
```bash
docker stats soccersmartbet-staging
```

**Enable query logging** (edit `docker-compose.yml`):
```yaml
command: ["postgres", "-c", "log_statement=all"]
```

## 📁 Directory Structure

```
.
├── docker-compose.yml          # Docker Compose configuration
├── .env.example                # Environment variables template
├── .env                        # Your local configuration (not in git)
├── db/
│   └── init/
│       ├── 001_create_schema.sql    # Database schema (from PR #4)
│       └── 002_seed_test_data.sql   # Test data for development
└── README.md                   # This file
```

## 🔒 Security Best Practices

1. **Strong Passwords:** Use 16+ character passwords with mixed case, numbers, and symbols
2. **Separate Credentials:** Different passwords for staging and production
3. **Never Commit Secrets:** `.env` is in `.gitignore` - keep it that way
4. **Production Secrets Management:** Use AWS Secrets Manager, HashiCorp Vault, etc. for production deployments
5. **Network Isolation:** Consider Docker networks or VPNs for production database access
6. **Regular Backups:** Implement automated backup strategy for production
7. **Access Control:** Use PostgreSQL roles and restrict permissions for application users

## 🚀 Next Steps

1. ✅ Start databases with `docker-compose up -d`
2. ✅ Verify connections with `docker-compose ps`
3. ✅ Explore test data in staging database
4. ⏭️ Integrate with SoccerSmartBet Python application (Task 2.1+)
5. ⏭️ Set up LangSmith tracing (Task 0.2)
6. ⏭️ Configure application config.yaml (Task 1.2)

## 📚 Additional Resources

- [PostgreSQL Docker Official Image](https://hub.docker.com/_/postgres)
- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/16/)
- [SoccerSmartBet Schema Documentation](./db/schema.md) _(from PR #4)_

## 🆘 Support

For issues or questions:
1. Check the Troubleshooting section above
2. Review Docker Compose logs: `docker-compose logs`
3. Consult PR #4 for schema details
4. Open an issue in the SoccerSmartBet repository

---

**Infrastructure Droid** 🤖 | Task 1.4 Complete
