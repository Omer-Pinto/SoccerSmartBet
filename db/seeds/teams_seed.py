"""
Seed the teams table from football-data.org.

Usage:
    python db/seeds/teams_seed.py --output json
    python db/seeds/teams_seed.py --output db
    python db/seeds/teams_seed.py --output db --competition PL --competition PD
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any

import requests
from dotenv import load_dotenv

load_dotenv()

FOOTBALL_DATA_API_KEY = os.getenv("FOOTBALL_DATA_API_KEY")
BASE_URL = "https://api.football-data.org/v4"
TIMEOUT = 15

# Competition codes to seed; covers top 5 leagues + UEFA competitions
DEFAULT_COMPETITIONS = ["PL", "PD", "SA", "BL1", "FL1", "CL", "EC", "WC"]

HEADERS = {
    "X-Auth-Token": FOOTBALL_DATA_API_KEY or "",
}


# ---------------------------------------------------------------------------
# football-data.org fetch
# ---------------------------------------------------------------------------

def fetch_teams_for_competition(competition_code: str) -> list[dict[str, Any]]:
    """Fetch all teams for a competition from football-data.org.

    Args:
        competition_code: e.g. "PL", "PD", "SA".

    Returns:
        List of raw team dicts from the API.
    """
    url = f"{BASE_URL}/competitions/{competition_code}/teams"
    response = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
    response.raise_for_status()
    return response.json().get("teams", [])


def fetch_all_teams(competition_codes: list[str]) -> list[dict[str, Any]]:
    """Fetch and deduplicate teams across all requested competitions.

    Args:
        competition_codes: List of competition code strings.

    Returns:
        Deduplicated list of team dicts keyed by football_data_id.
    """
    seen: dict[int, dict[str, Any]] = {}
    for code in competition_codes:
        print(f"Fetching {code}...", file=sys.stderr)
        teams = fetch_teams_for_competition(code)
        for t in teams:
            tid = t.get("id")
            if tid and tid not in seen:
                seen[tid] = t
        print(f"  -> {len(teams)} teams", file=sys.stderr)
    return list(seen.values())


# ---------------------------------------------------------------------------
# Normalise API data → registry format
# ---------------------------------------------------------------------------

def normalise_team(raw: dict[str, Any]) -> dict[str, Any]:
    """Convert football-data.org team object to registry dict.

    Args:
        raw: Raw team dict from football-data.org API.

    Returns:
        Dict with canonical_name, short_name, aliases, football_data_id, league, country.
    """
    area = raw.get("area", {})
    return {
        "canonical_name": raw.get("name", ""),
        "short_name": raw.get("shortName") or raw.get("tla") or None,
        "aliases": list(
            {raw.get("shortName"), raw.get("tla"), raw.get("name")} - {None, ""}
        ),
        "football_data_id": raw.get("id"),
        "fotmob_id": None,
        "winner_name_he": None,
        "league": None,  # competition not present in team-level response
        "country": area.get("name"),
    }


# ---------------------------------------------------------------------------
# Output modes
# ---------------------------------------------------------------------------

def output_json(teams: list[dict[str, Any]]) -> None:
    """Print registry-format JSON to stdout."""
    print(json.dumps(teams, ensure_ascii=False, indent=2))


def output_db(teams: list[dict[str, Any]]) -> None:
    """Upsert teams into the PostgreSQL teams table.

    Uses ON CONFLICT (canonical_name) DO UPDATE so it is safe to re-run.
    Requires DATABASE_URL or individual PG* env vars.
    """
    import psycopg2  # noqa: PLC0415

    database_url = os.getenv("DATABASE_URL")
    if database_url:
        conn = psycopg2.connect(database_url)
    else:
        conn = psycopg2.connect(
            host=os.getenv("PGHOST", "localhost"),
            port=int(os.getenv("PGPORT", "5432")),
            dbname=os.getenv("PGDATABASE", "soccersmartbet"),
            user=os.getenv("PGUSER", "postgres"),
            password=os.getenv("PGPASSWORD", ""),
        )

    upsert_sql = """
        INSERT INTO teams (
            canonical_name, short_name, aliases,
            football_data_id, fotmob_id, winner_name_he,
            league, country
        ) VALUES (
            %(canonical_name)s, %(short_name)s, %(aliases)s,
            %(football_data_id)s, %(fotmob_id)s, %(winner_name_he)s,
            %(league)s, %(country)s
        )
        ON CONFLICT (canonical_name) DO UPDATE SET
            short_name       = EXCLUDED.short_name,
            aliases          = EXCLUDED.aliases,
            football_data_id = EXCLUDED.football_data_id,
            fotmob_id        = COALESCE(EXCLUDED.fotmob_id, teams.fotmob_id),
            winner_name_he   = COALESCE(EXCLUDED.winner_name_he, teams.winner_name_he),
            league           = COALESCE(EXCLUDED.league, teams.league),
            country          = EXCLUDED.country
    """

    with conn:
        with conn.cursor() as cur:
            for team in teams:
                row = dict(team)
                row["aliases"] = json.dumps(row["aliases"], ensure_ascii=False)
                cur.execute(upsert_sql, row)
    conn.close()
    print(f"Upserted {len(teams)} teams into DB.", file=sys.stderr)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Seed teams table from football-data.org"
    )
    parser.add_argument(
        "--output",
        choices=["json", "db"],
        default="json",
        help="Output mode: print JSON or write to PostgreSQL (default: json)",
    )
    parser.add_argument(
        "--competition",
        action="append",
        dest="competitions",
        metavar="CODE",
        help="Competition code to fetch (repeatable). Default: PL PD SA BL1 FL1 CL EC WC",
    )
    args = parser.parse_args()

    if not FOOTBALL_DATA_API_KEY:
        print("ERROR: FOOTBALL_DATA_API_KEY not set in environment.", file=sys.stderr)
        sys.exit(1)

    competition_codes = args.competitions or DEFAULT_COMPETITIONS
    raw_teams = fetch_all_teams(competition_codes)
    teams = [normalise_team(t) for t in raw_teams]
    print(f"Total unique teams: {len(teams)}", file=sys.stderr)

    if args.output == "json":
        output_json(teams)
    else:
        output_db(teams)


if __name__ == "__main__":
    main()
