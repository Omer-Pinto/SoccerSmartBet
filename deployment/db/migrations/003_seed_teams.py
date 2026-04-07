"""Migration 003: Seed the teams table from teams_registry.json.

Run this script once against a running DB that has the teams table created
but empty. Safe to re-run — uses INSERT ON CONFLICT DO NOTHING.

Usage:
    DATABASE_URL=postgresql://... python deployment/db/migrations/003_seed_teams.py
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path

import psycopg2
import psycopg2.extras

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

_REGISTRY_PATH = (
    Path(__file__).parent.parent.parent.parent
    / "src"
    / "soccersmartbet"
    / "data"
    / "teams_registry.json"
)

_INSERT_SQL = """
INSERT INTO teams (
    canonical_name,
    aliases,
    fotmob_id,
    football_data_id,
    winner_name_he,
    league,
    country
)
VALUES (
    %(canonical_name)s,
    %(aliases)s,
    %(fotmob_id)s,
    %(football_data_id)s,
    %(winner_name_he)s,
    %(league)s,
    %(country)s
)
ON CONFLICT (canonical_name) DO NOTHING
"""


def run() -> None:
    """Read teams_registry.json and insert all teams into the teams table."""
    database_url = os.environ["DATABASE_URL"]

    teams: list[dict] = json.loads(_REGISTRY_PATH.read_text(encoding="utf-8"))
    logger.info("Loaded %d teams from %s", len(teams), _REGISTRY_PATH)

    conn = psycopg2.connect(database_url)
    try:
        with conn:
            with conn.cursor() as cur:
                inserted = 0
                skipped = 0
                for team in teams:
                    aliases = team.get("aliases") or []
                    cur.execute(
                        _INSERT_SQL,
                        {
                            "canonical_name": team["canonical_name"],
                            "aliases": psycopg2.extras.Json(aliases),
                            "fotmob_id": team.get("fotmob_id"),
                            "football_data_id": team.get("football_data_id"),
                            "winner_name_he": team.get("winner_name_he"),
                            "league": team.get("league"),
                            "country": team.get("country"),
                        },
                    )
                    if cur.rowcount == 1:
                        inserted += 1
                    else:
                        skipped += 1
        logger.info("Done: %d inserted, %d skipped (already existed)", inserted, skipped)
    finally:
        conn.close()


if __name__ == "__main__":
    run()
