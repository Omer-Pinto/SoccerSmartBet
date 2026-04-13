from __future__ import annotations

import io
import logging
import os

from telegram import Bot

from soccersmartbet.reports.telegram_message import format_gambling_time_message

logger = logging.getLogger(__name__)

TELEGRAM_BOT_TOKEN: str | None = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID: str | None = os.getenv("TELEGRAM_CHAT_ID")


def is_owner(chat_id: int) -> bool:
    """Return True if chat_id matches the configured owner chat ID."""
    return str(chat_id) == TELEGRAM_CHAT_ID


async def send_message(text: str, parse_mode: str | None = None) -> None:
    """Send a text message to the owner chat.

    Args:
        text: The message body to send.
        parse_mode: Optional Telegram parse mode, e.g. ``"HTML"`` or ``"Markdown"``.

    Raises:
        RuntimeError: If TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID is not configured.
    """
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        raise RuntimeError(
            "TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID must be set to send messages."
        )

    bot = Bot(token=TELEGRAM_BOT_TOKEN)
    async with bot:
        await bot.send_message(
            chat_id=int(TELEGRAM_CHAT_ID),
            text=text,
            parse_mode=parse_mode,
        )

    logger.info("Telegram message sent to chat_id=%s", TELEGRAM_CHAT_ID)


async def send_html_report(game_id: int, html_content: str, filename: str) -> None:
    """Send an HTML report as a document attachment to the owner chat.

    Args:
        game_id: The game ID (used only for logging).
        html_content: Complete self-contained HTML string to send as a file.
        filename: Filename for the attachment, e.g. "Arsenal_vs_Chelsea.html".

    Raises:
        RuntimeError: If TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID is not configured.
    """
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        raise RuntimeError(
            "TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID must be set to send documents."
        )

    document = io.BytesIO(html_content.encode("utf-8"))

    bot = Bot(token=TELEGRAM_BOT_TOKEN)
    async with bot:
        await bot.send_document(
            chat_id=int(TELEGRAM_CHAT_ID),
            document=document,
            filename=filename,
        )

    logger.info(
        "HTML report sent as document: game_id=%s filename=%s chat_id=%s",
        game_id,
        filename,
        TELEGRAM_CHAT_ID,
    )


async def send_gambling_time(game_ids: list[int]) -> None:
    """Format and send the gambling time message.

    Fetches game metadata from the database via format_gambling_time_message,
    then delivers the result to the owner chat.

    Args:
        game_ids: List of game IDs to include in the message.
    """
    text = format_gambling_time_message(game_ids)
    await send_message(text, parse_mode="HTML")
    logger.info("Gambling time message sent for %d game(s)", len(game_ids))
