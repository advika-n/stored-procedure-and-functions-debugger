"""Tests for CASE statement support (both simple and searched forms).
See app.parser's "CASE statement" and app.interpreter's own section of
the same name for the full design this exercises.

Every test here builds its AST via the real tokenizer -> parser
pipeline (never a hand-built dict), matching this project's existing
testing convention (see test_call_statement.py /
test_function_call_expression.py).
"""

import pytest

from app.interpreter import InterpreterError, run
from app.parser import parse
from app.tokenizer import tokenize


def _steps_as_dicts(steps):
    return [s.to_dict() for s in steps]


# -- tokenizer ----------------------------------------------------------------


def test_case_and_when_tokenize_as_keywords():
    tokens = tokenize("CASE x WHEN 1 THEN SET y = 1; END CASE;")
    kinds = [(t["type"], t["value"].upper()) for t in tokens]
    assert ("KEYWORD", "CASE") in kinds
    assert ("KEYWORD", "WHEN") in kinds


# -- parser: simple CASE --------------------------------------------------------


def test_simple_case_parses_operand_when_clauses_and_else():
    code = """\
CREATE PROCEDURE Demo()
BEGIN
    DECLARE score NUMBER DEFAULT 2;
    DECLARE label NUMBER DEFAULT 0;
    CASE score
        WHEN 1 THEN
            SET label = 100;
        WHEN 2 THEN
            SET label = 200;
        ELSE
            SET label = -1;
    END CASE;
END
"""
    ast = parse(tokenize(code))
    case_stmt = ast["body"][2]
    assert case_stmt["type"] == "CaseStatement"
    assert case_stmt["operand"] == {"type": "Identifier", "name": "score", "line": 5}
    assert len(case_stmt["when_clauses"]) == 2
    assert case_stmt["when_clauses"][0]["when"] == {"type": "NumberLiteral", "value": 1, "line": 6}
    assert case_stmt["when_clauses"][0]["body"][0]["type"] == "SetStatement"
    assert case_stmt["when_clauses"][1]["when"] == {"type": "NumberLiteral", "value": 2, "line": 8}
    assert case_stmt["else_body"] is not None
    assert case_stmt["else_body"][0]["type"] == "SetStatement"


def test_simple_case_with_no_else_parses_else_body_as_none():
    code = """\
CREATE PROCEDURE Demo()
BEGIN
    DECLARE score NUMBER DEFAULT 2;
    CASE score
        WHEN 1 THEN
            DECLARE unused NUMBER DEFAULT 1;
    END CASE;
END
"""
    ast = parse(tokenize(code))
    assert ast["body"][1]["else_body"] is None


# -- parser: searched CASE -------------------------------------------------------


def test_searched_case_parses_with_no_operand():
    code = """\
CREATE PROCEDURE Demo()
BEGIN
    DECLARE score NUMBER DEFAULT 75;
    DECLARE grade NUMBER DEFAULT 0;
    CASE
        WHEN score > 90 THEN
            SET grade = 4;
        WHEN score > 60 THEN
            SET grade = 3;
        ELSE
            SET grade = 0;
    END CASE;
END
"""
    ast = parse(tokenize(code))
    case_stmt = ast["body"][2]
    assert case_stmt["operand"] is None
    assert case_stmt["when_clauses"][0]["when"]["type"] == "BinaryExpr"
    assert case_stmt["when_clauses"][0]["when"]["operator"] == ">"


# -- parser: structural errors ---------------------------------------------------


def test_case_with_zero_when_clauses_raises_parser_error():
    code = """\
CREATE PROCEDURE Demo()
BEGIN
    DECLARE score NUMBER DEFAULT 1;
    CASE score
    END CASE;
END
"""
    with pytest.raises(Exception):  # ParserError -- see app.parser
        parse(tokenize(code))


def test_case_missing_end_case_raises_parser_error():
    code = """\
CREATE PROCEDURE Demo()
BEGIN
    DECLARE score NUMBER DEFAULT 1;
    CASE score
        WHEN 1 THEN
            SET score = 2;
    END;
END
"""
    with pytest.raises(Exception):
        parse(tokenize(code))


def test_case_missing_trailing_semicolon_raises_parser_error():
    code = """\
CREATE PROCEDURE Demo()
BEGIN
    DECLARE score NUMBER DEFAULT 1;
    CASE score
        WHEN 1 THEN
            SET score = 2;
    END CASE
END
"""
    with pytest.raises(Exception):
        parse(tokenize(code))


# -- parser: nesting/composability ------------------------------------------------


def test_case_nested_inside_if_and_while_parses():
    code = """\
CREATE PROCEDURE Demo()
BEGIN
    DECLARE i NUMBER DEFAULT 0;
    WHILE i < 3 DO
        IF i > 0 THEN
            CASE i
                WHEN 1 THEN
                    SET i = i + 10;
            END CASE;
        END IF;
        SET i = i + 1;
    END WHILE;
END
"""
    ast = parse(tokenize(code))
    while_stmt = ast["body"][1]
    if_stmt = while_stmt["body"][0]
    case_stmt = if_stmt["then_body"][0]
    assert case_stmt["type"] == "CaseStatement"


def test_case_nested_inside_another_case_parses():
    code = """\
CREATE PROCEDURE Demo()
BEGIN
    DECLARE a NUMBER DEFAULT 1;
    CASE a
        WHEN 1 THEN
            CASE a
                WHEN 1 THEN
                    SET a = 100;
            END CASE;
    END CASE;
END
"""
    ast = parse(tokenize(code))
    outer_case = ast["body"][1]
    inner_case = outer_case["when_clauses"][0]["body"][0]
    assert inner_case["type"] == "CaseStatement"


# -- interpreter: simple CASE -----------------------------------------------------


def test_simple_case_first_matching_when_wins():
    code = """\
CREATE PROCEDURE Demo()
BEGIN
    DECLARE score NUMBER DEFAULT 2;
    DECLARE label NUMBER DEFAULT 0;
    CASE score
        WHEN 1 THEN
            SET label = 100;
        WHEN 2 THEN
            SET label = 200;
        ELSE
            SET label = -1;
    END CASE;
END
"""
    steps = run(parse(tokenize(code)), {})
    assert steps[-1].to_dict()["variables"]["label"]["value"] == 200


def test_simple_case_no_match_runs_else():
    code = """\
CREATE PROCEDURE Demo()
BEGIN
    DECLARE score NUMBER DEFAULT 9;
    DECLARE label NUMBER DEFAULT 0;
    CASE score
        WHEN 1 THEN
            SET label = 100;
        ELSE
            SET label = -1;
    END CASE;
END
"""
    steps = run(parse(tokenize(code)), {})
    assert steps[-1].to_dict()["variables"]["label"]["value"] == -1


def test_simple_case_no_match_no_else_is_a_no_op():
    code = """\
CREATE PROCEDURE Demo()
BEGIN
    DECLARE score NUMBER DEFAULT 9;
    DECLARE label NUMBER DEFAULT -9;
    CASE score
        WHEN 1 THEN
            SET label = 100;
    END CASE;
    SET label = label + 1;
END
"""
    steps = run(parse(tokenize(code)), {})
    # -9 unchanged by the CASE, then +1 by the trailing SET.
    assert steps[-1].to_dict()["variables"]["label"]["value"] == -8


# -- interpreter: searched CASE ---------------------------------------------------


def test_searched_case_first_true_condition_wins():
    code = """\
CREATE PROCEDURE Demo()
BEGIN
    DECLARE score NUMBER DEFAULT 75;
    DECLARE grade NUMBER DEFAULT 0;
    CASE
        WHEN score > 90 THEN
            SET grade = 4;
        WHEN score > 60 THEN
            SET grade = 3;
        ELSE
            SET grade = 0;
    END CASE;
END
"""
    steps = run(parse(tokenize(code)), {})
    assert steps[-1].to_dict()["variables"]["grade"]["value"] == 3


def test_searched_case_none_true_runs_else():
    code = """\
CREATE PROCEDURE Demo()
BEGIN
    DECLARE score NUMBER DEFAULT 10;
    DECLARE grade NUMBER DEFAULT -1;
    CASE
        WHEN score > 90 THEN
            SET grade = 4;
        WHEN score > 60 THEN
            SET grade = 3;
        ELSE
            SET grade = 0;
    END CASE;
END
"""
    steps = run(parse(tokenize(code)), {})
    assert steps[-1].to_dict()["variables"]["grade"]["value"] == 0


def test_searched_case_none_true_no_else_is_a_no_op():
    code = """\
CREATE PROCEDURE Demo()
BEGIN
    DECLARE score NUMBER DEFAULT 10;
    DECLARE grade NUMBER DEFAULT -9;
    CASE
        WHEN score > 90 THEN
            SET grade = 4;
    END CASE;
    SET grade = grade + 1;
END
"""
    steps = run(parse(tokenize(code)), {})
    assert steps[-1].to_dict()["variables"]["grade"]["value"] == -8


def test_only_the_matching_when_is_evaluated_short_circuit():
    """A later WHEN's own expression must never even be evaluated once
    an earlier one has already matched -- proven here by a later WHEN
    calling an undefined function, which would raise if it were ever
    actually evaluated."""
    code = """\
CREATE PROCEDURE Demo()
BEGIN
    DECLARE a NUMBER DEFAULT 1;
    DECLARE label NUMBER DEFAULT 0;
    CASE
        WHEN a = 1 THEN
            SET label = 1;
        WHEN Ghost(a) = 1 THEN
            SET label = 2;
    END CASE;
END
"""
    steps = run(parse(tokenize(code)), {})
    assert steps[-1].to_dict()["variables"]["label"]["value"] == 1


# -- interpreter: nesting, matching the task's "verify, don't assume" ------------


def test_case_nested_inside_if_inside_while_and_case_inside_case():
    code = """\
CREATE PROCEDURE Nested()
BEGIN
    DECLARE i NUMBER DEFAULT 0;
    DECLARE total NUMBER DEFAULT 0;
    WHILE i < 4 DO
        IF i > 0 THEN
            CASE
                WHEN i = 1 THEN
                    CASE i
                        WHEN 1 THEN
                            SET total = total + 10;
                    END CASE;
                WHEN i = 2 THEN
                    SET total = total + 20;
                ELSE
                    SET total = total + 30;
            END CASE;
        END IF;
        SET i = i + 1;
    END WHILE;
END
"""
    steps = run(parse(tokenize(code)), {})
    assert steps[-1].to_dict()["variables"]["total"]["value"] == 60  # i=1,2,3 -> 10+20+30


def test_return_inside_a_when_body_stops_execution():
    code = """\
CREATE FUNCTION Classify(n NUMBER) RETURNS NUMBER
BEGIN
    CASE
        WHEN n > 10 THEN
            RETURN 1;
        ELSE
            RETURN 0;
    END CASE;
    RETURN -1;
END
"""
    ast = parse(tokenize(code))
    assert ast["type"] == "FunctionNode"
    steps = run(ast, {"n": 20})
    assert steps[-1].to_dict()["returnValue"] == {"value": 1, "type": "number"}
    # The trailing RETURN -1 must never execute.
    node_types = [s.to_dict()["nodeType"] for s in steps]
    assert node_types.count("ReturnNode") == 1


def test_function_call_as_case_operand_and_when_value():
    code = """\
CREATE FUNCTION Double(n NUMBER) RETURNS NUMBER
BEGIN
    RETURN n * 2;
END;

CREATE PROCEDURE Demo()
BEGIN
    DECLARE x NUMBER DEFAULT 3;
    DECLARE label NUMBER DEFAULT 0;
    CASE Double(x)
        WHEN 6 THEN
            SET label = 1;
        ELSE
            SET label = 2;
    END CASE;
END
"""
    steps = run(parse(tokenize(code)), {})
    assert steps[-1].to_dict()["variables"]["label"]["value"] == 1


# -- interpreter: DIVISION_BY_ZERO ------------------------------------------------


def test_unhandled_division_by_zero_in_operand_aborts_the_run():
    code = """\
CREATE PROCEDURE Demo()
BEGIN
    DECLARE z NUMBER DEFAULT 0;
    CASE 10 / z
        WHEN 1 THEN
            DECLARE unused NUMBER DEFAULT 1;
    END CASE;
END
"""
    with pytest.raises(InterpreterError, match="Division by zero"):
        run(parse(tokenize(code)), {})


def test_handled_division_by_zero_in_operand_falls_through_to_else():
    code = """\
CREATE PROCEDURE Demo()
BEGIN
    DECLARE z NUMBER DEFAULT 0;
    DECLARE label NUMBER DEFAULT 0;
    DECLARE safe NUMBER DEFAULT -1;
    DECLARE CONTINUE HANDLER FOR DIVISION_BY_ZERO SET safe = 1;
    CASE 10 / z
        WHEN 1 THEN
            SET label = 1;
        ELSE
            SET label = 2;
    END CASE;
END
"""
    steps = _steps_as_dicts(run(parse(tokenize(code)), {}))
    last = steps[-1]
    assert last["variables"]["label"]["value"] == 2  # ELSE ran, mirrors _exec_if's own convention
    assert last["variables"]["safe"]["value"] == 1
    case_step = next(s for s in steps if s["nodeType"] == "CaseStatement")
    assert case_step["error"]["condition"] == "DIVISION_BY_ZERO"
    assert case_step["branch"]["path"] == "else"


def test_handled_division_by_zero_in_a_when_expression_stops_evaluating_further_whens():
    code = """\
CREATE PROCEDURE Demo()
BEGIN
    DECLARE z NUMBER DEFAULT 0;
    DECLARE label NUMBER DEFAULT 0;
    DECLARE CONTINUE HANDLER FOR DIVISION_BY_ZERO SET label = -1;
    CASE
        WHEN 10 / z > 1 THEN
            SET label = 1;
        WHEN 1 = 1 THEN
            SET label = 2;
    END CASE;
END
"""
    steps = _steps_as_dicts(run(parse(tokenize(code)), {}))
    # The second WHEN (1 = 1, unconditionally true) must never run --
    # the division error already stopped the whole decision process.
    assert steps[-1]["variables"]["label"]["value"] == -1
    case_step = next(s for s in steps if s["nodeType"] == "CaseStatement")
    assert case_step["branch"]["path"] == "none"


# -- interpreter: step-trace shape ------------------------------------------------


def test_branch_field_shape_for_simple_case():
    code = """\
CREATE PROCEDURE Demo()
BEGIN
    DECLARE score NUMBER DEFAULT 2;
    DECLARE label NUMBER DEFAULT 0;
    CASE score
        WHEN 1 THEN
            SET label = 1;
        WHEN 2 THEN
            SET label = 2;
    END CASE;
END
"""
    steps = _steps_as_dicts(run(parse(tokenize(code)), {}))
    case_step = next(s for s in steps if s["nodeType"] == "CaseStatement")
    assert case_step["branch"] == {"condition": "score", "result": True, "path": "when-1"}


def test_branch_field_shape_for_searched_case_with_no_operand():
    code = """\
CREATE PROCEDURE Demo()
BEGIN
    DECLARE score NUMBER DEFAULT 2;
    CASE
        WHEN score = 2 THEN
            SET score = 20;
    END CASE;
END
"""
    steps = _steps_as_dicts(run(parse(tokenize(code)), {}))
    case_step = next(s for s in steps if s["nodeType"] == "CaseStatement")
    assert case_step["branch"] == {"condition": "CASE", "result": True, "path": "when-0"}


def test_case_inside_a_called_procedure_carries_the_call_field():
    code = """\
CREATE PROCEDURE Helper(IN n NUMBER, OUT label NUMBER)
BEGIN
    CASE
        WHEN n > 5 THEN
            SET label = 1;
        ELSE
            SET label = 0;
    END CASE;
END;

CREATE PROCEDURE Main()
BEGIN
    DECLARE result NUMBER DEFAULT 0;
    CALL Helper(10, result);
END
"""
    steps = _steps_as_dicts(run(parse(tokenize(code)), {}))
    case_step = next(s for s in steps if s["nodeType"] == "CaseStatement")
    assert case_step["call"] == {"procedureName": "Helper", "depth": 1, "stack": ["Helper"]}
