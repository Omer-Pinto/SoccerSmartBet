# Wave 8 Contract — Report Refactor Track

> Produced by Agent 8A. Branch: `major_report_refactor`. 8B code on disk uncommitted.

## 1. Target Pydantic Contract

**`GameReport`** — structured fields filled by Python; bullet fields + classification filled by LLM.

| Field | Type | Source |
|-------|------|--------|
| `h2h` | `H2HAggregate \| None` | Python (from `fetch_h2h`) |
| `h2h_bullets` | `list[str]` (≤2, ≤20 words) | LLM |
| `weather_bullets` | `list[str]` (≤3, ≤20 words) | LLM |
| `weather_cancellation_risk` | `Literal["low","medium","high","unknown"]` | LLM |
| `venue` | `str \| None` | Python (from `fetch_venue`) |

**`H2HAggregate`**: `home_team`, `away_team`, `home_team_wins`, `away_team_wins`, `draws`, `total_meetings`. Keyed by today's team identity. No historical per-match list.

**`TeamReport`**

| Field | Type | Source |
|-------|------|--------|
| `recovery_days` | `int` | Python |
| `form_streak` | `str` (5 chars, most recent LAST, `?` for missing) | Python |
| `last_5_games` | `list[RecentMatch]` | Python |
| `form_bullets` | `list[str]` (≤2, ≤12 words) | LLM |
| `league_rank` | `int \| None` | Python |
| `league_points` | `int \| None` | Python |
| `league_matches_played` | `int \| None` | Python |
| `league_bullets` | `list[str]` (≤3, ≤20 words) | LLM |
| `injury_bullets` | `list[str]` (≤5) | LLM |
| `news_bullets` | `list[str]` (≤3, ≤20 words) | LLM |

**`RecentMatch`**: `result` (W/D/L), `goals_for`, `goals_against`, `opponent`, `home_or_away`, `date` (YYYY-MM-DD).

**`ExpertGameReport`**: `expert_analysis: list[str]` (3–6 bullets, ≤20 words each) — LLM.

**DB (`game_reports`, `team_reports`, `expert_game_reports`)**: schema in `db/schema.sql` + `deployment/db/init/001_create_schema.sql` matches the Pydantic shape. Bullet columns are `JSONB`. `last_5_games` is `JSONB`. Live DB still on old schema — migration runs in 8E.

## 2. 8B Status — Ready to Commit

Restructured so Python builds the structured fields directly from tool outputs; the LLM is only asked for the bullet lists + `weather_cancellation_risk`. Pydantic public models unchanged; added two LLM-only submodels (`GameReportBullets`, `TeamReportBullets`) used only for the `.with_structured_output()` call.

Files modified (all uncommitted):
- `structured_outputs.py` — added `GameReportBullets`, `TeamReportBullets`.
- `agents/game_intelligence.py` — Python builds `H2HAggregate` + venue; LLM called with `GameReportBullets`.
- `agents/team_intelligence.py` — Python builds `recovery_days`, `form_streak`, `last_5_games`, league integers; LLM called with `TeamReportBullets`.
- `prompts.py` — `GAME_INTELLIGENCE_AGENT_PROMPT` and `TEAM_INTELLIGENCE_AGENT_PROMPT` rewritten to describe only bullet output + cancellation-risk enum.
- `db_utils.py`, `db/schema.sql`, `deployment/db/init/001_create_schema.sql` — unchanged since original 8B commit-candidate (correct).

## 3. H2H Root Cause

Confirmed: `fetch_h2h` is the only per-game caller of football-data.org. Every other tool in the per-game subgraph uses FotMob. LangGraph `Send()` fans out 7 games in parallel on a thread pool (`ContextThreadPoolExecutor`).

Per-game call volume today: up to 8 competition-scan calls (to find the match ID — football-data.org has no "find by teams" query) + 1 H2H call = up to 9. 7 games × 9 = up to 63 requests fired in the same second. Free-tier limit: 10 req/min. The competition scan has a retry-once pattern; the final H2H call has no retry.

`SelectedGame.league` is already known from the picker, but `fetch_h2h` ignores it and scans all competitions.

## 4. 8C Scope — Rate-Limited `fetch_h2h`

Thread pool is the concurrency model (LangGraph sync `invoke` path), so `threading.Lock` / `threading.Semaphore` — not asyncio primitives.

Changes:
1. **League hint.** Add `league: str | None` to `fetch_h2h` signature. Thread `game["league"]` through `Send()` payload → `AnalyzeGameState` → `run_game_intelligence` → `fetch_h2h`. When present, scan only that one competition.
2. **Per-run competition cache.** Module-level `dict[str, list[match]]` keyed by competition code, guarded by `threading.Lock`. Cleared at the start of each pre-gambling run via `reset_h2h_run_cache()` called from `graph_manager.run_pre_gambling_flow`.
3. **Token-bucket rate limiter.** Module-level, thread-safe. Default 8 tokens/minute (safety margin below the 10/min free-tier cap). All HTTP calls in `fetch_h2h` acquire one token before firing.
4. **Exponential backoff with jitter on 429.** `sleep = base * 2**attempt + uniform(0,1)`, capped at 32s, max 5 retries. Applied to both competition-scan and final H2H call.
5. **Timeout bump.** `TIMEOUT` 10s → 30s (matches free-tier latency of 12–15s normal, worse under load).
6. **Graceful degradation.** On retry-exhaustion, return `{"error": "Rate limit exceeded after N retries"}` — existing `error`-dict contract preserved. No crashes.
7. **Env vars for all thresholds.** `FDORG_MAX_REQ_PER_MIN`, `FDORG_BACKOFF_BASE_S`, `FDORG_BACKOFF_MAX_S`, `FDORG_MAX_RETRIES`, `FDORG_H2H_TIMEOUT_S`.

Resulting call volume for a typical 7-game run (4 PL + 2 SA + 1 CL): 3 unique competition fetches + 7 H2H = **10 calls**, spread by the limiter across ~75 seconds. Under the free-tier cap.

No new dependencies.

## 5. 8D Scope — Reduced

After 8B + 8C land, 8D is confirmation-only: run a real pre-gambling day, verify `h2h` populates when source data exists and is `None` otherwise. Skip if everything behaves correctly.

## 6. 8E Scope — Renderer + DB Migration

**File ownership:**
- Exclusive owner: `reports/html_report.py`, `pre_gambling_flow/nodes/combine_reports.py`, `gambling_flow/ai_betting_agent.py`.
- Read-only: `reports/telegram_message.py` (only reads `games.venue`, unchanged), `structured_outputs.py`, `db_utils.py`, `prompts.py`.

**Live DB migration** — apply ONLY with Omer's explicit OK, after pg_dump backup:

```sql
BEGIN;

-- game_reports: drop two TEXT cols, add new structured cols
ALTER TABLE game_reports
    DROP COLUMN IF EXISTS h2h_insights,
    DROP COLUMN IF EXISTS weather_risk,
    ADD COLUMN IF NOT EXISTS h2h_home_team TEXT,
    ADD COLUMN IF NOT EXISTS h2h_away_team TEXT,
    ADD COLUMN IF NOT EXISTS h2h_home_team_wins INTEGER,
    ADD COLUMN IF NOT EXISTS h2h_away_team_wins INTEGER,
    ADD COLUMN IF NOT EXISTS h2h_draws INTEGER,
    ADD COLUMN IF NOT EXISTS h2h_total_meetings INTEGER,
    ADD COLUMN IF NOT EXISTS h2h_bullets JSONB,
    ADD COLUMN IF NOT EXISTS weather_bullets JSONB,
    ADD COLUMN IF NOT EXISTS weather_cancellation_risk TEXT;

-- team_reports: drop four TEXT cols, add new structured cols
ALTER TABLE team_reports
    DROP COLUMN IF EXISTS form_trend,
    DROP COLUMN IF EXISTS injury_impact,
    DROP COLUMN IF EXISTS league_position,
    DROP COLUMN IF EXISTS team_news,
    ADD COLUMN IF NOT EXISTS form_streak VARCHAR(5),
    ADD COLUMN IF NOT EXISTS last_5_games JSONB,
    ADD COLUMN IF NOT EXISTS form_bullets JSONB,
    ADD COLUMN IF NOT EXISTS league_rank INTEGER,
    ADD COLUMN IF NOT EXISTS league_points INTEGER,
    ADD COLUMN IF NOT EXISTS league_matches_played INTEGER,
    ADD COLUMN IF NOT EXISTS league_bullets JSONB,
    ADD COLUMN IF NOT EXISTS injury_bullets JSONB,
    ADD COLUMN IF NOT EXISTS news_bullets JSONB;

-- expert_game_reports: TEXT → JSONB, wrap existing prose as single-element array
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'expert_game_reports'
          AND column_name = 'expert_analysis'
          AND data_type = 'text'
    ) THEN
        ALTER TABLE expert_game_reports
            ALTER COLUMN expert_analysis
            TYPE JSONB
            USING to_jsonb(ARRAY[expert_analysis]);
    END IF;
END;
$$;

COMMIT;
```

Zero rows deleted. Existing prose like `"Arsenal will press high..."` becomes `["Arsenal will press high..."]` — one-element JSON array. The new renderer displays it as a single bullet. The whole migration is re-runnable.

**Renderer note for EL/ECL games:** when `games.league` is EL or ECL, display `"H2H not tracked for this competition"` instead of the generic unavailable message. See issue #60.

## 7. Open Items

- **[#60](https://github.com/Omer-Pinto/SoccerSmartBet/issues/60)** — EL/ECL H2H source gap. No current source provides H2H for Europa League or Conference League. Not blocking; renderer will show a clear message. Research follow-up when priority allows.
