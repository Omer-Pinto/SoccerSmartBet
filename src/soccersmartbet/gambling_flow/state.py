"""
Gambling Flow State Definition

State schema for the Gambling Flow graph that runs after the user places bets
via Telegram. Tracks user bets, AI bets, and verification results.
"""

from __future__ import annotations

from typing import TypedDict


class BetSelection(TypedDict, total=False):
    """A single bet placed by either the user or the AI."""

    game_id: int
    prediction: str  # "1", "x", or "2"
    odds: float
    stake: float
    justification: str  # AI only — brief reasoning for the bet


class GamblingState(TypedDict):
    """Main state schema for the Gambling Flow graph.

    Fields:
        game_ids: DB primary keys for the games being bet on.
        user_bets: Bets placed by the user via Telegram.
        ai_bets: Bets placed by the AI betting agent.
        verification_result: "accepted" or "rejected" after validation.
        rejection_reason: Explanation when verification_result is "rejected".
    """

    game_ids: list[int]
    user_bets: list[BetSelection]
    ai_bets: list[BetSelection]
    verification_result: str
    rejection_reason: str
