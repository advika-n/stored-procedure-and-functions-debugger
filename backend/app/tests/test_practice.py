import json

import pytest

from app import practice
from app.practice import (
    DIFFICULTIES,
    _fallback_questions,
    _parse_practice_json,
    _strip_json_fences,
    generate_practice_questions,
)


def _valid_questions(n):
    return [
        {
            "question": f"Question {i}?",
            "options": ["A", "B", "C", "D"],
            "correctIndex": i % 4,
            "explanation": f"Because {i}.",
        }
        for i in range(n)
    ]


def _fake_client(responses):
    """A minimal Gemini client stand-in whose generate_content() returns
    each of `responses` in turn (as .text), one per call -- same pattern
    the old test_quiz.py used."""
    calls = []

    class FakeResponse:
        def __init__(self, text):
            self.text = text

    class FakeModels:
        def generate_content(self, model, contents, config):
            calls.append(
                {
                    "model": model,
                    "contents": contents,
                    "temperature": config.temperature,
                    "system_instruction": config.system_instruction,
                    "max_output_tokens": config.max_output_tokens,
                }
            )
            return FakeResponse(responses[len(calls) - 1])

    class FakeClient:
        models = FakeModels()

    return FakeClient(), calls


# -- _strip_json_fences / _parse_practice_json -------------------------------


def test_strip_json_fences_removes_a_json_labeled_fence():
    wrapped = "```json\n[1, 2, 3]\n```"
    assert _strip_json_fences(wrapped) == "[1, 2, 3]"


def test_strip_json_fences_removes_a_bare_fence():
    wrapped = "```\n[1, 2, 3]\n```"
    assert _strip_json_fences(wrapped) == "[1, 2, 3]"


def test_strip_json_fences_leaves_unfenced_text_alone():
    assert _strip_json_fences("[1, 2, 3]") == "[1, 2, 3]"


def test_parse_practice_json_accepts_well_formed_input():
    result = _parse_practice_json(json.dumps(_valid_questions(10)), 10)
    assert len(result) == 10
    for q in result:
        assert set(q.keys()) == {"question", "options", "correctIndex", "explanation"}
        assert len(q["options"]) == 4
        assert 0 <= q["correctIndex"] < 4


def test_parse_practice_json_handles_a_fenced_response_end_to_end():
    wrapped = "```json\n" + json.dumps(_valid_questions(3)) + "\n```"
    result = _parse_practice_json(wrapped, 3)
    assert len(result) == 3


def test_parse_practice_json_rejects_wrong_question_count():
    with pytest.raises(ValueError, match="exactly 5"):
        _parse_practice_json(json.dumps(_valid_questions(3)), 5)


def test_parse_practice_json_rejects_wrong_option_count():
    bad = [dict(_valid_questions(1)[0], options=["A", "B"])]
    with pytest.raises(ValueError, match="4 options"):
        _parse_practice_json(json.dumps(bad), 1)


def test_parse_practice_json_rejects_out_of_range_correct_index():
    bad = [dict(_valid_questions(1)[0], correctIndex=7)]
    with pytest.raises(ValueError, match="correctIndex"):
        _parse_practice_json(json.dumps(bad), 1)


def test_parse_practice_json_rejects_a_non_array_top_level():
    with pytest.raises(ValueError, match="array"):
        _parse_practice_json(json.dumps({"not": "a list"}), 1)


def test_parse_practice_json_rejects_missing_keys():
    bad = [{"question": "Q?", "options": ["A", "B", "C", "D"]}]
    with pytest.raises(KeyError):
        _parse_practice_json(json.dumps(bad), 1)


def test_parse_practice_json_raises_on_plain_garbage():
    with pytest.raises(json.JSONDecodeError):
        _parse_practice_json("not json at all", 1)


# -- fallback bank ------------------------------------------------------------


@pytest.mark.parametrize("difficulty", DIFFICULTIES)
def test_fallback_bank_has_at_least_five_questions_per_difficulty(difficulty):
    assert len(practice._FALLBACK_BANK[difficulty]) >= 5


@pytest.mark.parametrize("difficulty", DIFFICULTIES)
def test_fallback_questions_shape_is_valid(difficulty):
    questions = _fallback_questions(difficulty, 5)
    assert len(questions) == 5
    for q in questions:
        assert set(q.keys()) == {"question", "options", "correctIndex", "explanation"}
        assert len(q["options"]) == 4
        assert 0 <= q["correctIndex"] < 4


def test_fallback_questions_samples_without_replacement_when_enough_available():
    questions = _fallback_questions("easy", 5)
    texts = [q["question"] for q in questions]
    assert len(texts) == len(set(texts))  # no duplicates


def test_fallback_questions_falls_back_to_sampling_with_replacement_beyond_bank_size():
    bank_size = len(practice._FALLBACK_BANK["easy"])
    # Ask for more than the bank holds -- must not raise, and must still
    # return exactly the requested count (num_questions maxes at 15).
    questions = _fallback_questions("easy", min(15, bank_size + 3))
    assert len(questions) == min(15, bank_size + 3)


def test_fallback_questions_returns_independent_copies():
    questions = _fallback_questions("medium", 5)
    questions[0]["question"] = "mutated"
    assert practice._FALLBACK_BANK["medium"][0]["question"] != "mutated"


# -- generate_practice_questions: input validation ---------------------------


def test_generate_practice_questions_rejects_unknown_difficulty():
    with pytest.raises(ValueError, match="difficulty"):
        generate_practice_questions("impossible", 5)


@pytest.mark.parametrize("n", [0, 16, -1])
def test_generate_practice_questions_rejects_out_of_range_count(n):
    with pytest.raises(ValueError, match="num_questions"):
        generate_practice_questions("easy", n)


# -- generate_practice_questions: Gemini path (mocked) -----------------------


def test_generate_practice_questions_uses_gemini_when_it_succeeds(monkeypatch):
    fake_client, calls = _fake_client([json.dumps(_valid_questions(7))])
    monkeypatch.setattr(practice, "_get_gemini_client", lambda: fake_client)

    result = generate_practice_questions("medium", 7)

    assert len(result) == 7
    assert len(calls) == 1  # no retry needed
    assert "GATE" in calls[0]["system_instruction"]


def test_generate_practice_questions_prompt_reflects_requested_difficulty(monkeypatch):
    fake_client, calls = _fake_client([json.dumps(_valid_questions(3))])
    monkeypatch.setattr(practice, "_get_gemini_client", lambda: fake_client)

    generate_practice_questions("hard", 3)

    assert "HARD" in calls[0]["system_instruction"]


def test_generate_practice_questions_retries_once_on_unparseable_first_response(monkeypatch):
    fake_client, calls = _fake_client(["not json at all, oops", json.dumps(_valid_questions(5))])
    monkeypatch.setattr(practice, "_get_gemini_client", lambda: fake_client)

    result = generate_practice_questions("easy", 5)

    assert len(result) == 5
    assert len(calls) == 2
    assert calls[1]["temperature"] == 0.0
    assert "previous response could not be parsed" in calls[1]["contents"]


# -- generate_practice_questions: fallback path (Gemini fails outright) ------


def test_generate_practice_questions_falls_back_when_gemini_client_construction_fails(monkeypatch):
    def boom():
        raise RuntimeError("GEMINI_API_KEY is not set")

    monkeypatch.setattr(practice, "_get_gemini_client", boom)

    result = generate_practice_questions("easy", 6)

    assert len(result) == 6
    for q in result:
        assert set(q.keys()) == {"question", "options", "correctIndex", "explanation"}


def test_generate_practice_questions_falls_back_when_both_gemini_attempts_are_malformed(monkeypatch):
    fake_client, calls = _fake_client(["garbage one", "garbage two"])
    monkeypatch.setattr(practice, "_get_gemini_client", lambda: fake_client)

    result = generate_practice_questions("hard", 4)

    assert len(result) == 4
    assert len(calls) == 2  # both Gemini attempts were tried before falling back


def test_generate_practice_questions_falls_back_without_a_key(monkeypatch):
    # End-to-end version: no mocking of _get_gemini_client's internals,
    # exercises the real missing-key failure path.
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    result = generate_practice_questions("medium", 5)

    assert len(result) == 5
