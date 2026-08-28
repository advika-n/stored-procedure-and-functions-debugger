from fastapi.testclient import TestClient

from app import explainer
from app.main import app

client = TestClient(app)


def _clear_cache():
    explainer._cache.clear()


def test_explain_endpoint_returns_a_grounded_sentence(monkeypatch):
    # Mocked so this test is fast, offline, and deterministic -- Gemini's
    # actual output quality is checked manually (see project chat
    # history), and the fallback trigger itself has its own dedicated
    # tests in test_explainer.py.
    monkeypatch.setattr(explainer, "generate_gemini_explanation", lambda step, prev: "Gemini says hi.")
    _clear_cache()
    step = {
        "stepNumber": 1,
        "line": 1,
        "nodeType": "DeclareStatement",
        "statementText": "DECLARE total NUMBER DEFAULT 0;",
        "variables": {"total": {"value": 0, "type": "number", "changed": True}},
    }

    response = client.post("/explain", json={"step": step, "previousVariables": None})

    assert response.status_code == 200
    body = response.json()
    assert body["explanation"] == "Gemini says hi."
    assert body["source"] == "gemini"
    assert body["cached"] is False


def test_explain_endpoint_falls_back_to_template_without_a_key(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    _clear_cache()
    step = {
        "stepNumber": 1,
        "line": 1,
        "nodeType": "DeclareStatement",
        "statementText": "DECLARE total NUMBER DEFAULT 0;",
        "variables": {"total": {"value": 0, "type": "number", "changed": True}},
    }

    response = client.post("/explain", json={"step": step, "previousVariables": None})

    assert response.status_code == 200
    body = response.json()
    assert "total" in body["explanation"]
    assert body["source"] == "template"


def test_explain_endpoint_caches_repeat_requests(monkeypatch):
    monkeypatch.setattr(explainer, "generate_gemini_explanation", lambda step, prev: "Cached sentence.")
    _clear_cache()
    step = {
        "stepNumber": 1,
        "line": 1,
        "nodeType": "SetStatement",
        "statementText": "SET x = 1;",
        "variables": {"x": {"value": 1, "type": "number", "changed": True}},
    }

    first = client.post("/explain", json={"step": step}).json()
    second = client.post("/explain", json={"step": step}).json()

    assert first["cached"] is False
    assert second["cached"] is True
    assert second["explanation"] == first["explanation"]
