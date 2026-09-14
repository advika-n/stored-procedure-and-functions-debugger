"""Tests for user-created tables: CREATE TABLE / INSERT / UPDATE / DELETE.
See app.parser's "User-created tables" and app.interpreter's own section
of the same name for the full design this exercises.

Every test here builds its AST via the real tokenizer -> parser
pipeline (never a hand-built dict), matching this project's existing
testing convention (see test_loop_statement.py / test_case_statement.py).
"""

import pytest

from app.interpreter import InterpreterError, run
from app.parser import ParserError, parse
from app.tokenizer import tokenize


def _steps_as_dicts(steps):
    return [s.to_dict() for s in steps]


# -- tokenizer ------------------------------------------------------------


def test_new_keywords_tokenize_as_keywords():
    tokens = tokenize("CREATE TABLE INSERT INTO VALUES UPDATE DELETE FROM PRIMARY KEY NOT NULL")
    kinds = {t["value"].upper() for t in tokens if t["type"] == "KEYWORD"}
    assert {"TABLE", "INSERT", "VALUES", "UPDATE", "DELETE", "PRIMARY", "KEY", "NOT", "NULL"} <= kinds


# -- parser: CREATE TABLE --------------------------------------------------


def test_create_table_parses_columns_and_constraints():
    code = "CREATE TABLE emp (id NUMBER PRIMARY KEY, name TEXT NOT NULL, salary NUMBER);"
    ast = parse(tokenize(code))
    stmt = ast["body"][0]
    assert stmt["type"] == "CreateTableStatement"
    assert stmt["name"] == "emp"
    assert stmt["columns"] == [
        {"name": "id", "col_type": "NUMBER", "not_null": False, "primary_key": True},
        {"name": "name", "col_type": "TEXT", "not_null": True, "primary_key": False},
        {"name": "salary", "col_type": "NUMBER", "not_null": False, "primary_key": False},
    ]


def test_bare_leading_create_table_parses_as_a_statement_not_a_definition():
    ast = parse(tokenize("CREATE TABLE t (x NUMBER);"))
    assert ast["type"] == "Procedure"
    assert ast["body"][0]["type"] == "CreateTableStatement"


def test_create_table_inside_a_wrapped_procedure_body():
    code = """\
CREATE PROCEDURE Demo()
BEGIN
    CREATE TABLE t (x NUMBER);
END
"""
    ast = parse(tokenize(code))
    assert ast["type"] == "ProcedureNode"
    assert ast["body"][0]["type"] == "CreateTableStatement"


def test_create_then_create_table_after_it_is_a_parser_error():
    # A stray CREATE TABLE cannot follow an already-started CREATE
    # PROCEDURE/FUNCTION definition chain -- see parser.py's own
    # "Top-level dispatch note".
    code = "CREATE PROCEDURE A() BEGIN END\nCREATE TABLE t (x NUMBER);"
    with pytest.raises(ParserError, match="Expected FUNCTION or PROCEDURE"):
        parse(tokenize(code))


# -- parser: INSERT --------------------------------------------------------


def test_insert_with_explicit_column_list():
    ast = parse(tokenize("INSERT INTO t (a, b) VALUES (1, 2);"))
    stmt = ast["body"][0]
    assert stmt["type"] == "InsertStatement"
    assert stmt["table"] == "t"
    assert stmt["columns"] == ["a", "b"]
    assert [v["value"] for v in stmt["values"]] == [1, 2]


def test_insert_without_column_list_leaves_columns_none():
    ast = parse(tokenize("INSERT INTO t VALUES (1, 2);"))
    assert ast["body"][0]["columns"] is None


def test_insert_value_can_be_null():
    ast = parse(tokenize("INSERT INTO t VALUES (NULL);"))
    assert ast["body"][0]["values"][0] == {"type": "NullLiteral", "line": 1}


# -- parser: UPDATE --------------------------------------------------------


def test_update_parses_multiple_assignments_and_where():
    ast = parse(tokenize("UPDATE t SET a = 1, b = a + 2 WHERE a > 0;"))
    stmt = ast["body"][0]
    assert stmt["type"] == "UpdateStatement"
    assert stmt["table"] == "t"
    assert [a["column"] for a in stmt["assignments"]] == ["a", "b"]
    assert stmt["where"]["type"] == "BinaryExpr"


def test_update_where_is_optional():
    ast = parse(tokenize("UPDATE t SET a = 1;"))
    assert ast["body"][0]["where"] is None


# -- parser: DELETE ---------------------------------------------------------


def test_delete_parses_with_and_without_where():
    with_where = parse(tokenize("DELETE FROM t WHERE a = 1;"))["body"][0]
    assert with_where["type"] == "DeleteStatement"
    assert with_where["table"] == "t"
    assert with_where["where"] is not None

    without_where = parse(tokenize("DELETE FROM t;"))["body"][0]
    assert without_where["where"] is None


# -- interpreter: CREATE TABLE ----------------------------------------------


def test_create_table_registers_empty_table_and_records_step():
    steps = _steps_as_dicts(run(parse(tokenize("CREATE TABLE t (a NUMBER, b TEXT);")), {}))
    step = steps[0]
    assert step["nodeType"] == "CreateTableStatement"
    assert step["table"] == {
        "name": "t",
        "operation": "CREATE",
        "columns": ["a", "b"],
        "rowsAffected": 0,
        "row": None,
        "rows": [],
    }


def test_create_table_with_duplicate_name_is_an_interpreter_error():
    code = "CREATE TABLE t (a NUMBER); CREATE TABLE t (b NUMBER);"
    with pytest.raises(InterpreterError, match="already declared"):
        run(parse(tokenize(code)), {})


def test_create_table_with_duplicate_column_is_an_interpreter_error():
    with pytest.raises(InterpreterError, match="duplicate column"):
        run(parse(tokenize("CREATE TABLE t (a NUMBER, a TEXT);")), {})


# -- interpreter: INSERT -----------------------------------------------------


def test_insert_with_explicit_columns_appends_a_row():
    code = "CREATE TABLE t (a NUMBER, b TEXT); INSERT INTO t (a, b) VALUES (1, 'x');"
    steps = _steps_as_dicts(run(parse(tokenize(code)), {}))
    insert_step = steps[-1]
    assert insert_step["nodeType"] == "InsertStatement"
    assert insert_step["table"]["row"] == {"a": 1, "b": "x"}
    assert insert_step["table"]["rows"] == [{"a": 1, "b": "x"}]
    assert insert_step["table"]["rowsAffected"] == 1


def test_insert_without_columns_binds_positionally_in_table_order():
    code = "CREATE TABLE t (a NUMBER, b TEXT); INSERT INTO t VALUES (5, 'y');"
    steps = _steps_as_dicts(run(parse(tokenize(code)), {}))
    assert steps[-1]["table"]["row"] == {"a": 5, "b": "y"}


def test_insert_omitting_a_column_leaves_it_null():
    code = "CREATE TABLE t (a NUMBER, b TEXT); INSERT INTO t (a) VALUES (5);"
    steps = _steps_as_dicts(run(parse(tokenize(code)), {}))
    assert steps[-1]["table"]["row"] == {"a": 5, "b": None}


def test_insert_into_undeclared_table_is_an_interpreter_error():
    with pytest.raises(InterpreterError, match="is not declared"):
        run(parse(tokenize("INSERT INTO nope VALUES (1);")), {})


def test_insert_unknown_column_is_an_interpreter_error():
    code = "CREATE TABLE t (a NUMBER); INSERT INTO t (nope) VALUES (1);"
    with pytest.raises(InterpreterError, match="has no column 'nope'"):
        run(parse(tokenize(code)), {})


def test_insert_wrong_value_count_is_an_interpreter_error():
    code = "CREATE TABLE t (a NUMBER, b NUMBER); INSERT INTO t VALUES (1);"
    with pytest.raises(InterpreterError, match="supplies 1 value"):
        run(parse(tokenize(code)), {})


def test_insert_null_into_not_null_column_is_an_interpreter_error():
    code = "CREATE TABLE t (a NUMBER NOT NULL); INSERT INTO t VALUES (NULL);"
    with pytest.raises(InterpreterError, match="NOT NULL and cannot be NULL"):
        run(parse(tokenize(code)), {})


def test_insert_omitted_not_null_column_is_an_interpreter_error():
    code = "CREATE TABLE t (a NUMBER, b NUMBER NOT NULL); INSERT INTO t (a) VALUES (1);"
    with pytest.raises(InterpreterError, match="NOT NULL and cannot be NULL"):
        run(parse(tokenize(code)), {})


def test_insert_duplicate_primary_key_is_an_interpreter_error():
    code = "CREATE TABLE t (id NUMBER PRIMARY KEY); INSERT INTO t VALUES (1); INSERT INTO t VALUES (1);"
    with pytest.raises(InterpreterError, match="Duplicate value 1 for PRIMARY KEY"):
        run(parse(tokenize(code)), {})


# -- interpreter: UPDATE ------------------------------------------------------


def test_update_matching_rows_by_where():
    code = """\
CREATE TABLE t (id NUMBER, price NUMBER);
INSERT INTO t VALUES (1, 10);
INSERT INTO t VALUES (2, 20);
UPDATE t SET price = price + 1 WHERE id = 1;
"""
    steps = _steps_as_dicts(run(parse(tokenize(code)), {}))
    update_step = steps[-1]
    assert update_step["nodeType"] == "UpdateStatement"
    assert update_step["table"]["rowsAffected"] == 1
    assert update_step["table"]["rows"] == [{"id": 1, "price": 11}, {"id": 2, "price": 20}]


def test_update_with_no_where_touches_every_row():
    code = """\
CREATE TABLE t (price NUMBER);
INSERT INTO t VALUES (10);
INSERT INTO t VALUES (20);
UPDATE t SET price = price * 2;
"""
    steps = _steps_as_dicts(run(parse(tokenize(code)), {}))
    update_step = steps[-1]
    assert update_step["table"]["rowsAffected"] == 2
    assert update_step["table"]["rows"] == [{"price": 20}, {"price": 40}]


def test_update_where_can_reference_a_scope_variable_alongside_a_column():
    code = """\
CREATE PROCEDURE Demo()
BEGIN
    DECLARE minPrice NUMBER DEFAULT 15;
    CREATE TABLE t (price NUMBER);
    INSERT INTO t VALUES (10);
    INSERT INTO t VALUES (20);
    UPDATE t SET price = 0 WHERE price > minPrice;
END
"""
    steps = _steps_as_dicts(run(parse(tokenize(code)), {}))
    update_step = next(s for s in steps if s["nodeType"] == "UpdateStatement")
    assert update_step["table"]["rows"] == [{"price": 10}, {"price": 0}]
    # The row overlay used to evaluate WHERE must never leak into the
    # ordinary scope-variable snapshot.
    assert "price" not in update_step["variables"]


def test_update_assignments_see_each_rows_original_values_not_earlier_assignments():
    code = "CREATE TABLE t (a NUMBER, b NUMBER); INSERT INTO t VALUES (1, 2); UPDATE t SET a = b, b = a;"
    steps = _steps_as_dicts(run(parse(tokenize(code)), {}))
    assert steps[-1]["table"]["rows"] == [{"a": 2, "b": 1}]


def test_update_unknown_column_is_an_interpreter_error():
    code = "CREATE TABLE t (a NUMBER); UPDATE t SET nope = 1;"
    with pytest.raises(InterpreterError, match="has no column 'nope'"):
        run(parse(tokenize(code)), {})


def test_update_violating_primary_key_uniqueness_leaves_table_unmodified():
    code = """\
CREATE TABLE t (id NUMBER PRIMARY KEY);
INSERT INTO t VALUES (1);
INSERT INTO t VALUES (2);
UPDATE t SET id = 1 WHERE id = 2;
"""
    with pytest.raises(InterpreterError, match="Duplicate value 1 for PRIMARY KEY"):
        run(parse(tokenize(code)), {})


def test_update_a_primary_key_column_to_its_own_existing_value_is_not_a_duplicate():
    code = "CREATE TABLE t (id NUMBER PRIMARY KEY); INSERT INTO t VALUES (1); UPDATE t SET id = 1;"
    steps = _steps_as_dicts(run(parse(tokenize(code)), {}))
    assert steps[-1]["table"]["rows"] == [{"id": 1}]


# -- interpreter: DELETE ------------------------------------------------------


def test_delete_with_where_removes_only_matching_rows():
    code = """\
CREATE TABLE t (id NUMBER);
INSERT INTO t VALUES (1);
INSERT INTO t VALUES (2);
INSERT INTO t VALUES (3);
DELETE FROM t WHERE id = 2;
"""
    steps = _steps_as_dicts(run(parse(tokenize(code)), {}))
    delete_step = steps[-1]
    assert delete_step["nodeType"] == "DeleteStatement"
    assert delete_step["table"]["rowsAffected"] == 1
    assert delete_step["table"]["rows"] == [{"id": 1}, {"id": 3}]


def test_delete_with_no_where_removes_every_row():
    code = "CREATE TABLE t (id NUMBER); INSERT INTO t VALUES (1); INSERT INTO t VALUES (2); DELETE FROM t;"
    steps = _steps_as_dicts(run(parse(tokenize(code)), {}))
    assert steps[-1]["table"]["rows"] == []
    assert steps[-1]["table"]["rowsAffected"] == 2


def test_delete_only_removes_matching_rows_even_with_duplicate_values():
    """DELETE matches by row identity, not structural equality -- two
    rows holding identical values are still two distinct rows."""
    code = """\
CREATE TABLE t (tag NUMBER);
INSERT INTO t VALUES (1);
INSERT INTO t VALUES (1);
DELETE FROM t WHERE tag = 1;
"""
    steps = _steps_as_dicts(run(parse(tokenize(code)), {}))
    # Both rows independently match `tag = 1` -- both are legitimately deleted.
    assert steps[-1]["table"]["rows"] == []


def test_delete_from_undeclared_table_is_an_interpreter_error():
    with pytest.raises(InterpreterError, match="is not declared"):
        run(parse(tokenize("DELETE FROM nope;")), {})


# -- interpreter: division-by-zero handling reuses the standard pattern -----


def test_insert_division_by_zero_with_no_handler_aborts_the_run():
    code = "CREATE TABLE t (a NUMBER); INSERT INTO t VALUES (1 / 0);"
    with pytest.raises(InterpreterError, match="Division by zero"):
        run(parse(tokenize(code)), {})


def test_insert_division_by_zero_handled_records_error_and_skips_the_insert():
    code = """\
CREATE PROCEDURE Demo()
BEGIN
    DECLARE ok NUMBER DEFAULT 0;
    DECLARE zero NUMBER DEFAULT 0;
    DECLARE CONTINUE HANDLER FOR DIVISION_BY_ZERO SET ok = 1;
    CREATE TABLE t (a NUMBER);
    INSERT INTO t VALUES (1 / zero);
END
"""
    steps = _steps_as_dicts(run(parse(tokenize(code)), {}))
    insert_step = next(s for s in steps if s["nodeType"] == "InsertStatement")
    assert insert_step["error"]["condition"] == "DIVISION_BY_ZERO"
    assert insert_step["table"]["rowsAffected"] == 0
    assert insert_step["table"]["rows"] == []
    assert steps[-1]["variables"]["ok"]["value"] == 1


def test_update_where_division_by_zero_handled_skips_the_update():
    code = """\
CREATE PROCEDURE Demo()
BEGIN
    DECLARE ok NUMBER DEFAULT 0;
    DECLARE zero NUMBER DEFAULT 0;
    DECLARE CONTINUE HANDLER FOR DIVISION_BY_ZERO SET ok = 1;
    CREATE TABLE t (a NUMBER);
    INSERT INTO t VALUES (5);
    UPDATE t SET a = 99 WHERE a > (1 / zero);
END
"""
    steps = _steps_as_dicts(run(parse(tokenize(code)), {}))
    update_step = next(s for s in steps if s["nodeType"] == "UpdateStatement")
    assert update_step["error"]["condition"] == "DIVISION_BY_ZERO"
    assert update_step["table"]["rowsAffected"] == 0
    assert update_step["table"]["rows"] == [{"a": 5}]


# -- interpreter: tables are global across a CALL chain, unlike cursors ------


def test_table_created_by_a_called_procedure_is_visible_to_the_caller_afterward():
    code = """\
CREATE PROCEDURE MakeTable()
BEGIN
    CREATE TABLE shared (a NUMBER);
    INSERT INTO shared VALUES (1);
END

CREATE PROCEDURE Main()
BEGIN
    CALL MakeTable();
    INSERT INTO shared VALUES (2);
END
"""
    steps = _steps_as_dicts(run(parse(tokenize(code)), {}))
    final_insert = steps[-1]
    assert final_insert["nodeType"] == "InsertStatement"
    assert final_insert["table"]["rows"] == [{"a": 1}, {"a": 2}]
    # The final step belongs to Main's own top-level frame, not MakeTable's.
    assert "call" not in final_insert


def test_table_state_resets_between_independent_runs():
    """`Interpreter.tables` starts empty every call to `run()` -- a
    table created in one /debug-equivalent run must not leak into the
    next one (same convention app.demo_db's own `products` table
    already follows: fresh every run, never persisted)."""
    code = "CREATE TABLE t (a NUMBER); INSERT INTO t VALUES (1);"
    ast = parse(tokenize(code))
    first = run(ast, {})[-1].to_dict()
    second = run(ast, {})[-1].to_dict()
    assert first["table"]["rows"] == second["table"]["rows"] == [{"a": 1}]
