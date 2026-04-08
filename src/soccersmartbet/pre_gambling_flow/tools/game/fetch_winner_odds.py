"""
Fetch betting odds from winner.co.il Israeli Toto mobile API.

Uses a GET request to /api/v2/publicapi/GetCMobileLine which returns a flat
list of all available markets. Requires session cookies obtained by visiting
the main site first.
"""

import json
import uuid
from datetime import datetime
from typing import Any, Dict, Optional

import requests

from soccersmartbet.team_registry import resolve_team, get_source_name_he
from soccersmartbet.utils.timezone import ISR_TZ

# API Configuration
_BASE_URL = "https://www.winner.co.il"
_API_URL = f"{_BASE_URL}/api/v2/publicapi/GetCMobileLine"
TIMEOUT = 30

# Stable device ID for the session lifetime
_DEVICE_ID = str(uuid.uuid4())

# App metadata that mirrors the Android mobile web client
_USER_AGENT_DATA = json.dumps(
    {
        "devicemodel": "SM-G991B",
        "deviceos": "android",
        "deviceosversion": "14",
        "appversion": "2.6.0",
        "apptype": "mobileweb",
        "originId": "3",
        "isAccessibility": False,
    },
    separators=(",", ":"),
)

_REQUEST_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Linux; Android 14; SM-G991B) AppleWebKit/537.36",
    "Accept": "application/json",
    "Content-Type": "application/json",
    "DeviceId": _DEVICE_ID,
    "UserAgentData": _USER_AGENT_DATA,
    "appVersion": "2.6.0",
}

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

# ---------------------------------------------------------------------------
# Module-level session — initialised once, cookies persist across calls
# ---------------------------------------------------------------------------

_session: Optional[requests.Session] = None


def _get_session() -> requests.Session:
    """Return the module-level session, creating and priming it on first call."""
    global _session
    if _session is None:
        _session = requests.Session()
        # Visit the main page to acquire any required session cookies
        try:
            _session.get(
                _BASE_URL,
                headers={"User-Agent": _REQUEST_HEADERS["User-Agent"]},
                timeout=TIMEOUT,
            )
        except Exception:
            pass  # Proceed even if the homepage request fails
    return _session


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _build_headers() -> Dict[str, str]:
    """Return request headers with a fresh RequestId per call."""
    return {**_REQUEST_HEADERS, "RequestId": str(uuid.uuid4())}


def _to_float(value: Any) -> Optional[float]:
    """Safely convert a value to float, returning None on failure."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _parse_edate(e_date: int, m_hour: str) -> Optional[str]:
    """
    Convert winner.co.il date/time fields to an ISO-8601 string.

    Args:
        e_date: Integer in YYMMDD format (e.g. 260408 for 2026-04-08).
        m_hour: String in HHMM format (e.g. "2200" for 22:00).

    Returns:
        ISO-8601 datetime string or None if parsing fails.
    """
    try:
        date_str = str(e_date).zfill(6)
        year = 2000 + int(date_str[0:2])
        month = int(date_str[2:4])
        day = int(date_str[4:6])
        hour = int(m_hour[0:2])
        minute = int(m_hour[2:4])
        dt = datetime(year, month, day, hour, minute, tzinfo=ISR_TZ)
        return dt.isoformat()
    except Exception:
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


def _extract_1x2_odds(
    outcomes: list[Dict[str, Any]],
) -> Optional[Dict[str, float]]:
    """
    Extract home/draw/away odds from a 3-outcome list.

    The draw outcome is identified by its desc containing "X" (possibly wrapped
    in RTL Unicode markers). Home and away are assigned positionally from the
    remaining two outcomes.

    Returns:
        {"home": float, "draw": float, "away": float} or None.
    """
    if len(outcomes) != 3:
        return None

    draw_outcome = None
    for o in outcomes:
        desc = o.get("desc") or ""
        # Strip RTL/LTR Unicode control characters before checking for "X"
        stripped = "".join(c for c in desc if c.isalpha() or c.isdigit())
        if stripped == "X":
            draw_outcome = o
            break

    if draw_outcome is None:
        return None

    non_draw = [o for o in outcomes if o is not draw_outcome]
    if len(non_draw) != 2:
        return None

    odds_home = _to_float(non_draw[0].get("price"))
    odds_draw = _to_float(draw_outcome.get("price"))
    odds_away = _to_float(non_draw[1].get("price"))

    if odds_home is None or odds_draw is None or odds_away is None:
        return None

    return {"home": odds_home, "draw": odds_draw, "away": odds_away}


def _parse_soccer_markets(data: Dict[str, Any]) -> list[Dict[str, Any]]:
    """
    Parse the flat ``markets`` list from the GetCMobileLine response.

    Filters to 1X2 full-time result markets ("1X2" and "תוצאת סיום" both
    present in the ``mp`` field) and returns a list of enriched event dicts.

    Each entry contains:
        home_name_he, away_name_he, league_he, league_en,
        odds_home, odds_draw, odds_away, commence_time
    """
    events: list[Dict[str, Any]] = []
    markets: list[Dict[str, Any]] = data.get("markets") or []

    for market in markets:
        mp: str = market.get("mp") or ""
        if "1X2" not in mp or "תוצאת סיום" not in mp:
            continue

        desc: str = market.get("desc") or ""
        if " - " not in desc:
            continue

        home_he, away_he = desc.split(" - ", 1)
        home_he = home_he.strip()
        away_he = away_he.strip()

        league_he: str = market.get("league") or ""
        league_en: str = _map_league(league_he)

        e_date: int = market.get("e_date") or 0
        m_hour: str = str(market.get("m_hour") or "0000").zfill(4)
        commence_time = _parse_edate(e_date, m_hour)

        outcomes: list[Dict[str, Any]] = market.get("outcomes") or []
        odds = _extract_1x2_odds(outcomes)
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


def _he_name_for_english(english_name: str) -> Optional[str]:
    """
    Resolve an English team name to its Hebrew equivalent via team_registry.

    Example: "Barcelona" → "ברצלונה"
    """
    canonical = resolve_team(english_name)
    if canonical:
        return get_source_name_he(canonical)
    return None


def _events_match(
    event: Dict[str, Any],
    home_team_name: str,
    away_team_name: str,
) -> bool:
    """
    Return True if an event matches the requested home/away team names.

    Matching strategy (in priority order):
    1. Direct Hebrew lookup via team_registry
    2. Canonical name resolution on both sides via resolve_team
    """
    home_he = event["home_name_he"]
    away_he = event["away_name_he"]

    expected_home_he = _he_name_for_english(home_team_name)
    expected_away_he = _he_name_for_english(away_team_name)

    if expected_home_he and expected_away_he:
        if home_he == expected_home_he and away_he == expected_away_he:
            return True
        # Hebrew spelling may differ between registry and source; fall through
        # to canonical comparison before giving up.

    # Fallback: resolve both sides to canonical and compare
    home_canonical = resolve_team(home_he)
    away_canonical = resolve_team(away_he)
    req_home_canonical = resolve_team(home_team_name)
    req_away_canonical = resolve_team(away_team_name)

    if home_canonical and away_canonical and req_home_canonical and req_away_canonical:
        return home_canonical == req_home_canonical and away_canonical == req_away_canonical

    return False


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


# ---------------------------------------------------------------------------
# Shared API flow
# ---------------------------------------------------------------------------


def _fetch_all_soccer_events() -> tuple[list[Dict[str, Any]], Optional[str]]:
    """
    Call GetCMobileLine and parse all 1X2 soccer markets.

    Returns:
        (events, error) — events is a list of parsed event dicts,
        error is a string describing the failure or None on success.
    """
    session = _get_session()
    try:
        response = session.get(
            _API_URL,
            headers=_build_headers(),
            timeout=TIMEOUT,
        )
    except requests.RequestException as exc:
        return [], f"Network error reaching winner.co.il: {exc}"

    if response.status_code != 200:
        return [], (
            f"winner.co.il returned HTTP {response.status_code} "
            f"from GetCMobileLine"
        )

    try:
        data = response.json()
    except ValueError as exc:
        return [], f"Invalid JSON from winner.co.il: {exc}"

    try:
        events = _parse_soccer_markets(data)
    except Exception as exc:
        return [], f"Error parsing winner.co.il response: {exc}"

    return events, None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def fetch_winner_odds(home_team_name: str, away_team_name: str) -> Dict[str, Any]:
    """
    Fetch 1X2 odds for a specific match from winner.co.il.

    Calls GetCMobileLine, parses all 1X2 soccer markets, and returns odds for
    the requested fixture.

    Args:
        home_team_name: Home team name in English (e.g., "Barcelona").
        away_team_name: Away team name in English (e.g., "Atletico Madrid").

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
    events, error = _fetch_all_soccer_events()
    if error:
        return _error_dict(home_team_name, away_team_name, error)

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
        league: Optional English league name to filter by (e.g., "Champions League").
                Matching is case-insensitive substring. Pass None to return all.

    Returns:
        Dict with keys:
            events: list of odds dicts (one per soccer event)
            error: str | None — set on API failure so callers can distinguish
                   empty results from fetch errors
    """
    events, error = _fetch_all_soccer_events()
    if error:
        return {"events": [], "error": error}

    results: list[Dict[str, Any]] = []
    league_filter = league.lower() if league else None

    for event in events:
        if league_filter and league_filter not in event["league_en"].lower():
            continue

        home_en = resolve_team(event["home_name_he"]) or event["home_name_he"]
        away_en = resolve_team(event["away_name_he"]) or event["away_name_he"]

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
