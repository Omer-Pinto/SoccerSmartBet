"""FotMob API client with team name resolution."""

from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from mobfot import MobFot

FOTMOB_LEAGUES = {
    "Premier League": 47, "La Liga": 87, "Serie A": 55, "Bundesliga": 54,
    "Ligue 1": 53, "Champions League": 42, "Europa League": 73,
    "Eredivisie": 57, "Primeira Liga": 61,
}

_league_cache: Dict[int, Dict[str, Any]] = {}
_cache_time: Dict[int, datetime] = {}
CACHE_TTL = timedelta(minutes=60)


class FotMobClient:
    def __init__(self):
        self._client = MobFot()
        self._team_cache: Dict[str, Dict[str, Any]] = {}

    def _normalize(self, name: str) -> str:
        n = name.lower().strip()
        for s in [" fc", " cf", " sc", " afc"]:
            if n.endswith(s): n = n[:-len(s)]
        for p in ["fc ", "cf ", "sc ", "afc "]:
            if n.startswith(p): n = n[len(p):]
        return n.replace("é", "e").replace("á", "a").replace("ó", "o").replace("ñ", "n").strip()

    def _load_league(self, league_id: int) -> Dict[str, Any]:
        now = datetime.now()
        if league_id in _league_cache and now - _cache_time.get(league_id, datetime.min) < CACHE_TTL:
            return _league_cache[league_id]
        try:
            data = self._client.get_league(league_id)
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

    def get_team_data(self, team_id: int) -> Optional[Dict[str, Any]]:
        try:
            return self._client.get_team(team_id)
        except Exception:
            return None

    def get_match_data(self, match_id: int) -> Optional[Dict[str, Any]]:
        try:
            return self._client.get_match_details(match_id)
        except Exception:
            return None

    def get_league_standings(self, league_id: int) -> List[Dict[str, Any]]:
        teams = list(self._load_league(league_id).values())
        teams.sort(key=lambda x: x.get("position", 999))
        return teams


_client: Optional[FotMobClient] = None

def get_fotmob_client() -> FotMobClient:
    global _client
    if _client is None:
        _client = FotMobClient()
    return _client
