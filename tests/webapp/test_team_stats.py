"""Unit tests for GET /api/teams/{slug}/stats.

Covers:
  1. Atlético case — stored "Club Atlético de Madrid" (with accent + inserted word)
     resolves and returns matching bets.
  2. Unknown slug → 404 unknown_team.
  3. Resolved team with no matching bets → 404 not_found.
  4. Response JSON shape matches documented contract.

No DB is touched: get_cursor and team_registry module state are both mocked.
"""
from __future__ import annotations

import datetime
import importlib
from decimal import Decimal
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

# ---------------------------------------------------------------------------
# Registry state fixtures — injected before any import of the route module
# ---------------------------------------------------------------------------

# Minimal teams data that the registry would load from DB.
_TEAMS_DATA: list[dict] = [
    {
        "canonical_name": "Atletico Madrid",
        "short_name": "ATM",
        "aliases": [
            "Atletico",
            "Atlético Madrid",
            "Atlético de Madrid",
            "Club Atletico de Madrid",
            "ATM",
        ],
        "fotmob_id": None,
        "football_data_id": None,
        "winner_name_he": None,
        "league": "La Liga",
        "country": "Spain",
    },
    {
        "canonical_name": "Arsenal",
        "short_name": "ARS",
        "aliases": ["Arsenal FC", "The Gunners"],
        "fotmob_id": None,
        "football_data_id": None,
        "winner_name_he": None,
        "league": "Premier League",
        "country": "England",
    },
]


def _patch_registry(monkeypatch: pytest.MonkeyPatch) -> None:
    """Inject fake registry state so team_registry never hits the DB."""
    import soccersmartbet.team_registry as reg

    # Build the index the same way the real code does.
    idx = reg._build_index(_TEAMS_DATA)
    monkeypatch.setattr(reg, "_teams", _TEAMS_DATA)
    monkeypatch.setattr(reg, "_index", idx)
    monkeypatch.setattr(reg, "_loaded", True)


# ---------------------------------------------------------------------------
# Fake DB rows
# ---------------------------------------------------------------------------

_MATCH_DATE = datetime.date(2026, 4, 10)
_KICKOFF = datetime.time(20, 45)


def _make_row(
    bet_id: int,
    home_team: str,
    away_team: str,
    pnl: float | None = 10.0,
    stake: float = 50.0,
    odds: float = 2.1,
) -> tuple:
    """Return a tuple matching the SELECT column order in get_team_stats."""
    return (
        bet_id,           # 0  b.bet_id
        "user",           # 1  b.bettor
        "home",           # 2  b.prediction
        Decimal(str(stake)),  # 3  b.stake
        Decimal(str(odds)),   # 4  b.odds
        "win" if pnl and pnl > 0 else "loss",  # 5  b.result
        Decimal(str(pnl)) if pnl is not None else None,  # 6  b.pnl
        1000 + bet_id,    # 7  g.game_id
        home_team,        # 8  g.home_team
        away_team,        # 9  g.away_team
        _MATCH_DATE,      # 10 g.match_date
        _KICKOFF,         # 11 g.kickoff_time
        "La Liga",        # 12 g.league
        "home",           # 13 g.outcome
        2,                # 14 g.home_score
        1,                # 15 g.away_score
    )


# Rows returned by the mocked DB cursor: two Atletico bets + one Arsenal bet.
_DB_ROWS: list[tuple] = [
    # Stored with accent AND "Club ... de ..." prefix — the bug case.
    _make_row(1, "Club Atlético de Madrid", "Real Madrid", pnl=15.0),
    _make_row(2, "Barcelona", "Club Atlético de Madrid", pnl=-8.0),
    # Another team — must NOT appear in Atletico results.
    _make_row(3, "Arsenal FC", "Chelsea", pnl=5.0),
]

# A row for an Arsenal query with no settled bets (pnl=None).
_DB_ROWS_ARSENAL_UNSETTLED: list[tuple] = [
    _make_row(10, "Arsenal FC", "Chelsea", pnl=None),
]


def _make_client(monkeypatch: pytest.MonkeyPatch, db_rows: list[tuple]) -> TestClient:
    """Build a TestClient with registry and DB mocked."""
    _patch_registry(monkeypatch)

    # Mock get_cursor as a context manager that returns a cursor with fetchall.
    mock_cursor = MagicMock()
    mock_cursor.fetchall.return_value = db_rows

    mock_cm = MagicMock()
    mock_cm.__enter__ = MagicMock(return_value=mock_cursor)
    mock_cm.__exit__ = MagicMock(return_value=False)

    mock_get_cursor = MagicMock(return_value=mock_cm)

    # Patch get_cursor in the stats route module.
    monkeypatch.setattr(
        "soccersmartbet.webapp.routes.stats.get_cursor",
        mock_get_cursor,
    )

    # Build a minimal FastAPI app with just the stats router.
    from soccersmartbet.webapp.routes.stats import router

    app = FastAPI()
    app.include_router(router)
    return TestClient(app, raise_server_exceptions=False)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestGetTeamStats:
    """Tests for GET /api/teams/{slug}/stats."""

    def test_atletico_accented_stored_name_resolves(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Stored "Club Atlético de Madrid" (accent + inserted word) must match.

        This is the primary regression test.  The slug arrives URL-encoded as
        "Club Atlético de Madrid" (or the canonical "Atletico Madrid") and the
        DB stores the raw string with accent.  The old ILIKE approach failed
        because "Atletico Madrid" is not a substring of "Club Atlético de Madrid".
        The fix uses normalize_team_name on both sides and set membership.
        """
        client = _make_client(monkeypatch, _DB_ROWS)
        response = client.get("/api/teams/Club%20Atl%C3%A9tico%20de%20Madrid/stats")

        assert response.status_code == 200, response.text
        data = response.json()

        # Two bets involve Atletico (rows 0 and 1); Arsenal bet must be excluded.
        assert data["total_bets"] == 2
        assert data["team_name"] == "Atletico Madrid"

        home_teams = {b["home_team"] for b in data["bets"]}
        away_teams = {b["away_team"] for b in data["bets"]}
        assert "Club Atlético de Madrid" in home_teams | away_teams
        assert "Arsenal FC" not in home_teams | away_teams

    def test_canonical_slug_also_works(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Slug using the canonical name itself ("Atletico Madrid") must match."""
        client = _make_client(monkeypatch, _DB_ROWS)
        response = client.get("/api/teams/Atletico%20Madrid/stats")

        assert response.status_code == 200, response.text
        data = response.json()
        assert data["total_bets"] == 2
        assert data["team_name"] == "Atletico Madrid"

    def test_unknown_slug_returns_404_unknown_team(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A slug that cannot be resolved must return 404 with error=unknown_team."""
        client = _make_client(monkeypatch, _DB_ROWS)
        response = client.get("/api/teams/XYZ_Does_Not_Exist_9999/stats")

        assert response.status_code == 404, response.text
        detail = response.json().get("detail", {})
        assert detail.get("error") == "unknown_team"

    def test_resolved_team_no_bets_returns_404_not_found(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A valid slug that resolves but has no matching bets → 404 not_found.

        We use Arsenal as the slug but populate the DB with only Atletico rows
        so the filter produces an empty list after Python-side filtering.
        """
        # Only Atletico rows — Arsenal resolves fine but yields no filtered rows.
        client = _make_client(monkeypatch, _DB_ROWS[:2])
        response = client.get("/api/teams/Arsenal/stats")

        assert response.status_code == 404, response.text
        detail = response.json().get("detail", {})
        assert detail.get("error") == "not_found"

    def test_response_shape(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Response JSON must contain all documented top-level keys."""
        client = _make_client(monkeypatch, _DB_ROWS)
        response = client.get("/api/teams/Atletico%20Madrid/stats")

        assert response.status_code == 200
        data = response.json()
        for key in (
            "team_name",
            "total_bets",
            "total_stake",
            "total_pnl",
            "win_rate",
            "notable_games",
            "bets",
        ):
            assert key in data, f"Missing key: {key}"

    def test_pnl_and_win_rate_computed_correctly(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Aggregate P&L and win_rate must reflect only the matched rows.

        Rows: pnl=15.0 (win) and pnl=-8.0 (loss).  Total=7.0, win_rate=0.5.
        """
        client = _make_client(monkeypatch, _DB_ROWS)
        response = client.get("/api/teams/Atletico%20Madrid/stats")

        assert response.status_code == 200
        data = response.json()
        assert abs(data["total_pnl"] - 7.0) < 0.01
        assert data["win_rate"] == pytest.approx(0.5)

    def test_notable_games_capped_at_five(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """notable_games must contain at most 5 entries."""
        # Build 7 Atletico rows.
        many_rows = [
            _make_row(i, "Club Atlético de Madrid", "Opponent", pnl=float(i * 10))
            for i in range(1, 8)
        ]
        client = _make_client(monkeypatch, many_rows)
        response = client.get("/api/teams/Atletico%20Madrid/stats")

        assert response.status_code == 200
        assert len(response.json()["notable_games"]) <= 5
