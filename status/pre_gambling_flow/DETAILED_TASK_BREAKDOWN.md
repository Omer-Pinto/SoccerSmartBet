# Batch 4 - Detailed Task Breakdown

> **Purpose:** Capture architectural decisions from human-AI co-design for droid implementation  
> **Instructions for droids:** Follow these specifications unless you have good technical reasons to diverge (document deviations in PR)

**Context:** See `docs/research/data_sources/executive_summary.md` for enabled vs disabled data sources. Only implement fields with enabled sources.

---

## Task 1.3: State Definition

**File:** `src/pre_gambling_flow/state.py`  
**Reference:** `external_projects/StocksMarketRecommender.md` (state.py pattern)

### Requirements

#### 1. Phase Enum
```python
class Phase(Enum):
    SELECTING = "selecting"    # Smart Picker choosing interesting games
    FILTERING = "filtering"    # Fetching odds from The Odds API + applying threshold
    ANALYZING = "analyzing"    # Parallel subgraphs running (Game + Team Intelligence Agents)
    COMPLETE = "complete"      # Flow finished, ready to trigger Gambling Flow
```

**Why FILTERING phase:** Happens between game selection and analysis - fetch odds, apply minimum threshold, persist to DB.

#### 2. GameContext TypedDict
Minimal game info stored in state for **debugging without DB calls**.

**Required fields:**
- `game_id`: int - DB PK from `games.game_id` (SERIAL PRIMARY KEY from schema.sql)
- `home_team`: str
- `away_team`: str
- `match_date`: str - Format: YYYY-MM-DD
- `kickoff_time`: str - Format: HH:MM
- `league`: str
- `venue`: str - Stadium name from football-data.org
- `n1`: float - Home win odds (The Odds API)
- `n2`: float - Away win odds
- `n3`: float - Draw odds

**Why these fields:** Allow tracking flow progress without DB queries. Odds included for threshold debugging.

**Why TypedDict not Pydantic:** State fields should be simple typed dicts, not validated models (per LangGraph patterns).

#### 3. PreGamblingState TypedDict
```python
class PreGamblingState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    all_games: Annotated[list[GameContext], add]  # All games inserted to DB
    games_to_analyze: Annotated[list[int], add]  # Filtered game IDs (DB PKs)
    phase: Phase
```

**Field purposes:**
- `messages`: LLM conversation history (required for agent nodes)
- `all_games`: Full context for all games inserted to DB (for debugging, logging)
- `games_to_analyze`: Filtered game IDs (DB PKs) that passed odds threshold → spawn subgraphs for these
- `phase`: Current flow phase for conditional routing

**Critical architectural decision:** Game/team report data is NOT in state. It goes directly to DB from parallel subgraphs. State is for **coordination only**.

---

## Task 2.3: Structured Outputs (LLM Outputs Only)

**File:** `src/pre_gambling_flow/structured_outputs.py`  
**Reference:** `external_projects/StocksMarketRecommender.md` (structured_outputs.py pattern)

### Key Principle
**Only include schemas for LLM-generated outputs.** Python code outputs (like odds filtering, DB queries) don't need Pydantic models.

### Model 1: SelectedGames (Smart Game Picker LLM Output)

**Purpose:** LLM selects interesting games based on rivalry, derby status, playoff stakes.

```python
class SelectedGame(BaseModel):
    home_team: str
    away_team: str
    match_date: str  # YYYY-MM-DD
    kickoff_time: str  # HH:MM
    league: str
    venue: str | None = None  # Stadium name (optional if not in fixture data)
    justification: str  # Why this game is interesting (rivalry, derby, stakes)

class SelectedGames(BaseModel):
    games: list[SelectedGame] = Field(min_length=3, description="Minimum 3 games selected")
    selection_reasoning: str  # Overall selection strategy for today
```

**Validation notes:**
- `min_length=3`: System requires minimum 3 games per day
- `justification`: Should explain rivalry/importance/context, NOT just odds

### Model 2: GameReport (Game Intelligence Agent LLM Output)

**Purpose:** LLM analyzes H2H patterns and weather impact.

```python
class GameReport(BaseModel):
    h2h_insights: str = Field(description="AI-extracted patterns from H2H history (home dominance, scoring trends, defensive patterns)")
    weather_risk: str = Field(description="Cancellation risk assessment + draw probability impact based on conditions")
    venue: str = Field(description="Stadium name from fixtures API")
```

### Model 3: TeamReport (Team Intelligence Agent LLM Output)

**Purpose:** LLM analyzes team form, injuries, key players.

```python
class TeamReport(BaseModel):
    recovery_days: int = Field(ge=0, description="Days since team's last match (calculated from apifootball.com data)")
    form_trend: str = Field(description="AI-computed trajectory: 'improving', 'declining', or 'stable' with reasoning from last 5 games")
    injury_impact: str = Field(description="AI assessment: 'critical starters missing' vs 'minor depth issues' - MUST identify if injured players are starters using match_played/goals data")
    key_players_status: str = Field(description="Top performers' form inferred from goals/assists/games ratios (apifootball.com provides basic stats only)")
```

**Critical requirement for `injury_impact`:**
- apifootball.com provides: `player_injured`, `player_match_played`, `player_goals`, `player_type` (position)
- LLM MUST determine if injured players are starters vs bench warmers using `player_match_played`, `player_goals`, `player_type` fields
- User doesn't know all teams (e.g., Napoli) - LLM must identify if missing players are key contributors

**Note for `key_players_status`:** apifootball.com only has total goals/assists/games, not recent form. LLM infers from ratios.

---

## Task 2.4: Prompts Repository

**File:** `src/pre_gambling_flow/prompts.py`  
**Reference:** `external_projects/StocksMarketRecommender.md` (prompts.py pattern)

### Prompt 1: SMART_GAME_PICKER_PROMPT

**Agent role:** Analyze today's fixtures and select interesting games for betting.

**Selection criteria:**
- Rivalry (historical significance, fan passion)
- Derby status (local derbies, national importance)
- Playoff implications (title race, relegation battle, European qualification)
- League prestige (Champions League > Premier League > Championship)
- **NOT simple odds threshold** - that's done by separate filtering node

**Output:** SelectedGames structured model with justifications

**Emphasis:**
- Sophisticated analysis of context, not just fixture data
- Explain WHY each game is interesting
- Consider betting value (meaningful stakes, unpredictable outcomes)

**Available data:**
- Fixtures from football-data.org (teams, date, time, league, venue)
- 12 major competitions (Premier League, La Liga, Bundesliga, Serie A, Ligue 1, Champions League, etc.)

### Prompt 2: GAME_INTELLIGENCE_AGENT_PROMPT

**Agent role:** Analyze game-level factors (H2H patterns, weather impact).

**Tools available:**
- `fetch_h2h()`: Recent head-to-head results from football-data.org + apifootball.com
- `fetch_weather()`: Weather forecast from Open-Meteo (needs venue coordinates)

**Analysis required:**
1. **H2H Pattern Extraction:**
   - Identify home dominance, high-scoring trends, defensive patterns
   - Look for consistent results (e.g., "home team always wins", "always draws")
   - Extract betting-relevant patterns

2. **Weather Impact Analysis:**
   - Cancellation risk (heavy rain, snow, extreme wind)
   - Draw probability impact (bad weather favors draws)
   - Use venue coordinates lookup for Open-Meteo API

**Output:** GameReport with h2h_insights, weather_risk, venue

**Emphasis:**
- AI synthesis, not raw stats dumping
- Extract PATTERNS from H2H, not just list results
- Weather analysis should assess betting impact (cancellation = refund, bad weather = higher draw odds)

**LLM calls:** 2-3 calls expected (orchestration, analysis, synthesis)

### Prompt 3: TEAM_INTELLIGENCE_AGENT_PROMPT

**Agent role:** Analyze team-level factors (form, injuries, key players).

**Tools available:**
- `calculate_recovery_time()`: Days since last match (Python utility)
- `fetch_form()`: Last 5 matches from apifootball.com (W/D/L, scores)
- `fetch_injuries()`: Injured players from apifootball.com (player_injured field)
- `fetch_suspensions()`: Suspended players (if available via apifootball.com)
- `fetch_key_players_form()`: Top players' stats (goals/assists/games from apifootball.com)

**Analysis required:**
1. **Form Trend Analysis:**
   - Compute improving/declining trajectory from last 5 games
   - NOT just W/D/L count - look at score patterns, opponent strength
   - Output: "improving", "declining", "stable" + reasoning

2. **Injury Impact Assessment (CRITICAL):**
   - Flag whether injured players are starters vs bench warmers
   - Use `player_match_played`, `player_goals`, `player_type` to determine importance
   - For teams user doesn't know (e.g., Napoli), LLM MUST identify if missing players are key contributors
   - Output: "critical starters missing" vs "minor depth issues"

3. **Key Players Status:**
   - Assess top performers' form from goals/assists/games ratios
   - apifootball.com only has TOTAL stats, not recent form
   - Infer productivity from ratios (e.g., 10 goals in 15 games = productive)

**Output:** TeamReport with recovery_days, form_trend, injury_impact, key_players_status

**Emphasis:**
- AI synthesis, not raw stats
- Injury impact MUST assess starter importance (critical requirement)
- Form trend should explain trajectory, not just state W/D/L
- Key players analysis limited by basic stats (acknowledge limitation)

**LLM calls:** 3-5 calls expected (orchestration, form+injury analysis, synthesis)

---

## Droid Autonomy Guidelines

**Follow these specs unless you have good technical reasons to diverge.**

**Areas where droid has full autonomy:**
- Exact Field description text and wording
- Additional validation rules (regex, min/max values) beyond what's specified
- Docstring examples and formatting
- Error messages and edge case handling
- Import statements and code organization
- Prompt phrasing, tone, structure, examples (as long as goals are met)

**Areas where droid should NOT diverge:**
- Which fields are included/excluded (based on enabled data sources)
- Phase enum values (SELECTING, FILTERING, ANALYZING, COMPLETE)
- State field names and purposes (messages, all_games, games_to_analyze, phase)
- DB PK usage for game_id (not external API IDs)

**If you diverge:**
- Document reason in PR description
- Explain why the change improves on the spec
- Ensure it doesn't break dependencies (e.g., don't rename state fields that other nodes expect)

---

## References

- **Data sources:** `docs/research/data_sources/executive_summary.md`
- **DB schema:** `db/schema.sql`
- **State pattern:** `external_projects/StocksMarketRecommender.md`
- **Config:** `config/config.yaml`
