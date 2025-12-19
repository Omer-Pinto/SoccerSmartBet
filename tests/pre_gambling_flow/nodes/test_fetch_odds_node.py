from __future__ import annotations

import sys
from pathlib import Path

import pytest


# Ensure local `src/` is importable even if an older `soccersmartbet` package is installed.
REPO_ROOT = Path(__file__).resolve().parents[3]
SRC_PATH = REPO_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from soccersmartbet.pre_gambling_flow.nodes.fetch_odds_node import fetch_and_filter_odds
from soccersmartbet.pre_gambling_flow.structured_outputs import SelectedGame


def _sg(home: str, away: str) -> SelectedGame:
    return SelectedGame(
        home_team=home,
        away_team=away,
        match_date="2025-12-19",
        kickoff_time="20:00",
        league="Test League",
        venue=None,
        justification="test",
    )


def test_fetch_and_filter_odds_filters_incomplete_and_error(monkeypatch: pytest.MonkeyPatch):
    games = [_sg("A", "B"), _sg("C", "D"), _sg("E", "F")]

    def fake_fetch_odds(home_team_name: str, away_team_name: str):
        if (home_team_name, away_team_name) == ("A", "B"):
            return {
                "odds_home": 1.55,
                "odds_draw": 3.20,
                "odds_away": 2.05,
                "error": None,
            }
        if (home_team_name, away_team_name) == ("C", "D"):
            return {
                "odds_home": 1.90,
                "odds_draw": None,
                "odds_away": 4.10,
                "error": None,
            }
        return {
            "odds_home": None,
            "odds_draw": None,
            "odds_away": None,
            "error": "upstream error",
        }

    monkeypatch.setattr(
        "soccersmartbet.pre_gambling_flow.nodes.fetch_odds_node.fetch_odds",
        fake_fetch_odds,
    )

    filtered, included_indexes = fetch_and_filter_odds(
        games,
        min_odds_threshold=3.0,
        max_daily_games=10,
    )

    assert included_indexes == [0]
    assert len(filtered) == 1
    assert filtered[0]["home_team"] == "A"
    assert filtered[0]["away_team"] == "B"
    assert filtered[0]["n1"] == pytest.approx(1.55)
    assert filtered[0]["n2"] == pytest.approx(2.05)
    assert filtered[0]["n3"] == pytest.approx(3.20)


def test_fetch_and_filter_odds_enforces_max_daily_games(monkeypatch: pytest.MonkeyPatch):
    games = [_sg(f"H{i}", f"A{i}") for i in range(5)]

    def fake_fetch_odds(home_team_name: str, away_team_name: str):
        return {
            "odds_home": 2.10,
            "odds_draw": 3.10,
            "odds_away": 3.60,
            "error": None,
        }

    monkeypatch.setattr(
        "soccersmartbet.pre_gambling_flow.nodes.fetch_odds_node.fetch_odds",
        fake_fetch_odds,
    )

    filtered, included_indexes = fetch_and_filter_odds(
        games,
        min_odds_threshold=2.5,
        max_daily_games=3,
    )

    assert included_indexes == [0, 1, 2]
    assert len(filtered) == 3


def test_fetch_and_filter_odds_excludes_games_below_threshold(monkeypatch: pytest.MonkeyPatch):
    games = [_sg("A", "B"), _sg("C", "D")]

    def fake_fetch_odds(home_team_name: str, away_team_name: str):
        if (home_team_name, away_team_name) == ("A", "B"):
            return {
                "odds_home": 1.80,
                "odds_draw": 2.20,
                "odds_away": 2.10,
                "error": None,
            }
        return {
            "odds_home": 2.01,
            "odds_draw": 3.01,
            "odds_away": 2.90,
            "error": None,
        }

    monkeypatch.setattr(
        "soccersmartbet.pre_gambling_flow.nodes.fetch_odds_node.fetch_odds",
        fake_fetch_odds,
    )

    filtered, included_indexes = fetch_and_filter_odds(
        games,
        min_odds_threshold=3.0,
        max_daily_games=10,
    )

    assert included_indexes == [1]
    assert len(filtered) == 1
    assert filtered[0]["home_team"] == "C"
