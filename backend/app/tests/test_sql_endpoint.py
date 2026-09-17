from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_select_endpoint():
    response = client.post("/sql/execute", json={"sql": "SELECT name, price FROM products ORDER BY price"})
    assert response.status_code == 200
    body = response.json()
    assert body["kind"] == "rows"
    assert body["columns"] == ["name", "price"]
    assert body["rows"] == [["Widget", 10], ["Gizmo", 15], ["Gadget", 25]]
    assert body["rowCount"] == 3


def test_create_table_endpoint():
    response = client.post("/sql/execute", json={"sql": "CREATE TABLE orders (id INTEGER PRIMARY KEY, item TEXT)"})
    assert response.status_code == 200
    body = response.json()
    assert body["kind"] == "write"
    assert "CREATE" in body["description"]


def test_insert_endpoint():
    client.post("/sql/execute", json={"sql": "CREATE TABLE orders (id INTEGER PRIMARY KEY, item TEXT)"})
    response = client.post("/sql/execute", json={"sql": "INSERT INTO orders (item) VALUES ('Widget')"})
    assert response.status_code == 200
    body = response.json()
    assert body["kind"] == "write"
    assert body["rowsAffected"] == 1


def test_update_endpoint():
    client.post("/sql/execute", json={"sql": "CREATE TABLE orders (id INTEGER PRIMARY KEY, item TEXT)"})
    client.post("/sql/execute", json={"sql": "INSERT INTO orders (item) VALUES ('Widget')"})
    response = client.post("/sql/execute", json={"sql": "UPDATE orders SET item = 'Gadget' WHERE item = 'Widget'"})
    assert response.status_code == 200
    body = response.json()
    assert body["kind"] == "write"
    assert body["rowsAffected"] == 1


def test_delete_endpoint():
    client.post("/sql/execute", json={"sql": "CREATE TABLE orders (id INTEGER PRIMARY KEY, item TEXT)"})
    client.post("/sql/execute", json={"sql": "INSERT INTO orders (item) VALUES ('Widget')"})
    response = client.post("/sql/execute", json={"sql": "DELETE FROM orders WHERE item = 'Widget'"})
    assert response.status_code == 200
    body = response.json()
    assert body["kind"] == "write"
    assert body["rowsAffected"] == 1


def test_deliberate_sql_error_returns_clean_400():
    response = client.post("/sql/execute", json={"sql": "SELEKT * FROM products"})
    assert response.status_code == 400
    detail = response.json()["detail"]
    assert isinstance(detail, str)
    assert "Traceback" not in detail
    assert "syntax error" in detail.lower()


def test_sql_error_against_missing_table_returns_clean_400():
    response = client.post("/sql/execute", json={"sql": "DROP TABLE this_table_does_not_exist"})
    assert response.status_code == 400
    detail = response.json()["detail"]
    assert "no such table" in detail.lower()


def test_sql_console_and_cursor_share_one_source_of_truth():
    # A row written through the SQL Console must be visible to a
    # cursor's SELECT in the exact same request cycle a procedure
    # would use -- proving /sql/execute and /debug's OPEN/FETCH path
    # share app.user_db's one persistent database.
    insert = client.post(
        "/sql/execute",
        json={"sql": "INSERT INTO products (name, price) VALUES ('Sprocket', 42)"},
    )
    assert insert.status_code == 200

    code = """\
DECLARE total NUMBER DEFAULT 0;
DECLARE item_name STRING DEFAULT '';
DECLARE item_price NUMBER DEFAULT 0;
DECLARE prod_cursor CURSOR FOR SELECT name, price FROM products WHERE name = 'Sprocket';
OPEN prod_cursor;
FETCH prod_cursor INTO item_name, item_price;
SET total = total + item_price;
CLOSE prod_cursor;
"""
    debug_response = client.post("/debug", json={"code": code, "params": {}})
    assert debug_response.status_code == 200
    steps = debug_response.json()["steps"]
    assert steps[-1]["variables"]["total"]["value"] == 42
