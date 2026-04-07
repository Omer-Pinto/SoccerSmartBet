"""Expert Report Agent for pre-gambling flow.

This is NOT an agentic tool-calling LLM. It is a Python function that:
1. Receives the combined report text for a single game (already assembled by combine_reports)
2. Makes a single LLM call with structured output → ExpertGameReport
3. Writes the ExpertGameReport to the expert_game_reports table

The LLM acts as a world-class football analyst synthesizing all raw intelligence
into a cohesive pre-match narrative column.
"""

from __future__ import annotations

import logging
import os

logger = logging.getLogger(__name__)

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from soccersmartbet.pre_gambling_flow.agents.db_utils import insert_expert_report
from soccersmartbet.pre_gambling_flow.prompts import EXPERT_REPORT_PROMPT
from soccersmartbet.pre_gambling_flow.structured_outputs import ExpertGameReport

EXPERT_MODEL = os.getenv("EXPERT_MODEL", "gpt-5.4")


def run_expert_report(game_id: int, combined_report_text: str) -> ExpertGameReport:
    """Run the Expert Report Agent for a single game.

    Takes the combined report text already assembled by combine_reports for one
    game, invokes the LLM once with structured output, persists the result to
    the expert_game_reports table, and returns the ExpertGameReport.

    Args:
        game_id: Primary key of the game row in the ``games`` table.
        combined_report_text: The full pre-match intelligence dossier for this
            game as produced by combine_reports (includes odds, H2H, weather,
            venue, and both team reports).

    Returns:
        LLM-generated ExpertGameReport persisted to the database.
    """
    logger.info("run_expert_report: starting for game_id=%d", game_id)

    model = ChatOpenAI(model=EXPERT_MODEL, temperature=0.3)
    structured_model = model.with_structured_output(ExpertGameReport)

    system_msg = SystemMessage(content=EXPERT_REPORT_PROMPT)
    human_msg = HumanMessage(content=combined_report_text)

    result: ExpertGameReport = structured_model.invoke([system_msg, human_msg])
    logger.info("run_expert_report: LLM call done for game_id=%d", game_id)

    insert_expert_report(game_id, result)
    logger.info("run_expert_report: report saved to DB for game_id=%d", game_id)

    return result
