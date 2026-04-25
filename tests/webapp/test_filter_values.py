"""Unit tests for GET /api/filter/values?key=<dsl_key>.

Covers:
  1. Enum key (league) returns sorted unique list.
  2. Enum key (team) returns sorted unique list (union of home/away).
  3. Enum key (bettor) returns sorted unique list.
  4. Enum keys (outcome, prediction, result) return the canonical alias set
     without any DB hit.
  5. Numeric key (stake) returns min/max dict.
  6. Numeric key (odds) returns min/max dict.
  7. Date key (date) returns min/max YYYY-MM-DD strings.
  8. Month key returns sorted-desc YYYY-MM list.
  9. Unknown key returns HTTP 400 with expected detail message.
  10. Cache hit: second call does NOT invoke the DB fetcher again.
  11. fresh=1 bypasses cache and re-queries.

No live DB is touched — get_cursor is fully mocked.
"""
from __future__ import annotations

import datetime
from decimal import Decimal
from unittest.mock import MagicMock, call, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_cursor_cm(fetchall_return=None, fetchone_return=None):
    """Return a context-manager mock for get_cursor whose cursor returns
    the given values from fetchall / fetchone."""
    mock_cursor = MagicMock()
    mock_cursor.fetchall.return_value = fetchall_return or []
    mock_cursor.fetchone.return_value = fetchone_return

    mock_cm = MagicMock()
    mock_cm.__enter__ = MagicMock(return_value=mock_cursor)
    mock_cm.__exit__ = MagicMock(return_value=False)
    return mock_cm, mock_cursor


def _make_client(monkeypatch: pytest.MonkeyPatch, cursor_cm=None) -> TestClient:
    """Build a TestClient backed by the filter_values router with DB mocked."""
    # Clear the module-level cache so each test starts clean.
    import soccersmartbet.webapp.routes.filter_values as fv_module
    fv_module._cache.clear()

    if cursor_cm is not None:
        monkeypatch.setattr(
            "soccersmartbet.webapp.routes.filter_values.get_cursor",
            MagicMock(return_value=cursor_cm),
        )

    from soccersmartbet.webapp.routes.filter_values import router
    app = FastAPI()
    app.include_router(router)
    return TestClient(app, raise_server_exceptions=False)


# ---------------------------------------------------------------------------
# 1. Enum key: league
# ---------------------------------------------------------------------------


class TestLeagueKey:
    def test_returns_sorted_unique_list(self, monkeypatch: pytest.MonkeyPatch) -> None:
        rows = [("Bundesliga",), ("La Liga",), ("Premier League",)]
        cm, _ = _make_cursor_cm(fetchall_return=rows)
        client = _make_client(monkeypatch, cm)

        resp = client.get("/api/filter/values?key=league")
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["key"] == "league"
        assert data["kind"] == "enum"
        assert data["values"] == ["Bundesliga", "La Liga", "Premier League"]

    def test_empty_table_returns_empty_list(self, monkeypatch: pytest.MonkeyPatch) -> None:
        cm, _ = _make_cursor_cm(fetchall_return=[])
        client = _make_client(monkeypatch, cm)

        resp = client.get("/api/filter/values?key=league")
        assert resp.status_code == 200
        assert resp.json()["values"] == []


# ---------------------------------------------------------------------------
# 2. Enum key: team
# ---------------------------------------------------------------------------


class TestTeamKey:
    def test_returns_sorted_unique_list(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # DB returns union of home_team + away_team, already distinct + ordered.
        rows = [("Arsenal",), ("Barcelona",), ("Real Madrid",)]
        cm, _ = _make_cursor_cm(fetchall_return=rows)
        client = _make_client(monkeypatch, cm)

        resp = client.get("/api/filter/values?key=team")
        assert resp.status_code == 200
        data = resp.json()
        assert data["key"] == "team"
        assert data["kind"] == "enum"
        assert data["values"] == ["Arsenal", "Barcelona", "Real Madrid"]


# ---------------------------------------------------------------------------
# 3. Enum key: bettor
# ---------------------------------------------------------------------------


class TestBettorKey:
    def test_returns_distinct_bettors(self, monkeypatch: pytest.MonkeyPatch) -> None:
        rows = [("ai",), ("user",)]
        cm, _ = _make_cursor_cm(fetchall_return=rows)
        client = _make_client(monkeypatch, cm)

        resp = client.get("/api/filter/values?key=bettor")
        assert resp.status_code == 200
        data = resp.json()
        assert data["key"] == "bettor"
        assert data["kind"] == "enum"
        assert "ai" in data["values"]
        assert "user" in data["values"]


# ---------------------------------------------------------------------------
# 4. Enum keys (outcome, prediction, result) — static canonical aliases
# ---------------------------------------------------------------------------


class TestEnumKeys:
    @pytest.mark.parametrize("key", ["outcome", "prediction", "result"])
    def test_returns_canonical_alias_set(
        self, key: str, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """outcome/prediction/result return the fixed alias list, no DB query."""
        # No cursor mock needed — these keys never hit the DB.
        import soccersmartbet.webapp.routes.filter_values as fv_module
        fv_module._cache.clear()
        monkeypatch.setattr(
            "soccersmartbet.webapp.routes.filter_values.get_cursor",
            MagicMock(side_effect=AssertionError("get_cursor must not be called for enum-only keys")),
        )

        from soccersmartbet.webapp.routes.filter_values import router
        app = FastAPI()
        app.include_router(router)
        client = TestClient(app, raise_server_exceptions=False)

        resp = client.get(f"/api/filter/values?key={key}")
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["key"] == key
        assert data["kind"] == "enum"
        # Must include the three canonical human-readable labels.
        values = data["values"]
        assert "home" in values
        assert "draw" in values
        assert "away" in values
        # Must also include the DSL short-forms.
        assert "1" in values
        assert "x" in values
        assert "2" in values


# ---------------------------------------------------------------------------
# 5 & 6. Numeric keys: stake, odds
# ---------------------------------------------------------------------------


class TestNumericKeys:
    @pytest.mark.parametrize("key", ["stake", "odds"])
    def test_returns_min_max(self, key: str, monkeypatch: pytest.MonkeyPatch) -> None:
        cm, _ = _make_cursor_cm(fetchone_return=(Decimal("1.50"), Decimal("9.75")))
        client = _make_client(monkeypatch, cm)

        resp = client.get(f"/api/filter/values?key={key}")
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["key"] == key
        assert data["kind"] == "numeric"
        assert data["min"] == pytest.approx(1.50)
        assert data["max"] == pytest.approx(9.75)

    @pytest.mark.parametrize("key", ["stake", "odds"])
    def test_empty_table_returns_zero_range(
        self, key: str, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        cm, _ = _make_cursor_cm(fetchone_return=(None, None))
        client = _make_client(monkeypatch, cm)

        resp = client.get(f"/api/filter/values?key={key}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["min"] == pytest.approx(0.0)
        assert data["max"] == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# 7. Date key
# ---------------------------------------------------------------------------


class TestDateKey:
    def test_returns_min_max_iso_dates(self, monkeypatch: pytest.MonkeyPatch) -> None:
        cm, _ = _make_cursor_cm(
            fetchone_return=(datetime.date(2025, 9, 1), datetime.date(2026, 4, 20))
        )
        client = _make_client(monkeypatch, cm)

        resp = client.get("/api/filter/values?key=date")
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["key"] == "date"
        assert data["kind"] == "date"
        assert data["min"] == "2025-09-01"
        assert data["max"] == "2026-04-20"

    def test_empty_table_returns_empty_strings(self, monkeypatch: pytest.MonkeyPatch) -> None:
        cm, _ = _make_cursor_cm(fetchone_return=(None, None))
        client = _make_client(monkeypatch, cm)

        resp = client.get("/api/filter/values?key=date")
        assert resp.status_code == 200
        data = resp.json()
        assert data["min"] == ""
        assert data["max"] == ""


# ---------------------------------------------------------------------------
# 8. Month key
# ---------------------------------------------------------------------------


class TestMonthKey:
    def test_returns_sorted_desc_year_month(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # DB returns to_char(..., 'YYYY-MM') already ordered DESC.
        rows = [("2026-04",), ("2026-03",), ("2026-02",), ("2025-12",)]
        cm, _ = _make_cursor_cm(fetchall_return=rows)
        client = _make_client(monkeypatch, cm)

        resp = client.get("/api/filter/values?key=month")
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["key"] == "month"
        assert data["kind"] == "enum"
        assert data["values"] == ["2026-04", "2026-03", "2026-02", "2025-12"]


# ---------------------------------------------------------------------------
# 9. Unknown key → 400
# ---------------------------------------------------------------------------


class TestUnknownKey:
    def test_unknown_key_returns_400(self, monkeypatch: pytest.MonkeyPatch) -> None:
        import soccersmartbet.webapp.routes.filter_values as fv_module
        fv_module._cache.clear()

        from soccersmartbet.webapp.routes.filter_values import router
        app = FastAPI()
        app.include_router(router)
        client = TestClient(app, raise_server_exceptions=False)

        resp = client.get("/api/filter/values?key=foobar")
        assert resp.status_code == 400, resp.text
        assert "foobar" in resp.json()["detail"]

    def test_missing_key_param_returns_422(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """FastAPI returns 422 when the required 'key' query param is absent."""
        import soccersmartbet.webapp.routes.filter_values as fv_module
        fv_module._cache.clear()

        from soccersmartbet.webapp.routes.filter_values import router
        app = FastAPI()
        app.include_router(router)
        client = TestClient(app, raise_server_exceptions=False)

        resp = client.get("/api/filter/values")
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# 10. Cache hit: second call does not re-query the DB
# ---------------------------------------------------------------------------


class TestCaching:
    def test_second_call_uses_cache(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """The DB fetcher must be called exactly once across two requests."""
        rows = [("Premier League",), ("La Liga",)]
        cm, mock_cursor = _make_cursor_cm(fetchall_return=rows)
        mock_get_cursor = MagicMock(return_value=cm)
        monkeypatch.setattr(
            "soccersmartbet.webapp.routes.filter_values.get_cursor",
            mock_get_cursor,
        )

        import soccersmartbet.webapp.routes.filter_values as fv_module
        fv_module._cache.clear()

        from soccersmartbet.webapp.routes.filter_values import router
        app = FastAPI()
        app.include_router(router)
        client = TestClient(app, raise_server_exceptions=False)

        resp1 = client.get("/api/filter/values?key=league")
        resp2 = client.get("/api/filter/values?key=league")

        assert resp1.status_code == 200
        assert resp2.status_code == 200
        assert resp1.json() == resp2.json()

        # get_cursor must have been called exactly once (cache hit on second request).
        assert mock_get_cursor.call_count == 1

    def test_fresh_param_bypasses_cache(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """?fresh=1 must bypass the cache and trigger a new DB query."""
        rows = [("Bundesliga",)]
        cm, _ = _make_cursor_cm(fetchall_return=rows)
        mock_get_cursor = MagicMock(return_value=cm)
        monkeypatch.setattr(
            "soccersmartbet.webapp.routes.filter_values.get_cursor",
            mock_get_cursor,
        )

        import soccersmartbet.webapp.routes.filter_values as fv_module
        fv_module._cache.clear()

        from soccersmartbet.webapp.routes.filter_values import router
        app = FastAPI()
        app.include_router(router)
        client = TestClient(app, raise_server_exceptions=False)

        # First request populates cache.
        resp1 = client.get("/api/filter/values?key=league")
        assert resp1.status_code == 200
        assert mock_get_cursor.call_count == 1

        # Second request with fresh=1 must re-query.
        resp2 = client.get("/api/filter/values?key=league&fresh=1")
        assert resp2.status_code == 200
        assert mock_get_cursor.call_count == 2
