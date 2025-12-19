from __future__ import annotations

import datetime
import os
from dataclasses import dataclass
from typing import Any, Callable

import requests

from soccersmartbet.pre_gambling_flow.structured_outputs import SelectedGame, SelectedGames

BASE_URL = "https://api.football-data.org/v4"
TIMEOUT_S = 10
FOOTBALL_DATA_API_KEY_ENV = "FOOTBALL_DATA_API_KEY"


@dataclass(frozen=True, slots=True)
class CandidateFixture:
    match_id: int
    home_team: str
    away_team: str
    utc_date: str
    competition_name: str
    competition_code: str | None
    venue: str | None

    @property
    def kickoff_datetime_utc(self) -> datetime.datetime | None:
        return _parse_utc_datetime(self.utc_date)

    @property
    def match_date(self) -> str:
        dt = self.kickoff_datetime_utc
        if dt is None:
            return self.utc_date[:10]
        return dt.date().isoformat()

    @property
    def kickoff_time(self) -> str:
        dt = self.kickoff_datetime_utc
        if dt is None:
            return "00:00"
        return dt.time().replace(second=0, microsecond=0).strftime("%H:%M")


LlmSelectCallable = Callable[[list[CandidateFixture], datetime.date, int], SelectedGames | dict[str, Any]]


def run_smart_game_picker(
    date: datetime.date,
    max_games: int = 8,
    session: requests.Session | None = None,
    llm_select: LlmSelectCallable | None = None,
) -> SelectedGames:
    """Select today's most interesting games.

    If `llm_select` is provided, it is used to choose games and generate the
    structured output.

    The `llm_select` callable signature is expected to be:
        (candidates: list[CandidateFixture], date: datetime.date, max_games: int)
            -> SelectedGames | dict

    When returning a `dict`, it will be validated into `SelectedGames`.
    """

    if max_games < 3:
        raise ValueError("max_games must be >= 3")

    fixtures = fetch_candidate_fixtures(date=date, session=session)

    if not fixtures:
        raise RuntimeError(f"No fixtures returned for date={date.isoformat()}")

    if llm_select is not None:
        selected = llm_select(fixtures, date, max_games)
        return _coerce_selected_games(selected)

    return _heuristic_select(fixtures=fixtures, date=date, max_games=max_games)


def fetch_candidate_fixtures(
    date: datetime.date,
    session: requests.Session | None = None,
) -> list[CandidateFixture]:
    api_key = os.getenv(FOOTBALL_DATA_API_KEY_ENV)
    if not api_key:
        raise RuntimeError(f"{FOOTBALL_DATA_API_KEY_ENV} not found in environment")

    headers = {"X-Auth-Token": api_key}
    date_str = date.isoformat()

    params = {
        "dateFrom": date_str,
        "dateTo": date_str,
    }

    active_session = session or requests.Session()
    response = active_session.get(
        f"{BASE_URL}/matches",
        headers=headers,
        params=params,
        timeout=TIMEOUT_S,
    )

    try:
        response.raise_for_status()
    except requests.HTTPError as exc:
        detail = getattr(response, "text", "")
        detail_str = f"; body={detail[:500]!r}" if detail else ""
        raise RuntimeError(
            f"football-data.org fixtures API error: {response.status_code}{detail_str}"
        ) from exc

    payload = response.json() or {}
    matches = payload.get("matches") or []

    fixtures: list[CandidateFixture] = []
    for match in matches:
        match_id = match.get("id")
        home = (match.get("homeTeam") or {}).get("name")
        away = (match.get("awayTeam") or {}).get("name")
        utc_date = match.get("utcDate")
        competition = match.get("competition") or {}
        competition_name = competition.get("name")
        competition_code = competition.get("code")
        venue = match.get("venue")

        if not isinstance(match_id, int):
            continue
        if not isinstance(home, str) or not home.strip():
            continue
        if not isinstance(away, str) or not away.strip():
            continue
        if not isinstance(utc_date, str) or len(utc_date) < 10:
            continue
        if not isinstance(competition_name, str) or not competition_name.strip():
            continue

        fixtures.append(
            CandidateFixture(
                match_id=match_id,
                home_team=home.strip(),
                away_team=away.strip(),
                utc_date=utc_date,
                competition_name=competition_name.strip(),
                competition_code=(
                    competition_code.strip() if isinstance(competition_code, str) else None
                ),
                venue=venue.strip() if isinstance(venue, str) and venue.strip() else None,
            )
        )

    return fixtures


def _heuristic_select(
    fixtures: list[CandidateFixture],
    date: datetime.date,
    max_games: int,
) -> SelectedGames:
    if len(fixtures) < 3:
        raise RuntimeError(
            f"Not enough fixtures to select a slate (need>=3, got={len(fixtures)})"
        )

    fixtures_sorted = sorted(
        fixtures,
        key=lambda f: (
            -_competition_priority(f.competition_code, f.competition_name),
            (f.kickoff_datetime_utc or datetime.datetime.min.replace(tzinfo=datetime.UTC)),
            f.home_team,
            f.away_team,
        ),
    )

    selected: list[CandidateFixture] = []
    selected_ids: set[int] = set()
    leagues_selected: set[str] = set()

    # Pass 1: aim for diversity across competitions.
    for fixture in fixtures_sorted:
        if len(selected) >= max_games:
            break
        if fixture.match_id in selected_ids:
            continue
        if fixture.competition_name in leagues_selected:
            continue

        selected.append(fixture)
        selected_ids.add(fixture.match_id)
        leagues_selected.add(fixture.competition_name)

        if len(selected) >= 3 and len(leagues_selected) >= 3:
            # Early exit once we have the minimum slate and diversity.
            break

    # Pass 2: fill remaining slots regardless of league.
    if len(selected) < max_games:
        for fixture in fixtures_sorted:
            if len(selected) >= max_games:
                break
            if fixture.match_id in selected_ids:
                continue
            selected.append(fixture)
            selected_ids.add(fixture.match_id)

    if len(selected) < 3:
        raise RuntimeError(
            "Unable to select minimum 3 games from fixtures (insufficient viable matches)"
        )

    games = [
        SelectedGame(
            home_team=f.home_team,
            away_team=f.away_team,
            match_date=f.match_date,
            kickoff_time=f.kickoff_time,
            league=f.competition_name,
            venue=f.venue,
            justification=_build_heuristic_justification(f),
        )
        for f in selected[:max_games]
    ]

    return SelectedGames(
        games=games,
        selection_reasoning=(
            "Deterministic selection: prioritized high-prestige competitions "
            "and aimed for league diversity to produce a balanced daily slate. "
            f"Selected {len(games)} matches for {date.isoformat()} (max_games={max_games})."
        ),
    )


def _competition_priority(code: str | None, name: str) -> int:
    code_upper = (code or "").upper()
    priority_by_code = {
        "CL": 100,
        "EL": 90,
        "PL": 80,
        "PD": 78,
        "SA": 76,
        "BL1": 74,
        "FL1": 72,
        "PPL": 60,
        "DED": 58,
        "BSA": 55,
        "EC": 50,
        "WC": 50,
    }
    if code_upper in priority_by_code:
        return priority_by_code[code_upper]

    name_lower = name.lower()
    if "champions league" in name_lower:
        return 100
    if "europa league" in name_lower:
        return 90
    if "premier league" in name_lower:
        return 80
    if "la liga" in name_lower:
        return 78
    if "serie a" in name_lower:
        return 76
    if "bundesliga" in name_lower:
        return 74
    if "ligue 1" in name_lower:
        return 72

    return 10


def _build_heuristic_justification(fixture: CandidateFixture) -> str:
    derby_hint = _shared_city_token_hint(fixture.home_team, fixture.away_team)
    comp = fixture.competition_name
    if derby_hint:
        return (
            f"Selected as a high-interest match in {comp}; teams share a local identifier "
            f"('{derby_hint}'), which can indicate rivalry intensity."
        )

    return (
        f"Selected from {comp} as a higher-prestige competition where match stakes and "
        "competitive intensity are typically strong, making it suitable for deeper analysis."
    )


def _shared_city_token_hint(home: str, away: str) -> str | None:
    home_tokens = {t.strip(".,-").lower() for t in home.split() if len(t) >= 4}
    away_tokens = {t.strip(".,-").lower() for t in away.split() if len(t) >= 4}
    shared = sorted(home_tokens.intersection(away_tokens))
    if not shared:
        return None
    return shared[0].title()


def _parse_utc_datetime(utc_date: str | None) -> datetime.datetime | None:
    if not utc_date:
        return None

    try:
        # football-data.org uses e.g. 2025-11-20T19:45:00Z
        if utc_date.endswith("Z"):
            return datetime.datetime.fromisoformat(utc_date.replace("Z", "+00:00"))
        return datetime.datetime.fromisoformat(utc_date)
    except ValueError:
        return None


def _coerce_selected_games(value: SelectedGames | dict[str, Any]) -> SelectedGames:
    if isinstance(value, SelectedGames):
        return value

    validate = getattr(SelectedGames, "model_validate", None)
    if callable(validate):
        return validate(value)

    parse_obj = getattr(SelectedGames, "parse_obj", None)
    if callable(parse_obj):
        return parse_obj(value)

    raise TypeError("Unable to coerce value into SelectedGames")
