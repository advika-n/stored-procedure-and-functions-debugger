from fastapi.testclient import TestClient

from app import main
from app.main import app

client = TestClient(app)

SAMPLE_QUESTIONS = [
    {
        "question": f"Question {i}?",
        "options": ["A", "B", "C", "D"],
        "correctIndex": 0,
        "explanation": f"Explanation {i}.",
    }
    for i in range(5)
]


def test_quiz_generate_theory_returns_questions(monkeypatch):
    captured = {}

    def fake_generate_quiz(source, code=None):
        captured["source"] = source
        captured["code"] = code
        return SAMPLE_QUESTIONS

    monkeypatch.setattr(main, "generate_quiz", fake_generate_quiz)

    response = client.post("/quiz/generate", json={"source": "theory"})

    assert response.status_code == 200
    assert response.json() == {"questions": SAMPLE_QUESTIONS}
    assert captured["source"] == "theory"
    assert captured["code"] is None


def test_quiz_generate_procedure_passes_the_code_through(monkeypatch):
    captured = {}

    def fake_generate_quiz(source, code=None):
        captured["source"] = source
        captured["code"] = code
        return SAMPLE_QUESTIONS

    monkeypatch.setattr(main, "generate_quiz", fake_generate_quiz)

    code = "CREATE PROCEDURE p() BEGIN SET x = 1; END"
    response = client.post("/quiz/generate", json={"source": "procedure", "code": code})

    assert response.status_code == 200
    assert captured["source"] == "procedure"
    assert captured["code"] == code


def test_quiz_generate_rejects_an_unknown_source():
    response = client.post("/quiz/generate", json={"source": "nonsense"})

    assert response.status_code == 400
    assert "source" in response.json()["detail"]


def test_quiz_generate_rejects_procedure_source_without_code():
    response = client.post("/quiz/generate", json={"source": "procedure"})

    assert response.status_code == 400
    assert "code" in response.json()["detail"]


def test_quiz_generate_rejects_procedure_source_with_blank_code():
    response = client.post("/quiz/generate", json={"source": "procedure", "code": "   "})

    assert response.status_code == 400


def test_quiz_generate_returns_502_with_a_clear_message_when_gemini_fails(monkeypatch):
    def boom(source, code=None):
        raise RuntimeError("some internal SDK error detail")

    monkeypatch.setattr(main, "generate_quiz", boom)

    response = client.post("/quiz/generate", json={"source": "theory"})

    assert response.status_code == 502
    detail = response.json()["detail"]
    assert "some internal SDK error detail" not in detail  # no raw exception text leaked
    assert "Gemini" in detail


def test_quiz_generate_falls_back_gracefully_without_a_key(monkeypatch):
    # End-to-end version: no mocking of generate_quiz, so this exercises
    # the real missing-key failure path through the endpoint.
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    response = client.post("/quiz/generate", json={"source": "theory"})

    assert response.status_code == 502
    assert "Gemini" in response.json()["detail"]
