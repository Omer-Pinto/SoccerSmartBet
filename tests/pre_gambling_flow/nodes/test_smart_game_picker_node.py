import datetime
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / 'src'))


import pytest
import requests

from soccersmartbet.pre_gambling_flow.nodes.smart_game_picker_node import run_smart_game_picker
from soccersmartbet.pre_gambling_flow.structured_outputs import SelectedGames


class DummyResponse:
    def __init__(self, status_code: int, payload: dict):
        self.status_code = status_code
        self._payload = payload

    def json(self):
        return self._payload


def test_run_smart_game_picker_returns_selected_games_min_3(monkeypatch):
    monkeypatch.setenv("FOOTBALL_DATA_API_KEY", "dummy")

    def forbidden_get(*_args, **_kwargs):
        raise AssertionError("requests.get should not be called")

    monkeypatch.setattr(requests, "get", forbidden_get)

    call_counter = {"count": 0}

    def fake_session_get(self, url, headers=None, params=None, timeout=None):
        call_counter["count"] += 1
        assert "api.football-data.org" in url
        assert headers and "X-Auth-Token" in headers
        assert params and "dateFrom" in params and "dateTo" in params
        assert timeout is not None

        return DummyResponse(
            200,
            {
                "matches": [
                    {
                        "id": 1,
                        "utcDate": "2025-11-20T19:45:00Z",
                        "homeTeam": {"name": "Manchester City"},
                        "awayTeam": {"name": "Manchester United"},
                        "competition": {"name": "Premier League", "code": "PL"},
                    },
                    {
                        "id": 2,
                        "utcDate": "2025-11-20T17:00:00Z",
                        "homeTeam": {"name": "Barcelona"},
                        "awayTeam": {"name": "Real Madrid"},
                        "competition": {"name": "Primera Division", "code": "PD"},
                    },
                    {
                        "id": 3,
                        "utcDate": "2025-11-20T20:00:00Z",
                        "homeTeam": {"name": "Inter"},
                        "awayTeam": {"name": "Juventus"},
                        "competition": {"name": "Serie A", "code": "SA"},
                    },
                    {
                        "id": 4,
                        "utcDate": "2025-11-20T19:00:00Z",
                        "homeTeam": {"name": "PSG"},
                        "awayTeam": {"name": "Bayern"},
                        "competition": {"name": "UEFA Champions League", "code": "CL"},
                    },
                ]
            },
        )

    monkeypatch.setattr(requests.Session, "get", fake_session_get)

    result = run_smart_game_picker(
        date=datetime.date(2025, 11, 20),
        max_games=4,
        session=requests.Session(),
    )

    assert isinstance(result, SelectedGames)
    assert len(result.games) >= 3
    assert len(result.games) <= 4
    assert result.selection_reasoning
    assert call_counter["count"] == 1


def test_run_smart_game_picker_uses_llm_select(monkeypatch):
    monkeypatch.setenv("FOOTBALL_DATA_API_KEY", "dummy")

    def fake_session_get(self, *_args, **_kwargs):
        return DummyResponse(
            200,
            {
                "matches": [
                    {
                        "id": 10,
                        "utcDate": "2025-11-20T19:45:00Z",
                        "homeTeam": {"name": "Team A"},
                        "awayTeam": {"name": "Team B"},
                        "competition": {"name": "Premier League", "code": "PL"},
                    },
                    {
                        "id": 11,
                        "utcDate": "2025-11-20T17:00:00Z",
                        "homeTeam": {"name": "Team C"},
                        "awayTeam": {"name": "Team D"},
                        "competition": {"name": "Serie A", "code": "SA"},
                    },
                    {
                        "id": 12,
                        "utcDate": "2025-11-20T20:00:00Z",
                        "homeTeam": {"name": "Team E"},
                        "awayTeam": {"name": "Team F"},
                        "competition": {"name": "Bundesliga", "code": "BL1"},
                    },
                ]
            },
        )

    monkeypatch.setattr(requests.Session, "get", fake_session_get)

    called = {"value": False}

    def llm_select(candidates, date, max_games):
        called["value"] = True
        assert len(candidates) == 3
        assert max_games == 8
        return {
            "games": [
                {
                    "home_team": "Team A",
                    "away_team": "Team B",
                    "match_date": date.isoformat(),
                    "kickoff_time": "19:45",
                    "league": "Premier League",
                    "venue": None,
                    "justification": "LLM pick",
                },
                {
                    "home_team": "Team C",
                    "away_team": "Team D",
                    "match_date": date.isoformat(),
                    "kickoff_time": "17:00",
                    "league": "Serie A",
                    "venue": None,
                    "justification": "LLM pick",
                },
                {
                    "home_team": "Team E",
                    "away_team": "Team F",
                    "match_date": date.isoformat(),
                    "kickoff_time": "20:00",
                    "league": "Bundesliga",
                    "venue": None,
                    "justification": "LLM pick",
                },
            ],
            "selection_reasoning": "LLM selection",
        }

    result = run_smart_game_picker(
        date=datetime.date(2025, 11, 20),
        session=requests.Session(),
        llm_select=llm_select,
    )

    assert called["value"] is True
    assert result.selection_reasoning == "LLM selection"


def test_run_smart_game_picker_empty_fixtures_raises(monkeypatch):
    monkeypatch.setenv("FOOTBALL_DATA_API_KEY", "dummy")

    def fake_session_get(self, *_args, **_kwargs):
        return DummyResponse(200, {"matches": []})

    monkeypatch.setattr(requests.Session, "get", fake_session_get)

    with pytest.raises(RuntimeError, match=r"No fixtures returned"):
        run_smart_game_picker(date=datetime.date(2025, 11, 20), session=requests.Session())
