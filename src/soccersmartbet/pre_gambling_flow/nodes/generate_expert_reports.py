"""Generate Expert Reports node for the Pre-Gambling Flow.

Reads the combined report message from state (produced by combine_reports),
splits it by game, and calls the Expert Report Agent for each game to
produce a professional pre-match analysis column stored in expert_game_reports.
"""

from __future__ import annotations

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

from soccersmartbet.pre_gambling_flow.agents.expert_report import run_expert_report
from soccersmartbet.pre_gambling_flow.state import PreGamblingState

# Matches the header emitted by combine_reports._format_game_block:
#   === {home_team} vs {away_team} ({league}) ===
# Tolerates team names with punctuation, accented characters, and digits
# (e.g. "1. FC Köln", "Gil Vicente FC", "Atlético de Madrid").
_HEADER_RE = re.compile(r"^=== .+? vs .+? \(.+?\) ===\s*$", re.MULTILINE)


def _split_by_game(combined_text: str) -> list[str]:
    """Split combined report text into per-game sections.

    combine_reports emits headers of the form::

        === {home_team} vs {away_team} ({league}) ===

    Each section begins at that header and runs until the next one (or end of
    string).

    Args:
        combined_text: Full combined report text from combine_reports.

    Returns:
        List of per-game text sections, each starting with the game header.
    """
    # Lookahead split keeps each header at the start of its section.
    parts = re.split(r"(?m)(?=^=== .+? vs .+? \(.+?\) ===\s*$)", combined_text)
    # Discard leading whitespace/preamble chunks that have no header.
    return [p.strip() for p in parts if p.strip() and _HEADER_RE.match(p.strip())]


def generate_expert_reports(state: PreGamblingState) -> dict[str, Any]:
    """LangGraph node: generate expert analysis for each analyzed game.

    Reads the combined report message assembled by combine_reports, splits it
    into per-game sections, and calls run_expert_report for each game to
    produce a cohesive professional analysis column written to the DB.

    The game_id for each section is resolved by matching the section position
    against state["games_to_analyze"] — both lists are produced in the same
    order by combine_reports and persist_games.

    Args:
        state: Current Pre-Gambling Flow state. Must contain ``games_to_analyze``
            and at least one AIMessage from combine_reports in ``messages``.

    Returns:
        Empty dict — all output is written to the DB as a side effect.
    """
    game_ids: list[int] = state["games_to_analyze"]
    messages = state.get("messages", [])

    if not game_ids:
        logger.info("generate_expert_reports: no games to process")
        return {}

    # Find the last AIMessage — that is the combined report from combine_reports
    combined_text = ""
    for msg in reversed(messages):
        # AIMessage has .content attribute; check by class name to avoid importing
        if hasattr(msg, "content") and msg.__class__.__name__ == "AIMessage":
            combined_text = msg.content
            break

    if not combined_text:
        logger.info("generate_expert_reports: no combined report found in messages")
        return {}

    game_sections = _split_by_game(combined_text)
    logger.info(
        "generate_expert_reports: found %d game sections for %d game_ids",
        len(game_sections),
        len(game_ids),
    )

    for i, game_id in enumerate(game_ids):
        if i >= len(game_sections):
            logger.info(
                "generate_expert_reports: no section for game_id=%d (index %d), skipping",
                game_id,
                i,
            )
            continue

        section = game_sections[i]
        logger.info("generate_expert_reports: processing game_id=%d", game_id)
        run_expert_report(game_id, section)
        logger.info("generate_expert_reports: done for game_id=%d", game_id)

    return {}
