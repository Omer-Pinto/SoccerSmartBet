"""
Post-Games Flow State Definition

State schema for the post-games pipeline that runs after fixtures finish.
Tracks game IDs to process, fetched results, and per-game P&L breakdown.
"""

from __future__ import annotations

from typing import TypedDict


class SkippedGame(TypedDict):
    """A game that was skipped during result fetching.

    Fields:
        game_id: DB primary key.
        home_team: Home team name as stored in the DB.
        away_team: Away team name as stored in the DB.
        match_date: Match date string (YYYY-MM-DD).
        reason: Short human-readable explanation, e.g. "no FotMob fixture match".
    """

    game_id: int
    home_team: str
    away_team: str
    match_date: str
    reason: str


class PostGamesState(TypedDict):
    """Main state schema for the Post-Games Flow graph.

    Fields:
        game_ids: DB primary keys for the games that have finished.
        results: Keyed by game_id. Each value holds home_score, away_score,
            and outcome ("1"/"x"/"2").
        pnl_summary: Keyed by game_id. Each value holds user_pnl and ai_pnl
            floats representing net profit/loss for that game.
        skipped_games: Games that could not be matched to a FotMob fixture and
            therefore have no result. Populated by fetch_results; consumed by
            notify_daily_summary to send a Telegram alert.
    """

    game_ids: list[int]
    results: dict  # {game_id: {"home_score": int, "away_score": int, "outcome": str}}
    pnl_summary: dict  # {game_id: {"user_pnl": float, "ai_pnl": float}}
    skipped_games: list[SkippedGame]
