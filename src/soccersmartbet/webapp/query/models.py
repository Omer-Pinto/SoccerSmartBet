"""Pydantic models for the Query DSL engine.

``BetRow`` mirrors one row of the JOIN between ``bets`` and ``games``.
``FilterAggregates`` holds computed summary stats.
``FilterResult`` is the final envelope returned by ``run_filter()``.
"""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class BetRow(BaseModel):
    """One row returned by the History/P&L query.

    Column names mirror the SELECT in ``compiler.py`` exactly; no derived
    fields are added here so the model stays a pure mirror of the DB shape.
    """

    model_config = ConfigDict(frozen=True)

    # --- bets columns ---
    bet_id: int
    bettor: str
    prediction: str
    stake: Decimal
    odds: Decimal
    result: str | None
    pnl: Decimal | None

    # --- games columns ---
    game_id: int
    home_team: str
    away_team: str
    kickoff_time: datetime
    league: str
    outcome: str | None
    home_score: int | None
    away_score: int | None

    # placed_at may be absent on older rows (column added later)
    placed_at: datetime | None = None


class FilterAggregates(BaseModel):
    """Summary stats computed in Python from the result rows.

    Args:
        count: Number of rows in the result set.
        total_stake: Sum of all stakes.
        total_pnl: Sum of all realised P&L (only settled bets contribute a
            non-null pnl; unsettled bets are treated as 0 here).
        win_rate: Fraction of settled bets that were wins.  ``None`` when
            there are no settled bets (would be division by zero).
    """

    model_config = ConfigDict(frozen=True)

    count: int
    total_stake: Decimal
    total_pnl: Decimal
    win_rate: float | None


class FilterResult(BaseModel):
    """Top-level envelope returned by ``run_filter()``.

    Args:
        rows: Ordered list of matching bet+game rows.
        aggregates: Pre-computed summary statistics.
        row_cap_hit: ``True`` when ``len(rows) == row_cap``, meaning there may
            be more rows in the DB that were truncated.
        dsl: The raw DSL string that produced this result (echo-back for
            debugging and frontend display).
    """

    model_config = ConfigDict(frozen=True)

    rows: list[BetRow]
    aggregates: FilterAggregates
    row_cap_hit: bool
    dsl: str
