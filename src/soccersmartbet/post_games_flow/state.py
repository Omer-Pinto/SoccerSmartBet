"""
Post-Games Flow State Definition

State schema for the post-games pipeline that runs after fixtures finish.
Tracks game IDs to process, fetched results, and per-game P&L breakdown.
"""

from __future__ import annotations

from typing import TypedDict


class PostGamesState(TypedDict):
    """Main state schema for the Post-Games Flow graph.

    Fields:
        game_ids: DB primary keys for the games that have finished.
        results: Keyed by game_id. Each value holds home_score, away_score,
            and outcome ("1"/"x"/"2").
        pnl_summary: Keyed by game_id. Each value holds user_pnl and ai_pnl
            floats representing net profit/loss for that game.
    """

    game_ids: list[int]
    results: dict  # {game_id: {"home_score": int, "away_score": int, "outcome": str}}
    pnl_summary: dict  # {game_id: {"user_pnl": float, "ai_pnl": float}}
