"""Backs POST /sql/execute -- a standalone SQL console that runs
arbitrary SQL as-is against app.user_db's persistent database. Also
backs the raw-SQL-passthrough statements a procedure body can now
contain (CREATE TABLE / INSERT / UPDATE / DELETE / SELECT -- see
app.parser's "SQL passthrough statements" section and
app.interpreter's `_exec_sql_statement`), via `execute_sql_on_connection`
below, so both surfaces share one execution path and one error-message
convention rather than two.

Deliberately NOT routed through this project's own app.tokenizer /
app.parser / app.interpreter pipeline at all: that pipeline exists to
interpret this project's own procedural dialect (DECLARE/SET/IF/WHILE/
cursors/...), not to execute plain SQL statements. This is a raw
passthrough straight to the sqlite3 driver -- one statement, exactly as
typed, no step trace, no AST.
"""

from __future__ import annotations

import re
import sqlite3

from app import user_db

# Only used to build the human-readable "description" string in the
# response -- SQLite itself doesn't care what kind of statement it is,
# and this classification never decides *how* the statement runs (that
# is always the same cursor.execute() call below). So a statement this
# regex fails to classify (an odd keyword, a leading comment it can't
# parse) just gets a slightly generic description, never incorrect
# execution.
_LEADING_COMMENT_RE = re.compile(r"\s*(--[^\n]*\n|/\*.*?\*/)\s*", re.DOTALL)
_FIRST_WORD_RE = re.compile(r"[A-Za-z]+")

_DDL_KEYWORDS = {"CREATE", "DROP", "ALTER"}
_DML_KEYWORDS = {"INSERT", "UPDATE", "DELETE", "REPLACE"}

# Best-effort table-name extraction, used only for the DebugStep `sql`
# field's `tableName`/table-snapshot convenience (see app.interpreter's
# `_exec_sql_statement`) -- NOT used to decide how a statement executes,
# so a name this can't extract (an exotic statement shape) just means no
# snapshot, never incorrect execution. Deliberately simple regexes, not
# a real SQL parser, matching this module's own "no SQL parsing of our
# own" convention -- see the module docstring.
_CREATE_TABLE_NAME_RE = re.compile(r"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?[\"'\[`]?(\w+)", re.IGNORECASE)
_INSERT_TABLE_NAME_RE = re.compile(r"INSERT\s+(?:OR\s+\w+\s+)?INTO\s+[\"'\[`]?(\w+)", re.IGNORECASE)
_UPDATE_TABLE_NAME_RE = re.compile(r"UPDATE\s+[\"'\[`]?(\w+)", re.IGNORECASE)
_DELETE_TABLE_NAME_RE = re.compile(r"DELETE\s+FROM\s+[\"'\[`]?(\w+)", re.IGNORECASE)

_TABLE_NAME_PATTERNS = {
    "CREATE": _CREATE_TABLE_NAME_RE,
    "INSERT": _INSERT_TABLE_NAME_RE,
    "UPDATE": _UPDATE_TABLE_NAME_RE,
    "DELETE": _DELETE_TABLE_NAME_RE,
}


class SqlExecutionError(Exception):
    """A clean, user-facing SQL error message -- never a raw Python
    traceback. Always built from `str(sqlite3.Error)`, which SQLite
    itself already keeps human-readable (e.g. 'no such table: foo',
    'near \"SELCT\": syntax error')."""


def _first_keyword(sql: str) -> str:
    """The statement's leading keyword (SELECT/INSERT/CREATE/...),
    uppercased, skipping past any leading `--`/`/* */` comments."""
    remaining = sql
    while True:
        match = _LEADING_COMMENT_RE.match(remaining)
        if not match:
            break
        remaining = remaining[match.end():]
    word = _FIRST_WORD_RE.match(remaining.strip())
    return word.group(0).upper() if word else ""


def _write_description(keyword: str, rows_affected: int) -> str:
    if keyword in _DDL_KEYWORDS:
        return f"{keyword} statement executed successfully."
    if keyword in _DML_KEYWORDS:
        plural = "" if rows_affected == 1 else "s"
        return f"{keyword} affected {rows_affected} row{plural}."
    return "Statement executed successfully."


def extract_table_name(keyword: str, sql: str) -> str | None:
    """Best-effort table name for a CREATE/INSERT/UPDATE/DELETE
    statement (None for SELECT, or for a shape the regex doesn't
    recognize) -- see the module-level patterns above for exactly what's
    matched and why this is deliberately not a real parse."""
    pattern = _TABLE_NAME_PATTERNS.get(keyword)
    if pattern is None:
        return None
    match = pattern.search(sql)
    return match.group(1) if match else None


def execute_sql_on_connection(conn: sqlite3.Connection, sql: str) -> dict:
    """The actual execution logic, against a connection the caller
    already owns (opened and eventually closed by them) -- factored out
    of `execute_sql` below so `app.interpreter`'s `_exec_sql_statement`
    can run a raw-passthrough statement on the SAME connection/
    transaction its own run is already using (`self._db`), rather than
    opening a second, independent connection to the same file mid-run.

    Returns a dict shaped one of two ways:
      - a row-producing statement (SELECT, PRAGMA, ...):
          {"kind": "rows", "columns": [...], "rows": [[...], ...],
           "rowCount": int, "description": str}
      - a write/DDL statement (INSERT/UPDATE/DELETE/CREATE/DROP/ALTER):
          {"kind": "write", "rowsAffected": int, "description": str}

    Raises SqlExecutionError (a clean message, no traceback) on any
    SQLite error -- a bad table name, a syntax error, a constraint
    violation, running more than one statement at once, etc.
    """
    if not sql or not sql.strip():
        raise SqlExecutionError("No SQL to execute.")

    cursor = conn.cursor()
    try:
        cursor.execute(sql)
    except sqlite3.Error as exc:
        raise SqlExecutionError(str(exc)) from exc

    keyword = _first_keyword(sql)

    if cursor.description is not None:
        # A row-producing statement (SELECT, PRAGMA, ...) -- fetch
        # everything now, while the connection (and thus the cursor) is
        # still open.
        columns = [col[0] for col in cursor.description]
        rows = [list(row) for row in cursor.fetchall()]
        return {
            "kind": "rows",
            "columns": columns,
            "rows": rows,
            "rowCount": len(rows),
            "description": f"{keyword or 'Query'} returned {len(rows)} row{'' if len(rows) == 1 else 's'}.",
        }

    # A write/DDL statement -- commit so it actually persists to the
    # on-disk file, then report what changed. rowcount is -1 for
    # statements (like CREATE/DROP) that don't touch rows.
    conn.commit()
    rows_affected = cursor.rowcount if cursor.rowcount is not None and cursor.rowcount >= 0 else 0
    return {
        "kind": "write",
        "rowsAffected": rows_affected,
        "description": _write_description(keyword, rows_affected),
    }


def execute_sql(sql: str) -> dict:
    """Run one SQL statement against the persistent user database,
    opening and closing its own connection -- the entry point
    POST /sql/execute uses (see app.main). See `execute_sql_on_connection`
    above for the actual logic and the full return-shape/error contract;
    this is just that function plus connection lifecycle management."""
    conn = user_db.get_connection()
    try:
        return execute_sql_on_connection(conn, sql)
    finally:
        conn.close()
