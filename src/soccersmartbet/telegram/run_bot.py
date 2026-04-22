"""Entry point: start the SoccerSmartBet Telegram bot with daily scheduler."""
from __future__ import annotations

import asyncio
import logging

from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
)

from soccersmartbet.telegram.triggers import start_scheduler

if __name__ == "__main__":
    asyncio.run(start_scheduler())
