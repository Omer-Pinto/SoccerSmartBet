"""Tests for FotMob league-name resolution.

Covers:
- _normalise_league in persist_games (alias table)
- _normalise_league_for_lookup in fotmob_fixtures (tolerant prefix stripping)
- _resolve_fotmob_id returning None for truly unknown leagues
- _resolve_fotmob_id successfully resolving UEFA-prefixed names via the normaliser
"""
from __future__ import annotations

import pytest
from unittest.mock import patch, MagicMock
from datetime import date

from soccersmartbet.pre_gambling_flow.nodes.persist_games import _normalise_league
from soccersmartbet.pre_gambling_flow.tools.fotmob_fixtures import (
    _normalise_league_for_lookup,
    _resolve_fotmob_id,
)
from soccersmartbet.pre_gambling_flow.tools.fotmob_client import FOTMOB_LEAGUES


# ---------------------------------------------------------------------------
# _normalise_league — alias table in persist_games
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "raw, expected",
    [
        # UEFA-prefixed names that Winner.co.il emits
        ("UEFA Champions League", "Champions League"),
        ("uefa champions league", "Champions League"),
        ("UEFA Europa League", "Europa League"),
        ("UEFA Conference League", "Conference League"),
        ("UEFA Europa Conference League", "Conference League"),
        # Existing La Liga aliases
        ("Primera Division", "La Liga"),
        ("primera división", "La Liga"),
        ("LaLiga", "La Liga"),
        ("Spanish La Liga", "La Liga"),
        # Unknown names pass through unchanged
        ("Bundesliga", "Bundesliga"),
        ("Premier League", "Premier League"),
        ("Serie A", "Serie A"),
    ],
)
def test_normalise_league_aliases(raw: str, expected: str) -> None:
    assert _normalise_league(raw) == expected


# ---------------------------------------------------------------------------
# _normalise_league_for_lookup — tolerant normaliser in fotmob_fixtures
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "raw, expected_key",
    [
        # UEFA prefix stripped → matches FOTMOB_LEAGUES key (lower-cased)
        ("UEFA Champions League", "champions league"),
        ("UEFA Europa League", "europa league"),
        # No prefix — just lower-case + whitespace collapse
        ("Champions League", "champions league"),
        ("  Premier League  ", "premier league"),
        ("La Liga", "la liga"),
    ],
)
def test_normalise_league_for_lookup(raw: str, expected_key: str) -> None:
    assert _normalise_league_for_lookup(raw) == expected_key


def test_normalise_league_for_lookup_matches_all_fotmob_keys() -> None:
    """Every FOTMOB_LEAGUES key must normalise to itself (idempotency)."""
    for key in FOTMOB_LEAGUES:
        normalised = _normalise_league_for_lookup(key)
        assert normalised == key.lower(), (
            f"FOTMOB_LEAGUES key '{key}' normalised to '{normalised}', "
            "expected '{key.lower()}'"
        )


# ---------------------------------------------------------------------------
# _resolve_fotmob_id — end-to-end league lookup logic (FotMob I/O mocked)
# ---------------------------------------------------------------------------

_FAKE_MATCH = {
    "id": 9999,
    "home_name": "Arsenal",
    "away_name": "Atletico Madrid",
    "utc_time": "2026-05-02T19:00:00.000Z",
}


@pytest.mark.parametrize(
    "league_name",
    [
        "Champions League",           # exact FOTMOB_LEAGUES key
        "UEFA Champions League",      # Winner.co.il variant (the bug)
        "uefa champions league",      # lower-case variant
    ],
)
def test_resolve_fotmob_id_champions_league_variants(league_name: str) -> None:
    """_resolve_fotmob_id must find the CL match regardless of UEFA prefix."""
    with patch(
        "soccersmartbet.pre_gambling_flow.tools.fotmob_fixtures._fetch_league_matches",
        return_value=[_FAKE_MATCH],
    ):
        result = _resolve_fotmob_id(
            home_team="Arsenal",
            away_team="Atletico Madrid",
            match_date=date(2026, 5, 2),
            league_name=league_name,
        )
    assert result == 9999, (
        f"Expected fotmob_id 9999 for league_name='{league_name}', got {result}"
    )


def test_resolve_fotmob_id_unknown_league_returns_none(caplog: pytest.LogCaptureFixture) -> None:
    """An unrecognised league must return None and log the league name.

    User-facing WARNING with game context is emitted by the caller
    (enrich_games_with_fotmob_ids); _resolve_fotmob_id only logs at DEBUG.
    """
    import logging

    with caplog.at_level(logging.DEBUG, logger="soccersmartbet.pre_gambling_flow.tools.fotmob_fixtures"):
        result = _resolve_fotmob_id(
            home_team="TeamA",
            away_team="TeamB",
            match_date=date(2026, 5, 2),
            league_name="Made Up League XYZ",
        )

    assert result is None
    assert any("Made Up League XYZ" in r.message for r in caplog.records)


@pytest.mark.parametrize("fotmob_key", list(FOTMOB_LEAGUES.keys()))
def test_resolve_fotmob_id_all_fotmob_keys_resolve(fotmob_key: str) -> None:
    """Every FOTMOB_LEAGUES key should resolve to its league_id without error."""
    with patch(
        "soccersmartbet.pre_gambling_flow.tools.fotmob_fixtures._fetch_league_matches",
        return_value=[],  # empty — we only test that the league lookup succeeds
    ) as mock_fetch:
        _resolve_fotmob_id(
            home_team="X",
            away_team="Y",
            match_date=date(2026, 5, 2),
            league_name=fotmob_key,
        )
        # fetch was called → league_id was resolved (not short-circuited by None)
        mock_fetch.assert_called_once()
