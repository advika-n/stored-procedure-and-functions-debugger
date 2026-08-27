from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

CALCULATE_DISCOUNT = """\
DECLARE total NUMBER DEFAULT 0;
SET total = 5 * 3;
"""


def test_successful_debug_run_is_saved_to_history():
    assert client.get("/history").json()["runs"] == []

    response = client.post("/debug", json={"code": CALCULATE_DISCOUNT, "name": "CalculateDiscount"})
    assert response.status_code == 200

    runs = client.get("/history").json()["runs"]
    assert len(runs) == 1
    assert runs[0]["procedureName"] == "CalculateDiscount"
    assert runs[0]["status"] == "success"
    assert runs[0]["stepCount"] == len(response.json()["steps"])


def test_debug_run_without_a_name_falls_back_to_first_line():
    client.post("/debug", json={"code": "DECLARE z NUMBER DEFAULT 9;"})

    runs = client.get("/history").json()["runs"]
    assert runs[0]["procedureName"] == "DECLARE z NUMBER DEFAULT 9;"


def test_failed_debug_run_is_not_saved_to_history():
    # A syntax error (bad character) -- should 400 and leave history untouched.
    response = client.post("/debug", json={"code": "SET x = @1;"})
    assert response.status_code == 400

    assert client.get("/history").json()["runs"] == []


def test_history_entry_can_be_fetched_and_replayed():
    debug_response = client.post("/debug", json={"code": CALCULATE_DISCOUNT, "name": "Replay Me"})
    run_id = client.get("/history").json()["runs"][0]["id"]

    detail = client.get(f"/history/{run_id}").json()

    assert detail["code"] == CALCULATE_DISCOUNT
    assert detail["steps"] == debug_response.json()["steps"]
    assert detail["ast"] == debug_response.json()["ast"]
    assert detail["procedureName"] == "Replay Me"


def test_get_missing_history_entry_returns_404():
    response = client.get("/history/999999")
    assert response.status_code == 404


def test_delete_one_history_entry():
    client.post("/debug", json={"code": CALCULATE_DISCOUNT, "name": "ToDelete"})
    run_id = client.get("/history").json()["runs"][0]["id"]

    delete_response = client.delete(f"/history/{run_id}")
    assert delete_response.status_code == 200
    assert delete_response.json() == {"deleted": run_id}

    assert client.get("/history").json()["runs"] == []
    assert client.get(f"/history/{run_id}").status_code == 404


def test_delete_missing_history_entry_returns_404():
    assert client.delete("/history/999999").status_code == 404


def test_clear_all_history():
    client.post("/debug", json={"code": CALCULATE_DISCOUNT, "name": "A"})
    client.post("/debug", json={"code": CALCULATE_DISCOUNT, "name": "B"})

    response = client.delete("/history")

    assert response.status_code == 200
    assert response.json() == {"cleared": 2}
    assert client.get("/history").json()["runs"] == []


def test_history_survives_across_separate_requests():
    # Simulates "reload the browser tab": a brand-new TestClient (fresh
    # in-memory app state) should still see history written earlier,
    # since it's read from the SQLite file, not from server memory.
    client.post("/debug", json={"code": CALCULATE_DISCOUNT, "name": "Persisted"})

    fresh_client = TestClient(app)
    runs = fresh_client.get("/history").json()["runs"]

    assert any(r["procedureName"] == "Persisted" for r in runs)
