"""FotMob API client with team name resolution."""

import base64
import hashlib
import json
import time
import urllib.parse
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import requests

from soccersmartbet.team_registry import normalize_team_name

FOTMOB_LEAGUES = {
    "Premier League": 47, "La Liga": 87, "Serie A": 55, "Bundesliga": 54,
    "Ligue 1": 53, "Champions League": 42, "Europa League": 73,
    "Eredivisie": 57, "Primeira Liga": 61,
}

_league_cache: Dict[int, Dict[str, Any]] = {}
_cache_time: Dict[int, datetime] = {}
CACHE_TTL = timedelta(minutes=60)


def _generate_xmas_header(url: str) -> str:
    """Generate x-mas authentication header for FotMob API requests."""
    epoch_ms = str(int(time.time() * 1000))
    body = {
        "url": url,
        "code": epoch_ms,
        "foo": "production:74ac2edaa7d42530fa49330efe1eedcfb21b555d"
    }
    body_json = json.dumps(body, separators=(',', ':'))
    signature = hashlib.md5(body_json.encode()).hexdigest()
    token = {"body": body, "signature": signature}
    token_json = json.dumps(token, separators=(',', ':'))
    return base64.b64encode(token_json.encode()).decode()


class FotMobClient:
    def __init__(self) -> None:
        self._team_cache: Dict[str, Dict[str, Any]] = {}

    def _normalize(self, name: str) -> str:
        return normalize_team_name(name)

    def _request(self, endpoint: str, params: dict = None) -> Optional[dict]:
        url = f"https://www.fotmob.com{endpoint}"
        if params:
            url += "?" + urllib.parse.urlencode(params)
        headers = {
            "x-mas": _generate_xmas_header(url),
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        }
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code in (401, 403):
            raise PermissionError(
                f"FotMob auth failed ({response.status_code}) — x-mas key may be rotated"
            )
        response.raise_for_status()
        return response.json()

    def get_league_table(self, league_id: int) -> Optional[dict]:
        """Fetch raw league table data from FotMob."""
        try:
            return self._request("/api/data/tltable", params={"leagueId": league_id})
        except Exception:
            return None

    def get_team_data(self, team_id: int) -> Optional[Dict[str, Any]]:
        """Fetch team data including venue, form, and match info."""
        try:
            return self._request("/api/data/teams", params={"id": team_id})
        except Exception:
            return None

    def get_match_data(self, match_id: int) -> Optional[Dict[str, Any]]:
        """Fetch match details including lineup data."""
        try:
            return self._request("/api/data/match", params={"id": match_id})
        except Exception:
            return None

    def get_team_news(self, team_id: int) -> Optional[Dict[str, Any]]:
        """Fetch latest news articles for a team."""
        try:
            return self._request(
                "/api/data/tlnews",
                params={"id": team_id, "type": "team", "language": "en", "startIndex": 0}
            )
        except Exception:
            return None

    def _load_league(self, league_id: int) -> Dict[str, Any]:
        now = datetime.now()
        if league_id in _league_cache and now - _cache_time.get(league_id, datetime.min) < CACHE_TTL:
            return _league_cache[league_id]
        try:
            data = self.get_league_table(league_id)
            if not data:
                return {}
            tables = data.get("table", [])
            if not tables:
                return {}
            teams = {}
            for team in tables[0].get("data", {}).get("table", {}).get("all", []):
                teams[self._normalize(team.get("name", ""))] = {
                    "id": team.get("id"), "name": team.get("name"),
                    "league_id": league_id, "position": team.get("idx"),
                    "played": team.get("played"), "wins": team.get("wins"),
                    "draws": team.get("draws"), "losses": team.get("losses"),
                    "points": team.get("pts"),
                }
            _league_cache[league_id] = teams
            _cache_time[league_id] = now
            return teams
        except Exception:
            return {}

    def find_team(self, team_name: str) -> Optional[Dict[str, Any]]:
        """Find team by name across major leagues."""
        key = self._normalize(team_name)
        if key in self._team_cache:
            return self._team_cache[key]

        for league_name, league_id in FOTMOB_LEAGUES.items():
            teams = self._load_league(league_id)
            if key in teams:
                result = {**teams[key], "league_name": league_name}
                self._team_cache[key] = result
                return result
            for norm, info in teams.items():
                if key in norm or norm in key:
                    result = {**info, "league_name": league_name}
                    self._team_cache[key] = result
                    return result
        return None

    def get_league_standings(self, league_id: int) -> List[Dict[str, Any]]:
        """Return sorted list of teams in league standings."""
        teams = list(self._load_league(league_id).values())
        teams.sort(key=lambda x: x.get("position", 999))
        return teams


_client: Optional[FotMobClient] = None


def get_fotmob_client() -> FotMobClient:
    global _client
    if _client is None:
        _client = FotMobClient()
    return _client
