from fastapi.testclient import TestClient

from app import main
from app.main import app

client = TestClient(app)


def test_ask_endpoint_returns_a_grounded_answer(monkeypatch):
    # Mocked so this test is fast, offline, and deterministic -- same
    # convention as test_explain_endpoint.py. Patched on app.main (not
    # app.explainer), since main.py imports answer_question by name --
    # patching the origin module wouldn't affect main's own binding.
    monkeypatch.setattr(
        main, "answer_question", lambda code, step, question: "It took THEN because total (120) exceeded 100."
    )
    step = {
        "line": 4,
        "nodeType": "IfStatement",
        "statementText": "IF total > 100 THEN",
        "variables": {"total": {"value": 120, "type": "number", "changed": False}},
        "branch": {"condition": "total > 100", "result": True, "path": "then"},
    }

    response = client.post(
        "/ask",
        json={"code": "CREATE PROCEDURE p() BEGIN ... END;", "step": step, "question": "why did it take this branch"},
    )

    assert response.status_code == 200
    assert response.json() == {"answer": "It took THEN because total (120) exceeded 100."}


def test_ask_endpoint_returns_502_with_a_clear_message_when_gemini_fails(monkeypatch):
    def boom(code, step, question):
        raise RuntimeError("some internal SDK error detail")

    monkeypatch.setattr(main, "answer_question", boom)
    step = {"line": 1, "nodeType": "SetStatement", "statementText": "SET x = 1;", "variables": {}}

    response = client.post("/ask", json={"code": "SET x = 1;", "step": step, "question": "what does this do"})

    assert response.status_code == 502
    detail = response.json()["detail"]
    assert "some internal SDK error detail" not in detail  # no raw exception text leaked, just a clear message
    assert "Gemini" in detail


def test_ask_endpoint_falls_back_gracefully_without_a_key(monkeypatch):
    # End-to-end version: no mocking of answer_question, so this exercises
    # the real missing-key failure path through the endpoint.
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    step = {"line": 1, "nodeType": "SetStatement", "statementText": "SET x = 1;", "variables": {}}

    response = client.post("/ask", json={"code": "SET x = 1;", "step": step, "question": "what does this do"})

    assert response.status_code == 502
    assert "Gemini" in response.json()["detail"]
