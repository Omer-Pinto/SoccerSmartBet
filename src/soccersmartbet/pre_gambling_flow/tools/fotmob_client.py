"""
FotMob API client wrapper with team name resolution.

Provides a unified interface for FotMob data with:
- Team name to ID resolution (via league standings search)
- In-memory caching to reduce API calls
- Support for major European leagues

NO API KEY REQUIRED - uses unofficial FotMob API via mobfot package.
"""

from typing import Dict, Any, Optional, Tuple, List
from datetime import datetime, timedelta
from mobfot import MobFot
import logging

logger = logging.getLogger(__name__)

# Major European league IDs in FotMob
FOTMOB_LEAGUES = {
    "Premier League": 47,
    "La Liga": 87,
    "Serie A": 55,
    "Bundesliga": 54,
    "Ligue 1": 53,
    "Champions League": 42,
    "Europa League": 73,
    "Eredivisie": 57,
    "Primeira Liga": 61,
}

# Cache for league data (team name -> team info)
_league_cache: Dict[int, Dict[str, Any]] = {}
_cache_timestamp: Dict[int, datetime] = {}
CACHE_TTL_MINUTES = 60  # Cache expires after 1 hour


class FotMobClient:
    """
    FotMob API client with team name resolution.

    Usage:
        client = FotMobClient()

        # Find team by name
        team_info = client.find_team("Real Madrid")
        # Returns: {"id": 8633, "name": "Real Madrid", "league_id": 87, "league_name": "La Liga"}

        # Get team details
        team_data = client.get_team_data(8633)

        # Get match details
        match_data = client.get_match_data(match_id)
    """

    def __init__(self):
        self._client = MobFot()
        self._team_cache: Dict[str, Dict[str, Any]] = {}

    def _normalize_team_name(self, name: str) -> str:
        """Normalize team name for matching."""
        # Remove common prefixes/suffixes and lowercase
        normalized = name.lower().strip()
        # Remove "fc", "cf", "sc" etc
        for suffix in [" fc", " cf", " sc", " afc"]:
            if normalized.endswith(suffix):
                normalized = normalized[:-len(suffix)]
        for prefix in ["fc ", "cf ", "sc ", "afc "]:
            if normalized.startswith(prefix):
                normalized = normalized[len(prefix):]
        # Handle special characters
        normalized = normalized.replace("é", "e").replace("á", "a").replace("ó", "o")
        normalized = normalized.replace("ñ", "n").replace("ü", "u").replace("ö", "o")
        return normalized.strip()

    def _load_league_teams(self, league_id: int) -> Dict[str, Any]:
        """Load all teams from a league's standings table."""
        # Check cache first
        now = datetime.now()
        if league_id in _league_cache:
            cache_time = _cache_timestamp.get(league_id, datetime.min)
            if now - cache_time < timedelta(minutes=CACHE_TTL_MINUTES):
                return _league_cache[league_id]

        try:
            league_data = self._client.get_league(league_id)
            tables = league_data.get("table", [])

            if not tables:
                return {}

            # Get teams from standings
            teams_map = {}
            first_table = tables[0]
            all_teams = first_table.get("data", {}).get("table", {}).get("all", [])

            for team in all_teams:
                team_id = team.get("id")
                team_name = team.get("name", "")
                normalized = self._normalize_team_name(team_name)

                teams_map[normalized] = {
                    "id": team_id,
                    "name": team_name,
                    "league_id": league_id,
                    "position": team.get("idx"),
                    "played": team.get("played"),
                    "wins": team.get("wins"),
                    "draws": team.get("draws"),
                    "losses": team.get("losses"),
                    "goals_for": team.get("scoresFor"),
                    "goals_against": team.get("scoresAgainst"),
                    "goal_difference": team.get("goalConDiff"),
                    "points": team.get("pts"),
                }

            # Update cache
            _league_cache[league_id] = teams_map
            _cache_timestamp[league_id] = now

            return teams_map

        except Exception as e:
            logger.warning(f"Failed to load league {league_id}: {e}")
            return {}

    def find_team(self, team_name: str) -> Optional[Dict[str, Any]]:
        """
        Find team by name across all major leagues.

        Args:
            team_name: Team name (e.g., "Real Madrid", "Deportivo Alavés")

        Returns:
            Team info dict or None if not found:
            {
                "id": 8633,
                "name": "Real Madrid",
                "league_id": 87,
                "league_name": "La Liga",
                "position": 2,
                "points": 36,
                ...
            }
        """
        # Check team cache first
        cache_key = self._normalize_team_name(team_name)
        if cache_key in self._team_cache:
            return self._team_cache[cache_key]

        normalized_search = self._normalize_team_name(team_name)

        # Search across all leagues
        for league_name, league_id in FOTMOB_LEAGUES.items():
            teams_map = self._load_league_teams(league_id)

            # Try exact match first
            if normalized_search in teams_map:
                result = teams_map[normalized_search].copy()
                result["league_name"] = league_name
                self._team_cache[cache_key] = result
                return result

            # Try partial match
            for normalized_name, team_info in teams_map.items():
                if normalized_search in normalized_name or normalized_name in normalized_search:
                    result = team_info.copy()
                    result["league_name"] = league_name
                    self._team_cache[cache_key] = result
                    return result

        return None

    def get_team_data(self, team_id: int) -> Optional[Dict[str, Any]]:
        """
        Get full team data from FotMob.

        Returns team overview including:
        - teamForm (last 5 matches W/D/L)
        - venue info
        - lastMatch / nextMatch
        - coach info
        """
        try:
            return self._client.get_team(team_id)
        except Exception as e:
            logger.error(f"Failed to get team {team_id}: {e}")
            return None

    def get_match_data(self, match_id: int) -> Optional[Dict[str, Any]]:
        """
        Get match details from FotMob.

        Returns match data including:
        - content.weather
        - content.lineup (with unavailable players/injuries)
        - content.matchFacts
        """
        try:
            return self._client.get_match_details(match_id)
        except Exception as e:
            logger.error(f"Failed to get match {match_id}: {e}")
            return None

    def get_league_standings(self, league_id: int) -> List[Dict[str, Any]]:
        """
        Get full league standings.

        Returns list of teams with position, points, W/D/L etc.
        """
        teams_map = self._load_league_teams(league_id)
        # Return sorted by position
        teams_list = list(teams_map.values())
        teams_list.sort(key=lambda x: x.get("position", 999))
        return teams_list

    def find_upcoming_match(self, home_team: str, away_team: str) -> Optional[Dict[str, Any]]:
        """
        Find upcoming match between two teams.

        Args:
            home_team: Home team name
            away_team: Away team name

        Returns:
            Match info with ID and date, or None if not found
        """
        home_info = self.find_team(home_team)
        if not home_info:
            return None

        team_data = self.get_team_data(home_info["id"])
        if not team_data:
            return None

        overview = team_data.get("overview", {})
        next_match = overview.get("nextMatch", {})

        if not next_match:
            return None

        # Check if this is the match we're looking for
        match_home = next_match.get("home", {}).get("name", "")
        match_away = next_match.get("away", {}).get("name", "")

        away_normalized = self._normalize_team_name(away_team)
        match_home_norm = self._normalize_team_name(match_home)
        match_away_norm = self._normalize_team_name(match_away)

        # Check if away team matches either side
        if away_normalized in match_away_norm or match_away_norm in away_normalized:
            return {
                "match_id": next_match.get("id"),
                "home_team": match_home,
                "away_team": match_away,
                "date": next_match.get("status", {}).get("utcTime", ""),
            }
        elif away_normalized in match_home_norm or match_home_norm in away_normalized:
            # Teams might be reversed
            return {
                "match_id": next_match.get("id"),
                "home_team": match_home,
                "away_team": match_away,
                "date": next_match.get("status", {}).get("utcTime", ""),
            }

        return None


# Global client instance for convenience
_global_client: Optional[FotMobClient] = None


def get_fotmob_client() -> FotMobClient:
    """Get or create global FotMob client instance."""
    global _global_client
    if _global_client is None:
        _global_client = FotMobClient()
    return _global_client
