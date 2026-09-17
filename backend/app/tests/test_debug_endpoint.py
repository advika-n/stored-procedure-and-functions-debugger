from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

CALCULATE_DISCOUNT = """\
DECLARE total NUMBER DEFAULT 0;
DECLARE discount NUMBER DEFAULT 0;
SET total = price * quantity;
IF total > 100 THEN
    SET discount = total * 0.1;
ELSE
    SET discount = total * 0.05;
END IF;
SET total = total - discount;
"""


def test_debug_endpoint_returns_step_trace():
    response = client.post(
        "/debug",
        json={"code": CALCULATE_DISCOUNT, "params": {"price": 20, "quantity": 6}},
    )

    assert response.status_code == 200
    body = response.json()
    assert "steps" in body
    assert len(body["steps"]) == 6

    # The AST is included too, for the frontend's control-flow diagram.
    assert body["ast"]["type"] == "Procedure"
    assert [stmt["type"] for stmt in body["ast"]["body"]] == [
        "DeclareStatement",
        "DeclareStatement",
        "SetStatement",
        "IfStatement",
        "SetStatement",
    ]

    last_step = body["steps"][-1]
    assert last_step["variables"]["total"]["value"] == 108.0


def test_debug_endpoint_defaults_params_to_empty_dict():
    response = client.post("/debug", json={"code": "DECLARE x NUMBER DEFAULT 1;"})
    assert response.status_code == 200
    assert response.json()["steps"][0]["variables"]["x"]["value"] == 1


def test_debug_endpoint_includes_anti_pattern_advisor_issues():
    # See app/advisor.py -- issues are computed from the same `ast` this
    # endpoint already builds, so they ride along on every successful
    # /debug response rather than needing a separate endpoint/request.
    # CALCULATE_DISCOUNT itself is clean (no anti-patterns), so this
    # only proves the key is always present, empty or not.
    response = client.post(
        "/debug",
        json={"code": CALCULATE_DISCOUNT, "params": {"price": 20, "quantity": 6}},
    )
    assert response.status_code == 200
    assert response.json()["issues"] == []


def test_debug_endpoint_flags_a_real_anti_pattern():
    code = """\
DECLARE cur CURSOR FOR SELECT * FROM products;
OPEN cur;
"""
    response = client.post("/debug", json={"code": code, "params": {}})
    assert response.status_code == 200
    issues = response.json()["issues"]
    categories = {issue["category"] for issue in issues}
    assert "select-star" in categories
    assert "cursor-not-closed" in categories


def test_debug_endpoint_reports_tokenizer_error_with_line():
    response = client.post("/debug", json={"code": "SET x = @1;", "params": {}})

    assert response.status_code == 400
    detail = response.json()["detail"]
    assert detail["stage"] == "tokenize"
    assert detail["line"] == 1
    assert "@" in detail["message"]


def test_debug_endpoint_reports_parser_error_with_line():
    # Missing END IF/semicolon on a multi-line procedure.
    code = "IF x > 1 THEN\n    SET x = 2;\n"
    response = client.post("/debug", json={"code": code, "params": {"x": 0}})

    assert response.status_code == 400
    detail = response.json()["detail"]
    assert detail["stage"] == "parse"
    assert detail["message"]
    # Ran out of tokens after line 2 (the SET), so that's the best line
    # we can point at even though there's no token left to blame.
    assert detail["line"] == 2


def test_debug_endpoint_reports_interpreter_error_with_line():
    response = client.post("/debug", json={"code": "SET x = 1;", "params": {}})

    assert response.status_code == 400
    detail = response.json()["detail"]
    assert detail["stage"] == "interpret"
    assert detail["line"] == 1
    assert "x" in detail["message"]


def test_debug_endpoint_supports_cursors_against_the_seeded_demo_products_table():
    # No db_connection is passed explicitly here -- this proves the
    # endpoint itself opens + seeds one (see app/user_db.py), not just
    # that app.interpreter.run() supports cursors when a test hands it
    # one.
    code = """\
DECLARE total NUMBER DEFAULT 0;
DECLARE item_name STRING DEFAULT '';
DECLARE item_price NUMBER DEFAULT 0;
DECLARE prod_cursor CURSOR FOR SELECT name, price FROM products;
OPEN prod_cursor;
WHILE prod_cursor%FOUND DO
    FETCH prod_cursor INTO item_name, item_price;
    SET total = total + item_price;
END WHILE;
CLOSE prod_cursor;
"""
    response = client.post("/debug", json={"code": code, "params": {}})

    assert response.status_code == 200
    steps = response.json()["steps"]
    fetch_steps = [s for s in steps if s["nodeType"] == "FetchCursorNode"]
    assert [f["cursor"]["currentRow"] for f in fetch_steps] == [
        {"name": "Widget", "price": 10},
        {"name": "Gadget", "price": 25},
        {"name": "Gizmo", "price": 15},
    ]
    assert steps[-1]["variables"]["total"]["value"] == 50


def test_debug_endpoint_runs_a_multi_procedure_call_based_program():
    """End-to-end check that /debug (main.py itself untouched -- see
    CLAUDE.md/HANDOFF.md's CALL-support phase) correctly handles the new
    ProgramNode AST shape and a CallStatement trace without any endpoint
    changes: the interpreter/parser changes alone are enough."""
    code = """\
CREATE PROCEDURE ComputeSubtotal(IN price NUMBER, IN quantity NUMBER, OUT subtotal NUMBER)
BEGIN
    SET subtotal = price * quantity;
END;

CREATE PROCEDURE OrderTotal(IN price NUMBER, IN quantity NUMBER, OUT grandTotal NUMBER)
BEGIN
    DECLARE subtotal NUMBER DEFAULT 0;
    CALL ComputeSubtotal(price, quantity, subtotal);
    SET grandTotal = subtotal;
END;
"""
    response = client.post("/debug", json={"code": code, "params": {"price": 10, "quantity": 4}})

    assert response.status_code == 200
    body = response.json()
    assert body["ast"]["type"] == "ProgramNode"
    assert [d["name"] for d in body["ast"]["definitions"]] == ["ComputeSubtotal", "OrderTotal"]

    steps = body["steps"]
    assert steps[-1]["variables"]["grandTotal"]["value"] == 40

    nested = [s for s in steps if "call" in s]
    assert nested and all(s["call"]["procedureName"] == "ComputeSubtotal" for s in nested)
