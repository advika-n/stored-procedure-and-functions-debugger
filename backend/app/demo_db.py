"""A small, fixed, auto-seeded demo dataset every /debug run gets for
free, so cursor-based sample procedures work out of the box without a
schema-authoring feature -- which doesn't exist yet (a deliberate scope
boundary, see app.interpreter's module docstring's "Cursors" section).

Exactly one table, seeded fresh on every request:

    products(name TEXT, price NUMBER)
    ('Widget', 10), ('Gadget', 25), ('Gizmo', 15)

Deliberately small, fixed, and not user-editable -- documented here and
in Theory.jsx / README.md so it's not a mystery to anyone writing their
own cursor-based procedure against it. A fresh in-memory database is
created per request; nothing persists or carries over between runs.
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
