"""Tests for function calls inside procedures -- a procedure (or another
function) invoking a FUNCTION from within an expression (an assignment's
right-hand side, an IF/WHILE condition, another call's argument, ...)
and using its RETURNed value, as opposed to CALL, which can only target
a procedure and never produces a value. See app.parser's "Function
calls in expressions" and app.interpreter's own section of the same
name for the full design this exercises.

Every test here builds its AST via the real tokenizer -> parser
pipeline (never a hand-built dict), matching this project's existing
testing convention (see test_call_statement.py).
"""

import pytest

from app.interpreter import InterpreterError, run
from app.parser import parse
from app.tokenizer import tokenize


def _steps_as_dicts(steps):
    return [s.to_dict() for s in steps]


# -- parser: FunctionCallExpr as an expression, in every valid position ------


def test_function_call_parses_as_a_set_right_hand_side():
    code = """\
CREATE FUNCTION Square(n NUMBER) RETURNS NUMBER
BEGIN
    RETURN n * n;
END;

CREATE PROCEDURE Main()
BEGIN
    DECLARE y NUMBER DEFAULT 0;
    SET y = Square(5);
END;
"""
    ast = parse(tokenize(code))
    main = ast["definitions"][1]
    set_stmt = main["body"][1]
    assert set_stmt["value"] == {
        "type": "FunctionCallExpr",
        "name": "Square",
        "args": [{"type": "NumberLiteral", "value": 5, "line": 9}],
        "line": 9,
    }


def test_function_call_with_no_args_parses():
    code = """\
CREATE FUNCTION Answer() RETURNS NUMBER
BEGIN
    RETURN 42;
END;

CREATE PROCEDURE Main()
BEGIN
    DECLARE y NUMBER DEFAULT 0;
    SET y = Answer();
END;
"""
    ast = parse(tokenize(code))
    set_stmt = ast["definitions"][1]["body"][1]
    assert set_stmt["value"] == {"type": "FunctionCallExpr", "name": "Answer", "args": [], "line": 9}


def test_function_call_parses_in_an_if_condition():
    code = """\
CREATE FUNCTION IsBig(n NUMBER) RETURNS NUMBER
BEGIN
    RETURN n;
END;

CREATE PROCEDURE Main()
BEGIN
    DECLARE y NUMBER DEFAULT 0;
    IF IsBig(y) > 100 THEN
        SET y = 1;
    END IF;
END;
"""
    ast = parse(tokenize(code))
    if_stmt = ast["definitions"][1]["body"][1]
    assert if_stmt["type"] == "IfStatement"
    assert if_stmt["condition"]["left"] == {
        "type": "FunctionCallExpr",
        "name": "IsBig",
        "args": [{"type": "Identifier", "name": "y", "line": 9}],
        "line": 9,
    }


def test_function_call_parses_as_an_argument_to_another_function_call():
    code = """\
CREATE FUNCTION Double(n NUMBER) RETURNS NUMBER
BEGIN
    RETURN n * 2;
END;

CREATE PROCEDURE Main()
BEGIN
    DECLARE y NUMBER DEFAULT 0;
    SET y = Double(Double(3));
END;
"""
    ast = parse(tokenize(code))
    outer = ast["definitions"][1]["body"][1]["value"]
    assert outer["type"] == "FunctionCallExpr"
    assert outer["name"] == "Double"
    assert outer["args"][0]["type"] == "FunctionCallExpr"
    assert outer["args"][0]["name"] == "Double"
    assert outer["args"][0]["args"][0] == {"type": "NumberLiteral", "value": 3, "line": 9}


def test_function_call_parses_as_a_call_statements_own_argument():
    # Mixing the two mechanisms: a CallStatement (procedure) whose own
    # argument is a FunctionCallExpr (function) -- both grammars share
    # the same `expr` production for arguments, so this needs no special
    # parser handling to already work.
    code = """\
CREATE FUNCTION Tax(amount NUMBER) RETURNS NUMBER
BEGIN
    RETURN amount * 0.1;
END;

CREATE PROCEDURE ApplyTax(IN amount NUMBER, OUT total NUMBER)
BEGIN
    SET total = amount;
END;

CREATE PROCEDURE Main()
BEGIN
    DECLARE result NUMBER DEFAULT 0;
    CALL ApplyTax(Tax(100), result);
END;
"""
    ast = parse(tokenize(code))
    call_stmt = ast["definitions"][2]["body"][1]
    assert call_stmt["type"] == "CallStatement"
    assert call_stmt["args"][0] == {
        "type": "FunctionCallExpr",
        "name": "Tax",
        "args": [{"type": "NumberLiteral", "value": 100, "line": 14}],
        "line": 14,
    }


def test_function_call_parses_in_a_return_value():
    code = """\
CREATE FUNCTION Half(n NUMBER) RETURNS NUMBER
BEGIN
    RETURN n / 2;
END;

CREATE FUNCTION QuarterOf(n NUMBER) RETURNS NUMBER
BEGIN
    RETURN Half(Half(n));
END;
"""
    ast = parse(tokenize(code))  # a single FunctionNode -- exactly one CREATE, no CALL/second def
    assert ast["type"] == "ProgramNode"
    return_stmt = ast["definitions"][1]["body"][0]
    assert return_stmt["type"] == "ReturnNode"
    assert return_stmt["value"]["name"] == "Half"


def test_function_call_parses_in_a_declare_default():
    code = """\
CREATE FUNCTION Base() RETURNS NUMBER
BEGIN
    RETURN 10;
END;

CREATE PROCEDURE Main()
BEGIN
    DECLARE y NUMBER DEFAULT Base();
END;
"""
    ast = parse(tokenize(code))
    declare_stmt = ast["definitions"][1]["body"][0]
    assert declare_stmt["default"] == {"type": "FunctionCallExpr", "name": "Base", "args": [], "line": 8}


def test_plain_identifier_still_parses_without_a_following_paren():
    # A bare identifier, and a cursor %FOUND check, must both still
    # parse exactly as before -- the new '(' lookahead in _parse_primary
    # must not misfire on either.
    code = """\
CREATE PROCEDURE Main()
BEGIN
    DECLARE x NUMBER DEFAULT 1;
    DECLARE y NUMBER DEFAULT 0;
    SET y = x;
END;
"""
    ast = parse(tokenize(code))
    assert ast["type"] == "ProcedureNode"  # a single CREATE definition -- no ProgramNode wrapper
    set_stmt = ast["body"][2]
    assert set_stmt["value"] == {"type": "Identifier", "name": "x", "line": 5}


def test_cursor_found_check_still_parses_correctly():
    code = """\
CREATE PROCEDURE Main()
BEGIN
    DECLARE cur CURSOR FOR SELECT name FROM products;
    OPEN cur;
    WHILE cur%FOUND DO
        DECLARE done NUMBER DEFAULT 1;
    END WHILE;
END;
"""
    ast = parse(tokenize(code))
    assert ast["type"] == "ProcedureNode"
    while_stmt = ast["body"][2]
    assert while_stmt["condition"] == {"type": "CursorFoundExpr", "cursor": "cur", "line": 5}


def test_missing_closing_paren_raises_parser_error():
    code = """\
CREATE FUNCTION Square(n NUMBER) RETURNS NUMBER
BEGIN
    RETURN n * n;
END;

CREATE PROCEDURE Main()
BEGIN
    DECLARE y NUMBER DEFAULT 0;
    SET y = Square(5;
END;
"""
    with pytest.raises(Exception):  # ParserError -- see app.parser
        parse(tokenize(code))


# -- interpreter: basic evaluation + substitution -----------------------------


def test_function_call_result_used_in_an_assignment():
    code = """\
CREATE FUNCTION Square(n NUMBER) RETURNS NUMBER
BEGIN
    RETURN n * n;
END;

CREATE PROCEDURE Main()
BEGIN
    DECLARE y NUMBER DEFAULT 0;
    SET y = Square(5) + 1;
END;
"""
    steps = run(parse(tokenize(code)), {})
    assert steps[-1].to_dict()["variables"]["y"]["value"] == 26


def test_function_call_result_used_in_an_if_condition():
    code = """\
CREATE FUNCTION Square(n NUMBER) RETURNS NUMBER
BEGIN
    RETURN n * n;
END;

CREATE PROCEDURE Main()
BEGIN
    DECLARE x NUMBER DEFAULT 5;
    DECLARE y NUMBER DEFAULT 0;
    IF Square(x) > 20 THEN
        SET y = 1;
    ELSE
        SET y = 0;
    END IF;
END;
"""
    steps = run(parse(tokenize(code)), {})
    assert steps[-1].to_dict()["variables"]["y"]["value"] == 1  # 5*5=25 > 20


def test_function_call_result_used_in_a_while_condition():
    code = """\
CREATE FUNCTION IsBelow(n NUMBER, limit NUMBER) RETURNS NUMBER
BEGIN
    IF n < limit THEN
        RETURN 1;
    ELSE
        RETURN 0;
    END IF;
END;

CREATE PROCEDURE Main()
BEGIN
    DECLARE counter NUMBER DEFAULT 0;
    WHILE IsBelow(counter, 5) = 1 DO
        SET counter = counter + 1;
    END WHILE;
END;
"""
    steps = run(parse(tokenize(code)), {})
    assert steps[-1].to_dict()["variables"]["counter"]["value"] == 5


def test_multiple_arguments_bind_in_declared_order():
    code = """\
CREATE FUNCTION Subtract(a NUMBER, b NUMBER) RETURNS NUMBER
BEGIN
    RETURN a - b;
END;

CREATE PROCEDURE Main()
BEGIN
    DECLARE y NUMBER DEFAULT 0;
    SET y = Subtract(10, 3);
END;
"""
    steps = run(parse(tokenize(code)), {})
    assert steps[-1].to_dict()["variables"]["y"]["value"] == 7


def test_zero_argument_function_call():
    code = """\
CREATE FUNCTION Answer() RETURNS NUMBER
BEGIN
    RETURN 42;
END;

CREATE PROCEDURE Main()
BEGIN
    DECLARE y NUMBER DEFAULT 0;
    SET y = Answer();
END;
"""
    steps = run(parse(tokenize(code)), {})
    assert steps[-1].to_dict()["variables"]["y"]["value"] == 42


def test_argument_can_be_an_arbitrary_expression():
    code = """\
CREATE FUNCTION Square(n NUMBER) RETURNS NUMBER
BEGIN
    RETURN n * n;
END;

CREATE PROCEDURE Main()
BEGIN
    DECLARE x NUMBER DEFAULT 3;
    DECLARE y NUMBER DEFAULT 0;
    SET y = Square(x + 1);
END;
"""
    steps = run(parse(tokenize(code)), {})
    assert steps[-1].to_dict()["variables"]["y"]["value"] == 16  # (3+1)^2


# -- interpreter: nested calls, recursion, mutual recursion -------------------


def test_function_calling_a_different_function():
    code = """\
CREATE FUNCTION Double(n NUMBER) RETURNS NUMBER
BEGIN
    RETURN n * 2;
END;

CREATE FUNCTION QuadrupleViaDouble(n NUMBER) RETURNS NUMBER
BEGIN
    RETURN Double(Double(n));
END;

CREATE PROCEDURE Main()
BEGIN
    DECLARE y NUMBER DEFAULT 0;
    SET y = QuadrupleViaDouble(3);
END;
"""
    steps = run(parse(tokenize(code)), {})
    assert steps[-1].to_dict()["variables"]["y"]["value"] == 12


def test_self_recursive_function_call_computes_a_correct_result():
    """5! via a function calling itself through an expression (not a
    CALL statement) -- the entry procedure's own registration-by-name
    (see app.interpreter's module docstring) already generalizes to any
    definition, so a plain FunctionNode can self-recurse the same way."""
    code = """\
CREATE FUNCTION Fact(n NUMBER) RETURNS NUMBER
BEGIN
    IF n > 1 THEN
        RETURN n * Fact(n - 1);
    ELSE
        RETURN 1;
    END IF;
END;

CREATE PROCEDURE Main()
BEGIN
    DECLARE result NUMBER DEFAULT 0;
    SET result = Fact(5);
END;
"""
    steps = run(parse(tokenize(code)), {})
    assert steps[-1].to_dict()["variables"]["result"]["value"] == 120

    max_depth = max((s.to_dict().get("call") or {}).get("depth", 0) for s in steps)
    assert max_depth == 5  # Fact(5)->Fact(4)->Fact(3)->Fact(2)->Fact(1)


def test_mutual_recursion_between_two_functions():
    code = """\
CREATE FUNCTION IsOdd(n NUMBER) RETURNS NUMBER
BEGIN
    IF n = 0 THEN
        RETURN 0;
    ELSE
        RETURN IsEven(n - 1);
    END IF;
END;

CREATE FUNCTION IsEven(n NUMBER) RETURNS NUMBER
BEGIN
    IF n = 0 THEN
        RETURN 1;
    ELSE
        RETURN IsOdd(n - 1);
    END IF;
END;

CREATE PROCEDURE Main()
BEGIN
    DECLARE y NUMBER DEFAULT 0;
    SET y = IsEven(6);
END;
"""
    steps = run(parse(tokenize(code)), {})
    assert steps[-1].to_dict()["variables"]["y"]["value"] == 1  # 6 is even


def test_procedure_calls_procedure_which_calls_a_function():
    """Mixing both mechanisms in one chain: Main CALLs Inner (a
    procedure), and Inner itself invokes a FUNCTION via an expression --
    both must compose through the same call-depth/call-stack machinery."""
    code = """\
CREATE FUNCTION Tax(amount NUMBER) RETURNS NUMBER
BEGIN
    RETURN amount * 0.1;
END;

CREATE PROCEDURE Inner(IN price NUMBER, OUT total NUMBER)
BEGIN
    SET total = price + Tax(price);
END;

CREATE PROCEDURE Main()
BEGIN
    DECLARE grand NUMBER DEFAULT 0;
    CALL Inner(100, grand);
    SET grand = grand + 0;
END;
"""
    steps = run(parse(tokenize(code)), {})
    assert steps[-1].to_dict()["variables"]["grand"]["value"] == 110.0


def test_infinite_self_recursive_function_call_hits_the_depth_guard():
    # Named Recur, not Loop -- LOOP became a reserved keyword in the
    # LOOP/LEAVE support phase (see app.tokenizer), so it can no longer
    # be used as a procedure/function name.
    code = """\
CREATE FUNCTION Recur(n NUMBER) RETURNS NUMBER
BEGIN
    RETURN Recur(n + 1);
END;

CREATE PROCEDURE Main()
BEGIN
    DECLARE y NUMBER DEFAULT 0;
    SET y = Recur(1);
END;
"""
    with pytest.raises(InterpreterError, match="exceeded the maximum call depth"):
        run(parse(tokenize(code)), {})


def test_mutual_infinite_recursion_between_functions_hits_the_depth_guard():
    code = """\
CREATE FUNCTION A(n NUMBER) RETURNS NUMBER
BEGIN
    RETURN B(n + 1);
END;

CREATE FUNCTION B(n NUMBER) RETURNS NUMBER
BEGIN
    RETURN A(n + 1);
END;

CREATE PROCEDURE Main()
BEGIN
    DECLARE y NUMBER DEFAULT 0;
    SET y = A(1);
END;
"""
    with pytest.raises(InterpreterError, match="exceeded the maximum call depth"):
        run(parse(tokenize(code)), {})


# -- interpreter: error cases --------------------------------------------------


def test_calling_a_procedure_as_a_function_expression_raises_a_clean_error():
    code = """\
CREATE PROCEDURE Foo(IN x NUMBER)
BEGIN
    DECLARE y NUMBER DEFAULT x;
END;

CREATE PROCEDURE Main()
BEGIN
    DECLARE y NUMBER DEFAULT 0;
    SET y = Foo(1);
END;
"""
    with pytest.raises(InterpreterError, match="is not a function"):
        run(parse(tokenize(code)), {})


def test_calling_an_undefined_function_raises_a_clean_error():
    code = """\
CREATE PROCEDURE Main()
BEGIN
    DECLARE y NUMBER DEFAULT 0;
    SET y = Ghost(1);
END;
"""
    with pytest.raises(InterpreterError, match="Function 'Ghost' is not defined"):
        run(parse(tokenize(code)), {})


def test_function_call_with_wrong_argument_count_raises():
    code = """\
CREATE FUNCTION Add(a NUMBER, b NUMBER) RETURNS NUMBER
BEGIN
    RETURN a + b;
END;

CREATE PROCEDURE Main()
BEGIN
    DECLARE y NUMBER DEFAULT 0;
    SET y = Add(1);
END;
"""
    with pytest.raises(InterpreterError, match="expects 2 argument"):
        run(parse(tokenize(code)), {})


# -- interpreter: DIVISION_BY_ZERO around a function call ---------------------


def test_unhandled_division_by_zero_in_function_call_argument_aborts_the_run():
    code = """\
CREATE FUNCTION Identity(n NUMBER) RETURNS NUMBER
BEGIN
    RETURN n;
END;

CREATE PROCEDURE Main()
BEGIN
    DECLARE zero NUMBER DEFAULT 0;
    DECLARE y NUMBER DEFAULT 0;
    SET y = Identity(10 / zero);
END;
"""
    with pytest.raises(InterpreterError, match="Division by zero"):
        run(parse(tokenize(code)), {})


def test_handled_division_by_zero_in_function_call_argument_skips_the_call():
    code = """\
CREATE FUNCTION Identity(n NUMBER) RETURNS NUMBER
BEGIN
    RETURN n;
END;

CREATE PROCEDURE Main()
BEGIN
    DECLARE safe NUMBER DEFAULT -1;
    DECLARE zero NUMBER DEFAULT 0;
    DECLARE y NUMBER DEFAULT 0;
    DECLARE CONTINUE HANDLER FOR DIVISION_BY_ZERO SET safe = 1;
    SET y = Identity(10 / zero);
END;
"""
    steps = _steps_as_dicts(run(parse(tokenize(code)), {}))
    set_step = next(s for s in steps if s["nodeType"] == "SetStatement" and "y" in s["statementText"])
    assert set_step["error"]["condition"] == "DIVISION_BY_ZERO"
    assert set_step["variables"]["y"]["value"] == 0  # assignment never happened
    assert steps[-1]["variables"]["safe"]["value"] == 1  # handler ran
    # The function itself must never have been entered -- no step at
    # depth 1 anywhere in the trace.
    assert all((s.get("call") or {}).get("depth", 0) == 0 for s in steps)


def test_unhandled_division_by_zero_inside_function_body_aborts_the_whole_run():
    code = """\
CREATE FUNCTION Bad(n NUMBER) RETURNS NUMBER
BEGIN
    RETURN n / 0;
END;

CREATE PROCEDURE Main()
BEGIN
    DECLARE y NUMBER DEFAULT 0;
    SET y = Bad(5);
END;
"""
    with pytest.raises(InterpreterError, match="Division by zero"):
        run(parse(tokenize(code)), {})


def test_division_by_zero_inside_function_body_handled_by_its_own_internal_handler():
    code = """\
CREATE FUNCTION SafeDiv(a NUMBER, b NUMBER) RETURNS NUMBER
BEGIN
    DECLARE result NUMBER DEFAULT -1;
    DECLARE CONTINUE HANDLER FOR DIVISION_BY_ZERO SET result = 0;
    SET result = a / b;
    RETURN result;
END;

CREATE PROCEDURE Main()
BEGIN
    DECLARE y NUMBER DEFAULT -99;
    SET y = SafeDiv(10, 0);
END;
"""
    steps = run(parse(tokenize(code)), {})
    assert steps[-1].to_dict()["variables"]["y"]["value"] == 0


# -- interpreter: scope isolation ----------------------------------------------


def test_caller_and_callee_do_not_share_a_same_named_variable():
    code = """\
CREATE FUNCTION Compute(n NUMBER) RETURNS NUMBER
BEGIN
    RETURN n * 100;
END;

CREATE PROCEDURE Main()
BEGIN
    DECLARE n NUMBER DEFAULT 7;
    DECLARE y NUMBER DEFAULT 0;
    SET y = Compute(2);
END;
"""
    steps = run(parse(tokenize(code)), {})
    last = steps[-1].to_dict()
    assert last["variables"]["n"]["value"] == 7  # Main's own n, untouched by Compute's own n=2
    assert last["variables"]["y"]["value"] == 200


def test_function_body_cannot_see_callers_cursor_or_handler():
    code = """\
CREATE FUNCTION Peek() RETURNS NUMBER
BEGIN
    RETURN 1;
END;

CREATE PROCEDURE Main()
BEGIN
    DECLARE flag NUMBER DEFAULT 0;
    DECLARE CONTINUE HANDLER FOR DIVISION_BY_ZERO SET flag = 1;
    DECLARE y NUMBER DEFAULT 0;
    SET y = Peek();
END;
"""
    steps = _steps_as_dicts(run(parse(tokenize(code)), {}))
    peek_entry = next(s for s in steps if s.get("call") is not None)
    # Peek's own frame has only its own (empty) params -- no `flag`.
    assert "flag" not in peek_entry["variables"]


# -- interpreter: step-trace / Call Stack schema -------------------------------


def test_steps_inside_a_called_function_carry_the_call_field():
    code = """\
CREATE FUNCTION Square(n NUMBER) RETURNS NUMBER
BEGIN
    RETURN n * n;
END;

CREATE PROCEDURE Main()
BEGIN
    DECLARE y NUMBER DEFAULT 0;
    SET y = Square(5);
END;
"""
    steps = _steps_as_dicts(run(parse(tokenize(code)), {}))
    node_types = [s["nodeType"] for s in steps]
    assert node_types == [
        "ProcedureNode",  # Main's own entry step
        "DeclareStatement",  # DECLARE y
        "FunctionNode",  # Square's own entry step
        "ReturnNode",  # RETURN n * n
        "SetStatement",  # SET y = Square(5); -- back in Main's frame
    ]

    entry_step, return_step, set_step = steps[2], steps[3], steps[4]
    assert entry_step["call"] == {"procedureName": "Square", "depth": 1, "stack": ["Square"]}
    assert return_step["call"] == {"procedureName": "Square", "depth": 1, "stack": ["Square"]}
    assert return_step["returnValue"] == {"value": 25, "type": "number"}
    # Back in Main's own top-level frame -- no `call` field at all,
    # exactly like a CALL statement's own step already behaves.
    assert "call" not in set_step
    assert set_step["variables"]["y"]["value"] == 25


def test_nested_function_calls_produce_correctly_nested_call_stacks():
    code = """\
CREATE FUNCTION Inner(n NUMBER) RETURNS NUMBER
BEGIN
    RETURN n + 1;
END;

CREATE FUNCTION Outer(n NUMBER) RETURNS NUMBER
BEGIN
    RETURN Inner(n) * 2;
END;

CREATE PROCEDURE Main()
BEGIN
    DECLARE y NUMBER DEFAULT 0;
    SET y = Outer(3);
END;
"""
    steps = _steps_as_dicts(run(parse(tokenize(code)), {}))
    calls = [s.get("call") for s in steps if s.get("call") is not None]
    # Outer's own steps: depth 1, stack ["Outer"]. Inner's own step
    # (called from inside Outer): depth 2, stack ["Outer", "Inner"].
    depths = [c["depth"] for c in calls]
    assert 1 in depths and 2 in depths
    inner_call = next(c for c in calls if c["depth"] == 2)
    assert inner_call["stack"] == ["Outer", "Inner"]
    assert inner_call["procedureName"] == "Inner"
    assert steps[-1]["variables"]["y"]["value"] == 8  # (3+1)*2
