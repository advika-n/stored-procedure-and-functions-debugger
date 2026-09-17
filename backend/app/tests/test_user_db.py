from app import user_db


def test_get_connection_seeds_products_on_first_open():
    conn = user_db.get_connection()
    rows = conn.execute("SELECT name, price FROM products ORDER BY price").fetchall()
    assert rows == [("Widget", 10), ("Gizmo", 15), ("Gadget", 25)]
    conn.close()


def test_data_persists_across_separate_connections():
    # Unlike app.demo_db's :memory: connections, two separate
    # get_connection() calls must see each other's committed writes --
    # that's the entire point of this module (a persistent, on-disk,
    # shared-source-of-truth database).
    conn_a = user_db.get_connection()
    conn_a.execute("INSERT INTO products (name, price) VALUES ('Thingamajig', 99)")
    conn_a.commit()
    conn_a.close()

    conn_b = user_db.get_connection()
    count = conn_b.execute("SELECT COUNT(*) FROM products WHERE name = 'Thingamajig'").fetchone()[0]
    assert count == 1
    conn_b.close()


def test_reopening_does_not_reseed_an_existing_table():
    # A user deleting rows via the SQL Console must not have them
    # silently reappear the next time anything reopens the connection.
    conn_a = user_db.get_connection()
    conn_a.execute("DELETE FROM products")
    conn_a.commit()
    conn_a.close()

    conn_b = user_db.get_connection()
    assert conn_b.execute("SELECT COUNT(*) FROM products").fetchone()[0] == 0
    conn_b.close()


def test_dropping_the_table_lets_it_reseed_on_next_open():
    conn_a = user_db.get_connection()
    conn_a.execute("DROP TABLE products")
    conn_a.commit()
    conn_a.close()

    conn_b = user_db.get_connection()
    rows = conn_b.execute("SELECT COUNT(*) FROM products").fetchone()[0]
    assert rows == 3
    conn_b.close()
