"""Parser tests — no DB dependency.

Covers every grammar feature defined in parser.py:
  - simple eq (plain bare word)
  - quoted value (verbatim, no slug expansion)
  - slug expansion (hyphen → space)
  - range ops: >, <, >=, <=
  - inclusive range: low-high
  - list (comma-separated)
  - negation prefix !
  - case-insensitive keys
  - empty / whitespace DSL → empty list
  - unknown key → ParseError
  - repeated keys → AND semantics (two clauses)
"""
from __future__ import annotations

import pytest

from soccersmartbet.webapp.query.parser import FilterClause, ParseError, parse


# ---------------------------------------------------------------------------
# 1. Empty / whitespace → no clauses
# ---------------------------------------------------------------------------


def test_empty_string_returns_no_clauses() -> None:
    assert parse("") == []


def test_whitespace_only_returns_no_clauses() -> None:
    assert parse("   \t\n  ") == []


# ---------------------------------------------------------------------------
# 2. Simple eq — plain bare word
# ---------------------------------------------------------------------------


def test_simple_eq_league() -> None:
    clauses = parse("league:pl")
    assert len(clauses) == 1
    c = clauses[0]
    assert c.key == "league"
    assert c.op == "eq"
    assert c.values == ("pl",)
    assert c.negated is False


# ---------------------------------------------------------------------------
# 3. Quoted value — verbatim (no slug expansion)
# ---------------------------------------------------------------------------


def test_quoted_value_verbatim() -> None:
    clauses = parse('team:"real madrid"')
    assert len(clauses) == 1
    c = clauses[0]
    assert c.values == ("real madrid",)


# ---------------------------------------------------------------------------
# 4. Slug expansion: hyphen → space
# ---------------------------------------------------------------------------


def test_slug_expansion_hyphen_to_space() -> None:
    clauses = parse("team:real-madrid")
    assert clauses[0].values == ("real madrid",)


# ---------------------------------------------------------------------------
# 5. Range ops — individual operators
# ---------------------------------------------------------------------------


def test_range_gt() -> None:
    clauses = parse("odds:>2.5")
    c = clauses[0]
    assert c.op == "gt"
    assert c.values == (2.5,)


def test_range_lt() -> None:
    clauses = parse("odds:<1.5")
    c = clauses[0]
    assert c.op == "lt"
    assert c.values == (1.5,)


def test_range_gte() -> None:
    clauses = parse("stake:>=50")
    c = clauses[0]
    assert c.op == "gte"
    assert c.values == (50.0,)


def test_range_lte() -> None:
    clauses = parse("stake:<=200")
    c = clauses[0]
    assert c.op == "lte"
    assert c.values == (200.0,)


# ---------------------------------------------------------------------------
# 6. Inclusive range: 1.5-3.0
# ---------------------------------------------------------------------------


def test_inclusive_range() -> None:
    clauses = parse("odds:1.5-3.0")
    c = clauses[0]
    assert c.op == "between"
    assert c.values == (1.5, 3.0)


# ---------------------------------------------------------------------------
# 7. List (comma-separated)
# ---------------------------------------------------------------------------


def test_list_league() -> None:
    clauses = parse("league:pl,bundesliga,laliga")
    c = clauses[0]
    assert c.op == "in"
    assert c.values == ("pl", "bundesliga", "laliga")


def test_list_with_slug_expansion() -> None:
    clauses = parse("team:real-madrid,barcelona")
    c = clauses[0]
    assert c.op == "in"
    assert "real madrid" in c.values
    assert "barcelona" in c.values


# ---------------------------------------------------------------------------
# 8. Negation
# ---------------------------------------------------------------------------


def test_negation_draw() -> None:
    clauses = parse("outcome:!draw")
    c = clauses[0]
    assert c.op == "negated"
    assert c.negated is True
    assert c.values == ("draw",)


def test_negation_league() -> None:
    clauses = parse("league:!pl")
    c = clauses[0]
    assert c.op == "negated"
    assert c.negated is True


# ---------------------------------------------------------------------------
# 9. Case-insensitive keys
# ---------------------------------------------------------------------------


def test_key_case_insensitive_upper() -> None:
    clauses = parse("LEAGUE:pl")
    assert clauses[0].key == "league"


def test_key_case_insensitive_mixed() -> None:
    clauses = parse("League:pl")
    assert clauses[0].key == "league"


# ---------------------------------------------------------------------------
# 10. Multiple clauses in one DSL string
# ---------------------------------------------------------------------------


def test_multiple_clauses() -> None:
    clauses = parse("league:pl team:arsenal odds:>2.0")
    assert len(clauses) == 3
    keys = [c.key for c in clauses]
    assert keys == ["league", "team", "odds"]


# ---------------------------------------------------------------------------
# 11. Repeated key → two clauses (AND semantics)
# ---------------------------------------------------------------------------


def test_repeated_key_produces_two_clauses() -> None:
    clauses = parse("league:pl league:bundesliga")
    assert len(clauses) == 2
    assert all(c.key == "league" for c in clauses)
    assert clauses[0].values == ("pl",)
    assert clauses[1].values == ("bundesliga",)


# ---------------------------------------------------------------------------
# 12. Unknown key → ParseError
# ---------------------------------------------------------------------------


def test_unknown_key_raises_parse_error() -> None:
    with pytest.raises(ParseError, match="Unknown filter key"):
        parse("foo:bar")


def test_unknown_key_message_contains_key() -> None:
    with pytest.raises(ParseError, match="'xyz'"):
        parse("xyz:something")


# ---------------------------------------------------------------------------
# 13. date: plain value vs. range
# ---------------------------------------------------------------------------


def test_date_plain_eq() -> None:
    clauses = parse("date:2026-04-15")
    c = clauses[0]
    # "2026-04-15" must NOT be slug-expanded to "2026 04 15".
    # The ISO short-circuit must fire and return the value verbatim.
    assert c.key == "date"
    assert c.op == "eq"
    assert c.values == ("2026-04-15",), (
        f"Expected ('2026-04-15',) but got {c.values!r} — hyphens must not be expanded"
    )


def test_date_plain_eq_value_is_iso_string() -> None:
    """Regression: date eq value must be the raw ISO string, not space-separated."""
    clauses = parse("date:2026-04-15")
    assert clauses[0].values[0] == "2026-04-15"


def test_date_gte_range() -> None:
    clauses = parse("date:>=2026-04-01")
    c = clauses[0]
    assert c.op == "gte"
    assert c.values == ("2026-04-01",)


def test_month_plain_eq_value_is_iso_string() -> None:
    """Regression: month:YYYY-MM value must be the raw ISO string, not parsed as between."""
    clauses = parse("month:2026-04")
    c = clauses[0]
    assert c.op == "eq"
    assert c.values == ("2026-04",), (
        f"Expected ('2026-04',) but got {c.values!r} — hyphens must not be expanded"
    )


# ---------------------------------------------------------------------------
# 14. bettor and prediction keys
# ---------------------------------------------------------------------------


def test_bettor_eq() -> None:
    clauses = parse("bettor:user")
    assert clauses[0].key == "bettor"
    assert clauses[0].op == "eq"
    assert clauses[0].values == ("user",)


def test_prediction_eq() -> None:
    clauses = parse("prediction:1")
    assert clauses[0].key == "prediction"
    assert clauses[0].values == ("1",)
