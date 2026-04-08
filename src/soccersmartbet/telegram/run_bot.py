"""Entry point: start the SoccerSmartBet Telegram bot with daily scheduler."""
from __future__ import annotations

from soccersmartbet.telegram.triggers import start_scheduler

if __name__ == "__main__":
    start_scheduler()
