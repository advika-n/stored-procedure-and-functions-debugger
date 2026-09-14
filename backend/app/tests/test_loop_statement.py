"""Tests for LOOP/LEAVE support. See app.parser's "LOOP / LEAVE" and
app.interpreter's own section of the same name for the full design this
exercises.

Every test here builds its AST via the real tokenizer -> parser
pipeline (never a hand-built dict), matching this project's existing
testing convention (see test_call_statement.py / test_case_statement.py
/ test_function_call_expression.py).
"""

import pytest

import app.interpreter as interpreter_module
from app.interpreter import InterpreterError, run
from app.parser import ParserError, parse
from app.tokenizer import tokenize


def _steps_as_dicts(steps):
    return [s.to_dict() for s in steps]


# -- tokenizer ----------------------------------------------------------------


def test_loop_and_leave_tokenize_as_keywords():
    tokens = tokenize("LOOP LEAVE; END LOOP;")
    kinds = [(t["type"], t["value"].upper()) for t in tokens]
    assert ("KEYWORD", "LOOP") in kinds
    assert ("KEYWORD", "LEAVE") in kinds


def test_colon_tokenizes_as_punctuation():
    tokens = tokenize("outer: LOOP END LOOP outer;")
    colon = next(t for t in tokens if t["value"] == ":")
    assert colon["type"] == "PUNCTUATION"


# -- parser: unlabeled LOOP ----------------------------------------------------


def test_unlabeled_loop_parses_with_no_label():
    code = """\
CREATE PROCEDURE Demo()
BEGIN
    DECLARE i NUMBER DEFAULT 0;
    LOOP
        SET i = i + 1;
        LEAVE;
    END LOOP;
END
"""
    ast = parse(tokenize(code))
    loop_stmt = ast["body"][1]
    assert loop_stmt["type"] == "LoopStatement"
    assert loop_stmt["label"] is None
    assert len(loop_stmt["body"]) == 2
    assert loop_stmt["body"][0]["type"] == "SetStatement"
    leave_stmt = loop_stmt["body"][1]
    assert leave_stmt["type"] == "LeaveStatement"
    assert leave_stmt["label"] is None


# -- parser: labeled LOOP -------------------------------------------------------


def test_labeled_loop_parses_label_and_matching_end_label():
    code = """\
CREATE PROCEDURE Demo()
BEGIN
    outer: LOOP
        LEAVE outer;
    END LOOP outer;
END
"""
    ast = parse(tokenize(code))
    loop_stmt = ast["body"][0]
    assert loop_stmt["type"] == "LoopStatement"
    assert loop_stmt["label"] == "outer"
    assert loop_stmt["body"][0] == {"type": "LeaveStatement", "label": "outer", "line": 4}


def test_labeled_loop_end_label_is_optional():
    code = """\
CREATE PROCEDURE Demo()
BEGIN
    outer: LOOP
        LEAVE outer;
    END LOOP;
END
"""
    ast = parse(tokenize(code))
    assert ast["body"][0]["label"] == "outer"


def test_end_loop_label_mismatch_is_a_parser_error():
    code = "a: LOOP LEAVE a; END LOOP b;"
    with pytest.raises(ParserError, match="does not match"):
        parse(tokenize(code))


def test_end_loop_label_with_no_opening_label_is_a_parser_error():
    code = "LOOP LEAVE; END LOOP b;"
    with pytest.raises(ParserError, match="has no opening label"):
        parse(tokenize(code))


def test_loop_label_line_is_the_label_tokens_own_line():
    code = "outer:\nLOOP\n    LEAVE outer;\nEND LOOP outer;"
    ast = parse(tokenize(code))
    assert ast["body"][0]["line"] == 1


# -- parser: LEAVE --------------------------------------------------------------


def test_unlabeled_leave_parses():
    ast = parse(tokenize("LOOP LEAVE; END LOOP;"))
    assert ast["body"][0]["body"][0] == {"type": "LeaveStatement", "label": None, "line": 1}


def test_labeled_leave_parses():
    ast = parse(tokenize("mylabel: LOOP LEAVE mylabel; END LOOP mylabel;"))
    assert ast["body"][0]["body"][0]["label"] == "mylabel"


def test_missing_semicolon_after_leave_is_a_parser_error():
    with pytest.raises(ParserError):
        parse(tokenize("LOOP LEAVE END LOOP;"))


def test_missing_end_loop_is_a_parser_error():
    with pytest.raises(ParserError):
        parse(tokenize("LOOP LEAVE;"))


# -- parser: nesting inside every other block construct -------------------------


def test_loop_nests_inside_if_while_and_case():
    code = """\
CREATE PROCEDURE Demo()
BEGIN
    DECLARE x NUMBER DEFAULT 1;
    IF x = 1 THEN
        WHILE x < 3 DO
            CASE x
                WHEN 1 THEN
                    LOOP
                        LEAVE;
                    END LOOP;
            END CASE;
            SET x = x + 1;
        END WHILE;
    END IF;
END
"""
    # Just needs to parse without raising -- the real assertion is that
    # this doesn't blow up, since `_parse_block`/`_parse_statement` are
    # the exact same generic machinery IF/WHILE/CASE already nest through.
    ast = parse(tokenize(code))
    assert ast["type"] == "ProcedureNode"


def test_if_while_and_case_nest_inside_loop():
    code = """\
CREATE PROCEDURE Demo()
BEGIN
    DECLARE x NUMBER DEFAULT 1;
    LOOP
        IF x > 5 THEN
            LEAVE;
        END IF;
        WHILE x < 3 DO
            SET x = x + 1;
        END WHILE;
        CASE x
            WHEN 3 THEN
                SET x = x + 1;
        END CASE;
    END LOOP;
END
"""
    ast = parse(tokenize(code))
    assert ast["type"] == "ProcedureNode"


def test_loop_nests_inside_another_loop():
    code = """\
CREATE PROCEDURE Demo()
BEGIN
    outer: LOOP
        inner: LOOP
            LEAVE inner;
        END LOOP inner;
        LEAVE outer;
    END LOOP outer;
END
"""
    ast = parse(tokenize(code))
    outer = ast["body"][0]
    assert outer["label"] == "outer"
    assert outer["body"][0]["type"] == "LoopStatement"
    assert outer["body"][0]["label"] == "inner"


# -- interpreter: basic unlabeled LOOP/LEAVE -------------------------------------


def test_unlabeled_loop_runs_until_leave():
    code = """\
CREATE PROCEDURE Demo()
BEGIN
    DECLARE i NUMBER DEFAULT 0;
    LOOP
        SET i = i + 1;
        IF i > 3 THEN
            LEAVE;
        END IF;
    END LOOP;
END
"""
    steps = run(parse(tokenize(code)), {})
    final_i = steps[-1].to_dict()["variables"]["i"]["value"]
    assert final_i == 4


def test_loop_step_carries_loop_field_reusing_whiles_shape():
    code = """\
CREATE PROCEDURE Demo()
BEGIN
    DECLARE i NUMBER DEFAULT 0;
    LOOP
        SET i = i + 1;
        IF i > 2 THEN
            LEAVE;
        END IF;
    END LOOP;
END
"""
    steps = _steps_as_dicts(run(parse(tokenize(code)), {}))
    loop_steps = [s for s in steps if s["nodeType"] == "LoopStatement"]
    assert [s["loop"]["iteration"] for s in loop_steps] == [1, 2, 3]
    assert all(s["loop"]["result"] is True for s in loop_steps)
    assert all(s["loop"]["condition"] == "LOOP" for s in loop_steps)


def test_labeled_loop_step_includes_label_in_condition_text():
    code = "outer: LOOP LEAVE outer; END LOOP outer;"
    steps = _steps_as_dicts(run(parse(tokenize(code)), {}))
    loop_step = next(s for s in steps if s["nodeType"] == "LoopStatement")
    assert loop_step["loop"]["condition"] == "LOOP outer"


def test_leave_step_is_recorded_with_no_branch_or_loop_field():
    code = "LOOP LEAVE; END LOOP;"
    steps = _steps_as_dicts(run(parse(tokenize(code)), {}))
    leave_step = next(s for s in steps if s["nodeType"] == "LeaveStatement")
    assert leave_step["statementText"] == "LEAVE;"
    assert "branch" not in leave_step
    assert "loop" not in leave_step


def test_labeled_leave_step_renders_its_label():
    code = "outer: LOOP LEAVE outer; END LOOP outer;"
    steps = _steps_as_dicts(run(parse(tokenize(code)), {}))
    leave_step = next(s for s in steps if s["nodeType"] == "LeaveStatement")
    assert leave_step["statementText"] == "LEAVE outer;"


# -- interpreter: nested loops, labeled/unlabeled LEAVE resolution --------------


def test_unlabeled_leave_only_breaks_the_innermost_loop():
    code = """\
CREATE PROCEDURE Demo()
BEGIN
    DECLARE outerCount NUMBER DEFAULT 0;
    DECLARE innerCount NUMBER DEFAULT 0;
    outer: LOOP
        SET outerCount = outerCount + 1;
        IF outerCount > 2 THEN
            LEAVE outer;
        END IF;
        DECLARE j NUMBER DEFAULT 0;
        inner: LOOP
            SET j = j + 1;
            SET innerCount = innerCount + 1;
            IF j > 1 THEN
                LEAVE;
            END IF;
        END LOOP inner;
    END LOOP outer;
END
"""
    steps = run(parse(tokenize(code)), {})
    final = steps[-1].to_dict()["variables"]
    # Outer runs 3 times (1,2,3 -- LEAVEs on outerCount>2); inner runs
    # twice per outer pass that actually reaches it (passes 1 and 2 --
    # the 3rd pass LEAVEs outer before ever reaching the inner LOOP).
    assert final["outerCount"]["value"] == 3
    assert final["innerCount"]["value"] == 4  # 2 inner passes * 2 iterations each


def test_labeled_leave_breaks_directly_out_of_an_outer_loop_from_inside_the_inner_one():
    """The flagship nested case this phase asked for: LEAVE <label> from
    inside a doubly-nested LOOP jumps straight past the innermost loop
    entirely, skipping any remaining code in the outer loop's own body
    too -- not just stopping at the inner loop's own boundary."""
    code = """\
CREATE PROCEDURE FindPairSum()
BEGIN
    DECLARE target NUMBER DEFAULT 7;
    DECLARE i NUMBER DEFAULT 1;
    DECLARE j NUMBER DEFAULT 0;
    DECLARE foundI NUMBER DEFAULT 0;
    DECLARE foundJ NUMBER DEFAULT 0;
    outer: LOOP
        IF i > 5 THEN
            LEAVE outer;
        END IF;
        SET j = 1;
        inner: LOOP
            IF j > 5 THEN
                LEAVE;
            END IF;
            IF i + j = target THEN
                SET foundI = i;
                SET foundJ = j;
                LEAVE outer;
            END IF;
            SET j = j + 1;
        END LOOP inner;
        SET i = i + 1;
    END LOOP outer;
END
"""
    steps = run(parse(tokenize(code)), {})
    final = steps[-1].to_dict()["variables"]
    # Hand-derived (see samples.js/testCaseExpectations.js for the same
    # sample and its full derivation): i=1's inner pass (j=1..5) never
    # sums to 7 -- inner LEAVEs unlabeled once j>5, i increments to 2.
    # i=2's inner pass hits i+j=7 at j=5 -- LEAVE outer fires directly,
    # skipping i=2's own trailing `SET i = i + 1;` and every further
    # outer pass entirely.
    assert final["i"]["value"] == 2
    assert final["j"]["value"] == 5
    assert final["foundI"]["value"] == 2
    assert final["foundJ"]["value"] == 5
    # The final step is the LEAVE outer statement itself, not a later one.
    assert steps[-1].node_type == "LeaveStatement"


def test_leave_with_same_label_reused_across_sibling_loops_targets_only_its_own_loop():
    """Two sequential, unrelated LOOPs that happen to reuse the same
    label name (perfectly legal -- labels aren't globally unique, only
    locally meaningful while their own loop is on the stack) don't
    interfere with each other."""
    code = """\
CREATE PROCEDURE Demo()
BEGIN
    DECLARE a NUMBER DEFAULT 0;
    DECLARE b NUMBER DEFAULT 0;
    x: LOOP
        SET a = a + 1;
        LEAVE x;
    END LOOP x;
    x: LOOP
        SET b = b + 1;
        LEAVE x;
    END LOOP x;
END
"""
    steps = run(parse(tokenize(code)), {})
    final = steps[-1].to_dict()["variables"]
    assert final["a"]["value"] == 1
    assert final["b"]["value"] == 1


# -- interpreter: errors ---------------------------------------------------------


def test_leave_outside_any_loop_is_an_interpreter_error():
    with pytest.raises(InterpreterError, match="LEAVE used outside of any LOOP"):
        run(parse(tokenize("LEAVE;")), {})


def test_labeled_leave_with_no_matching_enclosing_loop_is_an_interpreter_error():
    code = "outer: LOOP LEAVE nope; END LOOP outer;"
    with pytest.raises(InterpreterError, match="no enclosing LOOP is labeled 'nope'"):
        run(parse(tokenize(code)), {})


def test_loop_with_no_leave_hits_the_max_iterations_guard(monkeypatch):
    # Reuses the exact same MAX_LOOP_ITERATIONS constant WHILE already
    # guards with (see the module docstring's "LOOP / LEAVE" section) --
    # lowered here just so the test doesn't actually spin 10,000 times.
    monkeypatch.setattr(interpreter_module, "MAX_LOOP_ITERATIONS", 5)
    code = """\
CREATE PROCEDURE Demo()
BEGIN
    DECLARE i NUMBER DEFAULT 0;
    LOOP
        SET i = i + 1;
    END LOOP;
END
"""
    with pytest.raises(InterpreterError, match=r"LOOP exceeded 5 iterations"):
        run(parse(tokenize(code)), {})


def test_labeled_loop_with_no_leave_hits_the_max_iterations_guard_names_its_label(monkeypatch):
    monkeypatch.setattr(interpreter_module, "MAX_LOOP_ITERATIONS", 3)
    code = "outer: LOOP DECLARE x NUMBER DEFAULT 1; END LOOP outer;"
    with pytest.raises(InterpreterError, match=r"LOOP outer exceeded 3 iterations"):
        run(parse(tokenize(code)), {})


# -- interpreter: RETURN inside a LOOP stops the whole function, not just the loop --


def test_return_inside_a_loop_stops_the_whole_function_not_just_the_loop():
    code = """\
CREATE FUNCTION FindFirst(limit NUMBER) RETURNS NUMBER
BEGIN
    DECLARE i NUMBER DEFAULT 0;
    LOOP
        SET i = i + 1;
        IF i > limit THEN
            RETURN i;
        END IF;
    END LOOP;
    RETURN -1;
END
"""
    steps = run(parse(tokenize(code)), {"limit": 3})
    final = steps[-1].to_dict()
    assert final["nodeType"] == "ReturnNode"
    assert final["returnValue"]["value"] == 4
    # The trailing `RETURN -1;` after the LOOP never executes.
    assert not any(s.to_dict().get("returnValue", {}).get("value") == -1 for s in steps)


# -- interpreter: loop-label scope is isolated across a CALL boundary -----------


def test_leave_cannot_target_a_label_from_the_callers_own_loop():
    """LOOP/LEAVE nesting is lexical -- a callee's LEAVE can only ever
    target a loop written inside its OWN source, never one still on the
    caller's stack purely because the caller happens to be paused inside
    a CALL right now."""
    code = """\
CREATE PROCEDURE Helper()
BEGIN
    LEAVE outer;
END

CREATE PROCEDURE Main()
BEGIN
    DECLARE i NUMBER DEFAULT 1;
    outer: LOOP
        IF i > 2 THEN
            LEAVE outer;
        END IF;
        CALL Helper();
        SET i = i + 1;
    END LOOP outer;
END
"""
    with pytest.raises(InterpreterError, match="no enclosing LOOP is labeled 'outer'"):
        run(parse(tokenize(code)), {})


def test_callee_may_reuse_the_same_label_name_as_the_caller_independently():
    """The callee's own `outer`-labeled loop is a completely separate,
    independently-resolved loop from the caller's own `outer` -- no
    collision, no interference either direction."""
    code = """\
CREATE PROCEDURE Helper()
BEGIN
    DECLARE k NUMBER DEFAULT 0;
    outer: LOOP
        SET k = k + 1;
        LEAVE outer;
    END LOOP outer;
END

CREATE PROCEDURE Main()
BEGIN
    DECLARE i NUMBER DEFAULT 1;
    outer: LOOP
        IF i > 2 THEN
            LEAVE outer;
        END IF;
        CALL Helper();
        SET i = i + 1;
    END LOOP outer;
END
"""
    steps = run(parse(tokenize(code)), {})
    # Made it all the way back to Main's own top-level frame and finished
    # cleanly (i reaches 3, then LEAVEs Main's own `outer`) -- proof the
    # callee's own LEAVE never accidentally consumed/corrupted Main's
    # loop-stack entry.
    final_top_level = next(s for s in reversed(steps) if s.to_dict().get("call") is None)
    assert final_top_level.to_dict()["variables"]["i"]["value"] == 3


def test_loop_inside_a_called_procedure_carries_the_call_field():
    code = """\
CREATE PROCEDURE Helper()
BEGIN
    DECLARE i NUMBER DEFAULT 0;
    LOOP
        SET i = i + 1;
        LEAVE;
    END LOOP;
END

CREATE PROCEDURE Main()
BEGIN
    CALL Helper();
END
"""
    steps = _steps_as_dicts(run(parse(tokenize(code)), {}))
    loop_step = next(s for s in steps if s["nodeType"] == "LoopStatement")
    assert loop_step["call"] == {"procedureName": "Helper", "depth": 1, "stack": ["Helper"]}
    leave_step = next(s for s in steps if s["nodeType"] == "LeaveStatement")
    assert leave_step["call"] == {"procedureName": "Helper", "depth": 1, "stack": ["Helper"]}
