from __future__ import annotations

import asyncio
import logging
from datetime import time

from telegram import Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from soccersmartbet.gambling_flow.handlers import handle_gamble_callback
from soccersmartbet.reports.html_report import generate_game_report_html
from soccersmartbet.reports.telegram_message import get_games_info
from soccersmartbet.telegram.bot import (
    TELEGRAM_BOT_TOKEN,
    is_owner,
    send_gambling_time,
    send_html_report,
)
from soccersmartbet.utils.timezone import ISR_TZ

logger = logging.getLogger(__name__)


async def trigger_pre_gambling_and_notify() -> None:
    """Run the full Pre-Gambling Flow, then notify via Telegram.

    Steps:
        1. Runs run_pre_gambling_flow() in a thread executor so the event
           loop is not blocked.
        2. Extracts game_ids from the result dict under key "games_to_analyze".
        3. Sends the gambling time text message (bullet list of games).
        4. For each game, generates the HTML report and sends it as a file
           attachment named "{home}_vs_{away}.html".
    """
    from soccersmartbet.pre_gambling_flow.graph_manager import run_pre_gambling_flow  # noqa: PLC0415

    logger.info("Pre-gambling flow trigger fired")

    result = await asyncio.to_thread(run_pre_gambling_flow)

    game_ids: list[int] = result.get("games_to_analyze", [])
    logger.info("Pre-gambling flow completed, games_to_analyze=%s", game_ids)

    await send_gambling_time(game_ids)
    logger.info("Gambling time notification dispatched for %d game(s)", len(game_ids))

    games_info = get_games_info(game_ids)
    info_by_id = {g["game_id"]: g for g in games_info}

    for game_id in game_ids:
        info = info_by_id.get(game_id)
        if info is None:
            logger.warning("No DB info for game_id=%s, skipping HTML report", game_id)
            continue

        home = info["home_team"].replace(" ", "_")
        away = info["away_team"].replace(" ", "_")
        filename = f"{home}_vs_{away}.html"

        logger.info("Generating HTML report: game_id=%s filename=%s", game_id, filename)
        html_content = await asyncio.to_thread(generate_game_report_html, game_id)

        await send_html_report(game_id, html_content, filename)


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
    application.add_handler(CallbackQueryHandler(handle_gamble_callback))
    application.add_handler(MessageHandler(filters.ALL, _handle_unknown))

    # Schedule daily job at 13:00 ISR
    job_time = time(hour=13, minute=0, tzinfo=ISR_TZ)
    application.job_queue.run_daily(  # type: ignore[union-attr]
        callback=_daily_job,
        time=job_time,
        name="pre_gambling_daily",
    )

    logger.info("SoccerSmartBet bot starting — daily job scheduled at 13:00 ISR")

    application.run_polling()
