from __future__ import annotations

import asyncio
import logging
from datetime import date, datetime

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from soccersmartbet.daily_runs import get_daily_run, get_pending_post_games, upsert_daily_run
from soccersmartbet.gambling_flow.handlers import handle_gamble_callback
from soccersmartbet.telegram.bot import (
    TELEGRAM_BOT_TOKEN,
    is_owner,
)
from soccersmartbet.utils.timezone import ISR_TZ, now_isr

logger = logging.getLogger(__name__)

# Pre-gambling trigger time (ISR) — set to 08:35 for testing, revert to 13:00 for production
_PRE_GAMBLING_HOUR = 8
_PRE_GAMBLING_MINUTE = 35


async def trigger_pre_gambling_and_notify() -> None:
    """Run the full Pre-Gambling Flow, then notify via Telegram.

    Writes pre_gambling_started_at to daily_runs before the flow begins and
    pre_gambling_completed_at + game_ids after it finishes. On no-games days,
    sends an interactive Yes/No prompt so the user can confirm whether the
    result makes sense (tracking for future improvement).
    """
    from soccersmartbet.pre_gambling_flow.graph_manager import run_pre_gambling_flow  # noqa: PLC0415

    today = now_isr().date()

    logger.info("Pre-gambling flow trigger fired for %s", today)
    upsert_daily_run(today, pre_gambling_started_at=now_isr())

    result = await asyncio.to_thread(run_pre_gambling_flow)

    game_ids: list[int] = result.get("games_to_analyze", [])
    games_found = len(game_ids)
    logger.info(
        "Pre-gambling flow completed: games_found=%d, game_ids=%s",
        games_found, game_ids,
    )

    upsert_daily_run(
        today,
        pre_gambling_completed_at=now_isr(),
        game_ids=game_ids,
        games_found=games_found,
    )

    if not game_ids:
        logger.info("No games selected — sending no-games confirmation prompt")
        from soccersmartbet.telegram.bot import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID  # noqa: PLC0415
        from telegram import Bot  # noqa: PLC0415

        text = (
            "\u26a0\ufe0f <b>No games selected today</b>\n\n"
            "The pre-gambling flow ran but found no games for betting.\n"
            "This could be a real no-games day or a bug in the picker.\n\n"
            "Does this make sense to you?"
        )
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("\u2705 Yes, expected", callback_data="no_games_yes"),
                InlineKeyboardButton("\u274c No, looks wrong", callback_data="no_games_no"),
            ]
        ])
        bot = Bot(token=TELEGRAM_BOT_TOKEN)
        async with bot:
            await bot.send_message(
                chat_id=int(TELEGRAM_CHAT_ID),
                text=text,
                reply_markup=keyboard,
                parse_mode="HTML",
            )
        return

    # Telegram notifications (gambling time + HTML reports + want-to-bet prompt)
    # are sent by the notify_telegram node inside the LangGraph flow.
    # No need to send them again here.
    logger.info("Pre-gambling flow done — %d game(s) selected, notifications sent by graph", len(game_ids))


# ---------------------------------------------------------------------------
# Wall-clock poller
# ---------------------------------------------------------------------------


async def _wall_clock_poller(application: Application) -> None:
    """Background asyncio task that replaces APScheduler's run_daily().

    Loops every 60 seconds and checks wall-clock time (datetime.now, not
    CLOCK_MONOTONIC). After a macOS sleep/resume the first iteration sees the
    real wall time and fires immediately if a trigger was missed.

    Pre-gambling fires at 13:00 ISR if today's daily_runs has no
    pre_gambling_started_at.

    Post-games fires when:
        - post_games_trigger_at is set (calculated once when gambling completes)
        - post_games_completed_at is not set
        - now >= post_games_trigger_at
    """
    logger.info("Wall-clock poller started")

    while True:
        try:
            now = now_isr()
            today = now.date()
            daily = get_daily_run(today)

            # ---- pre-gambling check ----------------------------------------
            pre_gambling_due = now.hour > _PRE_GAMBLING_HOUR or (
                now.hour == _PRE_GAMBLING_HOUR and now.minute >= _PRE_GAMBLING_MINUTE
            )

            if pre_gambling_due:
                if daily is None or daily["pre_gambling_started_at"] is None:
                    logger.info(
                        "Wall-clock poller: firing pre-gambling (now=%s, row=%s)",
                        now.strftime("%H:%M"),
                        "none" if daily is None else "no started_at",
                    )
                    await trigger_pre_gambling_and_notify()
                    # Refresh daily row for post-games check below
                    daily = get_daily_run(today)

                elif daily["pre_gambling_started_at"] is not None and daily["pre_gambling_completed_at"] is None:
                    # Flow started but never completed — likely crashed mid-run.
                    # Do NOT re-fire automatically: persist_games inserts raw rows,
                    # so re-running would duplicate games in the DB.
                    logger.warning(
                        "Wall-clock poller: pre-gambling started at %s but never completed "
                        "(possible crash). Manual trigger required to avoid duplicate games.",
                        daily["pre_gambling_started_at"],
                    )

            # ---- post-games check ------------------------------------------
            # Query for ANY pending post-games trigger (not just today's row),
            # because late games cross midnight (e.g. trigger at 01:00 Apr 13
            # is stored on the Apr 12 row).
            pending = get_pending_post_games()
            if pending is not None and now >= pending["post_games_trigger_at"]:
                logger.info(
                    "Wall-clock poller: firing post-games (now=%s, trigger_at=%s, run_date=%s)",
                    now.strftime("%H:%M"),
                    pending["post_games_trigger_at"].strftime("%H:%M"),
                    pending["run_date"],
                )
                await _fire_post_games(pending["game_ids"], pending["run_date"])

        except Exception:
            logger.exception("Wall-clock poller: unhandled error in polling loop")

        await asyncio.sleep(60)


async def _fire_post_games(game_ids: list[int], today: date) -> None:
    """Run post-games flow in a thread and mark completion in daily_runs."""
    from soccersmartbet.post_games_flow.graph_manager import run_post_games_flow  # noqa: PLC0415

    logger.info("Post-games flow starting for game_ids=%s", game_ids)
    await asyncio.to_thread(run_post_games_flow, game_ids)
    upsert_daily_run(today, post_games_completed_at=now_isr())
    logger.info("Post-games flow completed and daily_runs updated")


# ---------------------------------------------------------------------------
# Telegram Application handlers
# ---------------------------------------------------------------------------


async def _cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_chat is None:
        return
    if not is_owner(update.effective_chat.id):
        logger.info("Blocked /start from unauthorized chat_id=%s", update.effective_chat.id)
        return
    await update.message.reply_text("SoccerSmartBet bot is active")  # type: ignore[union-attr]


async def _handle_no_games_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle the no-games-day Yes/No confirmation buttons."""
    query = update.callback_query
    if query is None:
        return
    if update.effective_chat is None:
        return
    if not is_owner(update.effective_chat.id):
        await query.answer()
        return

    await query.answer()
    data: str = query.data or ""

    today = now_isr().date()

    if data == "no_games_yes":
        upsert_daily_run(today, no_games_user_confirmed=True)
        await query.edit_message_text(
            "\u2705 Got it — no games today, confirmed as expected.",
            parse_mode="HTML",
        )
        logger.info("No-games day confirmed by user as expected")
    elif data == "no_games_no":
        upsert_daily_run(today, no_games_user_confirmed=False)
        await query.edit_message_text(
            "\u274c Noted — something may be wrong with game selection. "
            "Logged for investigation.",
            parse_mode="HTML",
        )
        logger.warning("No-games day REJECTED by user — possible picker bug")


async def _handle_unknown(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_chat is None:
        return
    if not is_owner(update.effective_chat.id):
        logger.info("Ignored message from unauthorized chat_id=%s", update.effective_chat.id)


# ---------------------------------------------------------------------------
# Scheduler entry point
# ---------------------------------------------------------------------------


async def _post_init(application: Application) -> None:
    """Called by python-telegram-bot after Application is initialised.

    Starts the wall-clock poller as a background asyncio task via
    asyncio.create_task (not application.create_task to avoid PTB warning).
    """
    asyncio.create_task(_wall_clock_poller(application))
    logger.info("Wall-clock poller task created")


def start_scheduler() -> None:
    """Start the bot with wall-clock polling scheduler. Blocks forever.

    Registers command/callback handlers, then launches the wall-clock poller
    via post_init before entering run_polling().
    """
    if not TELEGRAM_BOT_TOKEN:
        raise RuntimeError("TELEGRAM_BOT_TOKEN must be set to start the scheduler.")

    application = (
        Application.builder()
        .token(TELEGRAM_BOT_TOKEN)
        .post_init(_post_init)
        .build()
    )

    application.add_handler(CommandHandler("start", _cmd_start))
    application.add_handler(
        CallbackQueryHandler(_handle_no_games_callback, pattern=r"^no_games_")
    )
    application.add_handler(CallbackQueryHandler(handle_gamble_callback))
    application.add_handler(MessageHandler(filters.ALL, _handle_unknown))

    logger.info(
        "SoccerSmartBet bot starting — wall-clock poller will fire at %02d:%02d ISR",
        _PRE_GAMBLING_HOUR, _PRE_GAMBLING_MINUTE,
    )

    application.run_polling()
