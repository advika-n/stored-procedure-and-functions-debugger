from app import demo_db


def test_create_demo_connection_seeds_the_products_table():
    conn = demo_db.create_demo_connection()
    rows = conn.execute("SELECT name, price FROM products ORDER BY price").fetchall()
    assert rows == [("Widget", 10), ("Gizmo", 15), ("Gadget", 25)]
    conn.close()


def test_each_call_returns_an_independent_connection():
    conn_a = demo_db.create_demo_connection()
    conn_b = demo_db.create_demo_connection()

    conn_a.execute("DELETE FROM products")
    conn_a.commit()

    assert conn_a.execute("SELECT COUNT(*) FROM products").fetchone()[0] == 0
    assert conn_b.execute("SELECT COUNT(*) FROM products").fetchone()[0] == 3

    conn_a.close()
    conn_b.close()
