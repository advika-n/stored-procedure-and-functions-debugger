"""Persistent history of debug runs, backed by a SQLite table.

Deliberate scope choice: only **successful** debug runs are saved. A
tokenize/parse/interpret failure never reaches `save_run` (see the
`/debug` handler in main.py), so `status` is always `"success"` for
every row that exists today -- the column is kept so the schema
doesn't need to change if failed attempts are ever worth logging too.

This is intentionally a single-user, unauthenticated "recent runs" log,
not a multi-user history store -- there's no user/session column and
no login. That's a deliberate scope choice for this course project, not
an oversight; see the docs for the rationale.

Uses the stdlib `sqlite3` module directly (no ORM), consistent with the
rest of this codebase's plain-dict style. A short-lived connection is
opened per call rather than shared across requests, since sqlite3
connections aren't safe to share across the threads FastAPI's sync
route handlers can run on.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "debug_history.db"

HISTORY_LIMIT = 50
NAME_MAX_LENGTH = 80


_CREATE_TABLE_SQL = """
    CREATE TABLE IF NOT EXISTS debug_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT NOT NULL,
        procedure_name TEXT NOT NULL,
        code TEXT NOT NULL,
        params TEXT NOT NULL,
        step_count INTEGER NOT NULL,
        status TEXT NOT NULL,
        ast TEXT NOT NULL,
        steps TEXT NOT NULL
    )
"""


def _connect() -> sqlite3.Connection:
    # Table creation happens here, on every connection, rather than once
    # eagerly at import time -- that way whichever DB_PATH is active
    # *right now* (the real one, or a test's monkeypatched temp file)
    # is the one that gets initialized, with no import-order dependency.
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute(_CREATE_TABLE_SQL)
    return conn


def init_db() -> None:
    """Kept for explicit/test use; _connect() already ensures the table
    exists on every call, so this is just a no-op connect-and-close."""
    with _connect():
        pass


def derive_procedure_name(code: str, explicit_name: str | None) -> str:
    """The sample picker's name if one was passed, otherwise the first
    non-blank line of the code (trimmed), otherwise a placeholder."""
    if explicit_name:
        return explicit_name[:NAME_MAX_LENGTH]
    for line in code.splitlines():
        stripped = line.strip()
        if stripped:
            return stripped[:NAME_MAX_LENGTH]
    return "Untitled procedure"


def _row_summary(row: sqlite3.Row) -> dict:
    return {
        "id": row["id"],
        "timestamp": row["timestamp"],
        "procedureName": row["procedure_name"],
        "stepCount": row["step_count"],
        "status": row["status"],
    }


def _row_detail(row: sqlite3.Row) -> dict:
    return {
        **_row_summary(row),
        "code": row["code"],
        "params": json.loads(row["params"]),
        "ast": json.loads(row["ast"]),
        "steps": json.loads(row["steps"]),
    }


def save_run(
    code: str,
    params: dict,
    steps: list[dict],
    ast: dict,
    name: str | None = None,
    status: str = "success",
) -> int:
    """Save one completed debug run and return its new id."""
    procedure_name = derive_procedure_name(code, name)
    timestamp = datetime.now(timezone.utc).isoformat()

    with _connect() as conn:
        cursor = conn.execute(
            """
            INSERT INTO debug_history
                (timestamp, procedure_name, code, params, step_count, status, ast, steps)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                timestamp,
                procedure_name,
                code,
                json.dumps(params),
                len(steps),
                status,
                json.dumps(ast),
                json.dumps(steps),
            ),
        )
        return cursor.lastrowid


def list_runs(limit: int = HISTORY_LIMIT) -> list[dict]:
    """Summaries only (no code/steps/ast), most recent first."""
    with _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM debug_history ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [_row_summary(row) for row in rows]


def get_run(run_id: int) -> dict | None:
    """Full detail for one run (code, params, ast, steps), or None."""
    with _connect() as conn:
        row = conn.execute(
            "SELECT * FROM debug_history WHERE id = ?", (run_id,)
        ).fetchone()
    return _row_detail(row) if row is not None else None


def delete_run(run_id: int) -> bool:
    """Delete one run. Returns True if a row was actually deleted."""
    with _connect() as conn:
        cursor = conn.execute("DELETE FROM debug_history WHERE id = ?", (run_id,))
        return cursor.rowcount > 0


def clear_all() -> int:
    """Delete every run. Returns how many rows were removed."""
    with _connect() as conn:
        cursor = conn.execute("DELETE FROM debug_history")
        return cursor.rowcount
