"""
Bet Verifier node for the Gambling Flow.

Validates both user and AI bets, then persists all valid bets to the
bets table with ON CONFLICT UPDATE.
"""

from __future__ import annotations

import logging

from soccersmartbet.db import get_cursor
from soccersmartbet.gambling_flow.state import BetSelection, GamblingState

logger = logging.getLogger(__name__)

_VALID_PREDICTIONS = {"1", "x", "2"}

_UPSERT_BET_SQL = """
INSERT INTO bets (game_id, bettor, prediction, odds, stake, justification)
VALUES (%(game_id)s, %(bettor)s, %(prediction)s, %(odds)s, %(stake)s, %(justification)s)
ON CONFLICT (game_id, bettor)
DO UPDATE SET
    prediction = EXCLUDED.prediction,
    odds = EXCLUDED.odds,
    stake = EXCLUDED.stake,
    justification = EXCLUDED.justification
"""


def _validate_bets(bets: list[BetSelection], label: str) -> str | None:
    """Validate a list of bet selections.

    Args:
        bets: The bet selections to validate.
        label: Human-readable label for error messages ("user" or "ai").

    Returns:
        Error message string if invalid, None if all valid.
    """
    for bet in bets:
        prediction = bet.get("prediction", "").lower()
        if prediction not in _VALID_PREDICTIONS:
            return f"{label} bet on game {bet.get('game_id')}: invalid prediction '{bet.get('prediction')}' (must be 1, x, or 2)"

        stake = bet.get("stake", 0)
        if not isinstance(stake, (int, float)) or stake <= 0:
            return f"{label} bet on game {bet.get('game_id')}: stake must be positive, got {stake}"

        odds = bet.get("odds", 0)
        if not isinstance(odds, (int, float)) or odds <= 1.0:
            return f"{label} bet on game {bet.get('game_id')}: odds must be > 1.0, got {odds}"

    return None


def verify_and_persist_bets(state: GamblingState) -> dict:
    """LangGraph node: validate user and AI bets, then persist to DB.

    Checks that all predictions are valid (1/x/2) and stakes are positive.
    If valid, upserts all bets into the bets table. Does NOT check balance.

    Args:
        state: Current Gambling Flow state with user_bets and ai_bets.

    Returns:
        State update dict with verification_result and rejection_reason.
    """
    user_bets: list[BetSelection] = state.get("user_bets", [])
    ai_bets: list[dict] = state.get("ai_bets", [])

    logger.info(
        "verify_and_persist_bets: validating %d user bet(s) and %d AI bet(s)",
        len(user_bets),
        len(ai_bets),
    )

    # Validate user bets
    user_error = _validate_bets(user_bets, "User")
    if user_error:
        logger.info("verify_and_persist_bets: rejected — %s", user_error)
        return {
            "verification_result": "rejected",
            "rejection_reason": user_error,
        }

    # Validate AI bets
    ai_error = _validate_bets(ai_bets, "AI")
    if ai_error:
        logger.info("verify_and_persist_bets: rejected — %s", ai_error)
        return {
            "verification_result": "rejected",
            "rejection_reason": ai_error,
        }

    # Persist all bets
    with get_cursor(commit=True) as cur:
        for bet in user_bets:
            cur.execute(_UPSERT_BET_SQL, {
                "game_id": bet["game_id"],
                "bettor": "user",
                "prediction": bet["prediction"].lower(),
                "odds": bet["odds"],
                "stake": bet["stake"],
                "justification": None,
            })

        for bet in ai_bets:
            cur.execute(_UPSERT_BET_SQL, {
                "game_id": bet["game_id"],
                "bettor": "ai",
                "prediction": bet["prediction"].lower(),
                "odds": bet["odds"],
                "stake": bet["stake"],
                "justification": bet.get("justification"),
            })

    logger.info(
        "verify_and_persist_bets: accepted and persisted %d total bet(s)",
        len(user_bets) + len(ai_bets),
    )

    return {
        "verification_result": "accepted",
        "rejection_reason": "",
    }
