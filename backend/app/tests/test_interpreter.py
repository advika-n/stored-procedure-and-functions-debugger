import json
import sqlite3

import pytest

from app.interpreter import InterpreterError, run
from app.parser import parse
from app.tokenizer import tokenize

# A small CalculateDiscount procedure: price/quantity come in as
# parameters, total and discount are locals computed from them.
CALCULATE_DISCOUNT = """\
DECLARE total NUMBER DEFAULT 0;
DECLARE discount NUMBER DEFAULT 0;
SET total = price * quantity;
IF total > 100 THEN
    SET discount = total * 0.1;
ELSE
    SET discount = total * 0.05;
END IF;
SET total = total - discount;
"""


def _run_calculate_discount(price, quantity):
    ast = parse(tokenize(CALCULATE_DISCOUNT))
    return run(ast, {"price": price, "quantity": quantity})


def test_calculate_discount_prints_step_trace():
    """Run CalculateDiscount and print its DebugStep trace.

    Run with `pytest -s` to see the printed trace and compare its
    shape (stepNumber, line, variables, branch) by eye against the
    source above.
    """
    steps = _run_calculate_discount(price=20, quantity=6)

    print("\n--- source ---")
    print(CALCULATE_DISCOUNT)
    print("--- step trace (price=20, quantity=6) ---")
    print(json.dumps([s.to_dict() for s in steps], indent=2))

    # total = price * quantity = 120 (> 100), so the THEN branch runs:
    # discount = 120 * 0.1 = 12, total = 120 - 12 = 108
    assert len(steps) == 6

    step1 = steps[0].to_dict()
    assert step1["stepNumber"] == 1
    assert step1["line"] == 1
    assert step1["nodeType"] == "DeclareStatement"
    assert step1["statementText"] == "DECLARE total NUMBER DEFAULT 0;"
    assert step1["variables"]["total"] == {"value": 0, "type": "number", "changed": True, "isOutput": False}
    assert step1["variables"]["price"] == {"value": 20, "type": "number", "changed": False, "isOutput": False}
    assert step1["variables"]["quantity"] == {"value": 6, "type": "number", "changed": False, "isOutput": False}
    assert "discount" not in step1["variables"]  # not declared yet

    step3 = steps[2].to_dict()
    assert step3["nodeType"] == "SetStatement"
    assert step3["statementText"] == "SET total = price * quantity;"
    assert step3["variables"]["total"] == {"value": 120, "type": "number", "changed": True, "isOutput": False}

    step4 = steps[3].to_dict()
    assert step4["nodeType"] == "IfStatement"
    assert step4["line"] == 4
    assert step4["statementText"] == "IF total > 100 THEN"
    assert step4["branch"] == {"condition": "total > 100", "result": True, "path": "then"}
    # Nothing changed on the condition-check step itself.
    assert step4["variables"]["total"]["changed"] is False

    step5 = steps[4].to_dict()
    assert step5["nodeType"] == "SetStatement"
    assert step5["line"] == 5
    assert step5["variables"]["discount"] == {"value": 12.0, "type": "number", "changed": True, "isOutput": False}

    step6 = steps[5].to_dict()
    assert step6["nodeType"] == "SetStatement"
    assert step6["line"] == 9
    assert step6["variables"]["total"] == {"value": 108.0, "type": "number", "changed": True, "isOutput": False}
    assert step6["variables"]["discount"]["changed"] is False


def test_calculate_discount_takes_else_branch_for_small_order():
    steps = _run_calculate_discount(price=10, quantity=2)  # total = 20, <= 100

    if_step = next(s.to_dict() for s in steps if s.node_type == "IfStatement")
    assert if_step["branch"] == {"condition": "total > 100", "result": False, "path": "else"}

    final = steps[-1].to_dict()
    # discount = 20 * 0.05 = 1.0, total = 20 - 1.0 = 19.0
    assert final["variables"]["discount"]["value"] == 1.0
    assert final["variables"]["total"]["value"] == 19.0


def test_if_without_else_can_take_no_branch():
    ast = parse(tokenize("IF x > 10 THEN SET x = 0; END IF;"))
    steps = run(ast, {"x": 1})

    if_step = steps[0].to_dict()
    assert if_step["branch"] == {"condition": "x > 10", "result": False, "path": "none"}
    # The THEN body never ran, so there's only the IfStatement step.
    assert len(steps) == 1
    assert if_step["variables"]["x"]["value"] == 1


def test_while_loop_produces_a_step_per_condition_check():
    ast = parse(tokenize("WHILE count < 3 DO SET count = count + 1; END WHILE;"))
    steps = run(ast, {"count": 0})

    while_steps = [s.to_dict() for s in steps if s.node_type == "WhileStatement"]
    # Checked when count is 0, 1, 2 (all true, loop runs) and 3 (false, exits).
    assert [s["loop"]["result"] for s in while_steps] == [True, True, True, False]
    assert [s["loop"]["iteration"] for s in while_steps] == [1, 2, 3, 4]

    final_count = [s for s in steps if s.node_type == "SetStatement"][-1]
    assert final_count.to_dict()["variables"]["count"]["value"] == 3


def test_set_on_undeclared_variable_raises():
    ast = parse(tokenize("SET x = 1;"))
    with pytest.raises(InterpreterError):
        run(ast, {})


def test_division_by_zero_raises():
    ast = parse(tokenize("DECLARE x NUMBER DEFAULT 1 / 0;"))
    with pytest.raises(InterpreterError):
        run(ast, {})


def test_runaway_while_loop_is_capped():
    ast = parse(tokenize("WHILE 1 = 1 DO SET x = x + 1; END WHILE;"))
    with pytest.raises(InterpreterError):
        run(ast, {"x": 0})


# -- cursors ------------------------------------------------------------
#
# The required demo scenario: a cursor opened over a 3-row SQLite table,
# looped through with FETCH, accumulating a value, then closed.


def _make_products_db() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE products (name TEXT, price NUMBER)")
    conn.executemany(
        "INSERT INTO products (name, price) VALUES (?, ?)",
        [("Widget", 10), ("Gadget", 25), ("Gizmo", 15)],
    )
    conn.commit()
    return conn


CURSOR_LOOP_PROCEDURE = """\
DECLARE total NUMBER DEFAULT 0;
DECLARE item_name STRING DEFAULT '';
DECLARE item_price NUMBER DEFAULT 0;
DECLARE prod_cursor CURSOR FOR SELECT name, price FROM products;
OPEN prod_cursor;
WHILE prod_cursor%FOUND DO
    FETCH prod_cursor INTO item_name, item_price;
    SET total = total + item_price;
END WHILE;
CLOSE prod_cursor;
"""


def test_cursor_loop_over_a_three_row_table_accumulates_and_prints_trace():
    """Open a cursor over a 3-row SQLite table, loop through it with
    FETCH accumulating `total`, and close it.

    Run with `pytest -s` to see the printed trace and eyeball
    cursor.currentRow / cursor.hasMore across the loop by eye.
    """
    conn = _make_products_db()
    ast = parse(tokenize(CURSOR_LOOP_PROCEDURE))
    steps = run(ast, db_connection=conn)

    print("\n--- source ---")
    print(CURSOR_LOOP_PROCEDURE)
    print("--- step trace ---")
    print(json.dumps([s.to_dict() for s in steps], indent=2))

    cursor_steps = [s.to_dict() for s in steps if s.to_dict().get("cursor")]
    kinds = [(s["nodeType"], s["cursor"]) for s in cursor_steps]

    # DECLARE prod_cursor -- not open yet.
    assert kinds[0] == ("CursorDeclNode", {"name": "prod_cursor", "currentRow": None, "rowIndex": 0, "hasMore": False})

    # OPEN prod_cursor -- 3 rows buffered, nothing fetched yet.
    assert kinds[1] == ("OpenCursorNode", {"name": "prod_cursor", "currentRow": None, "rowIndex": 0, "hasMore": True})

    # Three FETCHes, one per row, currentRow updating each time.
    fetch_cursor_fields = [c for kind, c in kinds if kind == "FetchCursorNode"]
    assert fetch_cursor_fields == [
        {"name": "prod_cursor", "currentRow": {"name": "Widget", "price": 10}, "rowIndex": 0, "hasMore": True},
        {"name": "prod_cursor", "currentRow": {"name": "Gadget", "price": 25}, "rowIndex": 1, "hasMore": True},
        {"name": "prod_cursor", "currentRow": {"name": "Gizmo", "price": 15}, "rowIndex": 2, "hasMore": False},
    ]

    # CLOSE prod_cursor -- last thing recorded.
    assert kinds[-1] == ("CloseCursorNode", {"name": "prod_cursor", "currentRow": None, "rowIndex": 3, "hasMore": False})

    # WHILE prod_cursor%FOUND checked 4 times: true, true, true, then
    # false (after the 3rd FETCH consumes the last row) -- the loop
    # never calls FETCH with nothing left, so FETCH's own NOT_FOUND
    # path is exercised separately below.
    while_results = [s.to_dict()["loop"]["result"] for s in steps if s.node_type == "WhileStatement"]
    assert while_results == [True, True, True, False]

    # 10 + 25 + 15 = 50, and it accumulated via three separate SET
    # statements (not hardcoded) -- proves this ran through the real
    # interpreter loop, not a canned result.
    final_total = next(
        s.to_dict()["variables"]["total"]["value"]
        for s in reversed(steps)
        if s.node_type == "SetStatement"
    )
    assert final_total == 50

    conn.close()


CURSOR_EXPLICIT_FLAG_PROCEDURE = """\
DECLARE total NUMBER DEFAULT 0;
DECLARE item_name STRING DEFAULT '';
DECLARE item_price NUMBER DEFAULT 0;
DECLARE done NUMBER DEFAULT 0;
DECLARE prod_cursor CURSOR FOR SELECT name, price FROM products;
OPEN prod_cursor;
WHILE done = 0 DO
    FETCH prod_cursor INTO item_name, item_price;
    IF prod_cursor%NOTFOUND THEN
        SET done = 1;
    ELSE
        SET total = total + item_price;
    END IF;
END WHILE;
CLOSE prod_cursor;
"""


def test_cursor_loop_using_the_documented_explicit_flag_fallback_pattern():
    """The fallback style documented for when %FOUND isn't used directly
    as the WHILE condition: an explicit boolean flag variable, set by
    checking %NOTFOUND right after each FETCH. This intentionally keeps
    calling FETCH one time past the last real row, so it also exercises
    FETCH's NOT_FOUND (hasMore=False, no row) path directly."""
    conn = _make_products_db()
    ast = parse(tokenize(CURSOR_EXPLICIT_FLAG_PROCEDURE))
    steps = run(ast, db_connection=conn)

    fetch_steps = [s.to_dict() for s in steps if s.node_type == "FetchCursorNode"]
    assert [f["cursor"]["hasMore"] for f in fetch_steps] == [True, True, False, False]
    # The 4th FETCH ran past the end: no row, so no currentRow.
    assert fetch_steps[-1]["cursor"]["currentRow"] is None

    final_total = next(
        s.to_dict()["variables"]["total"]["value"]
        for s in reversed(steps)
        if s.node_type == "SetStatement" and "total" in s.to_dict()["variables"]
    )
    assert final_total == 50

    conn.close()


def test_fetch_past_the_end_does_not_touch_target_variables():
    conn = _make_products_db()
    code = """\
DECLARE item_name STRING DEFAULT 'untouched';
DECLARE prod_cursor CURSOR FOR SELECT name FROM products WHERE price > 1000;
OPEN prod_cursor;
FETCH prod_cursor INTO item_name;
CLOSE prod_cursor;
"""
    ast = parse(tokenize(code))
    steps = run(ast, db_connection=conn)

    fetch_step = next(s.to_dict() for s in steps if s.node_type == "FetchCursorNode")
    assert fetch_step["cursor"] == {"name": "prod_cursor", "currentRow": None, "rowIndex": 0, "hasMore": False}
    assert fetch_step["variables"]["item_name"]["value"] == "untouched"

    conn.close()


def test_opening_an_undeclared_cursor_raises():
    ast = parse(tokenize("OPEN cur;"))
    with pytest.raises(InterpreterError, match="not declared"):
        run(ast)


def test_opening_an_already_open_cursor_raises():
    conn = _make_products_db()
    code = "DECLARE cur CURSOR FOR SELECT name FROM products; OPEN cur; OPEN cur;"
    ast = parse(tokenize(code))
    with pytest.raises(InterpreterError, match="already open"):
        run(ast, db_connection=conn)
    conn.close()


def test_fetching_from_an_unopened_cursor_raises():
    code = "DECLARE cur CURSOR FOR SELECT name FROM products; DECLARE x STRING DEFAULT ''; FETCH cur INTO x;"
    ast = parse(tokenize(code))
    with pytest.raises(InterpreterError, match="not open"):
        run(ast)


def test_closing_an_unopened_cursor_raises():
    ast = parse(tokenize("DECLARE cur CURSOR FOR SELECT name FROM products; CLOSE cur;"))
    with pytest.raises(InterpreterError, match="not open"):
        run(ast)


def test_cursor_query_against_a_missing_table_raises_a_clear_error():
    # No db_connection supplied -- run() falls back to a fresh, empty
    # in-memory database, so this table genuinely doesn't exist (the
    # documented scope boundary: no schema-authoring feature yet).
    ast = parse(tokenize("DECLARE cur CURSOR FOR SELECT * FROM nonexistent_table; OPEN cur;"))
    with pytest.raises(InterpreterError, match="query failed"):
        run(ast)


def test_fetch_column_count_mismatch_raises():
    conn = _make_products_db()
    code = """\
DECLARE only_one STRING DEFAULT '';
DECLARE cur CURSOR FOR SELECT name, price FROM products;
OPEN cur;
FETCH cur INTO only_one;
"""
    ast = parse(tokenize(code))
    with pytest.raises(InterpreterError, match="column"):
        run(ast, db_connection=conn)
    conn.close()


def test_cursor_state_is_not_exposed_in_the_variable_watch_table():
    conn = _make_products_db()
    code = "DECLARE cur CURSOR FOR SELECT name FROM products; OPEN cur; CLOSE cur;"
    ast = parse(tokenize(code))
    steps = run(ast, db_connection=conn)

    for step in steps:
        assert "cur" not in step.to_dict()["variables"]

    conn.close()


# -- exception handlers ---------------------------------------------------


def test_not_found_handler_runs_automatically_and_lets_the_loop_exit_cleanly():
    """The required end-to-end story: cursor opens, fetches update
    currentRow each step, NOT_FOUND triggers the handler, loop exits
    cleanly -- using a plain `WHILE done = 0` loop with no %FOUND /
    %NOTFOUND checks in the SQL at all, since the handler now does
    that automatically.

    The loop body guards the accumulation with `IF done = 0` -- a
    CONTINUE HANDLER resumes at the *next statement*, not by skipping
    the rest of the loop body, so without this guard the 4th
    (out-of-data) iteration would still run `SET total = total +
    item_price` against stale data from the 3rd row. This is a real,
    well-known MySQL cursor-loop gotcha, not an artifact of this
    interpreter -- and exactly the kind of thing this debugger is for
    surfacing.
    """
    conn = _make_products_db()
    code = """\
DECLARE total NUMBER DEFAULT 0;
DECLARE item_name STRING DEFAULT '';
DECLARE item_price NUMBER DEFAULT 0;
DECLARE done NUMBER DEFAULT 0;
DECLARE CONTINUE HANDLER FOR NOT_FOUND SET done = 1;
DECLARE prod_cursor CURSOR FOR SELECT name, price FROM products;
OPEN prod_cursor;
WHILE done = 0 DO
    FETCH prod_cursor INTO item_name, item_price;
    IF done = 0 THEN
        SET total = total + item_price;
    END IF;
END WHILE;
CLOSE prod_cursor;
"""
    ast = parse(tokenize(code))
    steps = run(ast, db_connection=conn)
    step_dicts = [s.to_dict() for s in steps]

    # 4 FETCHes total: 3 real rows, then one that runs past the end and
    # triggers NOT_FOUND.
    fetch_steps = [s for s in step_dicts if s["nodeType"] == "FetchCursorNode"]
    assert len(fetch_steps) == 4
    assert [f["cursor"]["currentRow"] for f in fetch_steps] == [
        {"name": "Widget", "price": 10},
        {"name": "Gadget", "price": 25},
        {"name": "Gizmo", "price": 15},
        None,
    ]
    assert [f["cursor"]["hasMore"] for f in fetch_steps] == [True, True, False, False]

    # The 4th FETCH is the one that triggers NOT_FOUND -- caught by
    # the registered handler, not "unhandled".
    triggering_fetch = fetch_steps[3]
    assert triggering_fetch["error"] == {
        "condition": "NOT_FOUND",
        "message": "Cursor 'prod_cursor' has no more rows to fetch",
        "handler": "NOT_FOUND handler",
    }
    assert "error" not in fetch_steps[0]  # a successful FETCH carries no error field

    # The handler's action (SET done = 1) shows up as its own step,
    # immediately after the triggering FETCH -- not merged into it,
    # not out of order.
    triggering_index = step_dicts.index(triggering_fetch)
    handler_step = step_dicts[triggering_index + 1]
    assert handler_step["nodeType"] == "SetStatement"
    assert handler_step["variables"]["done"] == {"value": 1, "type": "number", "changed": True, "isOutput": False}

    # The loop then exits cleanly on its next condition check (done=1
    # now) -- no crash, no leftover partial trace.
    final_while = next(s for s in reversed(step_dicts) if s["nodeType"] == "WhileStatement")
    assert final_while["loop"]["result"] is False

    # 10 + 25 + 15 = 50 -- the `IF done = 0` guard means the 4th
    # (out-of-data) iteration never re-adds the stale item_price left
    # over from the 3rd row.
    accumulate_steps = [s for s in step_dicts if s["statementText"] == "SET total = total + item_price;"]
    assert len(accumulate_steps) == 3  # guard skipped it on the 4th iteration
    assert accumulate_steps[-1]["variables"]["total"]["value"] == 50

    conn.close()


def test_not_found_without_a_handler_is_unhandled_but_still_non_fatal():
    conn = _make_products_db()
    code = """\
DECLARE item_name STRING DEFAULT '';
DECLARE cur CURSOR FOR SELECT name FROM products WHERE price > 1000;
OPEN cur;
FETCH cur INTO item_name;
"""
    ast = parse(tokenize(code))
    steps = run(ast, db_connection=conn)  # must not raise

    fetch_step = next(s.to_dict() for s in steps if s.node_type == "FetchCursorNode")
    assert fetch_step["error"] == {
        "condition": "NOT_FOUND",
        "message": "Cursor 'cur' has no more rows to fetch",
        "handler": "unhandled",
    }
    conn.close()


def test_division_by_zero_handler_runs_and_execution_continues():
    code = """\
DECLARE total NUMBER DEFAULT 0;
DECLARE safe_default NUMBER DEFAULT -1;
DECLARE CONTINUE HANDLER FOR DIVISION_BY_ZERO SET safe_default = 0;
SET total = 10 / 0;
SET total = total + 1;
"""
    ast = parse(tokenize(code))
    steps = run(ast)  # must not raise
    step_dicts = [s.to_dict() for s in steps]

    failing_set = next(s for s in step_dicts if s["statementText"] == "SET total = 10 / 0;")
    assert failing_set["error"] == {
        "condition": "DIVISION_BY_ZERO",
        "message": "Division by zero",
        "handler": "DIVISION_BY_ZERO handler",
    }
    # The assignment never happened -- total keeps its previous value.
    assert failing_set["variables"]["total"] == {"value": 0, "type": "number", "changed": False, "isOutput": False}

    # The handler's action runs immediately after, as its own step.
    failing_index = step_dicts.index(failing_set)
    handler_step = step_dicts[failing_index + 1]
    assert handler_step["statementText"] == "SET safe_default = 0;"
    assert handler_step["variables"]["safe_default"]["value"] == 0

    # Execution carried on to the next statement rather than aborting.
    last_step = step_dicts[-1]
    assert last_step["statementText"] == "SET total = total + 1;"
    assert last_step["variables"]["total"]["value"] == 1


def test_division_by_zero_without_a_handler_still_raises_same_as_before():
    # Backward compatibility: this is the exact scenario the pre-existing
    # test_division_by_zero_raises covers -- unhandled DIVISION_BY_ZERO
    # must still abort the run exactly like it always did.
    ast = parse(tokenize("DECLARE x NUMBER DEFAULT 1 / 0;"))
    with pytest.raises(InterpreterError, match="Division by zero"):
        run(ast, {})


def test_division_by_zero_handler_in_if_condition():
    code = """\
DECLARE flag NUMBER DEFAULT 0;
DECLARE CONTINUE HANDLER FOR DIVISION_BY_ZERO SET flag = 1;
IF 1 / 0 > 0 THEN
    SET flag = 2;
END IF;
"""
    ast = parse(tokenize(code))
    steps = run(ast)
    step_dicts = [s.to_dict() for s in steps]

    if_step = next(s for s in step_dicts if s["nodeType"] == "IfStatement")
    assert if_step["error"]["condition"] == "DIVISION_BY_ZERO"
    assert if_step["branch"]["result"] is False  # couldn't evaluate -- treated as not-taken

    # flag was set to 1 by the handler, and the THEN body (which would
    # have set it to 2) never ran.
    assert step_dicts[-1]["variables"]["flag"]["value"] == 1


def test_duplicate_handler_for_the_same_condition_raises():
    code = """\
DECLARE CONTINUE HANDLER FOR NOT_FOUND SET x = 1;
DECLARE CONTINUE HANDLER FOR NOT_FOUND SET x = 2;
"""
    ast = parse(tokenize(code))
    with pytest.raises(InterpreterError, match="already declared"):
        run(ast, {"x": 0})


# -- CREATE FUNCTION / RETURN ------------------------------------------------

GET_DISCOUNTED_PRICE = """\
CREATE FUNCTION GetDiscountedPrice(price DECIMAL, quantity INT)
RETURNS DECIMAL
BEGIN
    DECLARE total DECIMAL;
    SET total = price * quantity;
    IF total > 1000 THEN
        RETURN total * 0.9;
    ELSE
        RETURN total;
    END IF;
END
"""


def test_function_takes_the_discount_branch_and_stops_right_after_return():
    """price * quantity = 2000, over the 1000 threshold -- the THEN
    branch's RETURN should be the trace's last step, full stop."""
    ast = parse(tokenize(GET_DISCOUNTED_PRICE))
    steps = run(ast, {"price": 200, "quantity": 10})
    step_dicts = [s.to_dict() for s in steps]

    print("\n--- discount-branch step trace ---")
    print(json.dumps(step_dicts, indent=2))

    assert [s["nodeType"] for s in step_dicts] == [
        "FunctionNode",  # the CREATE FUNCTION ... BEGIN line itself -- see test_function_entry_step_* below
        "DeclareStatement",
        "SetStatement",
        "IfStatement",
        "ReturnNode",
    ]
    assert step_dicts[3]["branch"] == {"condition": "total > 1000", "result": True, "path": "then"}

    last_step = step_dicts[-1]
    assert last_step["nodeType"] == "ReturnNode"
    assert last_step["statementText"] == "RETURN total * 0.9;"
    assert last_step["returnValue"] == {"value": 1800.0, "type": "number"}

    # returnValue is absent everywhere except the RETURN step itself.
    for step in step_dicts[:-1]:
        assert "returnValue" not in step


def test_function_takes_the_plain_total_branch_and_stops_right_after_return():
    """price * quantity = 200, under the threshold -- the ELSE branch's
    RETURN should be the trace's last step; the THEN branch's RETURN
    (and the rest of the procedure, if there were any) never runs."""
    ast = parse(tokenize(GET_DISCOUNTED_PRICE))
    steps = run(ast, {"price": 20, "quantity": 10})
    step_dicts = [s.to_dict() for s in steps]

    assert [s["nodeType"] for s in step_dicts] == [
        "FunctionNode",
        "DeclareStatement",
        "SetStatement",
        "IfStatement",
        "ReturnNode",
    ]
    assert step_dicts[3]["branch"] == {"condition": "total > 1000", "result": False, "path": "else"}

    last_step = step_dicts[-1]
    assert last_step["statementText"] == "RETURN total;"
    assert last_step["returnValue"] == {"value": 200, "type": "number"}


def test_return_stops_execution_of_later_statements_in_the_same_block():
    # A trailing statement after the IF/ELSE must never run once RETURN
    # inside one of its branches has already fired.
    code = """\
CREATE FUNCTION F(x NUMBER) RETURNS NUMBER
BEGIN
    DECLARE marker NUMBER DEFAULT 0;
    IF x > 0 THEN
        RETURN x;
    ELSE
        RETURN 0;
    END IF;
    SET marker = 999;
END
"""
    ast = parse(tokenize(code))
    steps = run(ast, {"x": 5})
    step_dicts = [s.to_dict() for s in steps]

    assert step_dicts[-1]["nodeType"] == "ReturnNode"
    assert not any(s["nodeType"] == "SetStatement" and "marker = 999" in s["statementText"] for s in step_dicts)
    # marker itself was never touched past its DECLARE default.
    assert step_dicts[-1]["variables"]["marker"]["value"] == 0


def test_return_inside_a_nested_while_unwinds_the_whole_function():
    code = """\
CREATE FUNCTION FindFirst(limit NUMBER) RETURNS NUMBER
BEGIN
    DECLARE i NUMBER DEFAULT 0;
    WHILE i < limit DO
        IF i = 2 THEN
            RETURN i;
        END IF;
        SET i = i + 1;
    END WHILE;
    RETURN -1;
END
"""
    ast = parse(tokenize(code))
    steps = run(ast, {"limit": 10})
    step_dicts = [s.to_dict() for s in steps]

    assert step_dicts[-1]["nodeType"] == "ReturnNode"
    assert step_dicts[-1]["returnValue"] == {"value": 2, "type": "number"}
    # The WHILE loop never got anywhere near its full 10 iterations, and
    # the trailing `RETURN -1;` never ran either -- only ever one
    # RETURN step in the whole trace.
    assert len([s for s in step_dicts if s["nodeType"] == "WhileStatement"]) == 3  # i=0,1,2 checks
    assert len([s for s in step_dicts if s["nodeType"] == "ReturnNode"]) == 1


def test_function_that_falls_through_without_returning_raises_a_clear_error():
    # No ELSE branch: when the condition is false, nothing executes and
    # the function body simply ends -- this must be a clear
    # InterpreterError, never a silent None return.
    code = """\
CREATE FUNCTION MaybeReturn(x NUMBER) RETURNS NUMBER
BEGIN
    IF x > 0 THEN
        RETURN x;
    END IF;
END
"""
    ast = parse(tokenize(code))

    with pytest.raises(InterpreterError, match="MaybeReturn.*without executing a RETURN"):
        run(ast, {"x": -5})

    # The THEN branch, when it IS taken, still returns normally.
    steps = run(ast, {"x": 5})
    assert steps[-1].to_dict()["returnValue"] == {"value": 5, "type": "number"}


def test_a_procedure_is_never_held_to_the_must_return_rule():
    # Procedures (bare statement bodies, no CREATE wrapper) have no
    # RETURN concept and must never raise for "not returning".
    ast = parse(tokenize("DECLARE x NUMBER DEFAULT 1;"))
    steps = run(ast, {})
    assert steps[-1].to_dict()["nodeType"] == "DeclareStatement"


def test_existing_procedure_samples_still_run_unaffected():
    # Explicit regression check: CalculateDiscount and SumUntilLimit
    # (two of the app's own sample procedures) must produce exactly the
    # trace they always did -- CREATE FUNCTION support must not have
    # touched the bare-statement-body path at all.
    discount_code = """\
DECLARE total NUMBER DEFAULT 0;
DECLARE discount NUMBER DEFAULT 0;
SET total = price * quantity;
IF total > 100 THEN
    SET discount = total * 0.1;
ELSE
    SET discount = total * 0.05;
END IF;
SET total = total - discount;
"""
    ast = parse(tokenize(discount_code))
    steps = run(ast, {"price": 20, "quantity": 6})
    assert len(steps) == 6
    assert steps[-1].to_dict()["variables"]["total"]["value"] == 108.0

    sum_code = "DECLARE total NUMBER DEFAULT 0;\nDECLARE counter NUMBER DEFAULT 1;\nWHILE total < 15 DO\n    SET total = total + counter;\n    SET counter = counter + 1;\nEND WHILE;\n"
    ast2 = parse(tokenize(sum_code))
    steps2 = run(ast2, {})
    assert steps2[-1].to_dict()["variables"]["total"]["value"] == 15


# -- CREATE PROCEDURE ---------------------------------------------------

APPLY_DISCOUNT_PROCEDURE = """\
CREATE PROCEDURE ApplyDiscount(IN price NUMBER, IN quantity NUMBER, OUT total NUMBER)
BEGIN
    SET total = price * quantity;
    IF total > 100 THEN
        SET total = total * 0.9;
    END IF;
END
"""


def test_create_procedure_wrapper_parses_and_runs_with_params_seeded():
    """Case 1 from the task: a procedure written with the full
    CREATE PROCEDURE (...) BEGIN...END wrapper -- confirm it parses
    and runs correctly, params seeded properly."""
    ast = parse(tokenize(APPLY_DISCOUNT_PROCEDURE))
    assert ast["type"] == "ProcedureNode"

    steps = run(ast, {"price": 20, "quantity": 6})  # IN params supplied by the caller
    step_dicts = [s.to_dict() for s in steps]

    print("\n--- CREATE PROCEDURE wrapper step trace ---")
    print(json.dumps(step_dicts, indent=2))

    # total = 20 * 6 = 120 (> 100), so it gets the 0.9 discount applied.
    final_total = step_dicts[-1]["variables"]["total"]
    assert final_total["value"] == pytest.approx(108.0)


def test_create_procedure_out_param_is_flagged_and_visible_in_final_step():
    ast = parse(tokenize(APPLY_DISCOUNT_PROCEDURE))
    steps = run(ast, {"price": 20, "quantity": 6})
    step_dicts = [s.to_dict() for s in steps]

    # `total` is OUT -- flagged isOutput on every step, including the
    # very first one (now the ProcedureNode's own entry step, recorded
    # before any body statement runs -- see test_procedure_entry_step_*
    # below -- so `total` is still None there, just already flagged).
    # Its real computed value is visible in the last step.
    assert step_dicts[0]["nodeType"] == "ProcedureNode"
    assert step_dicts[0]["variables"]["total"] == {"value": None, "type": "null", "changed": False, "isOutput": True}
    assert step_dicts[-1]["variables"]["total"]["isOutput"] is True
    assert step_dicts[-1]["variables"]["total"]["value"] == pytest.approx(108.0)

    # IN params are never flagged as outputs.
    assert step_dicts[0]["variables"]["price"]["isOutput"] is False
    assert step_dicts[0]["variables"]["quantity"]["isOutput"] is False


def test_create_procedure_in_param_not_supplied_raises_not_declared():
    ast = parse(tokenize(APPLY_DISCOUNT_PROCEDURE))
    with pytest.raises(InterpreterError, match="not declared"):
        run(ast, {"price": 20})  # quantity missing


def test_create_procedure_inout_param_is_seeded_and_flagged_as_output():
    code = """\
CREATE PROCEDURE Increment(INOUT counter NUMBER)
BEGIN
    SET counter = counter + 1;
END
"""
    ast = parse(tokenize(code))
    steps = run(ast, {"counter": 5})
    step_dicts = [s.to_dict() for s in steps]

    assert step_dicts[-1]["variables"]["counter"] == {
        "value": 6,
        "type": "number",
        "changed": True,
        "isOutput": True,
    }


def test_create_procedure_out_param_stays_none_if_never_assigned():
    code = "CREATE PROCEDURE Noop(OUT result NUMBER) BEGIN DECLARE x NUMBER DEFAULT 1; END"
    ast = parse(tokenize(code))
    steps = run(ast, {})
    final_vars = steps[-1].to_dict()["variables"]
    assert final_vars["result"] == {"value": None, "type": "null", "changed": False, "isOutput": True}


def test_bare_procedure_body_is_never_flagged_as_having_outputs():
    # No params key at all -- isOutput must be False for everything.
    ast = parse(tokenize("DECLARE x NUMBER DEFAULT 1;\nSET x = 2;\n"))
    steps = run(ast, {})
    for step in steps:
        for entry in step.to_dict()["variables"].values():
            assert entry["isOutput"] is False


# Case 2 from the task -- an EXISTING bare-statement-list sample,
# completely unchanged, run through the exact same interpreter.run()
# path as everything above. This is the critical regression check.
def test_existing_bare_sample_runs_identically_after_create_procedure_support():
    ast = parse(tokenize(CALCULATE_DISCOUNT))
    steps = run(ast, {"price": 20, "quantity": 6})
    step_dicts = [s.to_dict() for s in steps]

    assert len(step_dicts) == 6
    assert step_dicts[-1]["variables"]["total"]["value"] == 108.0
    # Every variable is a plain local/param -- never an output.
    assert all(entry["isOutput"] is False for entry in step_dicts[-1]["variables"].values())


# -- entry step (CREATE FUNCTION/PROCEDURE line itself) ---------------------
#
# Both wrapped forms get one extra DebugStep, first, for the definition
# line itself -- otherwise it would never appear in the trace at all,
# and step 1 would jump straight past it to whatever the first body
# statement happens to be.


def test_function_entry_step_is_first_and_reflects_the_create_function_line():
    ast = parse(tokenize(GET_DISCOUNTED_PRICE))
    steps = run(ast, {"price": 200, "quantity": 10})
    entry = steps[0].to_dict()

    assert entry["nodeType"] == "FunctionNode"
    assert entry["line"] == 1  # the CREATE FUNCTION line, not the first body statement
    assert entry["statementText"] == "CREATE FUNCTION GetDiscountedPrice(price DECIMAL, quantity INT) RETURNS DECIMAL"

    # Params supplied by the caller are already visible at entry; `total`
    # isn't -- its DECLARE hasn't run yet, so it doesn't exist in scope
    # until step 2.
    assert entry["variables"] == {
        "price": {"value": 200, "type": "number", "changed": False, "isOutput": False},
        "quantity": {"value": 10, "type": "number", "changed": False, "isOutput": False},
    }

    # Step 2 is the function's actual first body statement.
    assert steps[1].to_dict()["nodeType"] == "DeclareStatement"


def test_function_entry_step_variables_are_empty_with_no_external_params():
    code = "CREATE FUNCTION Answer() RETURNS NUMBER BEGIN RETURN 42; END"
    ast = parse(tokenize(code))
    steps = run(ast, {})
    entry = steps[0].to_dict()
    assert entry["nodeType"] == "FunctionNode"
    assert entry["variables"] == {}  # nothing in scope yet -- no params, no DECLARE has run


def test_procedure_entry_step_is_first_and_reflects_the_create_procedure_line():
    ast = parse(tokenize(APPLY_DISCOUNT_PROCEDURE))
    steps = run(ast, {"price": 20, "quantity": 6})
    entry = steps[0].to_dict()

    assert entry["nodeType"] == "ProcedureNode"
    assert entry["line"] == 1
    assert entry["statementText"] == "CREATE PROCEDURE ApplyDiscount(IN price NUMBER, IN quantity NUMBER, OUT total NUMBER)"

    # The OUT param is already seeded (to None) and already flagged at
    # entry, before the body's first SET has run.
    assert entry["variables"] == {
        "price": {"value": 20, "type": "number", "changed": False, "isOutput": False},
        "quantity": {"value": 6, "type": "number", "changed": False, "isOutput": False},
        "total": {"value": None, "type": "null", "changed": False, "isOutput": True},
    }

    assert steps[1].to_dict()["nodeType"] == "SetStatement"


def test_bare_procedure_never_gets_an_entry_step():
    # The critical regression check for this specific feature: the
    # bare/legacy form has no CREATE line to represent, so it must
    # never gain one -- step 1 is exactly what it always was.
    ast = parse(tokenize(CALCULATE_DISCOUNT))
    steps = run(ast, {"price": 20, "quantity": 6})
    assert steps[0].to_dict()["nodeType"] == "DeclareStatement"
    assert all(s.to_dict()["nodeType"] not in ("Procedure", "ProcedureNode", "FunctionNode") for s in steps)
