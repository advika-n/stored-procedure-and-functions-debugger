"""The real, persistent SQLite database user data lives in -- backing
both cursor OPEN/FETCH statements (app.interpreter) and the standalone
SQL Console (POST /sql/execute, see app.sql_console/app.main). The two
share this one source of truth on purpose: a table created or edited
from the console is immediately what a cursor's embedded SELECT sees,
and vice versa.

Deliberately a separate file from app.history's `debug_history.db` --
that one is this app's own internal run-history log (a course-project
implementation detail); this one is the "real" database a user's SQL
actually runs against. The two are never mixed in the same file or
table namespace, so e.g. a `DROP TABLE` typed into the console can
never touch `debug_history`.

Persists across requests -- a real file on disk (`backend/data/
user_data.db`), opened fresh per call like app.history does (sqlite3
connections aren't safe to share across the threads FastAPI's sync
route handlers can run on), not recreated from scratch each time like
the old app.demo_db's `:memory:` connection. `products(name, price)` is
seeded once, the first time this file (or just this table) doesn't
exist yet -- see `_ensure_seed_data`. A user is free to DROP/ALTER/
INSERT/DELETE it via the SQL Console afterwards; those changes persist
for real, including across a backend restart.

app.demo_db.py is kept around, unchanged, purely as a small
self-contained fixture used directly by interpreter-level unit tests
that want a deterministic seeded connection without touching disk --
it is no longer wired into the live /debug request path (see
app.main), which uses this module instead.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "user_data.db"

PRODUCTS_TABLE = "products"
PRODUCTS_ROWS = [
    ("Widget", 10),
    ("Gadget", 25),
    ("Gizmo", 15),
]


def _ensure_seed_data(conn: sqlite3.Connection) -> None:
    """Create + seed `products(name, price)` the first time this
    database doesn't already have it -- e.g. a brand-new DB file, or
    one where the table was since DROPped. Never re-seeds a table that
    already exists (so rows a user INSERTed/DELETEd via the console
    are never silently reset)."""
    exists = conn.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table' AND name = ?",
        (PRODUCTS_TABLE,),
    ).fetchone()
    if exists is not None:
        return
    conn.execute("CREATE TABLE products (name TEXT, price NUMBER)")
    conn.executemany("INSERT INTO products (name, price) VALUES (?, ?)", PRODUCTS_ROWS)
    conn.commit()


def get_connection() -> sqlite3.Connection:
    """A connection to the persistent on-disk user database, seeding
    `products` if this is the first time it's been opened. Callers own
    the returned connection and are responsible for closing it."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    _ensure_seed_data(conn)
    return conn
