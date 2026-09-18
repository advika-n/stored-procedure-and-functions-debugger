from fastapi.testclient import TestClient

from app import main, practice
from app.main import app

client = TestClient(app)


def _sample_questions(n=5):
    return [
        {
            "question": f"Question {i}?",
            "options": ["A", "B", "C", "D"],
            "correctIndex": 0,
            "explanation": f"Explanation {i}.",
        }
        for i in range(n)
    ]


def test_practice_generate_returns_questions(monkeypatch):
    captured = {}

    def fake_generate(difficulty, num_questions):
        captured["difficulty"] = difficulty
        captured["numQuestions"] = num_questions
        return _sample_questions(num_questions)

    monkeypatch.setattr(main, "generate_practice_questions", fake_generate)

    response = client.post("/practice/generate", json={"difficulty": "medium", "numQuestions": 8})

    assert response.status_code == 200
    body = response.json()
    assert len(body["questions"]) == 8
    assert captured["difficulty"] == "medium"
    assert captured["numQuestions"] == 8


def test_practice_generate_rejects_an_unknown_difficulty():
    response = client.post("/practice/generate", json={"difficulty": "impossible", "numQuestions": 5})

    assert response.status_code == 400
    assert "difficulty" in response.json()["detail"]


def test_practice_generate_rejects_num_questions_below_one():
    response = client.post("/practice/generate", json={"difficulty": "easy", "numQuestions": 0})

    assert response.status_code == 422  # pydantic Field(ge=1) validation


def test_practice_generate_rejects_num_questions_above_fifteen():
    response = client.post("/practice/generate", json={"difficulty": "easy", "numQuestions": 16})

    assert response.status_code == 422  # pydantic Field(le=15) validation


def test_practice_generate_falls_back_gracefully_without_a_key_end_to_end(monkeypatch):
    # No mocking of generate_practice_questions -- exercises the real
    # missing-key -> fallback-bank path through the endpoint. Unlike the
    # old /quiz/generate (which 502'd with no key), this must succeed.
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    response = client.post("/practice/generate", json={"difficulty": "hard", "numQuestions": 5})

    assert response.status_code == 200
    questions = response.json()["questions"]
    assert len(questions) == 5
    for q in questions:
        assert len(q["options"]) == 4
        assert 0 <= q["correctIndex"] < 4


def test_practice_generate_handles_a_malformed_gemini_response_via_fallback(monkeypatch):
    class FakeResponse:
        text = "not json at all"

    class FakeModels:
        def generate_content(self, model, contents, config):
            return FakeResponse()

    class FakeClient:
        models = FakeModels()

    monkeypatch.setattr(practice, "_get_gemini_client", lambda: FakeClient())

    response = client.post("/practice/generate", json={"difficulty": "easy", "numQuestions": 5})

    assert response.status_code == 200
    assert len(response.json()["questions"]) == 5


def test_practice_generate_default_difficulty_values_are_accepted():
    for difficulty in ("easy", "medium", "hard"):
        response = client.post("/practice/generate", json={"difficulty": difficulty, "numQuestions": 1})
        assert response.status_code == 200
        assert len(response.json()["questions"]) == 1
