"""
Structured Outputs for Pre-Gambling Flow LLM Agents.

This module defines Pydantic schemas for AI-generated outputs from the
Pre-Gambling Flow's intelligent agents. Only LLM-generated outputs are modeled here;
Python code outputs (odds filtering, DB queries) do not require Pydantic schemas.

Following StocksMarketRecommender pattern: each agent node that produces structured
output has a corresponding BaseModel that enforces type safety and validation at
LLM response parsing time.

Reference Architecture:
- StocksMarketRecommender/structured_outputs.py (AnalysisOutput, InvestmentDecision)
- LangGraphWrappers ModelWrapper.structured_output parameter

Data Source Context:
- Only fields with enabled data sources (see docs/research/data_sources/executive_summary.md)
- Some DB schema fields will remain NULL - this is acceptable
- Focus is on actionable betting insights, not exhaustive data collection
"""

from pydantic import BaseModel, Field


# ============================================================================
# Smart Game Picker LLM Output
# ============================================================================


class SelectedGame(BaseModel):
    """
    A single game selected by the Smart Game Picker agent.

    The agent analyzes today's fixtures and selects games with high betting interest
    based on rivalry intensity, championship stakes, derby significance, or tactical
    intrigue - NOT just favorable odds.
    """

    home_team: str = Field(
        description="Home team name as it appears in fixtures API"
    )
    away_team: str = Field(
        description="Away team name as it appears in fixtures API"
    )
    match_date: str = Field(
        description="Match date in YYYY-MM-DD format"
    )
    kickoff_time: str = Field(
        description="Kickoff time in HH:MM format (24-hour)"
    )
    league: str = Field(
        description="League/competition name (e.g., 'Premier League', 'La Liga')"
    )
    venue: str | None = Field(
        default=None,
        description="Stadium name if available from fixtures API; None if not provided"
    )
    justification: str = Field(
        description=(
            "AI reasoning for why this game is interesting for betting analysis. "
            "Should explain rivalry context, derby significance, championship stakes, "
            "relegation battles, or tactical intrigue - NOT just 'good odds' or basic stats."
        )
    )


class SelectedGames(BaseModel):
    """
    Complete output from Smart Game Picker agent for today's betting slate.

    The system requires minimum 3 games per day to ensure diverse betting opportunities.
    The LLM must provide strategic reasoning for the overall selection, not just
    individual game justifications.
    """

    games: list[SelectedGame] = Field(
        min_length=3,
        description=(
            "List of selected games for today's betting analysis. "
            "Minimum 3 games required per system constraints."
        )
    )
    selection_reasoning: str = Field(
        description=(
            "Overall selection strategy explaining how today's picks form a cohesive "
            "betting slate. Should address diversity (leagues, match types), risk "
            "balance, and any patterns across the selections."
        )
    )


# ============================================================================
# Game Intelligence Agent LLM Output
# ============================================================================


class GameReport(BaseModel):
    """
    AI-generated game analysis from Game Intelligence Agent.

    This agent analyzes game-level factors: head-to-head history patterns,
    weather impact on play style and draw probability, and venue-specific
    advantages. Data comes from enabled sources only (see research docs).

    Fields NOT included (disabled data sources):
    - atmosphere_summary (crowd/atmosphere data not enabled)
    - venue_factors (advanced venue analytics not in scope for enabled sources)
    """

    h2h_insights: str = Field(
        description=(
            "AI-extracted patterns from head-to-head history between these teams. "
            "Should identify: home dominance trends, scoring pattern evolution, "
            "defensive stability shifts, recent form trajectory in matchups. "
            "NOT a simple stats dump - extract betting-relevant patterns."
        )
    )
    weather_risk: str = Field(
        description=(
            "Assessment of weather impact on game dynamics and outcome probabilities. "
            "Must address: (1) Cancellation/postponement risk, (2) Draw probability "
            "increase in adverse conditions, (3) Style-of-play changes (e.g., "
            "'Heavy rain favors defensive teams, reduces high-scoring probability'). "
            "Use weather API data from enabled sources."
        )
    )
    venue: str = Field(
        description=(
            "Stadium name extracted from fixtures API. "
            "Simple string field - no complex venue analytics (not in enabled sources)."
        )
    )


# ============================================================================
# Team Intelligence Agent LLM Output
# ============================================================================


class TeamReport(BaseModel):
    """
    AI-generated team analysis from Team Intelligence Agent.

    This agent analyzes team-level factors for betting assessment: recent form
    trajectory, injury impact on lineup strength, key players' contribution rates,
    and recovery status. Critically, the LLM must infer starter vs. bench status
    for injured players since apifootball.com only provides basic stats.

    Fields NOT included (disabled data sources):
    - rotation_risk (squad rotation data not reliably available)
    - morale_stability (qualitative morale/coach stability not in enabled sources)
    - relevant_news (structured news aggregation not enabled)

    Data Source Constraints (apifootball.com):
    - injury_impact: player_injured, player_match_played, player_goals, player_type available
    - key_players_status: Only total goals/assists/games (no recent form window)
    - form_trend: Last 5 games results available for trend calculation
    """

    recovery_days: int = Field(
        ge=0,
        description=(
            "Days elapsed since team's last competitive match. "
            "Calculated from apifootball.com match history. "
            "Critical for fatigue assessment: <3 days = high fatigue risk, "
            "3-5 days = normal, >7 days = extra rest/rhythm concerns."
        )
    )
    form_trend: str = Field(
        description=(
            "AI-computed trajectory from last 5 games: 'improving', 'declining', or 'stable'. "
            "Must include reasoning based on pattern analysis (e.g., 'Improving: 3 wins "
            "in last 4 after early slump, defensive solidity returning'). "
            "NOT just win/loss record - extract momentum and quality of performances."
        )
    )
    injury_impact: str = Field(
        description=(
            "AI assessment of injury list impact on expected lineup strength. "
            "CRITICAL: Must determine if injured players are starters vs. bench warmers "
            "using player_match_played, player_goals, and player_type (position) fields. "
            "Example: 'Critical - starting striker with 0.8 goals/game out' vs. "
            "'Minor - backup defender with 3 appearances missing'. "
            "User doesn't know all teams (e.g., Napoli) - LLM must identify key contributors."
        )
    )
    key_players_status: str = Field(
        description=(
            "Top performers' current contribution status inferred from cumulative stats. "
            "apifootball.com provides total goals/assists/games only (no recent form window). "
            "LLM must infer form from ratios and availability: 'Top scorer (12 goals/20 games) "
            "available and healthy' vs. 'Playmaker (8 assists/18 games) returning from suspension'. "
            "Focus on players with highest goals/assists per game ratios."
        )
    )
