"""
Pre-Gambling Flow Tools Package.

This package contains "dumb fetcher" tools used by Pre-Gambling Flow agents
to retrieve raw data from external APIs. Tools do NOT perform AI analysis -
they only fetch and return structured data.

Available Tools:
- fetch_venue: Retrieve venue information for a match
"""

from .fetch_venue import fetch_venue

__all__ = ["fetch_venue"]
