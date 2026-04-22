"""Query DSL engine — public API re-export.

Wave 12 routes import from here::

    from soccersmartbet.webapp.query import run_filter, FilterResult, ParseError
"""
from __future__ import annotations

from soccersmartbet.webapp.query.models import FilterResult
from soccersmartbet.webapp.query.parser import FilterClause, ParseError
from soccersmartbet.webapp.query.service import run_filter

__all__ = [
    "FilterClause",
    "FilterResult",
    "ParseError",
    "run_filter",
]
