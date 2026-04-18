"""
Structured Outputs for Pre-Gambling Flow LLM Agents.

This module defines Pydantic schemas for AI-generated outputs from the
Pre-Gambling Flow's intelligent agents. Only LLM-generated outputs are modeled here;
Python code outputs (odds filtering, DB queries) do not require Pydantic schemas.

Schema v2 — Wave 8B (branch ``major_report_refactor``). Reports now carry
structured facts (aggregates, typed streaks, per-match rows) with short
analytical bullets alongside them, replacing the previous long-form prose
fields. Soft length caps are enforced via prompts, not Pydantic validators,
so the LLM is trusted to self-regulate without rejecting edge-case outputs.

Reference Architecture:
- StocksMarketRecommender/structured_outputs.py (AnalysisOutput, InvestmentDecision)
- LangGraphWrappers ModelWrapper.structured_output parameter

Data Source Context:
- Only fields with enabled data sources (see docs/research/data_sources/executive_summary.md)
- Some DB schema fields will remain NULL - this is acceptable
- Focus is on actionable betting insights, not exhaustive data collection
"""

from typing import Literal

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
        min_length=1,
        description=(
            "List of selected games for today's betting analysis. "
            "Select all eligible games worth analyzing."
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


class H2HAggregate(BaseModel):
    """Aggregate head-to-head record between two teams across their meeting history.

    Aggregate only — do NOT include the historical match list. Past meetings'
    home/away roles may not match today's fixture, so only the total wins
    keyed by team identity are reliable.
    """

    home_team: str = Field(description="Team playing at home TODAY.")
    away_team: str = Field(description="Team playing away TODAY.")
    home_team_wins: int = Field(
        ge=0,
        description=(
            "Total all-time wins for the home team across all meetings, "
            "regardless of venue."
        ),
    )
    away_team_wins: int = Field(
        ge=0,
        description=(
            "Total all-time wins for the away team across all meetings, "
            "regardless of venue."
        ),
    )
    draws: int = Field(ge=0, description="Total draws across all meetings.")
    total_meetings: int = Field(
        ge=0, description="Total meetings counted (sum of wins + draws)."
    )


class GameReport(BaseModel):
    """AI-generated game-level analysis from the Game Intelligence Agent.

    Covers venue, weather and an aggregate H2H record — no per-match history.
    Short analytical bullets sit alongside the structured facts so downstream
    consumers can render either the data or the analysis, or both.
    """

    h2h: H2HAggregate | None = Field(
        default=None,
        description=(
            "Aggregate W/D/L between the two teams. Null when source "
            "data unavailable."
        ),
    )
    h2h_bullets: list[str] = Field(
        default_factory=list,
        description=(
            "Optional short analytical bullets on the aggregate. "
            "Cap: 2 bullets, <=20 words each. Empty list if no observation "
            "warranted. NEVER invent data."
        ),
    )
    weather_bullets: list[str] = Field(
        default_factory=list,
        description=(
            "Bullets covering cancellation risk, draw-probability impact, "
            "and style-of-play impact. Cap: 3 bullets, <=20 words each."
        ),
    )
    weather_cancellation_risk: Literal["low", "medium", "high", "unknown"] = Field(
        description=(
            "Cancellation/postponement risk classification from weather data."
        ),
    )
    venue: str | None = Field(
        default=None,
        description="Short stadium name as provided by FotMob. Null if unavailable.",
    )


# ============================================================================
# Team Intelligence Agent LLM Output
# ============================================================================


class RecentMatch(BaseModel):
    """One of the team's last 5 matches."""

    result: Literal["W", "D", "L"]
    goals_for: int = Field(ge=0)
    goals_against: int = Field(ge=0)
    opponent: str
    home_or_away: Literal["home", "away"]
    date: str = Field(description="YYYY-MM-DD")


class TeamReport(BaseModel):
    """AI-generated team-level analysis from the Team Intelligence Agent.

    Stores raw structured facts (recovery days, form streak, last-5 rows,
    league table snapshot) plus short analytical bullets on form, league
    context, injuries and pre-match news.
    """

    recovery_days: int = Field(
        ge=0, description="Days since last competitive match."
    )
    form_streak: str = Field(
        description=(
            "5-character streak, most recent LAST (e.g. 'LDDWW' means 5 games "
            "ago was L, most recent was W). Use exactly 5 chars when 5 games "
            "are available; pad with '?' if fewer."
        ),
    )
    last_5_games: list[RecentMatch] = Field(
        default_factory=list,
        description=(
            "Raw list of the last 5 matches, most recent FIRST. Up to 5 entries."
        ),
    )
    form_bullets: list[str] = Field(
        default_factory=list,
        description=(
            "Short analytical observations. Cap: 2 bullets, <=12 words each."
        ),
    )
    league_rank: int | None = Field(
        default=None,
        description="Current league position. Null if unavailable.",
    )
    league_points: int | None = Field(default=None)
    league_matches_played: int | None = Field(default=None)
    league_bullets: list[str] = Field(
        default_factory=list,
        description=(
            "Motivation/context bullets (title race, relegation, dead rubber, "
            "etc.). Cap: 3 bullets, <=20 words each."
        ),
    )
    injury_bullets: list[str] = Field(
        default_factory=list,
        description=(
            "One bullet per impactful injured/unavailable player. Format: "
            "'Name (position) - injury_type, return.' Importance judgement "
            "baked in. Cap: 5 bullets."
        ),
    )
    news_bullets: list[str] = Field(
        default_factory=list,
        description=(
            "Pre-match intel synthesized from team news. Cap: 3 bullets, "
            "<=20 words each."
        ),
    )


# ============================================================================
# LLM-only submodels for intelligence agents
# ============================================================================
#
# These submodels describe *only* the synthesis fields the LLM is asked to
# produce. Python already owns the structured fields (aggregate counts,
# integer league snapshot, raw last-5 rows, etc.) and merges the LLM's
# bullet output with those structured fields to form the final
# ``GameReport`` / ``TeamReport`` objects persisted to the DB.
#
# Do NOT use these as the DB contract; the DB writers still accept the
# public ``GameReport`` / ``TeamReport`` models defined above.


class GameReportBullets(BaseModel):
    """LLM output for game-intelligence synthesis fields only.

    Python merges this with structured fields (aggregate H2H, venue name)
    built from raw tool output to form the final ``GameReport``.
    """

    h2h_bullets: list[str] = Field(
        default_factory=list,
        description=(
            "<=2 bullets, <=20 words each. Empty list if no observation "
            "is warranted. NEVER invent data."
        ),
    )
    weather_bullets: list[str] = Field(
        default_factory=list,
        description=(
            "<=3 bullets, <=20 words each. Covers cancellation risk, "
            "draw-probability impact, and style-of-play impact."
        ),
    )
    weather_cancellation_risk: Literal["low", "medium", "high", "unknown"] = Field(
        description="Classification derived from weather data.",
    )


class TeamReportBullets(BaseModel):
    """LLM output for team-intelligence synthesis fields only.

    Python merges this with structured fields (recovery_days, form_streak,
    last_5_games, league rank/points/played) to form the final
    ``TeamReport``.
    """

    form_bullets: list[str] = Field(
        default_factory=list,
        description="<=2 bullets, <=12 words each.",
    )
    league_bullets: list[str] = Field(
        default_factory=list,
        description=(
            "<=3 bullets, <=20 words each. Motivation/context only "
            "(title race, relegation, dead rubber, etc.)."
        ),
    )
    injury_bullets: list[str] = Field(
        default_factory=list,
        description=(
            "<=5 bullets. ONE per impactful injured/unavailable player. "
            "Format: 'Name (POS) - injury_type, return.'"
        ),
    )
    news_bullets: list[str] = Field(
        default_factory=list,
        description="<=3 bullets, <=20 words each.",
    )


# ============================================================================
# Expert Game Report LLM Output
# ============================================================================


class ExpertGameReport(BaseModel):
    """Expert LLM pre-match analysis synthesizing game + team reports with odds.

    Produced by the Expert Report Agent after combine_reports has assembled
    all available intelligence. The expert produces cohesive analytical
    bullets — no verdicts, no score predictions, no prose column.
    """

    expert_analysis: list[str] = Field(
        default_factory=list,
        description=(
            "Cohesive pre-match analysis as 3-6 substantive bullets, "
            "<=20 words each. No opening flourishes. No betting verdict. "
            "Analysis only."
        ),
    )
