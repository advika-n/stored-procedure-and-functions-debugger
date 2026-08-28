import json

import pytest

from app import quiz
from app.quiz import _parse_quiz_json, _strip_json_fences, generate_quiz

VALID_QUESTIONS = [
    {
        "question": f"Question {i}?",
        "options": ["A", "B", "C", "D"],
        "correctIndex": i % 4,
        "explanation": f"Because {i}.",
    }
    for i in range(5)
]


def _fake_client(responses):
    """A minimal Gemini client stand-in whose generate_content() returns
    each of `responses` in turn (as .text), one per call -- lets a test
    script "first call returns garbage, second call returns valid JSON"
    without touching the network."""
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
                }
            )
            return FakeResponse(responses[len(calls) - 1])

    class FakeClient:
        models = FakeModels()

    return FakeClient(), calls


# -- _strip_json_fences: tolerating Gemini wrapping the response despite
# being told not to -- this is the specific robustness the task called
# out as worth testing directly, not just assuming instructions worked. --


def test_strip_json_fences_removes_a_json_labeled_fence():
    wrapped = "```json\n[1, 2, 3]\n```"
    assert _strip_json_fences(wrapped) == "[1, 2, 3]"


def test_strip_json_fences_removes_a_bare_fence():
    wrapped = "```\n[1, 2, 3]\n```"
    assert _strip_json_fences(wrapped) == "[1, 2, 3]"


def test_strip_json_fences_leaves_unfenced_text_alone():
    raw = "[1, 2, 3]"
    assert _strip_json_fences(raw) == "[1, 2, 3]"


def test_parse_quiz_json_handles_a_fenced_response_end_to_end():
    wrapped = "```json\n" + json.dumps(VALID_QUESTIONS) + "\n```"
    result = _parse_quiz_json(wrapped)
    assert len(result) == 5
    assert result[0]["question"] == "Question 0?"


# -- _parse_quiz_json: shape validation --------------------------------------


def test_parse_quiz_json_accepts_well_formed_input():
    result = _parse_quiz_json(json.dumps(VALID_QUESTIONS))
    assert len(result) == 5
    for q in result:
        assert set(q.keys()) == {"question", "options", "correctIndex", "explanation"}
        assert len(q["options"]) == 4
        assert 0 <= q["correctIndex"] < 4


def test_parse_quiz_json_rejects_wrong_question_count():
    with pytest.raises(ValueError, match="exactly 5"):
        _parse_quiz_json(json.dumps(VALID_QUESTIONS[:3]))


def test_parse_quiz_json_rejects_wrong_option_count():
    bad = [dict(VALID_QUESTIONS[0], options=["A", "B"])] + VALID_QUESTIONS[1:]
    with pytest.raises(ValueError, match="4 options"):
        _parse_quiz_json(json.dumps(bad))


def test_parse_quiz_json_rejects_out_of_range_correct_index():
    bad = [dict(VALID_QUESTIONS[0], correctIndex=7)] + VALID_QUESTIONS[1:]
    with pytest.raises(ValueError, match="correctIndex"):
        _parse_quiz_json(json.dumps(bad))


def test_parse_quiz_json_rejects_a_non_array_top_level():
    with pytest.raises(ValueError, match="array"):
        _parse_quiz_json(json.dumps({"not": "a list"}))


def test_parse_quiz_json_rejects_missing_keys():
    bad = [{"question": "Q?", "options": ["A", "B", "C", "D"]}] + VALID_QUESTIONS[1:]
    with pytest.raises(KeyError):
        _parse_quiz_json(json.dumps(bad))


def test_parse_quiz_json_raises_on_plain_garbage():
    with pytest.raises(json.JSONDecodeError):
        _parse_quiz_json("not json at all")


# -- generate_quiz: prompt building -------------------------------------------


def test_generate_quiz_theory_prompt_does_not_reference_any_code(monkeypatch):
    fake_client, calls = _fake_client([json.dumps(VALID_QUESTIONS)])
    monkeypatch.setattr(quiz, "_get_gemini_client", lambda: fake_client)

    generate_quiz("theory")

    assert len(calls) == 1
    assert "```sql" not in calls[0]["contents"]


def test_generate_quiz_procedure_prompt_includes_the_actual_source(monkeypatch):
    fake_client, calls = _fake_client([json.dumps(VALID_QUESTIONS)])
    monkeypatch.setattr(quiz, "_get_gemini_client", lambda: fake_client)

    code = "CREATE PROCEDURE ApplyDiscount() BEGIN SET total = price * 0.9; END"
    generate_quiz("procedure", code)

    assert len(calls) == 1
    assert code in calls[0]["contents"]
    assert "ONE SPECIFIC" in calls[0]["system_instruction"]


def test_generate_quiz_procedure_requires_code():
    with pytest.raises(ValueError, match="code is required"):
        generate_quiz("procedure", None)
    with pytest.raises(ValueError, match="code is required"):
        generate_quiz("procedure", "   ")


def test_generate_quiz_rejects_an_unknown_source():
    with pytest.raises(ValueError, match="Unknown quiz source"):
        generate_quiz("nonsense")


# -- generate_quiz: the retry-once-on-parse-failure path ---------------------
# This is the specific robustness the task called out as worth testing
# directly: Gemini's first response is malformed, the second (retry) is
# clean, and generate_quiz should recover transparently.


def test_generate_quiz_retries_once_when_the_first_response_is_unparseable(monkeypatch):
    fake_client, calls = _fake_client(["not json at all, oops", json.dumps(VALID_QUESTIONS)])
    monkeypatch.setattr(quiz, "_get_gemini_client", lambda: fake_client)

    result = generate_quiz("theory")

    assert len(result) == 5
    assert len(calls) == 2  # first call failed to parse, second (retry) succeeded
    assert calls[1]["temperature"] == 0.0  # the stricter retry is low-temperature
    assert "previous response could not be parsed" in calls[1]["contents"]


def test_generate_quiz_recovers_when_the_first_response_is_fenced_and_unparsed_by_mistake(monkeypatch):
    # A more realistic failure mode than total garbage: the first
    # response is *fenced* but with some stray prose Gemini added
    # despite instructions, which _strip_json_fences alone can't save --
    # the retry is what actually recovers here.
    first = "Sure, here is the quiz:\n```json\n" + json.dumps(VALID_QUESTIONS) + "\n```\nHope that helps!"
    fake_client, calls = _fake_client([first, json.dumps(VALID_QUESTIONS)])
    monkeypatch.setattr(quiz, "_get_gemini_client", lambda: fake_client)

    result = generate_quiz("theory")

    assert len(result) == 5
    assert len(calls) == 2


def test_generate_quiz_raises_when_both_attempts_fail(monkeypatch):
    fake_client, calls = _fake_client(["garbage one", "garbage two"])
    monkeypatch.setattr(quiz, "_get_gemini_client", lambda: fake_client)

    with pytest.raises(json.JSONDecodeError):
        generate_quiz("theory")

    assert len(calls) == 2  # both attempts were made before giving up


def test_generate_quiz_succeeds_on_the_first_clean_try_without_retrying(monkeypatch):
    fake_client, calls = _fake_client([json.dumps(VALID_QUESTIONS)])
    monkeypatch.setattr(quiz, "_get_gemini_client", lambda: fake_client)

    result = generate_quiz("theory")

    assert len(result) == 5
    assert len(calls) == 1  # no retry needed
