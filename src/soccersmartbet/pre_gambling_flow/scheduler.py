"""APScheduler-based trigger for the Pre-Gambling Flow.

This module is intentionally side-effect free: it does not start a scheduler on import.
Callers are expected to load configuration, build the scheduler with an injected job
function, and then start/shutdown it explicitly.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import yaml
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

DEFAULT_CONFIG_PATH = Path(__file__).resolve().parents[3] / "config" / "config.yaml"
DEFAULT_TIMEZONE = "UTC"
DEFAULT_DAILY_TIME = "14:00"
DEFAULT_JOB_ID = "pre_gambling_daily"


def load_config(path: str | Path = DEFAULT_CONFIG_PATH) -> dict[str, Any]:
    """Load YAML configuration from `config/config.yaml`.

    Args:
        path: Path to a YAML config file.

    Returns:
        Parsed config as a dictionary.

    Raises:
        FileNotFoundError: If the config file does not exist.
        ValueError: If the parsed YAML is not a mapping.
    """
    config_path = Path(path)
    raw = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    if raw is None:
        return {}
    if not isinstance(raw, dict):
        raise ValueError(f"Config must be a YAML mapping at top-level, got: {type(raw).__name__}")
    return raw


def _parse_daily_time(value: Any) -> tuple[int, int]:
    if not isinstance(value, str):
        raise ValueError(f"scheduler.daily_time must be a string in 'HH:MM' format, got: {type(value).__name__}")

    parts = value.strip().split(":")
    if len(parts) != 2:
        raise ValueError(f"scheduler.daily_time must be in 'HH:MM' 24h format, got: {value!r}")

    try:
        hour = int(parts[0])
        minute = int(parts[1])
    except ValueError as exc:
        raise ValueError(f"scheduler.daily_time must be numeric 'HH:MM', got: {value!r}") from exc

    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        raise ValueError(f"scheduler.daily_time must be a valid 24h time, got: {value!r}")

    return hour, minute


def build_scheduler(
    config: dict[str, Any],
    job_func: Callable[[], Any],
) -> BackgroundScheduler:
    """Build a scheduler instance with a single daily cron job.

    The job calls `job_func`, which is injected by the caller for testability.

    If `scheduler.enabled` is false, the scheduler is created but no job is registered.

    Args:
        config: Parsed configuration dict.
        job_func: Callable invoked by APScheduler.

    Returns:
        A `BackgroundScheduler` instance (not started).
    """
    scheduler_config = (config or {}).get("scheduler", {})
    if scheduler_config is None:
        scheduler_config = {}
    if not isinstance(scheduler_config, dict):
        raise ValueError(f"scheduler config must be a mapping, got: {type(scheduler_config).__name__}")

    enabled = bool(scheduler_config.get("enabled", True))
    timezone_name = str(scheduler_config.get("timezone", DEFAULT_TIMEZONE) or DEFAULT_TIMEZONE)
    daily_time = scheduler_config.get("daily_time", DEFAULT_DAILY_TIME)

    tzinfo = ZoneInfo(timezone_name)
    scheduler = BackgroundScheduler(timezone=tzinfo)

    if enabled:
        hour, minute = _parse_daily_time(daily_time)
        trigger = CronTrigger(hour=hour, minute=minute, timezone=tzinfo)
        scheduler.add_job(
            job_func,
            trigger=trigger,
            id=DEFAULT_JOB_ID,
            name="Pre-Gambling Flow Daily Trigger",
            replace_existing=True,
            max_instances=1,
            coalesce=True,
        )

    return scheduler


def start_scheduler(scheduler: BackgroundScheduler) -> None:
    """Start a built scheduler."""
    scheduler.start()


def shutdown_scheduler(scheduler: BackgroundScheduler) -> None:
    """Shutdown a started scheduler."""
    scheduler.shutdown(wait=False)
