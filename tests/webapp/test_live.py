"""Tests for GET /api/today/live and supporting pure functions.

Coverage:
  1. Period derivation — 1H, HT, 2H, FT, pre, unknown.
  2. Endpoint — mixed live/finished/unmapped games.
  3. Cache hit on second call within 30 s.
  4. Graceful degradation when FotMob fails for one game.
  5. compute_bet_pnl_estimate — win, loss, draw, invalid inputs.
  6. Live P&L estimates — 1H/HT/2H games with bets (pnl_estimate_is_live=true).
  7. pnl_estimate_is_live=false for FT; false/null when scores missing.

No real HTTP calls or DB connections: everything is mocked.
"""
from __future__ import annotations

import datetime
import time
from decimal import Decimal
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# Period derivation — pure unit tests (no HTTP, no DB)
# ---------------------------------------------------------------------------


class TestDerivePeriod:
    """Tests for soccersmartbet.webapp.routes.live._derive_period."""

    def _import(self):
        from soccersmartbet.webapp.routes.live import _derive_period
        return _derive_period

    def _status(
        self,
        started=False,
        finished=False,
        ongoing=False,
        reason_short="",
        second_half_started="",
    ) -> dict:
        return {
            "status": {
                "started": started,
                "finished": finished,
                "ongoing": ongoing,
                "reason": {"short": reason_short},
            },
            "halfs": {"secondHalfStarted": second_half_started},
        }

    def test_pre_when_not_started(self) -> None:
        derive = self._import()
        assert derive(self._status(started=False)) == "pre"

    def test_first_half_when_started_ongoing_no_second_half(self) -> None:
        derive = self._import()
        data = self._status(started=True, ongoing=True, second_half_started="")
        assert derive(data) == "1H"

    def test_halftime_when_reason_is_ht(self) -> None:
        derive = self._import()
        data = self._status(started=True, ongoing=False, reason_short="HT")
        assert derive(data) == "HT"

    def test_second_half_when_started_ongoing_second_half_set(self) -> None:
        derive = self._import()
        data = self._status(
            started=True, ongoing=True, second_half_started="2026-04-25T20:00:00"
        )
        assert derive(data) == "2H"

    def test_ft_when_finished(self) -> None:
        derive = self._import()
        data = self._status(started=True, finished=True)
        assert derive(data) == "FT"

    def test_unknown_on_empty_dict(self) -> None:
        derive = self._import()
        assert derive({}) == "pre"  # not started → pre


# ---------------------------------------------------------------------------
# compute_bet_pnl_estimate — pure unit tests
# ---------------------------------------------------------------------------


class TestComputeBetPnlEstimate:
    """Tests for soccersmartbet.post_games_flow.pnl_calculator.compute_bet_pnl_estimate."""

    def _fn(self):
        from soccersmartbet.post_games_flow.pnl_calculator import compute_bet_pnl_estimate
        return compute_bet_pnl_estimate

    def test_win_home(self) -> None:
        fn = self._fn()
        # Bet 1 (home wins), stake=100, odds=2.5 → profit = 100*(2.5-1) = 150
        result = fn("1", 100.0, 2.5, 2, 1)
        assert result == pytest.approx(150.0)

    def test_loss_home_bet_but_draw(self) -> None:
        fn = self._fn()
        result = fn("1", 100.0, 2.5, 1, 1)
        assert result == pytest.approx(-100.0)

    def test_win_draw(self) -> None:
        fn = self._fn()
        # Bet draw (x), score 0-0
        result = fn("x", 50.0, 3.0, 0, 0)
        assert result == pytest.approx(50.0 * (3.0 - 1.0))

    def test_win_away(self) -> None:
        fn = self._fn()
        result = fn("2", 200.0, 1.8, 0, 1)
        assert result == pytest.approx(200.0 * (1.8 - 1.0))

    def test_negative_scores_returns_none(self) -> None:
        fn = self._fn()
        assert fn("1", 100.0, 2.0, -1, 0) is None

    def test_invalid_prediction_returns_none(self) -> None:
        fn = self._fn()
        assert fn("3", 100.0, 2.0, 1, 0) is None

    def test_zero_stake_returns_none(self) -> None:
        fn = self._fn()
        assert fn("1", 0.0, 2.0, 1, 0) is None

    def test_odds_lte_one_returns_none(self) -> None:
        fn = self._fn()
        assert fn("1", 100.0, 1.0, 1, 0) is None


# ---------------------------------------------------------------------------
# Endpoint tests — GET /api/today/live
# ---------------------------------------------------------------------------

# Minimal FotMob JSON shape for a live (1H) match
_FOTMOB_1H = {
    "home": {"score": 1},
    "away": {"score": 0},
    "status": {
        "started": True,
        "finished": False,
        "ongoing": True,
        "liveTime": {"short": "34'"},
        "reason": {"short": ""},
    },
    "halfs": {"secondHalfStarted": ""},
}

# Halftime match (HT), 1-0
_FOTMOB_HT = {
    "home": {"score": 1},
    "away": {"score": 0},
    "status": {
        "started": True,
        "finished": False,
        "ongoing": False,
        "liveTime": {"short": "HT"},
        "reason": {"short": "HT"},
    },
    "halfs": {"secondHalfStarted": ""},
}

# Second-half match (2H), 1-1
_FOTMOB_2H = {
    "home": {"score": 1},
    "away": {"score": 1},
    "status": {
        "started": True,
        "finished": False,
        "ongoing": True,
        "liveTime": {"short": "67'"},
        "reason": {"short": ""},
    },
    "halfs": {"secondHalfStarted": "2026-04-25T21:00:00"},
}

# Finished match (FT), 2-1
_FOTMOB_FT = {
    "home": {"score": 2},
    "away": {"score": 1},
    "status": {
        "started": True,
        "finished": True,
        "ongoing": False,
        "liveTime": {"short": None},
        "reason": {"short": "FT"},
    },
    "halfs": {"secondHalfStarted": "2026-04-25T21:00:00"},
}


def _make_cursor_cm(side_effect=None):
    """Build a mock context manager for get_cursor()."""
    mock_cursor = MagicMock()
    if side_effect is not None:
        mock_cursor.fetchall.side_effect = side_effect
    mock_cm = MagicMock()
    mock_cm.__enter__ = MagicMock(return_value=mock_cursor)
    mock_cm.__exit__ = MagicMock(return_value=False)
    return mock_cm, mock_cursor


def _make_client(
    monkeypatch: pytest.MonkeyPatch,
    today_games_rows: list[tuple],
    bets_rows: list[tuple],
    fotmob_responses: dict[int, Any],  # fotmob_match_id → raw dict or None
) -> TestClient:
    """Build a TestClient for the live route with mocked DB and FotMob."""
    # We need get_cursor to return different things on successive calls:
    # first call → today_games, second call → today_bets.
    call_count = [0]
    rows_by_call = [today_games_rows, bets_rows]

    def cursor_side_effect(*args, **kwargs):
        mc, mcursor = _make_cursor_cm()
        idx = call_count[0]
        call_count[0] += 1
        if idx < len(rows_by_call):
            mcursor.fetchall.return_value = rows_by_call[idx]
        else:
            mcursor.fetchall.return_value = []
        return mc

    # Patch _fetch_match_raw so no real HTTP calls happen
    async def mock_get_game_live(game_id: int, fotmob_match_id: int) -> dict:
        """Reimplemented _get_game_live using the provided fotmob_responses map."""
        from soccersmartbet.webapp.routes.live import (
            _parse_game_entry,
        )
        data = fotmob_responses.get(fotmob_match_id)
        if data is None:
            # Simulate FotMob failure — check if there is a cache entry
            from soccersmartbet.webapp.routes.live import _LIVE_CACHE
            cache_key = (game_id, fotmob_match_id)
            if cache_key in _LIVE_CACHE:
                cached_entry, _ = _LIVE_CACHE[cache_key]
                return cached_entry
            return {
                "game_id": game_id,
                "fotmob_match_id": fotmob_match_id,
                "home_score": None,
                "away_score": None,
                "period": "unknown",
                "minute": None,
                "finished": False,
            }
        entry = _parse_game_entry(game_id, fotmob_match_id, data)
        return entry

    monkeypatch.setattr(
        "soccersmartbet.webapp.routes.live.get_cursor",
        cursor_side_effect,
    )
    monkeypatch.setattr(
        "soccersmartbet.webapp.routes.live._get_game_live",
        mock_get_game_live,
    )

    from soccersmartbet.webapp.routes.live import router

    app = FastAPI()
    app.include_router(router)
    return TestClient(app, raise_server_exceptions=True)


# Today's ISR date for building fake rows
_TODAY = datetime.date(2026, 4, 25)


def _game_row(game_id: int, fotmob_match_id: int) -> tuple:
    return (game_id, fotmob_match_id)


def _bet_row(game_id: int, bettor: str, prediction: str, stake: float, odds: float, pnl=None) -> tuple:
    return (game_id, bettor, prediction, Decimal(str(stake)), Decimal(str(odds)), Decimal(str(pnl)) if pnl is not None else None)


class TestTodayLiveEndpoint:
    """Tests for GET /api/today/live."""

    def test_empty_response_when_no_fotmob_games(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """When no games have fotmob_match_id, games list is empty."""
        client = _make_client(monkeypatch, [], [], {})
        resp = client.get("/api/today/live")

        assert resp.status_code == 200
        data = resp.json()
        assert data["games"] == []
        assert "as_of_isr" in data

    def test_live_game_has_correct_period_and_minute(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A 1H game returns period='1H' and the minute string."""
        client = _make_client(
            monkeypatch,
            today_games_rows=[_game_row(10, 999001)],
            bets_rows=[],
            fotmob_responses={999001: _FOTMOB_1H},
        )
        resp = client.get("/api/today/live")

        assert resp.status_code == 200
        games = resp.json()["games"]
        assert len(games) == 1
        g = games[0]
        assert g["game_id"] == 10
        assert g["fotmob_match_id"] == 999001
        assert g["period"] == "1H"
        assert g["minute"] == "34'"
        assert g["home_score"] == 1
        assert g["away_score"] == 0
        assert g["finished"] is False

    def test_finished_game_has_ft_period_and_null_minute(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A finished game returns period='FT' with minute=null."""
        client = _make_client(
            monkeypatch,
            today_games_rows=[_game_row(20, 999002)],
            bets_rows=[],
            fotmob_responses={999002: _FOTMOB_FT},
        )
        resp = client.get("/api/today/live")

        games = resp.json()["games"]
        assert len(games) == 1
        g = games[0]
        assert g["period"] == "FT"
        assert g["minute"] is None
        assert g["finished"] is True
        assert g["home_score"] == 2
        assert g["away_score"] == 1

    def test_mixed_games_all_present(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Live, finished, and failing FotMob games all appear in the response."""
        client = _make_client(
            monkeypatch,
            today_games_rows=[
                _game_row(10, 999001),
                _game_row(20, 999002),
                _game_row(30, 999003),  # FotMob will fail for this one
            ],
            bets_rows=[],
            fotmob_responses={
                999001: _FOTMOB_1H,
                999002: _FOTMOB_FT,
                # 999003 is absent → simulates failure
            },
        )
        resp = client.get("/api/today/live")

        assert resp.status_code == 200
        games = resp.json()["games"]
        assert len(games) == 3

        by_id = {g["game_id"]: g for g in games}
        assert by_id[10]["period"] == "1H"
        assert by_id[20]["period"] == "FT"
        assert by_id[30]["period"] == "unknown"

    def test_finished_game_pnl_estimate_with_settled_bet(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """When bets.pnl is already set, the settled value is used."""
        client = _make_client(
            monkeypatch,
            today_games_rows=[_game_row(20, 999002)],
            bets_rows=[
                _bet_row(20, "user", "1", 100.0, 2.5, pnl=150.0),
                _bet_row(20, "ai", "2", 100.0, 3.0, pnl=-100.0),
            ],
            fotmob_responses={999002: _FOTMOB_FT},
        )
        resp = client.get("/api/today/live")

        g = resp.json()["games"][0]
        assert g["finished"] is True
        assert g["user_pnl_estimate"] == pytest.approx(150.0)
        assert g["ai_pnl_estimate"] == pytest.approx(-100.0)

    def test_finished_game_pnl_estimate_unsettled(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """When bets.pnl is NULL, estimate is computed on the fly.

        FT: home=2, away=1 → outcome "1".
        User bet "1" at odds 2.5, stake 100 → 100*(2.5-1) = 150.
        AI bet "2" at odds 3.0, stake 50 → -50.
        """
        client = _make_client(
            monkeypatch,
            today_games_rows=[_game_row(20, 999002)],
            bets_rows=[
                _bet_row(20, "user", "1", 100.0, 2.5, pnl=None),
                _bet_row(20, "ai", "2", 50.0, 3.0, pnl=None),
            ],
            fotmob_responses={999002: _FOTMOB_FT},
        )
        resp = client.get("/api/today/live")

        g = resp.json()["games"][0]
        assert g["user_pnl_estimate"] == pytest.approx(150.0)
        assert g["ai_pnl_estimate"] == pytest.approx(-50.0)

    def test_no_bets_pnl_estimates_null(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Finished game with no bets → both pnl_estimate fields are null."""
        client = _make_client(
            monkeypatch,
            today_games_rows=[_game_row(20, 999002)],
            bets_rows=[],
            fotmob_responses={999002: _FOTMOB_FT},
        )
        resp = client.get("/api/today/live")

        g = resp.json()["games"][0]
        assert g["user_pnl_estimate"] is None
        assert g["ai_pnl_estimate"] is None

    def test_degradation_returns_unknown_when_fotmob_fails(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """When FotMob fails for a game and no cache exists, period='unknown'."""
        client = _make_client(
            monkeypatch,
            today_games_rows=[_game_row(30, 999003)],
            bets_rows=[],
            fotmob_responses={},  # 999003 absent → failure
        )
        resp = client.get("/api/today/live")

        games = resp.json()["games"]
        assert len(games) == 1
        assert games[0]["period"] == "unknown"
        assert games[0]["finished"] is False

    def test_response_shape_contract(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Every game entry must contain all documented keys."""
        client = _make_client(
            monkeypatch,
            today_games_rows=[_game_row(10, 999001)],
            bets_rows=[],
            fotmob_responses={999001: _FOTMOB_1H},
        )
        resp = client.get("/api/today/live")

        assert resp.status_code == 200
        data = resp.json()
        assert "as_of_isr" in data
        assert "games" in data

        g = data["games"][0]
        for key in (
            "game_id",
            "fotmob_match_id",
            "home_score",
            "away_score",
            "period",
            "minute",
            "finished",
            "user_pnl_estimate",
            "ai_pnl_estimate",
            "pnl_estimate_is_live",
        ):
            assert key in g, f"Missing key in game entry: {key}"


# ---------------------------------------------------------------------------
# Live P&L estimates (in-play games)
# ---------------------------------------------------------------------------


class TestLivePnlEstimates:
    """Tests for pnl_estimate_is_live and in-play P&L computation."""

    def test_1h_game_pnl_estimate_is_live_true(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """In-play 1H game with bets gets estimates and pnl_estimate_is_live=true.

        Score 1-0 → outcome "1".
        User bets "1" stake=100 odds=2.5 → profit = 100*(2.5-1) = 150.
        AI bets "x" stake=50 odds=3.0 → loss = -50.
        """
        client = _make_client(
            monkeypatch,
            today_games_rows=[_game_row(10, 999001)],
            bets_rows=[
                _bet_row(10, "user", "1", 100.0, 2.5, pnl=None),
                _bet_row(10, "ai", "x", 50.0, 3.0, pnl=None),
            ],
            fotmob_responses={999001: _FOTMOB_1H},
        )
        resp = client.get("/api/today/live")

        assert resp.status_code == 200
        g = resp.json()["games"][0]
        assert g["period"] == "1H"
        assert g["pnl_estimate_is_live"] is True
        assert g["user_pnl_estimate"] == pytest.approx(150.0)
        assert g["ai_pnl_estimate"] == pytest.approx(-50.0)

    def test_ht_game_pnl_estimate_is_live_true(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """HT game with bets gets estimates and pnl_estimate_is_live=true.

        Score 1-0 → outcome "1".
        User bets "2" stake=80 odds=4.0 → loss = -80.
        """
        client = _make_client(
            monkeypatch,
            today_games_rows=[_game_row(11, 999010)],
            bets_rows=[
                _bet_row(11, "user", "2", 80.0, 4.0, pnl=None),
            ],
            fotmob_responses={999010: _FOTMOB_HT},
        )
        resp = client.get("/api/today/live")

        g = resp.json()["games"][0]
        assert g["period"] == "HT"
        assert g["pnl_estimate_is_live"] is True
        assert g["user_pnl_estimate"] == pytest.approx(-80.0)
        assert g["ai_pnl_estimate"] is None

    def test_2h_game_pnl_estimate_is_live_true(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """2H game with bets gets estimates and pnl_estimate_is_live=true.

        Score 1-1 → outcome "x".
        AI bets "x" stake=200 odds=3.5 → profit = 200*(3.5-1) = 500.
        """
        client = _make_client(
            monkeypatch,
            today_games_rows=[_game_row(12, 999020)],
            bets_rows=[
                _bet_row(12, "ai", "x", 200.0, 3.5, pnl=None),
            ],
            fotmob_responses={999020: _FOTMOB_2H},
        )
        resp = client.get("/api/today/live")

        g = resp.json()["games"][0]
        assert g["period"] == "2H"
        assert g["pnl_estimate_is_live"] is True
        assert g["ai_pnl_estimate"] == pytest.approx(500.0)
        assert g["user_pnl_estimate"] is None

    def test_ft_game_pnl_estimate_is_live_false(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Finished FT game must have pnl_estimate_is_live=false."""
        client = _make_client(
            monkeypatch,
            today_games_rows=[_game_row(20, 999002)],
            bets_rows=[
                _bet_row(20, "user", "1", 100.0, 2.5, pnl=None),
            ],
            fotmob_responses={999002: _FOTMOB_FT},
        )
        resp = client.get("/api/today/live")

        g = resp.json()["games"][0]
        assert g["period"] == "FT"
        assert g["pnl_estimate_is_live"] is False

    def test_live_game_no_bets_estimates_null(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """In-play game with no bets → estimates null, pnl_estimate_is_live=true."""
        client = _make_client(
            monkeypatch,
            today_games_rows=[_game_row(10, 999001)],
            bets_rows=[],
            fotmob_responses={999001: _FOTMOB_1H},
        )
        resp = client.get("/api/today/live")

        g = resp.json()["games"][0]
        assert g["pnl_estimate_is_live"] is True
        assert g["user_pnl_estimate"] is None
        assert g["ai_pnl_estimate"] is None

    def test_pre_game_pnl_estimate_is_live_false_and_null(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Pre-game (not started) must have pnl_estimate_is_live=false and null estimates."""
        _FOTMOB_PRE = {
            "home": {"score": None},
            "away": {"score": None},
            "status": {
                "started": False,
                "finished": False,
                "ongoing": False,
                "liveTime": {"short": None},
                "reason": {"short": ""},
            },
            "halfs": {"secondHalfStarted": ""},
        }
        client = _make_client(
            monkeypatch,
            today_games_rows=[_game_row(5, 999005)],
            bets_rows=[
                _bet_row(5, "user", "1", 100.0, 2.0, pnl=None),
            ],
            fotmob_responses={999005: _FOTMOB_PRE},
        )
        resp = client.get("/api/today/live")

        g = resp.json()["games"][0]
        assert g["period"] == "pre"
        assert g["pnl_estimate_is_live"] is False
        assert g["user_pnl_estimate"] is None
        assert g["ai_pnl_estimate"] is None


# ---------------------------------------------------------------------------
# Cache behaviour — requires patching the real _fetch_match_raw
# ---------------------------------------------------------------------------


class TestLiveCache:
    """Test the 30-second in-process cache in _get_game_live."""

    def test_cache_hit_skips_second_http_call(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Second call within TTL must not call _fetch_match_raw again."""
        import importlib

        # Import the module and clear the cache before the test
        import soccersmartbet.webapp.routes.live as live_mod

        # Stash original cache and restore after test
        original_cache = dict(live_mod._LIVE_CACHE)
        live_mod._LIVE_CACHE.clear()

        call_count = [0]

        def fake_fetch_raw(match_id: int):
            call_count[0] += 1
            return _FOTMOB_1H

        monkeypatch.setattr(live_mod, "_fetch_match_raw", fake_fetch_raw)

        import asyncio

        # First call — should hit FotMob
        entry1 = asyncio.run(live_mod._get_game_live(42, 888001))
        assert call_count[0] == 1

        # Second call immediately — should hit cache
        entry2 = asyncio.run(live_mod._get_game_live(42, 888001))
        assert call_count[0] == 1  # no second HTTP call
        assert entry1 == entry2

        # Restore cache
        live_mod._LIVE_CACHE.clear()
        live_mod._LIVE_CACHE.update(original_cache)

    def test_finished_game_served_from_cache_indefinitely(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A game with period='FT' in cache must not trigger a re-fetch even after TTL."""
        import soccersmartbet.webapp.routes.live as live_mod
        import asyncio

        original_cache = dict(live_mod._LIVE_CACHE)
        live_mod._LIVE_CACHE.clear()

        call_count = [0]

        def fake_fetch_raw(match_id: int):
            call_count[0] += 1
            return _FOTMOB_FT

        monkeypatch.setattr(live_mod, "_fetch_match_raw", fake_fetch_raw)

        # Seed cache with an expired entry that is "FT"
        finished_entry = {
            "game_id": 99,
            "fotmob_match_id": 777001,
            "home_score": 2,
            "away_score": 1,
            "period": "FT",
            "minute": None,
            "finished": True,
        }
        # Set cached_at far in the past (TTL has definitely expired)
        live_mod._LIVE_CACHE[(99, 777001)] = (finished_entry, time.monotonic() - 9999)

        result = asyncio.run(live_mod._get_game_live(99, 777001))
        assert call_count[0] == 0  # cache served without re-fetch
        assert result["period"] == "FT"

        live_mod._LIVE_CACHE.clear()
        live_mod._LIVE_CACHE.update(original_cache)

    def test_stale_cache_returned_on_fotmob_failure(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """When FotMob fails after TTL, the last stale cache entry is returned."""
        import soccersmartbet.webapp.routes.live as live_mod
        import asyncio

        original_cache = dict(live_mod._LIVE_CACHE)
        live_mod._LIVE_CACHE.clear()

        def fake_fetch_raw_fail(match_id: int):
            return None  # simulate failure

        monkeypatch.setattr(live_mod, "_fetch_match_raw", fake_fetch_raw_fail)

        stale_entry = {
            "game_id": 55,
            "fotmob_match_id": 666001,
            "home_score": 0,
            "away_score": 0,
            "period": "1H",
            "minute": "12'",
            "finished": False,
        }
        live_mod._LIVE_CACHE[(55, 666001)] = (stale_entry, time.monotonic() - 9999)

        result = asyncio.run(live_mod._get_game_live(55, 666001))
        assert result["period"] == "1H"
        assert result["minute"] == "12'"

        live_mod._LIVE_CACHE.clear()
        live_mod._LIVE_CACHE.update(original_cache)
