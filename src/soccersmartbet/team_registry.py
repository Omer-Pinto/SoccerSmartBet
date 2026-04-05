"""
Team name registry with canonical name resolution across FotMob, football-data.org, winner.co.il.

Loaded once at import time from bundled JSON — no DB dependency at runtime.
"""

from __future__ import annotations

import json
import unicodedata
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

_REGISTRY_PATH = Path(__file__).parent / "data" / "teams_registry.json"

# Raw list of team dicts loaded from JSON
_teams: list[dict] = json.loads(_REGISTRY_PATH.read_text(encoding="utf-8"))

# normalized_name → canonical_name (reverse index built at load time)
_index: dict[str, str] = {}


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

    # Strip suffixes
    for suffix in (" fc", " cf", " sc", " afc", " club", " sporting"):
        if n.endswith(suffix):
            n = n[: -len(suffix)]

    # Strip prefixes
    for prefix in ("fc ", "cf ", "sc ", "afc ", "club ", "sporting "):
        if n.startswith(prefix):
            n = n[len(prefix):]

    return n.strip()


def _build_index() -> dict[str, str]:
    idx: dict[str, str] = {}
    for team in _teams:
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


_index = _build_index()


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
    for team in _teams:
        if team["canonical_name"] == canonical:
            return team.get("winner_name_he")
    return None
