from __future__ import annotations

import asyncio
import logging
import signal
from datetime import date
from typing import Coroutine, Any

import uvicorn
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup, Update
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
    TELEGRAM_CHAT_ID,
    is_owner,
)
from soccersmartbet.utils.timezone import now_isr
from soccersmartbet.webapp.runtime_state import LAST_POLLER_TICK
from soccersmartbet.webapp.audit import EventType, write_run_event
from soccersmartbet.webapp.run_mutex import FlowConflict, acquire_flow, mark_failed, release_flow

logger = logging.getLogger(__name__)

# Pre-gambling trigger time (ISR) — set to 08:35 for testing, revert to 13:00 for production
_PRE_GAMBLING_HOUR = 8
_PRE_GAMBLING_MINUTE = 35

# ---------------------------------------------------------------------------
# In-flight flow task registry (C1/C4)
# ---------------------------------------------------------------------------

_ACTIVE_FLOW_TASKS: set[asyncio.Task] = set()


def _spawn_flow(coro: Coroutine[Any, Any, Any]) -> asyncio.Task:
    """Create a task, register it, and auto-remove on completion."""
    task = asyncio.create_task(coro)
    _ACTIVE_FLOW_TASKS.add(task)
    task.add_done_callback(_ACTIVE_FLOW_TASKS.discard)
    return task


async def _send_operator_alert(text: str) -> None:
    """Send an HTML-formatted operator alert to the owner chat.

    Swallows send failures (logged via logger.exception) so the caller's
    error-recovery flow is never blocked by a Telegram outage.
    """
    try:
        bot = Bot(token=TELEGRAM_BOT_TOKEN)
        async with bot:
            await bot.send_message(
                chat_id=int(TELEGRAM_CHAT_ID),
                text=text,
                parse_mode="HTML",
            )
    except Exception:
        logger.exception("Failed to send operator alert via Telegram")


async def trigger_pre_gambling_and_notify() -> None:
    """Run the full Pre-Gambling Flow, then notify via Telegram.

    Acquires the flow mutex (daily_runs.status) before invoking.  Writes
    run_events audit rows on start, completion, and failure.  On no-games
    days sends an interactive Yes/No prompt.
    """
    from soccersmartbet.pre_gambling_flow.graph_manager import run_pre_gambling_flow  # noqa: PLC0415

    today = now_isr().date()
    logger.info("Pre-gambling flow trigger fired for %s", today)

    try:
        with acquire_flow(today, "pre_gambling_running", triggered_by="scheduler") as ctx:
            write_run_event(
                today,
                EventType.PRE_GAMBLING_STARTED,
                "scheduler",
                {
                    "flow_type": "pre_gambling",
                    "triggered_at_isr": now_isr().isoformat(),
                    "attempt_count": ctx.attempt_count,
                },
            )
            upsert_daily_run(today, pre_gambling_started_at=now_isr())
    except FlowConflict as exc:
        logger.warning(
            "Pre-gambling flow already running (status=%s) — skipping scheduler fire", exc
        )
        return

    started = now_isr()
    try:
        result = await asyncio.to_thread(run_pre_gambling_flow)
    except Exception as exc:
        mark_failed(today, exc)
        write_run_event(
            today,
            EventType.PRE_GAMBLING_FAILED,
            "scheduler",
            {
                "flow_type": "pre_gambling",
                "error_type": type(exc).__name__,
                "error_message": str(exc)[:2000],
            },
        )
        alert_text = (
            "❗ <b>Pre-gambling flow FAILED</b>\n\n"
            f"<b>Error type:</b> {type(exc).__name__}\n"
            f"<b>Message:</b> {exc}\n\n"
            f"<b>Time:</b> {now_isr().strftime('%Y-%m-%d %H:%M ISR')}\n\n"
            "The <code>daily_runs</code> row has been marked <code>failed</code>.\n\n"
            "Re-trigger manually when ready."
        )
        await _send_operator_alert(alert_text)
        # Re-raised for future Wave 11 HTTP-route exception handling; poller's bare except logs it.
        raise

    game_ids: list[int] = result.get("games_to_analyze", [])
    games_found = len(game_ids)
    logger.info(
        "Pre-gambling flow completed: games_found=%d, game_ids=%s",
        games_found,
        game_ids,
    )

    try:
        release_flow(today, "pre_gambling_done")
    except Exception as exc:
        logger.exception("release_flow failed — marking flow failed instead")
        mark_failed(today, exc)
        raise
    elapsed = (now_isr() - started).total_seconds()
    write_run_event(
        today,
        EventType.PRE_GAMBLING_COMPLETED,
        "scheduler",
        {
            "flow_type": "pre_gambling",
            "game_ids": game_ids,
            "games_found": games_found,
            "elapsed_seconds": round(elapsed, 2),
        },
    )
    upsert_daily_run(
        today,
        pre_gambling_completed_at=now_isr(),
        game_ids=game_ids,
        games_found=games_found,
    )

    if not game_ids:
        logger.info("No games selected — sending no-games confirmation prompt")
        text = (
            "⚠️ <b>No games selected today</b>\n\n"
            "The pre-gambling flow ran but found no games for betting.\n"
            "This could be a real no-games day or a bug in the picker.\n\n"
            "Does this make sense to you?"
        )
        today_iso = today.isoformat()
        keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "✅ Yes, expected", callback_data=f"no_games_yes:{today_iso}"
                    ),
                    InlineKeyboardButton(
                        "❌ No, looks wrong", callback_data=f"no_games_no:{today_iso}"
                    ),
                ]
            ]
        )
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
    logger.info("Pre-gambling flow done — %d game(s) selected, notifications sent by graph", len(game_ids))


# ---------------------------------------------------------------------------
# Wall-clock poller
# ---------------------------------------------------------------------------


async def _wall_clock_poller(application: Application) -> None:
    """Background asyncio task that replaces APScheduler's run_daily().

    Loops every 60 seconds and checks wall-clock time.  After a macOS
    sleep/resume the first iteration sees the real wall time and fires
    immediately if a trigger was missed.

    Pre-gambling fires at _PRE_GAMBLING_HOUR:_PRE_GAMBLING_MINUTE ISR if
    today's daily_runs has no pre_gambling_started_at.

    Post-games fires when:
        - post_games_trigger_at is set (calculated once when gambling completes)
        - post_games_completed_at is not set
        - now >= post_games_trigger_at

    Updates _LAST_POLLER_TICK[0] every iteration for /api/health.

    Flow triggers are spawned as background tasks so the poller's 60s heartbeat
    stays fresh while a multi-minute flow runs. Concurrent fires are deduped by
    the daily_runs.status mutex.
    """
    logger.info("Wall-clock poller started")

    while True:
        try:
            now = now_isr()
            today = now.date()

            # Update health tick — poller is alive
            LAST_POLLER_TICK[0] = now.isoformat()

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
                    _spawn_flow(trigger_pre_gambling_and_notify())

                elif daily.get("status") in (
                    "pre_gambling_running",
                    "gambling_running",
                    "post_games_running",
                ):
                    # Flow started but mutex still held — do NOT re-fire.
                    logger.warning(
                        "Wall-clock poller: flow in progress (status=%s) — skipping re-fire.",
                        daily["status"],
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
                _spawn_flow(_fire_post_games(pending["game_ids"], pending["run_date"]))

        except Exception:
            logger.exception("Wall-clock poller: unhandled error in polling loop")

        await asyncio.sleep(60)


async def _fire_post_games(game_ids: list[int], today: date) -> None:
    """Run post-games flow in a thread and mark completion in daily_runs."""
    from soccersmartbet.post_games_flow.graph_manager import run_post_games_flow  # noqa: PLC0415

    logger.info("Post-games flow starting for game_ids=%s", game_ids)

    try:
        with acquire_flow(today, "post_games_running", triggered_by="scheduler") as ctx:
            write_run_event(
                today,
                EventType.POST_GAMES_STARTED,
                "scheduler",
                {
                    "flow_type": "post_games",
                    "triggered_at_isr": now_isr().isoformat(),
                    "attempt_count": ctx.attempt_count,
                },
            )
    except FlowConflict as exc:
        logger.warning(
            "Post-games flow already running (status=%s) — skipping scheduler fire", exc
        )
        return

    started = now_isr()
    try:
        await asyncio.to_thread(run_post_games_flow, game_ids)
    except Exception as exc:
        mark_failed(today, exc)
        write_run_event(
            today,
            EventType.POST_GAMES_FAILED,
            "scheduler",
            {
                "flow_type": "post_games",
                "error_type": type(exc).__name__,
                "error_message": str(exc)[:2000],
            },
        )
        alert_text = (
            "❗ <b>Post-games flow FAILED</b>\n\n"
            f"<b>Error type:</b> {type(exc).__name__}\n"
            f"<b>Message:</b> {exc}\n\n"
            f"<b>Time:</b> {now_isr().strftime('%Y-%m-%d %H:%M ISR')}\n\n"
            "The <code>daily_runs</code> row has been marked <code>failed</code>.\n\n"
            "To re-run manually: use the dashboard or wait for the next poller tick."
        )
        await _send_operator_alert(alert_text)
        # Re-raised for future Wave 11 HTTP-route exception handling; poller's bare except logs it.
        raise

    try:
        release_flow(today, "post_games_done")
    except Exception as exc:
        logger.exception("release_flow failed — marking flow failed instead")
        mark_failed(today, exc)
        raise
    elapsed = (now_isr() - started).total_seconds()
    write_run_event(
        today,
        EventType.POST_GAMES_COMPLETED,
        "scheduler",
        {
            "flow_type": "post_games",
            "game_ids": game_ids,
            "games_found": len(game_ids),
            "elapsed_seconds": round(elapsed, 2),
        },
    )
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

    # Parse the date embedded in callback_data (e.g. "no_games_yes:2026-04-22").
    action, _, date_str = data.partition(":")
    try:
        target_date = date.fromisoformat(date_str) if date_str else now_isr().date()
    except ValueError:
        target_date = now_isr().date()

    if action == "no_games_yes":
        upsert_daily_run(target_date, no_games_user_confirmed=True)
        await query.edit_message_text(
            "✅ Got it — no games today, confirmed as expected.",
            parse_mode="HTML",
        )
        logger.info("No-games day confirmed by user as expected")
    elif action == "no_games_no":
        upsert_daily_run(target_date, no_games_user_confirmed=False)
        await query.edit_message_text(
            "❌ Noted — something may be wrong with game selection. "
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
# Scheduler entry point — async, co-hosts FastAPI + Telegram + poller
# ---------------------------------------------------------------------------


async def start_scheduler() -> None:
    """Start the bot with wall-clock polling scheduler and FastAPI dashboard.

    Runs as a single asyncio event loop:
      - uvicorn.Server serves FastAPI on 127.0.0.1:8083
      - wall-clock poller fires at _PRE_GAMBLING_HOUR:_PRE_GAMBLING_MINUTE ISR
      - Telegram updater receives updates via long-polling

    Graceful shutdown on SIGTERM / SIGINT:
      1. Signal uvicorn to stop
      2. Stop/shutdown Telegram application
      3. Cancel poller task
    """
    if not TELEGRAM_BOT_TOKEN:
        raise RuntimeError("TELEGRAM_BOT_TOKEN must be set to start the scheduler.")
    if not TELEGRAM_CHAT_ID:
        raise RuntimeError("TELEGRAM_CHAT_ID must be set to start the scheduler.")

    # Build Telegram application — manual lifecycle; no post_init
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", _cmd_start))
    application.add_handler(
        CallbackQueryHandler(_handle_no_games_callback, pattern=r"^no_games_")
    )
    application.add_handler(CallbackQueryHandler(handle_gamble_callback))
    application.add_handler(MessageHandler(filters.ALL, _handle_unknown))

    logger.info(
        "SoccerSmartBet bot starting — wall-clock poller will fire at %02d:%02d ISR",
        _PRE_GAMBLING_HOUR,
        _PRE_GAMBLING_MINUTE,
    )

    # Manual Telegram lifecycle (no post_init, no run_polling)
    await application.initialize()
    await application.updater.start_polling()
    await application.start()

    # Build uvicorn server for FastAPI dashboard
    from soccersmartbet.webapp.app import app as fastapi_app  # noqa: PLC0415

    config = uvicorn.Config(
        fastapi_app,
        host="127.0.0.1",
        port=8083,
        log_level="info",
        lifespan="on",
    )
    server = uvicorn.Server(config)

    # Shutdown coordination
    shutdown_event = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, shutdown_event.set)

    # Start background tasks
    poller_task = asyncio.create_task(_wall_clock_poller(application))
    server_task = asyncio.create_task(server.serve())

    logger.info("FastAPI dashboard listening on http://127.0.0.1:8083")

    # Wait for shutdown signal
    await shutdown_event.wait()

    logger.info("Shutdown signal received — beginning graceful shutdown")

    # Shutdown sequence
    server.should_exit = True
    await application.updater.stop()
    await application.stop()
    await application.shutdown()
    poller_task.cancel()

    # Drain in-flight flow tasks before cancelling server/poller (C1/C4)
    if _ACTIVE_FLOW_TASKS:
        logger.info("Shutdown: draining %d in-flight flow task(s)", len(_ACTIVE_FLOW_TASKS))
        try:
            await asyncio.wait_for(
                asyncio.gather(*_ACTIVE_FLOW_TASKS, return_exceptions=True),
                timeout=20,
            )
        except asyncio.TimeoutError:
            logger.warning("Shutdown: flow drain timed out — cancelling")
            for t in _ACTIVE_FLOW_TASKS:
                t.cancel()
            await asyncio.gather(*_ACTIVE_FLOW_TASKS, return_exceptions=True)

    try:
        await asyncio.wait_for(
            asyncio.gather(server_task, poller_task, return_exceptions=True),
            timeout=30,
        )
    except asyncio.TimeoutError:
        logger.warning("Shutdown timed out after 30s — force-cancelling tasks")
        server_task.cancel()
        poller_task.cancel()
        # Give cancelled tasks a brief chance to finalize
        await asyncio.gather(server_task, poller_task, return_exceptions=True)

    logger.info("Graceful shutdown complete")
