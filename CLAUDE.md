# SoccerSmartBet — Project Rules

## TIMEZONE: ISR ONLY — NO EXCEPTIONS

**NEVER use `datetime.now()`, `datetime.now(ISR_TZ)`, `datetime.utcnow()`, or any raw datetime construction.**

ALWAYS use the helpers from `soccersmartbet.utils.timezone`:
- `now_isr()` — current time
- `utc_to_isr()` — convert API responses
- `format_isr_time()` — display HH:MM
- `format_isr_date()` — display YYYY-MM-DD

Before committing ANY code, grep for `datetime.now` — if it appears outside `utils/timezone.py`, the code is WRONG.

This rule has been violated 10+ times. There are no exceptions. No "it's technically equivalent." Use the utils.

## DB: Schema changes must hit live DB

`deployment/db/init/001_create_schema.sql` only runs on first Docker volume creation. Editing it does NOT update the running database.

**NEVER run live DDL without Omer's explicit approval for that specific change.** This applies to agents, sub-agents, parallel waves, worktrees — everything. The live DB is shared across all worktrees; it is not isolated by git branches. Stage DDL in the SQL file only. Live-apply happens ONLY after Omer's explicit OK for that specific DDL. When dispatching sub-agents, do NOT instruct them to run `docker exec ... psql ...` or any other live-DB command as part of their task; that step belongs to the orchestrator after approval.

When changing schema (with approval):
1. Edit the SQL file
2. Get Omer's explicit OK to apply against live DB
3. Run the same DDL against live DB: `docker exec soccersmartbet-staging psql -U postgres -d soccersmartbet_staging -c "..."`
4. If the bot is running, restart it after code changes
5. NEVER delete the Docker volume or database — data must survive

## GIT: Never rewrite history

No `--amend`, no `--force-push`, no squashing, no interactive rebase. Ever. Unless explicitly asked. Honest commit history, even if it shows mistakes.

## BOT: Restart after ANY DB data change

The team registry caches in memory on first load. If you insert/update teams, the running bot won't see them. ALWAYS restart the bot after DB changes. This has caused 3 incidents.

## DB: PostgreSQL timezone is Asia/Jerusalem

Set via `ALTER DATABASE`. All `created_at` columns are `TIMESTAMPTZ`. All timestamps display in ISR. Do not change this.
