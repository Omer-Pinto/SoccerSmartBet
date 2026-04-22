"""
Team name registry with canonical name resolution across FotMob, football-data.org, winner.co.il.

Loaded on first use from the PostgreSQL ``teams`` table (DATABASE_URL env var).
The full team list is cached in module-level memory after the first DB read — no
repeated round-trips during a single process lifetime.

Public API is identical to the previous JSON-backed version so all callers
remain unchanged.
"""

from __future__ import annotations

import logging
import os
import threading
import unicodedata
from typing import Optional

from soccersmartbet.db import get_cursor

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Module-level cache
# ---------------------------------------------------------------------------

# Populated lazily on first call to _ensure_loaded()
_teams: list[dict] = []
_index: dict[str, str] = {}
_loaded: bool = False
_lock: threading.Lock = threading.Lock()


def _load_from_db() -> list[dict]:
    """Read all rows from the teams table and return as a list of dicts."""
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise RuntimeError(
            "DATABASE_URL environment variable is not set; cannot load team registry from DB."
        )

    with get_cursor(commit=False) as cur:
        cur.execute(
            """
            SELECT
                canonical_name,
                short_name,
                aliases,
                fotmob_id,
                football_data_id,
                winner_name_he,
                league,
                country
            FROM teams
            ORDER BY canonical_name
            """
        )
        rows = cur.fetchall()

    teams: list[dict] = []
    for row in rows:
        (
            canonical_name,
            short_name,
            aliases,
            fotmob_id,
            football_data_id,
            winner_name_he,
            league,
            country,
        ) = row
        teams.append(
            {
                "canonical_name": canonical_name,
                "short_name": short_name,
                # psycopg3 returns JSONB as a Python object (list or None)
                "aliases": aliases if isinstance(aliases, list) else [],
                "fotmob_id": fotmob_id,
                "football_data_id": football_data_id,
                "winner_name_he": winner_name_he,
                "league": league,
                "country": country,
            }
        )
    return teams


def _ensure_loaded() -> None:
    """Load teams from DB into module cache if not already loaded.

    Uses double-checked locking so that once ``_loaded`` is True the fast path
    (no lock acquisition) is taken by every subsequent caller.
    """
    global _teams, _index, _loaded
    if _loaded:
        return
    with _lock:
        # Second check inside the lock: a concurrent thread may have completed
        # the load between the outer check and acquiring the lock.
        if _loaded:
            return
        new_teams = _load_from_db()
        new_index = _build_index(new_teams)
        _teams = new_teams
        _index = new_index
        _loaded = True
    logger.info("team_registry: loaded %d teams from DB", len(_teams))


def reload_registry() -> None:
    """Force-reload teams from DB. Call at the start of each flow run.

    The slow DB round-trip is performed *outside* the lock so other reads are
    not blocked for its duration.  All three globals are then swapped atomically
    under the lock so no reader ever sees a partially-updated state.
    """
    global _teams, _index, _loaded
    new_teams = _load_from_db()
    new_index = _build_index(new_teams)
    with _lock:
        _teams = new_teams
        _index = new_index
        _loaded = True
    logger.info("team_registry: reloaded %d teams from DB", len(_teams))


# ---------------------------------------------------------------------------
# Normalization
# ---------------------------------------------------------------------------


def normalize_team_name(name: str) -> str:
    """Lowercase, strip accents, remove common prefix/suffix tokens.

    Shared normalization used by both team_registry and fotmob_client.
    """
    # Accent folding via Unicode decomposition
    nfkd = unicodedata.normalize("NFKD", name)
    ascii_str = "".join(c for c in nfkd if not unicodedata.combining(c))
    n = ascii_str.lower().strip()

    # Manual fallback for characters that survive NFKD unchanged
    for src, dst in (("ü", "u"), ("ö", "o"), ("ä", "a"), ("ß", "ss")):
        n = n.replace(src, dst)

    # Normalize punctuation that varies between sources
    n = n.replace("-", " ").replace("'", "").replace(".", "")

    # Strip suffixes
    for suffix in (" fc", " cf", " sc", " afc", " club", " sporting"):
        if n.endswith(suffix):
            n = n[: -len(suffix)]

    # Strip prefixes
    for prefix in ("fc ", "cf ", "sc ", "afc ", "club ", "sporting "):
        if n.startswith(prefix):
            n = n[len(prefix):]

    return n.strip()


def _build_index(teams: list[dict]) -> dict[str, str]:
    idx: dict[str, str] = {}
    for team in teams:
        canonical = team["canonical_name"]
        # Index the canonical name itself
        idx[normalize_team_name(canonical)] = canonical
        # Index every alias
        for alias in team.get("aliases") or []:
            norm = normalize_team_name(alias)
            if norm and norm not in idx:
                idx[norm] = canonical
        # Index short_name
        short = team.get("short_name")
        if short:
            norm = normalize_team_name(short)
            if norm and norm not in idx:
                idx[norm] = canonical
        # Index Hebrew name (winner.co.il)
        he_name = team.get("winner_name_he")
        if he_name:
            if he_name not in idx:
                idx[he_name] = canonical
    return idx


# ---------------------------------------------------------------------------
# Levenshtein (pure Python DP — no new deps)
# ---------------------------------------------------------------------------


def _levenshtein(a: str, b: str) -> int:
    """Compute edit distance between two strings."""
    if len(a) < len(b):
        a, b = b, a
    if not b:
        return len(a)
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        curr = [i]
        for j, cb in enumerate(b, 1):
            curr.append(min(prev[j] + 1, curr[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = curr
    return prev[-1]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def resolve_team(name: str) -> Optional[str]:
    """Resolve any team name string to its canonical name.

    Resolution order:
      1. Exact match after normalization
      2. Substring match (normalized query contained in a normalized key, or vice-versa)
      3. Levenshtein distance <= min(3, len(query)//3) against all index keys

    Args:
        name: Any team name variant (e.g. "Barça", "Man City", "ברצלונה").

    Returns:
        Canonical name string, or None if no confident match found.
    """
    _ensure_loaded()
    norm = normalize_team_name(name)

    # 1. Exact
    if norm in _index:
        return _index[norm]

    # 2. Substring — query inside key or key inside query
    for key, canonical in _index.items():
        if norm in key or key in norm:
            return canonical

    # 3. Fuzzy Levenshtein
    threshold = max(1, min(3, len(norm) // 3))
    best_dist = threshold + 1
    best_canonical: Optional[str] = None
    for key, canonical in _index.items():
        dist = _levenshtein(norm, key)
        if dist < best_dist:
            best_dist = dist
            best_canonical = canonical

    return best_canonical


def get_team_aliases(canonical: str) -> list[str]:
    """Return all known aliases for a canonical team name.

    Args:
        canonical: Exact canonical name (e.g. "FC Barcelona").

    Returns:
        List of alias strings; empty list if team not found.
    """
    _ensure_loaded()
    for team in _teams:
        if team["canonical_name"] == canonical:
            return list(team.get("aliases") or [])
    return []


def get_source_id(canonical: str, source: str) -> Optional[int]:
    """Return the numeric ID used by a data source for a team.

    Args:
        canonical: Exact canonical name.
        source: One of "fotmob", "football_data".

    Returns:
        Integer ID, or None if unknown/unmapped.
    """
    _ensure_loaded()
    field_map = {"fotmob": "fotmob_id", "football_data": "football_data_id"}
    if source not in field_map:
        raise ValueError(f"Unknown source '{source}'. Valid: {list(field_map)}")
    field = field_map[source]
    for team in _teams:
        if team["canonical_name"] == canonical:
            return team.get(field)
    return None


def get_source_name_he(canonical: str) -> Optional[str]:
    """Return the Hebrew name used by winner.co.il for a team.

    Args:
        canonical: Exact canonical name.

    Returns:
        Hebrew name string, or None if unknown/unmapped.
    """
    _ensure_loaded()
    for team in _teams:
        if team["canonical_name"] == canonical:
            return team.get("winner_name_he")
    return None
