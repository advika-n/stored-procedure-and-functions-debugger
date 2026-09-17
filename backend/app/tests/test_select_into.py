"""Tests for `SELECT col1, col2, ... INTO var1, var2, ... FROM table
WHERE condition;` -- a single-row lookup statement, distinct from both
the cursor mechanism (DECLARE CURSOR/OPEN/FETCH/CLOSE, unchanged by
this) and the standalone-SELECT SqlStatement passthrough (a whole
result set as one DebugStep, nothing assigned to a variable). See
app.parser's and app.interpreter's own "SELECT ... INTO" module
docstring sections for the full design this exercises.

Every test here builds its AST via the real tokenizer -> parser
pipeline (never a hand-built dict), matching this project's existing
testing convention (see test_sql_passthrough_statement.py /
test_case_statement.py). Interpreter tests run the real
`Interpreter.run()` against a private `:memory:` connection (same
pattern test_interpreter.py's own cursor/FETCH tests already use via
`_make_products_db`), since these statements only mean anything against
a real SQLite connection.

Note: `found`/`notfound` are reserved KEYWORDs in this grammar (the
`cur_name%FOUND`/`cur_name%NOTFOUND` cursor-attribute suffix -- see
app.tokenizer), so no variable/parameter here is ever literally named
`found` -- `matched`/`was_found` stand in for it below.
"""

from __future__ import annotations

import sqlite3

import pytest
from fastapi.testclient import TestClient

from app.interpreter import InterpreterError, run
from app.main import app
from app.parser import ParserError, parse
from app.tokenizer import tokenize

client = TestClient(app)


def _steps_as_dicts(steps):
    return [s.to_dict() for s in steps]


def _make_products_db() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE products (name TEXT, price NUMBER)")
    conn.executemany(
        "INSERT INTO products (name, price) VALUES (?, ?)",
        [("Widget", 10), ("Gadget", 25), ("Gizmo", 15)],
    )
    conn.commit()
    return conn


def _run(code: str, conn: sqlite3.Connection, params: dict | None = None):
    return run(parse(tokenize(code)), params or {}, db_connection=conn)


# -- parser -------------------------------------------------------------------


def test_select_into_parses_as_its_own_node_type():
    ast = parse(tokenize("SELECT name INTO item_name FROM products WHERE name = 'Widget';"))
    node = ast["body"][0]
    assert node["type"] == "SelectIntoStatement"
    assert node["targets"] == ["item_name"]


def test_select_into_with_multiple_columns_and_targets():
    ast = parse(
        tokenize(
            "SELECT name, price INTO item_name, item_price FROM products WHERE name = 'Widget';"
        )
    )
    node = ast["body"][0]
    assert node["targets"] == ["item_name", "item_price"]
    assert node["selectClause"] == "name, price"


def test_select_into_query_field_has_into_clause_stripped():
    # `query` is handed straight to SQLite, which has no `SELECT ...
    # INTO ...` syntax in this position -- confirm the parser actually
    # strips it rather than leaving it in and relying on SQLite to
    # reject it.
    ast = parse(tokenize("SELECT name INTO x FROM products WHERE price > 10;"))
    node = ast["body"][0]
    assert "INTO" not in node["query"].upper()
    assert node["query"] == "SELECT name FROM products WHERE price > 10"


def test_bare_select_without_into_still_parses_as_sql_statement():
    # The dispatch decision (`_select_has_into`) must not misroute a
    # perfectly ordinary standalone SELECT that happens to have no INTO
    # at all -- it stays a SqlStatement passthrough exactly as before
    # this fix.
    ast = parse(tokenize("SELECT name FROM products WHERE price > 10;"))
    node = ast["body"][0]
    assert node["type"] == "SqlStatement"
    assert node["keyword"] == "SELECT"


def test_select_into_statement_valid_anywhere_a_statement_is():
    # Same "parseable inside IF/WHILE/CASE/LOOP bodies, a handler's
    # action, ..." convention every other statement type in this
    # grammar already has.
    ast = parse(
        tokenize(
            """\
IF 1 = 1 THEN
    SELECT name INTO x FROM products WHERE price > 10;
END IF;
"""
        )
    )
    then_body = ast["body"][0]["then_body"]
    assert then_body[0]["type"] == "SelectIntoStatement"


def test_missing_column_list_before_into_raises_parser_error():
    with pytest.raises(ParserError):
        parse(tokenize("SELECT INTO x FROM products;"))


def test_missing_target_variable_after_into_raises_parser_error():
    with pytest.raises(ParserError):
        parse(tokenize("SELECT name INTO FROM products;"))


def test_missing_from_clause_after_into_var_list_raises_parser_error():
    with pytest.raises(ParserError):
        parse(tokenize("SELECT name INTO x;"))


# -- interpreter: found / not-found / multi-row --------------------------------


def test_found_exactly_one_row_assigns_columns_positionally():
    conn = _make_products_db()
    code = """\
DECLARE item_name STRING DEFAULT '';
DECLARE item_price NUMBER DEFAULT 0;
SELECT name, price INTO item_name, item_price FROM products WHERE name = 'Widget';
"""
    steps = _steps_as_dicts(_run(code, conn))
    final_vars = steps[-1]["variables"]
    assert final_vars["item_name"]["value"] == "Widget"
    assert final_vars["item_price"]["value"] == 10
    conn.close()


def test_found_step_carries_the_new_sql_shape_with_into_field():
    conn = _make_products_db()
    code = "DECLARE item_name STRING DEFAULT ''; SELECT name INTO item_name FROM products WHERE name = 'Gadget';"
    steps = _steps_as_dicts(_run(code, conn))
    select_step = steps[-1]
    assert select_step["nodeType"] == "SelectIntoStatement"
    sql = select_step["sql"]
    assert sql["keyword"] == "SELECT"
    assert sql["kind"] == "rows"
    assert sql["into"] == ["item_name"]
    assert sql["columns"] == ["name"]
    assert sql["rows"] == [["Gadget"]]
    assert sql["rowCount"] == 1
    assert "error" not in select_step
    conn.close()


def test_zero_rows_triggers_not_found_and_a_registered_handler_catches_it():
    conn = _make_products_db()
    code = """\
DECLARE item_name STRING DEFAULT 'unset';
DECLARE not_found_flag NUMBER DEFAULT 0;
DECLARE CONTINUE HANDLER FOR NOT_FOUND SET not_found_flag = 1;
SELECT name INTO item_name FROM products WHERE name = 'Nonexistent';
"""
    steps = _steps_as_dicts(_run(code, conn))  # must not raise
    select_step = next(s for s in steps if s["nodeType"] == "SelectIntoStatement")
    assert select_step["error"] == {
        "condition": "NOT_FOUND",
        "message": "SELECT INTO matched no row",
        "handler": "NOT_FOUND handler",
    }
    # The target variable is untouched -- kept its prior value, exactly
    # like a cursor FETCH running past the end leaves its targets alone.
    assert select_step["sql"]["rows"] == []
    assert select_step["sql"]["rowCount"] == 0

    # Handler's action (SET not_found_flag = 1) runs as its own
    # subsequent step, same sequencing as an exhausted cursor FETCH's
    # own handler already gets.
    triggering_index = steps.index(select_step)
    handler_step = steps[triggering_index + 1]
    assert handler_step["nodeType"] == "SetStatement"
    assert handler_step["variables"]["not_found_flag"]["value"] == 1

    assert steps[-1]["variables"]["item_name"]["value"] == "unset"
    conn.close()


def test_zero_rows_without_a_handler_is_unhandled_but_still_non_fatal():
    # NOT_FOUND is unconditionally non-fatal whether or not a handler is
    # registered -- same treatment an exhausted cursor FETCH already
    # gets (see app.interpreter's "Exception handlers" section). Must
    # NOT raise.
    conn = _make_products_db()
    code = "DECLARE x STRING DEFAULT ''; SELECT name INTO x FROM products WHERE name = 'Nonexistent';"
    steps = _steps_as_dicts(_run(code, conn))  # must not raise
    select_step = steps[-1]
    assert select_step["error"] == {
        "condition": "NOT_FOUND",
        "message": "SELECT INTO matched no row",
        "handler": "unhandled",
    }
    conn.close()


def test_more_than_one_row_raises_a_distinct_immediately_fatal_error():
    # A genuinely different problem from "no data" -- must NOT be routed
    # through NOT_FOUND or any handler; always a hard error.
    conn = _make_products_db()
    code = "DECLARE x STRING DEFAULT ''; SELECT name INTO x FROM products WHERE price > 5;"
    with pytest.raises(InterpreterError) as excinfo:
        _run(code, conn)
    message = str(excinfo.value)
    assert "exactly one row" in message.lower()
    assert "3" in message  # all three seeded products have price > 5
    conn.close()


def test_more_than_one_row_is_not_caught_by_a_not_found_handler():
    # Confirm the multi-row case really does bypass the handler
    # mechanism entirely -- even with a NOT_FOUND handler registered, it
    # still raises (NOT_FOUND is simply the wrong condition for this).
    conn = _make_products_db()
    code = """\
DECLARE x STRING DEFAULT '';
DECLARE flag NUMBER DEFAULT 0;
DECLARE CONTINUE HANDLER FOR NOT_FOUND SET flag = 1;
SELECT name INTO x FROM products WHERE price > 5;
"""
    with pytest.raises(InterpreterError):
        _run(code, conn)
    conn.close()


def test_column_count_mismatch_raises_a_clear_error():
    conn = _make_products_db()
    code = "DECLARE x STRING DEFAULT ''; DECLARE y NUMBER DEFAULT 0; SELECT name INTO x, y FROM products WHERE name = 'Widget';"
    with pytest.raises(InterpreterError) as excinfo:
        _run(code, conn)
    message = str(excinfo.value).lower()
    assert "1 column" in message or "returns 1 column" in message
    conn.close()


def test_undeclared_target_variable_raises_a_clear_error():
    conn = _make_products_db()
    code = "SELECT name INTO never_declared FROM products WHERE name = 'Widget';"
    with pytest.raises(InterpreterError) as excinfo:
        _run(code, conn)
    assert "not declared" in str(excinfo.value).lower()
    conn.close()


def test_sql_error_from_a_bad_select_into_query_is_a_clean_interpreter_error():
    conn = _make_products_db()
    code = "DECLARE x STRING DEFAULT ''; SELECT name INTO x FROM nonexistent_table WHERE name = 'Widget';"
    with pytest.raises(InterpreterError) as excinfo:
        _run(code, conn)
    message = str(excinfo.value)
    assert "Traceback" not in message
    assert "no such table" in message.lower()
    conn.close()


# -- distinct from the cursor mechanism ----------------------------------------


def test_select_into_and_a_cursor_coexist_in_the_same_run():
    # Both mechanisms read the same real database, independently of each
    # other -- a SELECT INTO lookup does not disturb a separately
    # declared/opened cursor's own state.
    conn = _make_products_db()
    code = """\
DECLARE total NUMBER DEFAULT 0;
DECLARE item_name STRING DEFAULT '';
DECLARE item_price NUMBER DEFAULT 0;
DECLARE looked_up_price NUMBER DEFAULT 0;
DECLARE cur CURSOR FOR SELECT name, price FROM products;
SELECT price INTO looked_up_price FROM products WHERE name = 'Gizmo';
OPEN cur;
WHILE cur%FOUND DO
    FETCH cur INTO item_name, item_price;
    SET total = total + item_price;
END WHILE;
CLOSE cur;
"""
    steps = _steps_as_dicts(_run(code, conn))
    final_vars = steps[-1]["variables"]
    assert final_vars["looked_up_price"]["value"] == 15  # Gizmo
    assert final_vars["total"]["value"] == 35 + 15  # Widget+Gadget+Gizmo, unaffected


# -- end-to-end: the real /debug endpoint --------------------------------------


def test_debug_endpoint_select_into_found_case_via_a_created_table():
    # DROP isn't part of the procedural grammar (only CREATE TABLE/
    # INSERT/UPDATE/DELETE/SELECT are -- see app.parser's "SQL
    # passthrough statements" section), so this relies on `CREATE TABLE
    # IF NOT EXISTS` + a leading DELETE for idempotency instead of a
    # trailing DROP, same convention the InventoryValueReport/
    # ManageInventory samples already use.
    code = """\
CREATE PROCEDURE LookupOne()
BEGIN
    DECLARE qty NUMBER DEFAULT 0;
    CREATE TABLE IF NOT EXISTS select_into_probe (id NUMBER, qty NUMBER);
    DELETE FROM select_into_probe;
    INSERT INTO select_into_probe VALUES (1, 7);
    SELECT qty INTO qty FROM select_into_probe WHERE id = 1;
END
"""
    response = client.post("/debug", json={"code": code, "params": {}})
    assert response.status_code == 200
    body = response.json()
    steps = body["steps"]
    select_step = next(s for s in steps if s["nodeType"] == "SelectIntoStatement")
    assert select_step["sql"]["rows"] == [[7]]
    assert steps[-1]["variables"]["qty"]["value"] == 7


def test_debug_endpoint_select_into_not_found_case_via_a_created_table():
    # `found`/`notfound` are reserved KEYWORDs (see module docstring
    # above), so the OUT param tracking this is named `was_found`.
    code = """\
CREATE PROCEDURE LookupMissing(OUT was_found NUMBER)
BEGIN
    DECLARE qty NUMBER DEFAULT -1;
    CREATE TABLE IF NOT EXISTS select_into_probe2 (id NUMBER, qty NUMBER);
    DELETE FROM select_into_probe2;
    DECLARE CONTINUE HANDLER FOR NOT_FOUND SET was_found = 0;
    SET was_found = 1;
    SELECT qty INTO qty FROM select_into_probe2 WHERE id = 999;
END
"""
    response = client.post("/debug", json={"code": code, "params": {}})
    assert response.status_code == 200
    body = response.json()
    steps = body["steps"]
    select_step = next(s for s in steps if s["nodeType"] == "SelectIntoStatement")
    assert select_step["error"]["condition"] == "NOT_FOUND"
    assert steps[-1]["variables"]["was_found"]["value"] == 0
    assert steps[-1]["variables"]["qty"]["value"] == -1  # untouched
