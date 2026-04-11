from __future__ import annotations

import asyncio
import logging

from telegram import Bot

from soccersmartbet.gambling_flow.handlers import send_want_to_bet
from soccersmartbet.pre_gambling_flow.state import PreGamblingState
from soccersmartbet.reports.html_report import generate_game_report_html
from soccersmartbet.reports.telegram_message import get_games_info
from soccersmartbet.telegram.bot import (
    TELEGRAM_BOT_TOKEN,
    send_gambling_time,
    send_html_report,
)

logger = logging.getLogger(__name__)


def notify_telegram(state: PreGamblingState) -> dict:
    """LangGraph node: send gambling time message + HTML reports via Telegram.

    After all HTML reports are sent, also sends the interactive "want to bet?"
    prompt so the user can place bets via inline keyboard buttons.
    """
    game_ids: list[int] = state["games_to_analyze"]

    if not game_ids:
        logger.info("notify_telegram: no games, skipping notification")
        return {}

    async def _send_all() -> None:
        await send_gambling_time(game_ids)

        games_info = get_games_info(game_ids)
        info_by_id = {g["game_id"]: g for g in games_info}

        for game_id in game_ids:
            info = info_by_id.get(game_id)
            if info is None:
                continue
            home = info["home_team"].replace(" ", "_")
            away = info["away_team"].replace(" ", "_")
            filename = f"{home}_vs_{away}.html"
            html = generate_game_report_html(game_id)
            await send_html_report(game_id, html, filename)

        # Send interactive "want to bet?" prompt after all HTML reports
        bot = Bot(token=TELEGRAM_BOT_TOKEN)
        async with bot:
            await send_want_to_bet(game_ids, bot)

    asyncio.run(_send_all())
    logger.info("notify_telegram: sent notifications for %d game(s)", len(game_ids))
    return {}
