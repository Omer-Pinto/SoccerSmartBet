import logging
import os
import time
from typing import Any

import requests
from dotenv import load_dotenv

from soccersmartbet.team_registry import normalize_team_name, resolve_team

load_dotenv()

logger = logging.getLogger(__name__)

FOOTBALL_DATA_API_KEY = os.getenv("FOOTBALL_DATA_API_KEY")
BASE_URL = "https://api.football-data.org/v4"
TIMEOUT = int(os.getenv("FDORG_H2H_TIMEOUT_S", "30"))

_BACKOFF_SEQUENCE = [5, 10, 20, 40, 80]

LEAGUE_CODE_MAP: dict[str, str] = {
    "premier league": "PL",
    "english premier league": "PL",
    "la liga": "PD",
    "serie a": "SA",
    "bundesliga": "BL1",
    "ligue 1": "FL1",
    "champions league": "CL",
    "uefa champions league": "CL",
    "european championship": "EC",
    "euro": "EC",
    "world cup": "WC",
    "fifa world cup": "WC",
    "championship": "ELC",
    "english championship": "ELC",
    "eredivisie": "DED",
    "primeira liga": "PPL",
    "portuguese primeira liga": "PPL",
    "brasileirao": "BSA",
    "serie a brasileirao": "BSA",
}


def _graceful(home: str, away: str) -> dict[str, Any]:
    return {
        "home_team": home,
        "away_team": away,
        "upcoming_match_id": None,
        "upcoming_match_date": None,
        "h2h_matches": [],
        "total_h2h": 0,
        "error": "couldn't retrieve h2h due to API issues",
    }


def _get_with_backoff(
    url: str,
    headers: dict[str, str],
    params: dict[str, Any],
) -> requests.Response | None:
    for attempt, sleep_s in enumerate([0] + _BACKOFF_SEQUENCE):
        if sleep_s:
            logger.warning(
                "fetch_h2h: 429 on %s, sleeping %ds (attempt %d/%d)",
                url,
                sleep_s,
                attempt,
                len(_BACKOFF_SEQUENCE) + 1,
            )
            time.sleep(sleep_s)
        resp = requests.get(url, headers=headers, params=params, timeout=TIMEOUT)
        if resp.status_code != 429:
            return resp
    logger.warning("fetch_h2h: exhausted retries on %s", url)
    return None


def fetch_h2h(
    home_team_name: str,
    away_team_name: str,
    limit: int = 5,
    league: str | None = None,
) -> dict[str, Any]:
    if not FOOTBALL_DATA_API_KEY:
        return {
            "home_team": home_team_name,
            "away_team": away_team_name,
            "upcoming_match_id": None,
            "upcoming_match_date": None,
            "h2h_matches": [],
            "total_h2h": 0,
            "error": "FOOTBALL_DATA_API_KEY not found in environment",
        }

    if league is None:
        return _graceful(home_team_name, away_team_name)

    competition_code = LEAGUE_CODE_MAP.get(league.lower())
    if competition_code is None:
        return _graceful(home_team_name, away_team_name)

    headers = {"X-Auth-Token": FOOTBALL_DATA_API_KEY}

    try:
        home_canonical = resolve_team(home_team_name) or home_team_name
        away_canonical = resolve_team(away_team_name) or away_team_name
        home_input_norm = normalize_team_name(home_canonical)
        away_input_norm = normalize_team_name(away_canonical)

        scan_url = f"{BASE_URL}/competitions/{competition_code}/matches"
        scan_resp = _get_with_backoff(
            scan_url, headers, {"status": "TIMED,SCHEDULED"}
        )

        if scan_resp is None:
            return _graceful(home_team_name, away_team_name)

        if scan_resp.status_code != 200:
            return {
                "home_team": home_team_name,
                "away_team": away_team_name,
                "upcoming_match_id": None,
                "upcoming_match_date": None,
                "h2h_matches": [],
                "total_h2h": 0,
                "error": f"H2H API error: {scan_resp.status_code}",
            }

        upcoming_match = None
        candidates = []
        for match in scan_resp.json().get("matches", []):
            home_name = (match.get("homeTeam") or {}).get("name")
            away_name = (match.get("awayTeam") or {}).get("name")
            if not home_name or not away_name:
                continue

            home_resolved = resolve_team(home_name) or home_name
            away_resolved = resolve_team(away_name) or away_name
            home_norm = normalize_team_name(home_resolved)
            away_norm = normalize_team_name(away_resolved)

            home_matches_home = home_input_norm in home_norm or home_norm in home_input_norm
            away_matches_away = away_input_norm in away_norm or away_norm in away_input_norm
            home_matches_away = home_input_norm in away_norm or away_norm in home_input_norm
            away_matches_home = away_input_norm in home_norm or home_norm in away_input_norm

            if (home_matches_home and away_matches_away) or (home_matches_away and away_matches_home):
                candidates.append(match)

        if candidates:
            candidates.sort(key=lambda m: m.get("utcDate") or "")
            upcoming_match = candidates[0]

        if not upcoming_match:
            return {
                "home_team": home_team_name,
                "away_team": away_team_name,
                "upcoming_match_id": None,
                "upcoming_match_date": None,
                "h2h_matches": [],
                "total_h2h": 0,
                "error": f"No upcoming match found between {home_team_name} and {away_team_name}",
            }

        match_id = upcoming_match["id"]
        match_date = upcoming_match.get("utcDate", "")[:10]

        h2h_resp = _get_with_backoff(
            f"{BASE_URL}/matches/{match_id}/head2head",
            headers,
            {"limit": limit},
        )

        if h2h_resp is None:
            return _graceful(home_team_name, away_team_name)

        if h2h_resp.status_code != 200:
            return {
                "home_team": home_team_name,
                "away_team": away_team_name,
                "upcoming_match_id": match_id,
                "upcoming_match_date": match_date,
                "h2h_matches": [],
                "total_h2h": 0,
                "error": f"H2H API error: {h2h_resp.status_code}",
            }

        h2h_matches = []
        for match in h2h_resp.json().get("matches", []):
            utc_date = match.get("utcDate", "")
            match_date_str = utc_date[:10] if utc_date else "Unknown"

            home = match.get("homeTeam", {}).get("name", "Unknown")
            away = match.get("awayTeam", {}).get("name", "Unknown")

            score = match.get("score", {}).get("fullTime", {})
            score_home = score.get("home")
            score_away = score.get("away")

            winner = "DRAW"
            if score_home is not None and score_away is not None:
                if score_home > score_away:
                    home_match_canonical = resolve_team(home) or home
                    input_home_canonical = resolve_team(home_team_name) or home_team_name
                    if normalize_team_name(home_match_canonical) == normalize_team_name(input_home_canonical):
                        winner = home_team_name
                    else:
                        winner = away_team_name
                elif score_away > score_home:
                    away_match_canonical = resolve_team(away) or away
                    input_home_canonical = resolve_team(home_team_name) or home_team_name
                    if normalize_team_name(away_match_canonical) == normalize_team_name(input_home_canonical):
                        winner = home_team_name
                    else:
                        winner = away_team_name

            h2h_matches.append({
                "date": match_date_str,
                "home_team": home,
                "away_team": away,
                "score_home": score_home,
                "score_away": score_away,
                "winner": winner,
            })

        return {
            "home_team": home_team_name,
            "away_team": away_team_name,
            "upcoming_match_id": match_id,
            "upcoming_match_date": match_date,
            "h2h_matches": h2h_matches,
            "total_h2h": len(h2h_matches),
            "error": None,
        }

    except requests.Timeout:
        return {
            "home_team": home_team_name,
            "away_team": away_team_name,
            "upcoming_match_id": None,
            "upcoming_match_date": None,
            "h2h_matches": [],
            "total_h2h": 0,
            "error": f"Request timeout after {TIMEOUT}s",
        }
    except Exception as e:
        return {
            "home_team": home_team_name,
            "away_team": away_team_name,
            "upcoming_match_id": None,
            "upcoming_match_date": None,
            "h2h_matches": [],
            "total_h2h": 0,
            "error": f"Unexpected error: {e}",
        }
