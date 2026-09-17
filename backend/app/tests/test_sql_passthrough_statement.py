"""Tests for SQL passthrough statements: CREATE TABLE / INSERT / UPDATE
/ DELETE / SELECT valid inside a procedure body, executed for real
against app.user_db's persistent database (raw text, straight to
SQLite -- no SQL parsing of this project's own). See app.parser's "SQL
passthrough statements" and app.interpreter's own section of the same
name for the full design this exercises, and app.parser's/app.
interpreter's module docstrings for why this REPLACED an earlier
phase's simulated CreateTableStatement/InsertStatement/UpdateStatement/
DeleteStatement feature rather than sitting alongside it.

Parser tests build their AST via the real tokenizer -> parser pipeline
(never a hand-built dict), matching this project's existing testing
convention. Interpreter tests run the real `Interpreter.run()` against
`app.user_db.get_connection()` -- the exact connection app.main's
`/debug` handler uses -- since these statements only mean anything
against a real SQLite connection now, unlike the old simulation. A few
end-to-end tests go through the real `/debug` TestClient endpoint,
which is what actually proves the whole pipeline (parse -> interpret ->
clean error surfacing) end to end.

`_isolated_user_db` (autouse, see conftest.py) means every test here
gets its own throwaway on-disk database -- never the real
backend/data/user_data.db.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app import user_db
from app.interpreter import InterpreterError, run
from app.main import app
from app.parser import ParserError, parse
from app.tokenizer import tokenize

client = TestClient(app)


def _steps_as_dicts(steps):
    return [s.to_dict() for s in steps]


def _run(code: str, params: dict | None = None):
    conn = user_db.get_connection()
    try:
        return run(parse(tokenize(code)), params or {}, db_connection=conn)
    finally:
        conn.close()


# -- parser: all five keywords parse to one shared node type ------------------


@pytest.mark.parametrize(
    "code,keyword",
    [
        ("CREATE TABLE t (id NUMBER, name TEXT);", "CREATE"),
        ("INSERT INTO t VALUES (1, 'Widget');", "INSERT"),
        ("UPDATE t SET name = 'Gadget' WHERE id = 1;", "UPDATE"),
        ("DELETE FROM t WHERE id = 1;", "DELETE"),
        ("SELECT * FROM t;", "SELECT"),
    ],
)
def test_each_keyword_parses_to_a_shared_sql_statement_node(code, keyword):
    ast = parse(tokenize(code))
    stmt = ast["body"][0]
    assert stmt["type"] == "SqlStatement"
    assert stmt["keyword"] == keyword
    # `sql` is the ENTIRE statement text, including the leading keyword
    # itself (unlike a cursor's CursorDeclNode.query, which starts only
    # after CURSOR FOR) -- verified directly, not assumed.
    assert stmt["sql"].upper().startswith(keyword)
    assert not stmt["sql"].endswith(";")  # the trailing ';' is consumed, not captured


def test_sql_statement_valid_anywhere_a_statement_is():
    code = """\
CREATE PROCEDURE Demo()
BEGIN
    DECLARE flag NUMBER DEFAULT 1;
    IF flag = 1 THEN
        CREATE TABLE t (id NUMBER);
        INSERT INTO t VALUES (1);
    END IF;
    WHILE flag = 1 DO
        SET flag = 0;
    END WHILE;
END
"""
    # IF/WHILE bodies accepting SqlStatement -- a parse-only check (no
    # ParserError), matching every other statement type's own "valid
    # inside IF/WHILE" coverage elsewhere in this test suite.
    ast = parse(tokenize(code))
    assert ast["type"] == "ProcedureNode"


def test_bare_leading_create_table_is_a_statement_not_a_definition():
    ast = parse(tokenize("CREATE TABLE t (x NUMBER);"))
    assert ast["type"] == "Procedure"
    assert ast["body"][0]["type"] == "SqlStatement"


def test_unrecognized_statement_error_message_mentions_select():
    with pytest.raises(ParserError) as excinfo:
        parse(tokenize("FROBNICATE t;"))
    assert "SELECT" in str(excinfo.value)


# -- interpreter: real execution against app.user_db --------------------------


def test_create_table_and_insert_produce_a_write_sql_step_with_snapshot():
    steps = _steps_as_dicts(
        _run(
            """\
CREATE TABLE t (id NUMBER PRIMARY KEY, name TEXT);
INSERT INTO t VALUES (1, 'Widget');
"""
        )
    )
    create_step, insert_step = steps
    assert create_step["nodeType"] == "SqlStatement"
    assert create_step["sql"]["keyword"] == "CREATE"
    assert create_step["sql"]["kind"] == "write"
    assert create_step["sql"]["tableName"] == "t"
    assert create_step["sql"]["snapshot"] == {"columns": ["id", "name"], "rows": []}

    assert insert_step["sql"]["keyword"] == "INSERT"
    assert insert_step["sql"]["rowsAffected"] == 1
    assert insert_step["sql"]["snapshot"] == {"columns": ["id", "name"], "rows": [[1, "Widget"]]}


def test_update_and_delete_report_rows_affected_and_snapshot():
    steps = _steps_as_dicts(
        _run(
            """\
CREATE TABLE t (id NUMBER, qty NUMBER);
INSERT INTO t VALUES (1, 5);
INSERT INTO t VALUES (2, 5);
UPDATE t SET qty = 10 WHERE id = 1;
DELETE FROM t WHERE id = 2;
"""
        )
    )
    update_step, delete_step = steps[3], steps[4]

    assert update_step["sql"]["keyword"] == "UPDATE"
    assert update_step["sql"]["rowsAffected"] == 1
    # snapshot is the table's FULL current state, not a diff -- both
    # rows appear, not just the one the UPDATE actually touched.
    assert update_step["sql"]["snapshot"]["rows"] == [[1, 10], [2, 5]]

    assert delete_step["sql"]["keyword"] == "DELETE"
    assert delete_step["sql"]["rowsAffected"] == 1
    assert delete_step["sql"]["snapshot"]["rows"] == [[1, 10]]


def test_standalone_select_produces_a_rows_sql_step():
    steps = _steps_as_dicts(
        _run(
            """\
CREATE TABLE t (id NUMBER, name TEXT);
INSERT INTO t VALUES (1, 'Widget');
SELECT id, name FROM t;
"""
        )
    )
    select_step = steps[-1]
    assert select_step["nodeType"] == "SqlStatement"
    assert select_step["sql"]["keyword"] == "SELECT"
    assert select_step["sql"]["kind"] == "rows"
    assert select_step["sql"]["columns"] == ["id", "name"]
    assert select_step["sql"]["rows"] == [[1, "Widget"]]
    assert select_step["sql"]["rowCount"] == 1
    # A row-producing SELECT step has no rowsAffected/tableName/snapshot
    # at all -- kind == "rows" and kind == "write" are mutually exclusive
    # shapes, not a superset/subset.
    assert "rowsAffected" not in select_step["sql"]
    assert "tableName" not in select_step["sql"]


def test_raw_insert_is_immediately_visible_to_a_cursor_select_same_run():
    # The whole point of retiring the old simulation: a table CREATEd/
    # INSERTed via SqlStatement and a cursor's embedded SELECT now share
    # ONE real database (app.user_db), not two disconnected worlds. See
    # app.interpreter's "Cursors" and "SQL passthrough statements"
    # module docstring sections.
    steps = _steps_as_dicts(
        _run(
            """\
DECLARE total NUMBER DEFAULT 0;
DECLARE item_name STRING DEFAULT '';
DECLARE item_price NUMBER DEFAULT 0;
CREATE TABLE inv (id NUMBER, item TEXT, price NUMBER);
INSERT INTO inv VALUES (1, 'Widget', 10);
INSERT INTO inv VALUES (2, 'Gadget', 25);
DECLARE cur CURSOR FOR SELECT item, price FROM inv;
OPEN cur;
WHILE cur%FOUND DO
    FETCH cur INTO item_name, item_price;
    SET total = total + item_price;
END WHILE;
CLOSE cur;
"""
        )
    )
    assert steps[-1]["variables"]["total"]["value"] == 35


def test_sql_error_from_a_bad_statement_is_a_clean_interpreter_error():
    with pytest.raises(InterpreterError) as excinfo:
        _run("INSERT INTO nonexistent_table VALUES (1);")
    message = str(excinfo.value)
    assert "Traceback" not in message
    assert "no such table" in message.lower()


def test_no_variable_interpolation_inside_sql_statements():
    # A genuine, documented capability loss vs. the retired simulated
    # feature (see app.parser's module docstring): a procedure-scope
    # variable's NAME appearing inside a passthrough statement means
    # whatever SQLite resolves it to (a column reference), never a
    # substitution of that variable's current value.
    with pytest.raises(InterpreterError) as excinfo:
        _run(
            """\
DECLARE price NUMBER DEFAULT 10;
CREATE TABLE t (id NUMBER);
INSERT INTO t VALUES (price);
"""
        )
    assert "no such column" in str(excinfo.value).lower()


def test_no_constraint_enforcement_written_in_this_interpreter_any_more():
    # The retired simulation enforced NOT NULL/PRIMARY KEY itself in
    # Python; this phase enforces nothing of its own -- whatever real
    # SQLite does with a given CREATE TABLE is authoritative. A
    # non-INTEGER PRIMARY KEY column does NOT reject NULL by itself in
    # real SQLite (a well-known SQLite quirk) -- verified directly here
    # so this documented behavior change doesn't silently bit-rot.
    steps = _steps_as_dicts(
        _run(
            """\
CREATE TABLE t (id NUMBER PRIMARY KEY);
INSERT INTO t VALUES (NULL);
"""
        )
    )
    assert steps[-1]["sql"]["rowsAffected"] == 1


def test_two_char_comparison_operator_now_round_trips_correctly():
    # This used to be a documented round-trip caveat (this tokenizer had
    # no single-token `<=`, so it reconstructed as two separate tokens
    # with a forced space, producing invalid SQL) -- fixed as a side
    # effect of extending the procedural comparison rule to accept
    # `>=`/`<=`/`<>` too (see app.tokenizer's module docstring for the
    # lexing-order fix, app.parser's "SQL passthrough statements" section
    # for why this now round-trips cleanly). `<=` inside a raw-passthrough
    # WHERE clause now reassembles correctly and DELETEs exactly the rows
    # SQLite itself would delete for `id <= 5`.
    steps = _run(
        """\
CREATE TABLE t (id NUMBER);
INSERT INTO t VALUES (3);
INSERT INTO t VALUES (7);
DELETE FROM t WHERE id <= 5;
SELECT id FROM t;
"""
    )
    final_select = steps[-1].to_dict()["sql"]
    assert final_select["rows"] == [[7]]  # only id=3 was <= 5 and got deleted


# -- end-to-end: the real /debug endpoint --------------------------------------


def test_debug_endpoint_runs_a_full_create_insert_update_select_procedure():
    code = """\
CREATE PROCEDURE Demo()
BEGIN
    CREATE TABLE t (id NUMBER, qty NUMBER);
    INSERT INTO t VALUES (1, 5);
    UPDATE t SET qty = 9 WHERE id = 1;
    SELECT qty FROM t;
END
"""
    response = client.post("/debug", json={"code": code, "params": {}})
    assert response.status_code == 200
    steps = response.json()["steps"]
    node_types = [s["nodeType"] for s in steps]
    # One entry step (ProcedureNode) + 4 SqlStatement steps.
    assert node_types.count("SqlStatement") == 4
    assert steps[-1]["sql"]["rows"] == [[9]]


def test_debug_endpoint_surfaces_a_sql_error_as_a_clean_400():
    code = "INSERT INTO no_such_table VALUES (1);"
    response = client.post("/debug", json={"code": code, "params": {}})
    assert response.status_code == 400
    detail = response.json()["detail"]
    assert detail["stage"] == "interpret"
    assert "no such table" in detail["message"].lower()
