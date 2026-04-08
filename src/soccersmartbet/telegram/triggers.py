from __future__ import annotations

import asyncio
import logging
import os
from datetime import time

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from soccersmartbet.telegram.bot import TELEGRAM_BOT_TOKEN, is_owner, send_gambling_time
from soccersmartbet.utils.timezone import ISR_TZ

logger = logging.getLogger(__name__)

REPORTS_BASE_URL: str = os.getenv("REPORTS_BASE_URL", "http://localhost:8000")


async def trigger_pre_gambling_and_notify() -> None:
    """Run the full Pre-Gambling Flow, then send gambling time message via Telegram.

    Steps:
        1. Runs run_pre_gambling_flow() (synchronous LangGraph call) in a thread
           executor so the event loop is not blocked.
        2. Extracts game_ids from the result dict under key "games_to_analyze".
        3. Sends the gambling time Telegram message with report links.
    """
    from soccersmartbet.pre_gambling_flow.graph_manager import run_pre_gambling_flow  # noqa: PLC0415

    logger.info("Pre-gambling flow trigger fired")

    result = await asyncio.to_thread(run_pre_gambling_flow)

    game_ids: list[int] = result.get("games_to_analyze", [])
    logger.info("Pre-gambling flow completed, games_to_analyze=%s", game_ids)

    await send_gambling_time(game_ids, REPORTS_BASE_URL)
    logger.info("Gambling time notification dispatched for %d game(s)", len(game_ids))


# ---------------------------------------------------------------------------
# Telegram Application handlers
# ---------------------------------------------------------------------------


async def _cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start — reply only to the owner."""
    if update.effective_chat is None:
        return

    if not is_owner(update.effective_chat.id):
        logger.info(
            "Blocked /start from unauthorized chat_id=%s", update.effective_chat.id
        )
        return

    await update.message.reply_text("SoccerSmartBet bot is active")  # type: ignore[union-attr]


async def _handle_unknown(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Ignore all messages from non-owner chats."""
    if update.effective_chat is None:
        return

    if not is_owner(update.effective_chat.id):
        logger.info(
            "Ignored message from unauthorized chat_id=%s", update.effective_chat.id
        )


async def _daily_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    """JobQueue callback that fires the pre-gambling flow daily."""
    logger.info("Daily scheduler job triggered")
    await trigger_pre_gambling_and_notify()


# ---------------------------------------------------------------------------
# Scheduler entry point
# ---------------------------------------------------------------------------


def start_scheduler() -> None:
    """Start the daily scheduler. Blocks forever.

    Schedules trigger_pre_gambling_and_notify to run daily at 13:00 ISR.
    Also registers a /start command handler (owner-gated) and a catch-all
    handler that silently drops messages from non-owner chats.

    Calls application.run_polling() which blocks until the process exits.
    """
    if not TELEGRAM_BOT_TOKEN:
        raise RuntimeError("TELEGRAM_BOT_TOKEN must be set to start the scheduler.")

    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Register command and fallback handlers
    application.add_handler(CommandHandler("start", _cmd_start))
    application.add_handler(MessageHandler(filters.ALL, _handle_unknown))

    # Schedule daily job at 13:00 ISR
    job_time = time(hour=13, minute=0, tzinfo=ISR_TZ)
    application.job_queue.run_daily(  # type: ignore[union-attr]
        callback=_daily_job,
        time=job_time,
        name="pre_gambling_daily",
    )

    logger.info(
        "SoccerSmartBet bot starting — daily job scheduled at 13:00 ISR, base_url=%s",
        REPORTS_BASE_URL,
    )

    application.run_polling()
