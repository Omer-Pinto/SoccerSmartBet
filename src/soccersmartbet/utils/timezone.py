from __future__ import annotations

from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo

ISR_TZ = ZoneInfo("Asia/Jerusalem")


def utc_to_isr(dt_or_str: datetime | str) -> datetime:
    if isinstance(dt_or_str, str):
        dt_or_str = datetime.fromisoformat(dt_or_str.replace("Z", "+00:00"))
    if dt_or_str.tzinfo is None:
        dt_or_str = dt_or_str.replace(tzinfo=timezone.utc)
    return dt_or_str.astimezone(ISR_TZ)


def now_isr() -> datetime:
    return datetime.now(tz=ISR_TZ)


def format_isr_time(dt: datetime, fmt: str = "%H:%M") -> str:
    return dt.strftime(fmt)


def format_isr_date(dt: datetime, fmt: str = "%Y-%m-%d") -> str:
    return dt.strftime(fmt)


def today_isr() -> date:
    """Return today's date in the ISR timezone (Asia/Jerusalem).

    Safe replacement for ``date.today()`` which uses the system-local clock
    (UTC in Docker). Between 22:00–23:59 ISR the two values diverge.
    """
    return now_isr().date()


def isr_datetime(
    year: int,
    month: int,
    day: int,
    hour: int = 0,
    minute: int = 0,
    second: int = 0,
) -> datetime:
    """Construct a timezone-aware datetime in the ISR timezone.

    Use this instead of ``datetime(year, month, day, …, tzinfo=ISR_TZ)``
    directly, so that grep for ``datetime(`` inside application code stays
    clean and the intent (ISR wall-clock time) is explicit.

    Args:
        year: Four-digit year.
        month: Month (1–12).
        day: Day of month (1–31).
        hour: Hour (0–23). Defaults to 0.
        minute: Minute (0–59). Defaults to 0.
        second: Second (0–59). Defaults to 0.

    Returns:
        A timezone-aware :class:`datetime` in ``Asia/Jerusalem``.
    """
    return datetime(year, month, day, hour, minute, second, tzinfo=ISR_TZ)
