"""A small, fixed, auto-seeded in-memory dataset, kept around purely as
a deterministic test fixture for interpreter-level unit tests that want
a seeded `sqlite3.Connection` without touching disk.

No longer wired into the live /debug request path -- app.main now
opens app.user_db's persistent, on-disk, SQL-Console-shared database
instead (see that module's docstring for why). This module is
unchanged and still fine to use directly wherever a test wants a cheap,
throwaway, always-identical `products` table.

Exactly one table, seeded fresh on every call:

    products(name TEXT, price NUMBER)
    ('Widget', 10), ('Gadget', 25), ('Gizmo', 15)

A fresh in-memory database is created per call; nothing persists or
carries over between calls -- that's the point, for test isolation.
"""

from __future__ import annotations

import sqlite3

PRODUCTS_TABLE = "products"
PRODUCTS_COLUMNS = ("name", "price")
PRODUCTS_ROWS = [
    ("Widget", 10),
    ("Gadget", 25),
    ("Gizmo", 15),
]


def create_demo_connection() -> sqlite3.Connection:
    """A fresh in-memory SQLite connection, seeded with the `products`
    demo table described above. Callers own the returned connection
    and are responsible for closing it."""
    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE products (name TEXT, price NUMBER)")
    conn.executemany("INSERT INTO products (name, price) VALUES (?, ?)", PRODUCTS_ROWS)
    conn.commit()
    return conn
