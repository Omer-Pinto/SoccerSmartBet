"""Unit tests for _parse_edate in fetch_winner_odds.

Verifies that winner.co.il's m_hour field (= kickoff - 1 minute) is corrected
to actual kickoff time by adding 1 minute.
"""
from __future__ import annotations

import pytest

from soccersmartbet.pre_gambling_flow.tools.game.fetch_winner_odds import _parse_edate
from soccersmartbet.utils.timezone import isr_datetime
from datetime import timedelta


@pytest.mark.parametrize(
    "e_date, m_hour, expected_hhmm, expected_date_str",
    [
        # Canonical case: 21:59 m_hour → 22:00 kickoff, same day
        (260408, "2159", "22:00", "2026-04-08"),
        # Regular offset: 21:44 → 21:45 same day
        (260408, "2144", "21:45", "2026-04-08"),
        # Midnight rollover: 23:59 → 00:00 next day (2026-04-09)
        (260408, "2359", "00:00", "2026-04-09"),
        # Sanity/uniformity: even a 22:00 input becomes 22:01.
        # winner always reports kickoff-1, so a true 22:00 input would never
        # appear in practice — but the +1 is applied uniformly to all winner
        # inputs by design.
        (260408, "2200", "22:01", "2026-04-08"),
    ],
)
def test_parse_edate_adds_one_minute(
    e_date: int, m_hour: str, expected_hhmm: str, expected_date_str: str
) -> None:
    result = _parse_edate(e_date, m_hour)
    assert result is not None

    expected_hour, expected_minute = map(int, expected_hhmm.split(":"))
    expected_year = int(expected_date_str[:4])
    expected_month = int(expected_date_str[5:7])
    expected_day = int(expected_date_str[8:10])
    expected_dt = isr_datetime(expected_year, expected_month, expected_day, expected_hour, expected_minute)

    from datetime import datetime
    parsed_dt = datetime.fromisoformat(result)
    assert parsed_dt == expected_dt


def test_parse_edate_returns_none_on_invalid_input() -> None:
    assert _parse_edate(0, "XXXX") is None
    assert _parse_edate(0, "") is None
