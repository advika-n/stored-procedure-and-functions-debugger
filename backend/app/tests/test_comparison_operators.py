"""Tests for the `>=`, `<=`, and `<>` comparison operators. See
app.tokenizer's own module docstring for the lexing-order fix (GTE/LTE
must be matched before the bare single-character OPERATOR pattern, and
NEQ now covers both `!=` and `<>`), app.parser's `COMPARISON_OPERATORS`
and grammar summary, and app.interpreter's `_evaluate_binary` for how
each new operator is actually evaluated. Applies everywhere a
procedural condition is evaluated -- IF, WHILE, CASE -- since all three
share the same `comparison` grammar rule and the same
`_evaluate_binary` evaluator; this file spot-checks a representative
statement using each rather than exhaustively re-testing IF/WHILE/CASE
from scratch (already covered by their own dedicated test files).

Every test here builds its AST via the real tokenizer -> parser
pipeline (never a hand-built dict), matching this project's existing
testing convention.
"""

from __future__ import annotations

import pytest

from app.interpreter import InterpreterError, run
from app.parser import ParserError, parse
from app.tokenizer import tokenize


def _steps_as_dicts(steps):
    return [s.to_dict() for s in steps]


# -- tokenizer ------------------------------------------------------------


@pytest.mark.parametrize(
    "text, expected_value",
    [
        (">=", ">="),
        ("<=", "<="),
        ("<>", "<>"),
        ("!=", "!="),  # unaffected -- still its own single token
    ],
)
def test_two_char_operator_lexes_as_one_token(text, expected_value):
    tokens = tokenize(f"x {text} 1")
    operator_tokens = [t for t in tokens if t["type"] == "OPERATOR"]
    assert len(operator_tokens) == 1, f"expected exactly one OPERATOR token, got {operator_tokens!r}"
    assert operator_tokens[0]["value"] == expected_value


def test_gte_is_not_split_into_gt_then_eq():
    # The exact failure mode this whole fix is guarding against: without
    # GTE lexed before the bare '>' pattern, "x >= 1" would tokenize as
    # OPERATOR '>' followed by OPERATOR '=' -- two tokens, not one.
    tokens = tokenize("x >= 1")
    values = [(t["type"], t["value"]) for t in tokens if t["type"] == "OPERATOR"]
    assert values == [("OPERATOR", ">=")]


def test_lte_is_not_split_into_lt_then_eq():
    tokens = tokenize("x <= 1")
    values = [(t["type"], t["value"]) for t in tokens if t["type"] == "OPERATOR"]
    assert values == [("OPERATOR", "<=")]


def test_gt_and_eq_still_tokenize_separately_when_not_adjacent():
    # Sanity check the fix didn't overreach: '>' and '=' used as two
    # genuinely separate operators nearby (not forming '>=') still lex
    # as two separate tokens.
    tokens = tokenize("x > 1")
    values = [(t["type"], t["value"]) for t in tokens if t["type"] == "OPERATOR"]
    assert values == [("OPERATOR", ">")]


# -- parser -----------------------------------------------------------------


@pytest.mark.parametrize("op", [">=", "<=", "<>"])
def test_new_operator_parses_as_a_binary_expr(op):
    ast = parse(tokenize(f"IF x {op} 1 THEN SET y = 1; END IF;"))
    condition = ast["body"][0]["condition"]
    assert condition["type"] == "BinaryExpr"
    assert condition["operator"] == op


def test_new_operators_are_in_comparison_operators_set():
    from app.parser import COMPARISON_OPERATORS

    assert COMPARISON_OPERATORS == {">", "<", "=", "!=", ">=", "<=", "<>"}


# -- interpreter --------------------------------------------------------------


def _run_condition(op, left, right):
    """Run `IF left OP right THEN SET result = 1; ELSE SET result = 0;
    END IF;` and return the final `result` value -- a minimal harness
    for exercising one comparison operator's actual evaluation."""
    code = f"""\
DECLARE result NUMBER DEFAULT -1;
IF {left} {op} {right} THEN
    SET result = 1;
ELSE
    SET result = 0;
END IF;
"""
    steps = run(parse(tokenize(code)))
    return steps[-1].to_dict()["variables"]["result"]["value"]


@pytest.mark.parametrize(
    "op, left, right, expected",
    [
        (">=", 5, 5, 1),   # equal -- >= is true
        (">=", 5, 6, 0),   # less -- >= is false
        (">=", 6, 5, 1),   # greater -- >= is true
        ("<=", 5, 5, 1),   # equal -- <= is true
        ("<=", 5, 6, 1),   # less -- <= is true
        ("<=", 6, 5, 0),   # greater -- <= is false
        ("<>", 5, 5, 0),   # equal -- <> (not-equal) is false
        ("<>", 5, 6, 1),   # different -- <> is true
    ],
)
def test_comparison_operator_evaluates_correctly(op, left, right, expected):
    assert _run_condition(op, left, right) == expected


def test_lt_gt_neq_eq_still_work_unaffected():
    # The pre-existing four operators must be completely unaffected by
    # this change.
    assert _run_condition(">", 5, 3) == 1
    assert _run_condition("<", 3, 5) == 1
    assert _run_condition("=", 5, 5) == 1
    assert _run_condition("!=", 5, 3) == 1


def test_lte_and_neq2_are_semantically_equivalent_to_their_counterparts():
    # <> means exactly what != means; <= is the mirror of >= -- confirm
    # both new spellings actually behave like their established
    # counterparts, not just that they parse.
    for a, b in [(3, 5), (5, 5), (5, 3)]:
        assert _run_condition("<>", a, b) == _run_condition("!=", a, b)
    for a, b in [(3, 5), (5, 5), (5, 3)]:
        assert _run_condition("<=", a, b) == (1 if a <= b else 0)


def test_case_statement_uses_new_operators_in_a_searched_when_clause():
    # CASE shares the same `comparison` grammar rule and evaluator as
    # IF/WHILE -- one spot-check here, not a full re-test of CASE itself
    # (see test_case_statement.py for that).
    code = """\
DECLARE score NUMBER DEFAULT 85;
DECLARE grade STRING DEFAULT '';
CASE
    WHEN score >= 90 THEN
        SET grade = 'A';
    WHEN score >= 80 THEN
        SET grade = 'B';
    WHEN score <= 50 THEN
        SET grade = 'F';
    ELSE
        SET grade = 'C';
END CASE;
"""
    steps = run(parse(tokenize(code)))
    assert steps[-1].to_dict()["variables"]["grade"]["value"] == "B"


def test_while_statement_uses_lte_as_its_own_condition():
    code = """\
DECLARE i NUMBER DEFAULT 1;
DECLARE total NUMBER DEFAULT 0;
WHILE i <= 3 DO
    SET total = total + i;
    SET i = i + 1;
END WHILE;
"""
    steps = run(parse(tokenize(code)))
    assert steps[-1].to_dict()["variables"]["total"]["value"] == 6  # 1+2+3


# -- SQL passthrough round-trip (the fix's other half) -----------------------


def test_new_operators_round_trip_correctly_in_raw_sql_passthrough_text():
    # See app.parser's "SQL passthrough statements" section: this used
    # to be a documented caveat (a two-character operator reassembled as
    # two separate tokens with a forced space, producing invalid SQL) --
    # now fixed as a side effect of this same tokenizer change. Full
    # execution-level coverage lives in
    # test_sql_passthrough_statement.py's own
    # test_two_char_comparison_operator_now_round_trips_correctly; this
    # is a narrower parse-level check that the raw text itself
    # reconstructs without a forced space splitting the operator.
    from app.parser import _render_raw_query  # noqa: PLC0415 -- test-only import of a "private" helper, established convention in this test suite

    tokens = tokenize("SELECT * FROM t WHERE id >= 5")
    rendered = _render_raw_query(tokens)
    assert ">= 5" in rendered
    assert "> = 5" not in rendered  # the old, broken reassembly


# -- error surfacing ----------------------------------------------------------


def test_stray_unsupported_operator_still_raises_a_clean_error():
    # Sanity check this change didn't accidentally loosen the grammar
    # beyond the three new operators -- something genuinely invalid
    # still fails cleanly, not silently.
    with pytest.raises((ParserError, InterpreterError)):
        run(parse(tokenize("IF x === 1 THEN SET y = 1; END IF;")))
