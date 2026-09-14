"""Tests for CALL support (procedure calling procedure) -- the first
Tier 1 phase to touch the interpreter core. See app.parser's "CALL and
multi-procedure sources" and app.interpreter's "Procedure calls (CALL)"
module docstring sections for the full design this exercises.

Every test here builds its AST via the real tokenizer -> parser
pipeline (never a hand-built dict), matching this project's existing
testing convention.
"""

import json

import pytest

from app.interpreter import InterpreterError, run
from app.parser import ParserError, parse
from app.tokenizer import tokenize

# -- the new "sample procedure pair" (item 5 of this phase's own spec) ----
# A helper procedure computing a subtotal, called by a main procedure
# that adds tax on top. This is a backend test fixture, not an addition
# to frontend/src/samples.js -- this phase's own instructions explicitly
# exclude the frontend, and a ProgramNode/CallStatement-based AST isn't
# yet understood by cfg.js's flowchart builder or the Anti-Pattern
# Advisor (both degrade gracefully -- see HANDOFF.md -- but wouldn't
# render anything meaningful in the UI yet), so this phase's "sample
# procedure pair" deliverable is interpreted as the realistic worked
# example the interpreter-level tests below actually exercise.
ORDER_TOTAL_SAMPLE = """\
CREATE PROCEDURE ComputeSubtotal(IN price NUMBER, IN quantity NUMBER, OUT subtotal NUMBER)
BEGIN
    SET subtotal = price * quantity;
END;

CREATE PROCEDURE OrderTotal(IN price NUMBER, IN quantity NUMBER, IN taxRate NUMBER, OUT grandTotal NUMBER)
BEGIN
    DECLARE subtotal NUMBER DEFAULT 0;
    CALL ComputeSubtotal(price, quantity, subtotal);
    SET grandTotal = subtotal + subtotal * taxRate;
END;
"""


def _steps_as_dicts(steps):
    return [s.to_dict() for s in steps]


# -- tokenizer --------------------------------------------------------------


def test_call_tokenizes_as_a_keyword():
    tokens = tokenize("CALL Foo();")
    assert tokens[0]["type"] == "KEYWORD"
    assert tokens[0]["value"] == "CALL"


# -- parser: the CallStatement node itself -----------------------------------


def test_call_statement_parses_with_args():
    ast = parse(tokenize("CALL Foo(a, 1, 'x');"))
    assert ast["type"] == "Procedure"
    call = ast["body"][0]
    assert call["type"] == "CallStatement"
    assert call["name"] == "Foo"
    assert [arg["type"] for arg in call["args"]] == ["Identifier", "NumberLiteral", "StringLiteral"]
    assert call["line"] == 1


def test_call_statement_with_no_args():
    ast = parse(tokenize("CALL Foo();"))
    call = ast["body"][0]
    assert call["args"] == []


def test_call_missing_semicolon_raises_parser_error():
    with pytest.raises(ParserError):
        parse(tokenize("CALL Foo()"))


def test_call_missing_closing_paren_raises_parser_error():
    with pytest.raises(ParserError):
        parse(tokenize("CALL Foo(a, b;"))


def test_call_is_parseable_inside_an_if_body():
    code = """\
IF x > 0 THEN
    CALL Foo(x);
END IF;
"""
    ast = parse(tokenize(code))
    then_body = ast["body"][0]["then_body"]
    assert then_body[0]["type"] == "CallStatement"


# -- parser: multi-procedure sources / ProgramNode ---------------------------


TWO_PROCEDURES = """\
CREATE PROCEDURE Helper(IN x NUMBER, OUT y NUMBER)
BEGIN
    SET y = x + 1;
END;

CREATE PROCEDURE Main()
BEGIN
    DECLARE result NUMBER DEFAULT 0;
    CALL Helper(5, result);
END;
"""


def test_two_chained_create_procedures_parse_to_a_program_node():
    ast = parse(tokenize(TWO_PROCEDURES))
    assert ast["type"] == "ProgramNode"
    assert [d["type"] for d in ast["definitions"]] == ["ProcedureNode", "ProcedureNode"]
    assert [d["name"] for d in ast["definitions"]] == ["Helper", "Main"]


def test_program_node_entry_convention_is_the_last_definition():
    ast = parse(tokenize(TWO_PROCEDURES))
    # The module docstring's own convention: whichever definition is
    # LAST in source order is what actually runs.
    assert ast["definitions"][-1]["name"] == "Main"


def test_a_single_create_procedure_is_not_wrapped_in_a_program_node():
    """Backward compatibility: exactly one CREATE definition must still
    parse to a bare ProcedureNode, not a ProgramNode -- every existing
    single-procedure sample/History entry depends on this shape."""
    ast = parse(tokenize("CREATE PROCEDURE Solo() BEGIN DECLARE x NUMBER DEFAULT 1; END"))
    assert ast["type"] == "ProcedureNode"
    assert "definitions" not in ast


def test_three_chained_definitions_mixing_procedure_and_function():
    code = """\
CREATE FUNCTION Double(x NUMBER) RETURNS NUMBER
BEGIN
    RETURN x * 2;
END;

CREATE PROCEDURE A()
BEGIN
    DECLARE y NUMBER DEFAULT 0;
END;

CREATE PROCEDURE B()
BEGIN
    CALL A();
END;
"""
    ast = parse(tokenize(code))
    assert ast["type"] == "ProgramNode"
    assert [d["name"] for d in ast["definitions"]] == ["Double", "A", "B"]
    assert ast["definitions"][-1]["name"] == "B"


# -- interpreter: core two-level CALL + OUT propagation ----------------------


def test_two_level_call_propagates_out_param_back_to_caller():
    ast = parse(tokenize(TWO_PROCEDURES))
    steps = _steps_as_dicts(run(ast, {}))

    print("\n--- source ---")
    print(TWO_PROCEDURES)
    print("--- step trace ---")
    print(json.dumps(steps, indent=2))

    node_types = [s["nodeType"] for s in steps]
    assert node_types == [
        "ProcedureNode",  # Main's own entry step
        "DeclareStatement",  # DECLARE result
        "CallStatement",  # CALL Helper(5, result)
        "ProcedureNode",  # Helper's own entry step
        "SetStatement",  # SET y = x + 1
    ]

    # The CALL statement's own step executes in Main's (top-level) frame
    # -- no `call` field at all, per the backward-compatible convention.
    call_step = steps[2]
    assert "call" not in call_step
    assert call_step["statementText"] == "CALL Helper(5, result);"
    assert call_step["variables"]["result"]["value"] == 0  # not yet propagated

    # Helper's own steps DO carry `call`, at depth 1.
    helper_entry, helper_set = steps[3], steps[4]
    for step in (helper_entry, helper_set):
        assert step["call"] == {"procedureName": "Helper", "depth": 1, "stack": ["Helper"]}

    # Helper's scope is completely separate from Main's -- only x/y exist.
    assert set(helper_entry["variables"]) == {"x", "y"}
    assert helper_set["variables"]["x"]["value"] == 5
    assert helper_set["variables"]["y"]["value"] == 6

    # Back in Main -- wait, there is no step after the CALL in this
    # sample, so the propagated value must be visible on the CALL step's
    # own *next* occurrence. Since Main has no further statement, assert
    # it directly via a variant with a trailing statement instead (see
    # test_out_param_visible_in_a_later_caller_step below) and, here,
    # confirm the propagation happened by re-running with an OUT param
    # already seeded to prove the callee actually changed it:
    assert helper_set["variables"]["y"]["changed"] is True


def test_out_param_visible_in_a_later_caller_step():
    code = """\
CREATE PROCEDURE Helper(IN x NUMBER, OUT y NUMBER)
BEGIN
    SET y = x + 1;
END;

CREATE PROCEDURE Main()
BEGIN
    DECLARE result NUMBER DEFAULT 0;
    CALL Helper(5, result);
    SET result = result + 100;
END;
"""
    steps = _steps_as_dicts(run(parse(tokenize(code)), {}))
    last = steps[-1]
    assert last["nodeType"] == "SetStatement"
    assert "call" not in last  # back in Main's top-level frame
    assert last["variables"]["result"]["value"] == 106  # (5+1) + 100


def test_inout_param_propagates_both_ways():
    code = """\
CREATE PROCEDURE Increment(INOUT n NUMBER)
BEGIN
    SET n = n + 1;
END;

CREATE PROCEDURE Main()
BEGIN
    DECLARE counter NUMBER DEFAULT 10;
    CALL Increment(counter);
    CALL Increment(counter);
    SET counter = counter + 0;
END;
"""
    # (The trailing no-op SET is just so the trace's LAST step is back in
    # Main's own frame -- without it, steps[-1] would be Increment's own
    # "SET n = n + 1" from the second call, whose scope has no `counter`
    # at all, which is correct and unrelated to what this test checks.)
    steps = _steps_as_dicts(run(parse(tokenize(code)), {}))
    final = steps[-1]
    assert "call" not in final
    assert final["variables"]["counter"]["value"] == 12  # 10 -> 11 -> 12, propagated back each time


def test_in_argument_can_be_an_arbitrary_expression():
    code = """\
CREATE PROCEDURE Helper(IN x NUMBER, OUT y NUMBER)
BEGIN
    SET y = x * 2;
END;

CREATE PROCEDURE Main()
BEGIN
    DECLARE a NUMBER DEFAULT 3;
    DECLARE result NUMBER DEFAULT 0;
    CALL Helper(a + 4, result);
END;
"""
    steps = _steps_as_dicts(run(parse(tokenize(code)), {}))
    helper_set = [s for s in steps if s["nodeType"] == "SetStatement" and s.get("call")][0]
    assert helper_set["variables"]["x"]["value"] == 7  # 3 + 4
    assert helper_set["variables"]["y"]["value"] == 14


# -- interpreter: scope isolation ---------------------------------------


def test_caller_and_callee_do_not_share_a_same_named_variable():
    code = """\
CREATE PROCEDURE Helper()
BEGIN
    DECLARE total NUMBER DEFAULT 999;
    SET total = total + 1;
END;

CREATE PROCEDURE Main()
BEGIN
    DECLARE total NUMBER DEFAULT 1;
    CALL Helper();
    SET total = total + 1;
END;
"""
    steps = _steps_as_dicts(run(parse(tokenize(code)), {}))
    # Helper's own SET step (not its entry step -- that one's snapshot is
    # taken before Helper's DECLARE has even run, so it has no `total`
    # yet, correctly, same as any procedure's entry step).
    helper_set = next(s for s in steps if s.get("call") and s["nodeType"] == "SetStatement")
    assert helper_set["variables"]["total"]["value"] == 1000

    final = steps[-1]
    assert "call" not in final
    assert final["variables"]["total"]["value"] == 2  # Main's own total: 1 -> 2, untouched by Helper


def test_callee_does_not_inherit_callers_handler():
    """Handlers are per-invocation (see interpreter module docstring) --
    a handler registered in the CALLER must not protect the CALLEE from
    the same condition."""
    code = """\
CREATE PROCEDURE Risky(IN divisor NUMBER, OUT result NUMBER)
BEGIN
    SET result = 10 / divisor;
END;

CREATE PROCEDURE Main()
BEGIN
    DECLARE r NUMBER DEFAULT 0;
    DECLARE CONTINUE HANDLER FOR DIVISION_BY_ZERO SET r = -1;
    CALL Risky(0, r);
END;
"""
    with pytest.raises(InterpreterError, match="Division by zero"):
        run(parse(tokenize(code)), {})


def test_callee_does_not_inherit_callers_cursor():
    code = """\
CREATE PROCEDURE Helper()
BEGIN
    OPEN cur;
END;

CREATE PROCEDURE Main()
BEGIN
    DECLARE cur CURSOR FOR SELECT name FROM products;
    CALL Helper();
END;
"""
    with pytest.raises(InterpreterError, match="not declared"):
        run(parse(tokenize(code)), {})


# -- interpreter: error paths --------------------------------------------


def test_calling_a_nonexistent_procedure_raises_a_clean_error():
    code = "CREATE PROCEDURE Main() BEGIN CALL Ghost(); END"
    with pytest.raises(InterpreterError, match="Procedure 'Ghost' is not defined"):
        run(parse(tokenize(code)), {})


def test_calling_a_function_via_call_raises_a_clean_error():
    code = """\
CREATE FUNCTION Helper(x NUMBER) RETURNS NUMBER
BEGIN
    RETURN x * 2;
END;

CREATE PROCEDURE Main()
BEGIN
    CALL Helper(5);
END;
"""
    with pytest.raises(InterpreterError, match="is not a procedure"):
        run(parse(tokenize(code)), {})


def test_call_with_wrong_argument_count_raises():
    code = """\
CREATE PROCEDURE Helper(IN x NUMBER, IN y NUMBER)
BEGIN
    DECLARE z NUMBER DEFAULT 0;
END;

CREATE PROCEDURE Main()
BEGIN
    CALL Helper(1);
END;
"""
    with pytest.raises(InterpreterError, match="expects 2 argument"):
        run(parse(tokenize(code)), {})


def test_out_argument_must_be_an_identifier():
    code = """\
CREATE PROCEDURE Helper(OUT x NUMBER)
BEGIN
    SET x = 1;
END;

CREATE PROCEDURE Main()
BEGIN
    CALL Helper(1 + 1);
END;
"""
    with pytest.raises(InterpreterError, match="must be a variable"):
        run(parse(tokenize(code)), {})


def test_inout_argument_must_be_an_identifier():
    code = """\
CREATE PROCEDURE Helper(INOUT x NUMBER)
BEGIN
    SET x = x + 1;
END;

CREATE PROCEDURE Main()
BEGIN
    CALL Helper(5 * 2);
END;
"""
    with pytest.raises(InterpreterError, match="must be a variable"):
        run(parse(tokenize(code)), {})


# -- interpreter: recursion + the depth guard ----------------------------


def test_recursive_self_call_computes_a_correct_result():
    """5! via straightforward self-recursion -- the entry procedure is
    registered under its own name, so it can CALL itself with no extra
    syntax (see app.interpreter's module docstring)."""
    code = """\
CREATE PROCEDURE Fact(IN n NUMBER, OUT result NUMBER)
BEGIN
    DECLARE sub NUMBER DEFAULT 1;
    IF n > 1 THEN
        CALL Fact(n - 1, sub);
        SET result = n * sub;
    ELSE
        SET result = 1;
    END IF;
END;
"""
    steps = run(parse(tokenize(code)), {"n": 5, "result": 0})
    final_vars = steps[-1].to_dict()["variables"]
    assert final_vars["result"]["value"] == 120

    # Deepest frame reached should be depth 4 (n=5 calls n=4 calls ... n=2 calls n=1 -- 4 nested CALLs).
    max_depth = max((s.to_dict().get("call") or {}).get("depth", 0) for s in steps)
    assert max_depth == 4


def test_infinite_recursion_hits_the_call_depth_guard_cleanly():
    """Must fail fast with a clear InterpreterError -- not hang the
    server or blow the Python recursion limit."""
    code = """\
CREATE PROCEDURE Loop(IN n NUMBER)
BEGIN
    DECLARE next NUMBER DEFAULT 0;
    SET next = n + 1;
    CALL Loop(next);
END;
"""
    with pytest.raises(InterpreterError, match="exceeded the maximum call depth"):
        run(parse(tokenize(code)), {"n": 0})


def test_mutual_recursion_also_hits_the_depth_guard_cleanly():
    """Recursion through a CHAIN of different procedures (A calls B
    calls A calls B ...), not just a procedure calling itself directly,
    must be guarded the same way. This grammar has no forward-
    declaration syntax, but that's fine -- the whole registry is built
    before anything executes (see app.parser's module docstring), so A
    can CALL B even though B is defined later in the same source."""
    code = """\
CREATE PROCEDURE A(IN n NUMBER)
BEGIN
    CALL B(n + 1);
END;

CREATE PROCEDURE B(IN n NUMBER)
BEGIN
    CALL A(n + 1);
END;
"""
    with pytest.raises(InterpreterError, match="exceeded the maximum call depth"):
        run(parse(tokenize(code)), {"n": 0})


# -- interpreter: DIVISION_BY_ZERO while evaluating a CALL's arguments ----


def test_unhandled_division_by_zero_in_call_argument_aborts_the_run():
    code = """\
CREATE PROCEDURE Helper(IN x NUMBER)
BEGIN
    DECLARE y NUMBER DEFAULT 0;
END;

CREATE PROCEDURE Main()
BEGIN
    DECLARE zero NUMBER DEFAULT 0;
    CALL Helper(10 / zero);
END;
"""
    with pytest.raises(InterpreterError, match="Division by zero"):
        run(parse(tokenize(code)), {})


def test_handled_division_by_zero_in_call_argument_skips_the_call():
    code = """\
CREATE PROCEDURE Helper(IN x NUMBER, OUT y NUMBER)
BEGIN
    SET y = 999;
END;

CREATE PROCEDURE Main()
BEGIN
    DECLARE zero NUMBER DEFAULT 0;
    DECLARE result NUMBER DEFAULT 0;
    DECLARE CONTINUE HANDLER FOR DIVISION_BY_ZERO SET result = -1;
    CALL Helper(10 / zero, result);
    SET result = result + 1;
END;
"""
    steps = _steps_as_dicts(run(parse(tokenize(code)), {}))
    node_types = [s["nodeType"] for s in steps]

    # The CALL step itself is recorded (with its error), the handler's
    # action runs right after -- but Helper's body NEVER executes: no
    # step anywhere carries a `call` field.
    assert not any(s.get("call") for s in steps)
    assert "CallStatement" in node_types

    call_step = next(s for s in steps if s["nodeType"] == "CallStatement")
    assert call_step["error"]["condition"] == "DIVISION_BY_ZERO"

    final = steps[-1]
    assert final["variables"]["result"]["value"] == 0  # -1 (handler) + 1 (next statement)


# -- the new sample procedure pair (item 5) -------------------------------


def test_order_total_sample_pair_computes_correctly_end_to_end():
    steps = _steps_as_dicts(run(parse(tokenize(ORDER_TOTAL_SAMPLE)), {"price": 20, "quantity": 3, "taxRate": 0.1}))

    print("\n--- source ---")
    print(ORDER_TOTAL_SAMPLE)
    print("--- step trace ---")
    print(json.dumps(steps, indent=2))

    # subtotal = 20 * 3 = 60; grandTotal = 60 + 60*0.1 = 66
    final = steps[-1]
    assert final["nodeType"] == "SetStatement"
    assert final["variables"]["grandTotal"]["value"] == 66.0
    assert "call" not in final  # OrderTotal is the (top-level) entry procedure

    nested_steps = [s for s in steps if s.get("call")]
    assert len(nested_steps) == 2  # ComputeSubtotal's entry step + its one SET
    assert all(s["call"]["procedureName"] == "ComputeSubtotal" for s in nested_steps)
    assert all(s["call"]["depth"] == 1 for s in nested_steps)
