"""System prompt + single-shot LLM call for the AI insights endpoint.

This is NOT a LangGraph flow — it is one synchronous ``ChatOpenAI.invoke``
wrapped in :func:`asyncio.to_thread` by the caller in :mod:`jobs`.

The model / temperature choice mirrors
:mod:`soccersmartbet.pre_gambling_flow.agents.game_intelligence`:
``ChatOpenAI(model=INTELLIGENCE_MODEL, temperature=0.2)``.  ``INTELLIGENCE_MODEL``
is the same env-driven constant used by the rest of the codebase so the
insights endpoint inherits Omer's model choice for free.
"""
from __future__ import annotations

import logging
from typing import Iterable

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from soccersmartbet.pre_gambling_flow.agents.game_intelligence import INTELLIGENCE_MODEL
from soccersmartbet.utils.timezone import format_isr_date, format_isr_time
from soccersmartbet.webapp.query.models import BetRow, FilterResult

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """You are analyzing an expert football bettor's own betting history.

He already knows basic football stats — skip obvious things (e.g. "you bet a
lot on home teams", "longer odds pay more when they hit", "draws are rare").
He wants edges he does not already see.

Focus on:
- Bettor-vs-AI win-rate delta per league / stake range
  (i.e. places where the human meaningfully out- or under-performs the AI).
- Stake-size correlation with outcome — does he size up on losers?
- League blind spots — leagues where he consistently loses money.
- Prediction-type bias — a home/draw/away imbalance that is actively
  costing him (not just "he picks more 1s").
- Odds-range performance bands — which price band is actually profitable
  and which is dead money.

Respond in English.  Output markdown bullets only — no JSON, no preamble,
no closing remark.  Maximum 5 bullets.  Every bullet MUST start with a
concrete number, delta, or percentage (e.g. "-12% ROI in La Liga across
47 bets", "AI +8pp win-rate vs you on 1.5-1.8 odds").  If the data does
not support 5 useful bullets, return fewer — do not pad.

If the user message contains a sampling-note warning, explicitly caveat
the conclusions — state "based on recent 500 bets only" in the first or
last bullet.  Never claim trends across the full history when sampled."""


# ---------------------------------------------------------------------------
# User-message assembly
# ---------------------------------------------------------------------------


def _format_row(row: BetRow) -> str:
    """Format one :class:`BetRow` as a single markdown table row."""
    pnl = f"{row.pnl:.2f}" if row.pnl is not None else ""
    result = row.result or ""
    outcome = row.outcome or ""
    score = (
        f"{row.home_score}-{row.away_score}"
        if row.home_score is not None and row.away_score is not None
        else ""
    )
    return (
        f"| {format_isr_date(row.match_date)} | {row.league} | "
        f"{row.home_team} vs {row.away_team} | {row.bettor} | "
        f"{row.prediction} | {row.stake:.2f} | {row.odds:.2f} | "
        f"{result} | {outcome} | {score} | {pnl} |"
    )


def _build_table(rows: Iterable[BetRow]) -> str:
    """Serialise rows as a markdown table the LLM can scan as context."""
    header = (
        "| date | league | match | bettor | prediction | stake | odds | "
        "result | outcome | score | pnl |"
    )
    sep = "|" + "|".join(["---"] * 11) + "|"
    body = "\n".join(_format_row(r) for r in rows)
    return "\n".join([header, sep, body])


#: Hard human-readable warning prepended when ``FilterResult.row_cap_hit``
#: is True.  The ``row_cap_hit: True`` boolean in the aggregates block is
#: easy for an LLM to skim past; this block is written as a prose caveat so
#: the model actually reads it and scopes its bullets accordingly.
_SAMPLING_NOTE = (
    "⚠️  Sampling note: the bet history shown below is the MOST RECENT 500 rows.\n"
    "The complete filter matched more rows — older activity is not in this prompt.\n"
    "Caveat any trend-over-time claims; caveat any \"always\"/\"never\"/\"lately\" claims."
)


def _build_user_message(result: FilterResult) -> str:
    """Assemble the full user message: filter echo + aggregates + bet table.

    When :attr:`FilterResult.row_cap_hit` is True, the row table has been
    truncated to the 500 most-recent bets.  A prose ``_SAMPLING_NOTE`` is
    prepended (in addition to the ``row_cap_hit: True`` flag in the
    aggregates block) so the LLM cannot silently reason over a partial
    history as if it were the whole.
    """
    agg = result.aggregates
    win_rate = f"{agg.win_rate:.3f}" if agg.win_rate is not None else "n/a"

    header_lines: list[str] = []
    if result.row_cap_hit:
        header_lines.extend([_SAMPLING_NOTE, ""])
    header_lines.extend(
        [
            "## Filter",
            f"DSL: `{result.dsl or '(empty — full history)'}`",
            "",
            "## Aggregates",
            f"- rows: {agg.count}",
            f"- total_stake: {agg.total_stake:.2f}",
            f"- total_pnl: {agg.total_pnl:.2f}",
            f"- win_rate: {win_rate}",
            f"- row_cap_hit: {result.row_cap_hit}",
            "",
            "## Rows",
        ]
    )
    return "\n".join(header_lines) + "\n" + _build_table(result.rows)


# ---------------------------------------------------------------------------
# Public LLM call (sync — caller wraps in asyncio.to_thread)
# ---------------------------------------------------------------------------


def generate_insights(result: FilterResult) -> str:
    """Run a single ``ChatOpenAI`` call and return the markdown bullet list.

    Must be called from a worker thread (``asyncio.to_thread``) — the
    underlying ``ChatOpenAI.invoke`` is synchronous and would otherwise
    block FastAPI's event loop.

    Args:
        result: Non-empty :class:`FilterResult` produced by
            :func:`soccersmartbet.webapp.query.service.run_filter`.

    Returns:
        The markdown response body (trimmed) — nothing else, no JSON
        wrapper.  Raises on any LLM-side failure; the job manager catches
        and records the error.
    """
    logger.info(
        "generate_insights: calling %s with %d rows",
        INTELLIGENCE_MODEL,
        result.aggregates.count,
    )

    model = ChatOpenAI(model=INTELLIGENCE_MODEL, temperature=0.2)
    response = model.invoke(
        [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=_build_user_message(result)),
        ]
    )

    # LangChain AIMessage.content can be str or a list of content blocks.
    content = response.content
    if isinstance(content, list):
        content = "".join(
            part.get("text", "") if isinstance(part, dict) else str(part)
            for part in content
        )
    return content.strip()
