"""Shared mutable runtime state for the SoccerSmartBet single-process app.

Single source of truth for in-process state read by HTTP handlers and
written by the wall-clock poller. Kept dependency-free so any layer can
import without circular issues.
"""
from __future__ import annotations

# Mutable single-element list holding the ISO-8601 ISR string of the most
# recent poller tick. Updated by triggers._wall_clock_poller every iteration,
# read by webapp.app's /api/health endpoint. Empty string until the first
# poller tick. CPython GIL guarantees readers see a complete value.
LAST_POLLER_TICK: list[str] = [""]
