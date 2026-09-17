import pytest

from app.sql_console import SqlExecutionError, execute_sql


def test_select_returns_columns_and_rows():
    result = execute_sql("SELECT name, price FROM products ORDER BY price")
    assert result["kind"] == "rows"
    assert result["columns"] == ["name", "price"]
    assert result["rows"] == [["Widget", 10], ["Gizmo", 15], ["Gadget", 25]]
    assert result["rowCount"] == 3
    assert "3 row" in result["description"]


def test_select_with_no_matching_rows():
    result = execute_sql("SELECT * FROM products WHERE price > 1000")
    assert result["kind"] == "rows"
    assert result["rows"] == []
    assert result["rowCount"] == 0


def test_create_table():
    result = execute_sql("CREATE TABLE notes (id INTEGER PRIMARY KEY, body TEXT)")
    assert result["kind"] == "write"
    assert "CREATE" in result["description"]

    # The new table is immediately queryable -- same connection source
    # of truth as the products table.
    listed = execute_sql("SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'notes'")
    assert listed["rowCount"] == 1


def test_insert_reports_rows_affected():
    execute_sql("CREATE TABLE notes (id INTEGER PRIMARY KEY, body TEXT)")
    result = execute_sql("INSERT INTO notes (body) VALUES ('hello')")
    assert result["kind"] == "write"
    assert result["rowsAffected"] == 1
    assert "1 row" in result["description"]


def test_update_reports_rows_affected():
    execute_sql("CREATE TABLE notes (id INTEGER PRIMARY KEY, body TEXT)")
    execute_sql("INSERT INTO notes (body) VALUES ('a')")
    execute_sql("INSERT INTO notes (body) VALUES ('b')")

    result = execute_sql("UPDATE notes SET body = 'updated'")
    assert result["kind"] == "write"
    assert result["rowsAffected"] == 2
    assert "2 row" in result["description"]

    selected = execute_sql("SELECT body FROM notes ORDER BY id")
    assert selected["rows"] == [["updated"], ["updated"]]


def test_delete_reports_rows_affected():
    execute_sql("CREATE TABLE notes (id INTEGER PRIMARY KEY, body TEXT)")
    execute_sql("INSERT INTO notes (body) VALUES ('a')")
    execute_sql("INSERT INTO notes (body) VALUES ('b')")

    result = execute_sql("DELETE FROM notes WHERE body = 'a'")
    assert result["kind"] == "write"
    assert result["rowsAffected"] == 1

    remaining = execute_sql("SELECT COUNT(*) AS n FROM notes")
    assert remaining["rows"] == [[1]]


def test_writes_persist_across_calls():
    # Each execute_sql() call opens its own connection (like
    # app.user_db.get_connection() everywhere else) -- a write from one
    # call must be visible to the next.
    execute_sql("CREATE TABLE persisted (x INTEGER)")
    execute_sql("INSERT INTO persisted (x) VALUES (42)")
    result = execute_sql("SELECT x FROM persisted")
    assert result["rows"] == [[42]]


def test_sql_syntax_error_raises_clean_message_not_a_traceback():
    with pytest.raises(SqlExecutionError) as excinfo:
        execute_sql("SELEKT * FROM products")
    message = str(excinfo.value)
    assert "Traceback" not in message
    assert "syntax error" in message.lower()


def test_sql_error_against_nonexistent_table():
    with pytest.raises(SqlExecutionError) as excinfo:
        execute_sql("SELECT * FROM no_such_table")
    assert "no such table" in str(excinfo.value).lower()


def test_empty_sql_raises_clean_error():
    with pytest.raises(SqlExecutionError):
        execute_sql("")
    with pytest.raises(SqlExecutionError):
        execute_sql("   ")


def test_multiple_statements_at_once_raises_clean_error():
    with pytest.raises(SqlExecutionError):
        execute_sql("CREATE TABLE a (x INTEGER); CREATE TABLE b (y INTEGER);")
