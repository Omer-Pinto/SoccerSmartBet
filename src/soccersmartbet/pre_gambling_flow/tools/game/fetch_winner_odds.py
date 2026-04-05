"""
Fetch betting odds from winner.co.il Israeli Toto mobile API.

Implements the 2-step GetCMobileHashes + GetCMobileLine flow to retrieve
1X2 odds for soccer matches listed on the Israeli Toto platform.
"""

import hashlib
import uuid
import json
from typing import Dict, Any, Optional
import requests

# API Configuration
BASE_URL = "https://api.winner.co.il/api/CouponDataCenter"
TIMEOUT = 15

# Static device ID derived from a deterministic SHA256 hash
_DEVICE_SEED = "soccersmartbet-device"
DEVICE_ID = hashlib.sha256(_DEVICE_SEED.encode()).hexdigest()

# Fixed app metadata headers
APP_VERSION = "3.0.0"
USER_AGENT_DATA = json.dumps(
    {
        "os": "Android",
        "osVersion": "14",
        "appVersion": APP_VERSION,
        "deviceModel": "SM-G991B",
    },
    separators=(",", ":"),
)

# Hebrew league name → English canonical name
LEAGUE_MAP_HE: Dict[str, str] = {
    "ספרדית ראשונה": "La Liga",
    "אנגלית ראשונה": "Premier League",
    "איטלקית ראשונה": "Serie A",
    "גרמנית ראשונה": "Bundesliga",
    "צרפתית ראשונה": "Ligue 1",
    "ליגת האלופות": "Champions League",
    "ליגת אירופה": "Europa League",
    "ליגת Winner": "Israeli Premier League",
}

# Hebrew team name → lowercase English name (for fuzzy matching against caller input)
TEAM_HE_TO_EN: Dict[str, str] = {
    "ברצלונה": "barcelona",
    "ריאל מדריד": "real madrid",
    "אתלטיקו מדריד": "atletico madrid",
    "צ'לסי": "chelsea",
    "ליברפול": "liverpool",
    "מנצ'סטר סיטי": "manchester city",
    "מנצ'סטר יונייטד": "manchester united",
    "ארסנל": "arsenal",
    "טוטנהאם": "tottenham",
    "יובנטוס": "juventus",
    "אינטר מילאן": "inter",
    "מילאן": "ac milan",
    "נאפולי": "napoli",
    "באיירן מינכן": "bayern",
    "דורטמונד": "dortmund",
    "פ.ס.ז'": "psg",
    "מרסיי": "marseille",
    "מונאקו": "monaco",
    "רומא": "roma",
    "לאציו": "lazio",
}


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _build_headers() -> Dict[str, str]:
    """Build request headers with a fresh requestid per call."""
    return {
        "Content-Type": "application/json",
        "deviceid": DEVICE_ID,
        "appversion": APP_VERSION,
        "requestid": str(uuid.uuid4()),
        "useragentdata": USER_AGENT_DATA,
    }


def _error_dict(
    home_team_name: str,
    away_team_name: str,
    message: str,
    league: Optional[str] = None,
    home_name_he: Optional[str] = None,
    away_name_he: Optional[str] = None,
) -> Dict[str, Any]:
    """Return a standardised error response dict."""
    return {
        "home_team": home_team_name,
        "away_team": away_team_name,
        "match_id": None,
        "commence_time": None,
        "odds_home": None,
        "odds_draw": None,
        "odds_away": None,
        "bookmaker": None,
        "league": league,
        "home_name_he": home_name_he,
        "away_name_he": away_name_he,
        "error": message,
    }


def _get_mobile_hashes() -> Optional[Dict[str, Any]]:
    """
    Step 1: POST GetCMobileHashes.

    Returns the raw JSON response body or None on failure.
    """
    try:
        response = requests.post(
            f"{BASE_URL}/GetCMobileHashes",
            headers=_build_headers(),
            json={"LanguageId": 2},
            timeout=TIMEOUT,
        )
        if response.status_code != 200:
            return None
        return response.json()
    except Exception:
        return None


def _get_mobile_line(hashes: list = None) -> Optional[Dict[str, Any]]:
    """
    Step 2: POST GetCMobileLine.

    Args:
        hashes: Hash list from Step 1 response. Forwarded to the API.

    Returns the raw JSON response body or None on failure.
    """
    try:
        response = requests.post(
            f"{BASE_URL}/GetCMobileLine",
            headers=_build_headers(),
            json={
                "LanguageId": 2,
                "Hashes": hashes or [],
                "FavoritesHashCode": "",
                "FavoritesData": None,
            },
            timeout=TIMEOUT,
        )
        if response.status_code != 200:
            return None
        return response.json()
    except Exception:
        return None


def _parse_soccer_events(data: Dict[str, Any]) -> list[Dict[str, Any]]:
    """
    Walk Sports → Tournaments → Events and return a flat list of enriched
    soccer event dicts containing parsed odds and league info.

    Each entry has:
        home_name_he, away_name_he, league_he, league_en,
        odds_home, odds_draw, odds_away, commence_time
    """
    events: list[Dict[str, Any]] = []
    sports = data.get("Sports") or []

    for sport in sports:
        sport_name: str = sport.get("Name") or sport.get("SportName") or ""
        if "כדורגל" not in sport_name:
            continue

        tournaments = sport.get("Tournaments") or []
        for tournament in tournaments:
            league_he: str = tournament.get("Name") or tournament.get("TournamentName") or ""
            league_en: str = _map_league(league_he)

            raw_events = tournament.get("Events") or []
            for event in raw_events:
                home_he: str = event.get("HomeName") or ""
                away_he: str = event.get("AwayName") or ""
                commence_time: Optional[str] = (
                    event.get("EventDate")
                    or event.get("StartTime")
                    or event.get("Date")
                )

                markets = event.get("Markets") or []
                odds = _extract_1x2_odds(markets, home_he, away_he)
                if odds is None:
                    continue

                events.append(
                    {
                        "home_name_he": home_he,
                        "away_name_he": away_he,
                        "league_he": league_he,
                        "league_en": league_en,
                        "odds_home": odds["home"],
                        "odds_draw": odds["draw"],
                        "odds_away": odds["away"],
                        "commence_time": commence_time,
                    }
                )

    return events


def _extract_1x2_odds(
    markets: list[Dict[str, Any]],
    home_name_he: str = "",
    away_name_he: str = "",
) -> Optional[Dict[str, float]]:
    """
    Find the 1X2 market and return {"home", "draw", "away"} decimal prices.

    A 1X2 market is identified by having exactly 3 outcomes where one outcome
    name contains "X" or "תיקו" (Hebrew for "draw").

    Home/away assignment uses outcome names matched against the event's Hebrew
    team names. Falls back to positional order only when names don't match.

    Returns None if no valid 1X2 market is found.
    """
    for market in markets:
        outcomes = market.get("Outcomes") or market.get("Selections") or []
        if len(outcomes) != 3:
            continue

        draw_outcome = next(
            (
                o
                for o in outcomes
                if "X" in (o.get("Name") or "")
                or "תיקו" in (o.get("Name") or "")
            ),
            None,
        )
        if draw_outcome is None:
            continue

        non_draw = [o for o in outcomes if o is not draw_outcome]
        if len(non_draw) != 2:
            continue

        # Try to match outcome names against home/away Hebrew team names
        home_outcome = None
        away_outcome = None
        if home_name_he and away_name_he:
            for o in non_draw:
                oname = o.get("Name") or ""
                if home_name_he in oname or oname in home_name_he:
                    home_outcome = o
                elif away_name_he in oname or oname in away_name_he:
                    away_outcome = o

        # Fall back to positional if name matching didn't resolve both
        if home_outcome is None or away_outcome is None:
            home_outcome = non_draw[0]
            away_outcome = non_draw[1]

        odds_home = _to_float(home_outcome.get("Price") or home_outcome.get("Odds"))
        odds_draw = _to_float(draw_outcome.get("Price") or draw_outcome.get("Odds"))
        odds_away = _to_float(away_outcome.get("Price") or away_outcome.get("Odds"))

        if odds_home is None or odds_draw is None or odds_away is None:
            continue

        return {"home": odds_home, "draw": odds_draw, "away": odds_away}

    return None


def _to_float(value: Any) -> Optional[float]:
    """Safely convert a value to float, returning None on failure."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _map_league(league_he: str) -> str:
    """
    Map a Hebrew league name to its English canonical name.

    Uses substring matching so partial tournament names still map correctly.
    Falls back to the original Hebrew string if no match is found.
    """
    for he_key, en_val in LEAGUE_MAP_HE.items():
        if he_key in league_he:
            return en_val
    return league_he


def _he_name_for_english(english_name: str) -> Optional[str]:
    """
    Return the Hebrew key whose mapped English value substring-matches
    the given English team name (case-insensitive).

    Example: "Manchester City" → "מנצ'סטר סיטי"
    """
    english_lower = english_name.lower()
    for he, en in TEAM_HE_TO_EN.items():
        if english_lower in en or en in english_lower:
            return he
    return None


def _events_match(
    event: Dict[str, Any],
    home_team_name: str,
    away_team_name: str,
) -> bool:
    """
    Return True if an event matches the requested home/away team names.

    Matching strategy (in priority order):
    1. Direct Hebrew lookup via TEAM_HE_TO_EN
    2. Substring match of the caller's English name against the Hebrew-to-
       English value strings stored in TEAM_HE_TO_EN
    """
    home_he = event["home_name_he"]
    away_he = event["away_name_he"]

    # Resolve Hebrew names for caller's English inputs
    expected_home_he = _he_name_for_english(home_team_name)
    expected_away_he = _he_name_for_english(away_team_name)

    if expected_home_he and expected_away_he:
        return home_he == expected_home_he and away_he == expected_away_he

    # Fallback: substring match on the mapped English values
    home_en = TEAM_HE_TO_EN.get(home_he, "").lower()
    away_en = TEAM_HE_TO_EN.get(away_he, "").lower()
    home_req = home_team_name.lower()
    away_req = away_team_name.lower()

    home_matches = home_req in home_en or home_en in home_req
    away_matches = away_req in away_en or away_en in away_req
    return home_matches and away_matches


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def fetch_winner_odds(home_team_name: str, away_team_name: str) -> Dict[str, Any]:
    """
    Fetch 1X2 odds for a specific match from winner.co.il.

    Executes the 2-step mobile API flow (GetCMobileHashes then GetCMobileLine),
    parses all soccer events, and returns odds for the requested fixture.

    Args:
        home_team_name: Home team name in English (e.g., "Barcelona").
        away_team_name: Away team name in English (e.g., "Real Madrid").

    Returns:
        Dict with keys:
            home_team (str), away_team (str),
            match_id (None — winner API has no stable match ID),
            commence_time (str | None),
            odds_home (float | None), odds_draw (float | None),
            odds_away (float | None),
            bookmaker ("winner.co.il"),
            league (str | None),
            home_name_he (str | None), away_name_he (str | None),
            error (str | None)
    """
    # Step 1 — obtain hashes
    hashes_data = _get_mobile_hashes()
    if hashes_data is None:
        return _error_dict(
            home_team_name,
            away_team_name,
            "Failed to reach winner.co.il GetCMobileHashes endpoint",
        )

    # Step 2 — fetch full line, forwarding hashes from Step 1
    hashes_list = hashes_data.get("Hashes") or []
    line_data = _get_mobile_line(hashes=hashes_list)
    if line_data is None:
        return _error_dict(
            home_team_name,
            away_team_name,
            "Failed to reach winner.co.il GetCMobileLine endpoint",
        )

    try:
        events = _parse_soccer_events(line_data)
    except Exception as exc:
        return _error_dict(
            home_team_name,
            away_team_name,
            f"Error parsing winner.co.il response: {exc}",
        )

    for event in events:
        if _events_match(event, home_team_name, away_team_name):
            return {
                "home_team": home_team_name,
                "away_team": away_team_name,
                "match_id": None,
                "commence_time": event["commence_time"],
                "odds_home": event["odds_home"],
                "odds_draw": event["odds_draw"],
                "odds_away": event["odds_away"],
                "bookmaker": "winner.co.il",
                "league": event["league_en"],
                "home_name_he": event["home_name_he"],
                "away_name_he": event["away_name_he"],
                "error": None,
            }

    return _error_dict(
        home_team_name,
        away_team_name,
        f"No upcoming match found between {home_team_name} and {away_team_name} on winner.co.il",
    )


def fetch_all_winner_odds(league: Optional[str] = None) -> Dict[str, Any]:
    """
    Fetch all available 1X2 odds from winner.co.il, optionally filtered by league.

    Args:
        league: Optional English league name to filter by (e.g., "La Liga").
                Matching is case-insensitive substring. Pass None to return all.

    Returns:
        Dict with keys:
            events: list of odds dicts (one per soccer event)
            error: str | None — set on API failure so callers can distinguish
                   empty results from fetch errors
    """
    # Step 1 — obtain hashes
    hashes_data = _get_mobile_hashes()
    if hashes_data is None:
        return {"events": [], "error": "Failed to reach winner.co.il GetCMobileHashes endpoint"}

    # Step 2 — fetch full line, forwarding hashes from Step 1
    hashes_list = hashes_data.get("Hashes") or []
    line_data = _get_mobile_line(hashes=hashes_list)
    if line_data is None:
        return {"events": [], "error": "Failed to reach winner.co.il GetCMobileLine endpoint"}

    try:
        events = _parse_soccer_events(line_data)
    except Exception as exc:
        return {"events": [], "error": f"Error parsing winner.co.il response: {exc}"}

    results: list[Dict[str, Any]] = []
    league_filter = league.lower() if league else None

    for event in events:
        if league_filter and league_filter not in event["league_en"].lower():
            continue

        # Resolve English team names from Hebrew where possible
        home_en = TEAM_HE_TO_EN.get(event["home_name_he"], event["home_name_he"])
        away_en = TEAM_HE_TO_EN.get(event["away_name_he"], event["away_name_he"])

        results.append(
            {
                "home_team": home_en,
                "away_team": away_en,
                "match_id": None,
                "commence_time": event["commence_time"],
                "odds_home": event["odds_home"],
                "odds_draw": event["odds_draw"],
                "odds_away": event["odds_away"],
                "bookmaker": "winner.co.il",
                "league": event["league_en"],
                "home_name_he": event["home_name_he"],
                "away_name_he": event["away_name_he"],
                "error": None,
            }
        )

    return {"events": results, "error": None}
