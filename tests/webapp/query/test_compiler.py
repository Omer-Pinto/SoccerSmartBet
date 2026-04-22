"""Compiler tests — no DB dependency.

Tests verify:
  1. SQL-injection safety: user payload must appear only in params dict,
     never interpolated into the SQL string.
  2. Correct SQL skeleton for every supported operator.
  3. Row cap enforcement (hard max 2000).
  4. Empty AST → WHERE TRUE (match everything).
  5. Named %(name)s placeholders present in SQL, not f-string interpolation.
  6. Enum value aliases (outcome/prediction/result): home/draw/away → 1/x/2.
"""
from __future__ import annotations

import pytest

from soccersmartbet.webapp.query.compiler import compile as compile_filter
from soccersmartbet.webapp.query.parser import parse

# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _compile(dsl: str, row_cap: int = 2000):
    """Parse DSL then compile; return (sql, params)."""
    return compile_filter(parse(dsl), row_cap=row_cap)


# ---------------------------------------------------------------------------
# 1. SQL injection safety
# ---------------------------------------------------------------------------


def test_injection_payload_not_in_sql() -> None:
    """The literal injection payload must appear only in params, not in SQL.

    We pass the injection string as a quoted DSL value so the parser accepts it.
    The payload contains SQL-breaking characters; they must stay in the param
    dict only and never be interpolated into the SQL string.
    """
    # Use a quoted value so the parser treats it as a single token.
    malicious = "xleague'; DROP TABLE bets;--"
    dsl = f'league:"{malicious}"'
    sql, params = _compile(dsl)

    # The literal payload must NOT appear anywhere in the SQL string.
    assert malicious not in sql, "Injection payload leaked into SQL string!"

    # The literal payload MUST appear in params (as a bound value).
    assert any(malicious in str(v) for v in params.values()), (
        "Injection payload not found in params — binding may be broken"
    )


def test_sql_uses_named_placeholder_not_fstring() -> None:
    """SQL must use %(name)s placeholders, not raw interpolated values."""
    # Use a unique value that cannot appear in column names.
    sql, params = _compile("league:UNIQUEVAL99")
    # The bound value must not appear literally in the SQL text.
    assert "UNIQUEVAL99" not in sql
    # A named placeholder pattern must be present.
    assert "%(" in sql


def test_injection_team_payload_not_in_sql() -> None:
    """Team injection: payload stays in params."""
    # Quoted so the parser accepts the full string as a single value.
    payload = "arsenal'; DELETE FROM games;--"
    dsl = f'team:"{payload}"'
    sql, params = _compile(dsl)
    assert payload not in sql
    # Team binding wraps in ILIKE %; check the base payload is in a param value.
    assert any(payload in str(v) for v in params.values())


# ---------------------------------------------------------------------------
# 2. Operator SQL skeletons
# ---------------------------------------------------------------------------


def test_empty_dsl_produces_where_true() -> None:
    sql, params = _compile("")
    assert "WHERE TRUE" in sql
    assert params == {"row_cap": 2000}


def test_eq_league_sql_shape() -> None:
    # Use a value that cannot appear in any column name or SQL keyword.
    sql, params = _compile("league:PREMIERLEAGUE99")
    assert "g.league" in sql
    assert "ILIKE" in sql
    assert "PREMIERLEAGUE99" not in sql  # value must be in params only


def test_gt_odds_sql_shape() -> None:
    sql, params = _compile("odds:>2.5")
    assert "b.odds > " in sql
    assert 2.5 in params.values()


def test_lt_odds_sql_shape() -> None:
    sql, params = _compile("odds:<1.5")
    assert "b.odds < " in sql
    assert 1.5 in params.values()


def test_gte_stake_sql_shape() -> None:
    sql, params = _compile("stake:>=50")
    assert "b.stake >= " in sql
    assert 50.0 in params.values()


def test_lte_stake_sql_shape() -> None:
    sql, params = _compile("stake:<=200")
    assert "b.stake <= " in sql
    assert 200.0 in params.values()


def test_between_odds_sql_shape() -> None:
    sql, params = _compile("odds:1.5-3.0")
    assert "BETWEEN" in sql
    assert 1.5 in params.values()
    assert 3.0 in params.values()


def test_in_list_league_sql_shape() -> None:
    sql, params = _compile("league:pl,bundesliga,laliga")
    assert "IN (" in sql
    # Three placeholders should be in params (plus row_cap)
    value_params = {k: v for k, v in params.items() if k != "row_cap"}
    assert len(value_params) == 3
    values = set(value_params.values())
    assert "pl" in values
    assert "bundesliga" in values
    assert "laliga" in values


def test_negated_clause_wraps_not() -> None:
    sql, params = _compile("outcome:!draw")
    assert "NOT" in sql


def test_team_compiles_to_home_or_away() -> None:
    sql, params = _compile("team:arsenal")
    assert "g.home_team ILIKE" in sql
    assert "g.away_team ILIKE" in sql
    assert "OR" in sql


def test_date_clause_uses_match_date() -> None:
    """date: compiles to direct g.match_date comparison (already ISR-local DATE)."""
    sql, params = _compile("date:2026-04-15")
    assert "g.match_date" in sql


def test_date_eq_param_is_iso_string() -> None:
    """Regression: date eq param must be '2026-04-15', not '2026 04 15' (no spaces)."""
    _, params = _compile("date:2026-04-15")
    value_params = {k: v for k, v in params.items() if k != "row_cap"}
    assert len(value_params) == 1
    bound = next(iter(value_params.values()))
    assert bound == "2026-04-15", (
        f"Expected '2026-04-15' but got {bound!r} — hyphens must not be expanded to spaces"
    )


def test_month_clause_extracts_year_and_month() -> None:
    sql, params = _compile("month:2026-04")
    assert "EXTRACT(YEAR" in sql
    assert "EXTRACT(MONTH" in sql
    # month: builds a TIMESTAMP from match_date + kickoff_time then converts to ISR
    assert "Asia/Jerusalem" in sql
    assert "g.match_date" in sql
    assert "g.kickoff_time" in sql


def test_month_eq_params_are_integers() -> None:
    """Regression: month:YYYY-MM must bind integer year and month, not floats or strings."""
    _, params = _compile("month:2026-04")
    value_params = {k: v for k, v in params.items() if k != "row_cap"}
    assert len(value_params) == 2
    values = set(value_params.values())
    assert 2026 in values, f"Year 2026 not found in params: {value_params}"
    assert 4 in values, f"Month 4 not found in params: {value_params}"


def test_bettor_clause() -> None:
    sql, params = _compile("bettor:user")
    assert "b.bettor" in sql
    assert "user" not in sql  # value in params, not SQL


def test_prediction_clause() -> None:
    sql, params = _compile("prediction:1")
    assert "b.prediction" in sql


# ---------------------------------------------------------------------------
# 3. Row cap
# ---------------------------------------------------------------------------


def test_row_cap_default_2000() -> None:
    _, params = _compile("")
    assert params["row_cap"] == 2000


def test_row_cap_custom_respected() -> None:
    _, params = _compile("", row_cap=500)
    assert params["row_cap"] == 500


def test_row_cap_hard_max_2000() -> None:
    _, params = _compile("", row_cap=9999)
    assert params["row_cap"] == 2000


# ---------------------------------------------------------------------------
# 4. Multi-clause AND
# ---------------------------------------------------------------------------


def test_multiple_clauses_joined_with_and() -> None:
    sql, params = _compile("league:pl bettor:user")
    # Both columns should appear and they should be AND-joined.
    assert "g.league" in sql
    assert "b.bettor" in sql
    assert "AND" in sql


# ---------------------------------------------------------------------------
# 5. Base SELECT columns present
# ---------------------------------------------------------------------------


def test_base_select_contains_expected_columns() -> None:
    sql, _ = _compile("")
    for col in (
        "b.bet_id",
        "b.stake",
        "b.odds",
        "g.league",
        "g.outcome",
        "g.match_date",
        "g.kickoff_time",
    ):
        assert col in sql, f"Expected column {col!r} missing from SELECT"


def test_order_limit_present() -> None:
    sql, _ = _compile("")
    assert "ORDER BY g.match_date DESC, g.kickoff_time DESC" in sql
    assert "LIMIT %(row_cap)s" in sql


# ---------------------------------------------------------------------------
# 6. Enum value aliases — outcome / prediction / result
# ---------------------------------------------------------------------------


def test_outcome_draw_maps_to_x() -> None:
    """outcome:draw must emit exact-eq (not ILIKE) with canonical value 'x'."""
    sql, params = _compile("outcome:draw")
    assert "g.outcome = " in sql
    assert "ILIKE" not in sql
    assert "x" in params.values()


def test_outcome_home_maps_to_1() -> None:
    sql, params = _compile("outcome:home")
    assert "g.outcome = " in sql
    assert "1" in params.values()


def test_outcome_away_maps_to_2() -> None:
    sql, params = _compile("outcome:away")
    assert "g.outcome = " in sql
    assert "2" in params.values()


def test_outcome_canonical_x_accepted_verbatim() -> None:
    """outcome:x must work — canonical values are self-aliased."""
    sql, params = _compile("outcome:x")
    assert "g.outcome = " in sql
    assert "x" in params.values()


def test_outcome_list_home_away_maps_to_in_1_2() -> None:
    """outcome:home,away -> IN ('1', '2') with exact-eq semantics."""
    sql, params = _compile("outcome:home,away")
    assert "g.outcome IN" in sql
    value_params = {k: v for k, v in params.items() if k != "row_cap"}
    assert set(value_params.values()) == {"1", "2"}


def test_prediction_home_maps_to_1() -> None:
    sql, params = _compile("prediction:home")
    assert "b.prediction = " in sql
    assert "ILIKE" not in sql
    assert "1" in params.values()


def test_result_draw_maps_to_x() -> None:
    sql, params = _compile("result:draw")
    assert "b.result = " in sql
    assert "x" in params.values()


def test_outcome_unknown_value_raises_parse_error() -> None:
    """An unrecognised alias for an enum key must raise ParseError."""
    from soccersmartbet.webapp.query.parser import ParseError

    with pytest.raises(ParseError, match="Invalid value"):
        _compile("outcome:unknown_word")


def test_negated_outcome_draw_maps_to_x() -> None:
    """outcome:!draw -> NOT (g.outcome = 'x')."""
    sql, params = _compile("outcome:!draw")
    assert "NOT" in sql
    assert "g.outcome = " in sql
    assert "x" in params.values()
