import pytest

from app import explainer
from app.explainer import explain_step, generate_template_explanation


@pytest.fixture(autouse=True)
def clear_cache():
    """Each test uses its own step content, but clear the module-level
    cache anyway so tests never depend on execution order."""
    explainer._cache.clear()
    yield
    explainer._cache.clear()


# -- template generator: deterministic, no network involved -----------------


def test_declare_explanation_reads_the_initial_value():
    step = {
        "line": 1,
        "nodeType": "DeclareStatement",
        "statementText": "DECLARE total NUMBER DEFAULT 0;",
        "variables": {"total": {"value": 0, "type": "number", "changed": True}},
    }
    text = generate_template_explanation(step, None)
    assert "total" in text
    assert "0" in text


def test_set_explanation_reads_before_and_after_values():
    step = {
        "line": 3,
        "nodeType": "SetStatement",
        "statementText": "SET total = price * quantity;",
        "variables": {
            "price": {"value": 20, "type": "number", "changed": False},
            "quantity": {"value": 6, "type": "number", "changed": False},
            "total": {"value": 120, "type": "number", "changed": True},
        },
    }
    previous = {"total": {"value": 0, "type": "number", "changed": True}}
    text = generate_template_explanation(step, previous)
    assert "total" in text
    assert "120" in text
    assert "0" in text  # the previous value
    assert "price * quantity" in text  # the actual expression, not generic text


def test_if_then_explanation_reflects_condition_and_live_value():
    step = {
        "line": 4,
        "nodeType": "IfStatement",
        "statementText": "IF total > 100 THEN",
        "variables": {"total": {"value": 120, "type": "number", "changed": False}},
        "branch": {"condition": "total > 100", "result": True, "path": "then"},
    }
    text = generate_template_explanation(step, None)
    assert "120" in text  # the live value substituted in
    assert "100" in text
    assert "THEN" in text
    assert "ELSE" not in text


def test_if_else_explanation_says_else_ran():
    step = {
        "line": 4,
        "nodeType": "IfStatement",
        "statementText": "IF total > 100 THEN",
        "variables": {"total": {"value": 20, "type": "number", "changed": False}},
        "branch": {"condition": "total > 100", "result": False, "path": "else"},
    }
    text = generate_template_explanation(step, None)
    assert "ELSE" in text
    assert "20" in text


def test_while_loop_explanation_mentions_iteration():
    step = {
        "line": 1,
        "nodeType": "WhileStatement",
        "statementText": "WHILE count < 3 DO",
        "variables": {"count": {"value": 1, "type": "number", "changed": False}},
        "loop": {"condition": "count < 3", "result": True, "iteration": 2},
    }
    text = generate_template_explanation(step, None)
    assert "count" in text
    assert "1" in text
    assert "loop body ran again" in text


def test_explanations_are_not_generic_boilerplate():
    # Two different SET steps should produce two different sentences --
    # if the generator were falling back to generic text this would fail.
    step_a = {
        "line": 1,
        "nodeType": "SetStatement",
        "statementText": "SET x = 1;",
        "variables": {"x": {"value": 1, "type": "number", "changed": True}},
    }
    step_b = {
        "line": 2,
        "nodeType": "SetStatement",
        "statementText": "SET y = 2;",
        "variables": {"y": {"value": 2, "type": "number", "changed": True}},
    }
    assert generate_template_explanation(step_a, None) != generate_template_explanation(step_b, None)


# -- orchestrator: cache + fallback behavior (Gemini path mocked) -----------


def test_explain_step_uses_gemini_when_it_succeeds(monkeypatch):
    monkeypatch.setattr(explainer, "generate_gemini_explanation", lambda step, prev: "Gemini's sentence.")
    step = {"line": 1, "nodeType": "SetStatement", "statementText": "SET x = 1;", "variables": {}}

    result = explain_step(step, None)

    assert result == {"explanation": "Gemini's sentence.", "source": "gemini", "cached": False}


def test_explain_step_falls_back_to_template_when_gemini_fails(monkeypatch):
    def boom(step, prev):
        raise RuntimeError("no credentials")

    monkeypatch.setattr(explainer, "generate_gemini_explanation", boom)
    step = {
        "line": 1,
        "nodeType": "DeclareStatement",
        "statementText": "DECLARE x NUMBER DEFAULT 1;",
        "variables": {"x": {"value": 1, "type": "number", "changed": True}},
    }

    result = explain_step(step, None)

    assert result["source"] == "template"
    assert result["cached"] is False
    assert "x" in result["explanation"]


def test_explain_step_caches_and_does_not_call_the_generator_again(monkeypatch):
    calls = []

    def fake_gemini(step, prev):
        calls.append(1)
        return "Generated once."

    monkeypatch.setattr(explainer, "generate_gemini_explanation", fake_gemini)
    step = {"line": 1, "nodeType": "SetStatement", "statementText": "SET x = 1;", "variables": {}}

    first = explain_step(step, None)
    second = explain_step(step, None)

    assert first["cached"] is False
    assert second["cached"] is True
    assert second["explanation"] == first["explanation"]
    assert len(calls) == 1  # the generator ran exactly once, not twice


def test_explain_step_treats_different_previous_variables_as_different_cache_entries(monkeypatch):
    monkeypatch.setattr(explainer, "generate_gemini_explanation", lambda step, prev: f"prev={prev}")
    step = {"line": 1, "nodeType": "SetStatement", "statementText": "SET x = 1;", "variables": {}}

    result_a = explain_step(step, {"x": {"value": 0}})
    result_b = explain_step(step, {"x": {"value": 99}})

    assert result_a["explanation"] != result_b["explanation"]
    assert result_a["cached"] is False
    assert result_b["cached"] is False


# -- generate_gemini_explanation itself: the missing/wrong-key path ---------
# (no mocking of generate_gemini_explanation here -- this exercises the
# real function, proving the fallback trigger works, not just that
# explain_step correctly reacts to *some* exception.)


def test_generate_gemini_explanation_raises_when_key_is_missing(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    step = {"line": 1, "nodeType": "SetStatement", "statementText": "SET x = 1;", "variables": {}}

    with pytest.raises(RuntimeError, match="GEMINI_API_KEY"):
        explainer.generate_gemini_explanation(step, None)


def test_explain_step_falls_back_to_template_when_key_is_missing(monkeypatch):
    # End-to-end version of the above: simulates exactly what "rename the
    # env var to something wrong" does, through the real orchestrator.
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    step = {
        "line": 1,
        "nodeType": "DeclareStatement",
        "statementText": "DECLARE x NUMBER DEFAULT 1;",
        "variables": {"x": {"value": 1, "type": "number", "changed": True}},
    }

    result = explain_step(step, None)

    assert result["source"] == "template"
    assert "x" in result["explanation"]


# -- Ask AI: answer_question -------------------------------------------------
# Separate feature from the per-step explanation above: a free-form question
# about the current step, answered fresh (no cache) with the full source as
# context. Reuses the same _get_gemini_client()/_GEMINI_MODEL wiring, so the
# missing-key failure mode is identical.


def test_answer_question_prompt_includes_source_step_and_question(monkeypatch):
    captured = {}

    class FakeResponse:
        text = "Because total exceeded 100."

    class FakeModels:
        def generate_content(self, model, contents, config):
            captured["model"] = model
            captured["contents"] = contents
            captured["system_instruction"] = config.system_instruction
            return FakeResponse()

    class FakeClient:
        models = FakeModels()

    monkeypatch.setattr(explainer, "_get_gemini_client", lambda: FakeClient())

    code = "CREATE PROCEDURE p() BEGIN IF total > 100 THEN ... END IF; END;"
    step = {
        "line": 4,
        "nodeType": "IfStatement",
        "statementText": "IF total > 100 THEN",
        "variables": {"total": {"value": 120, "type": "number", "changed": False}},
        "branch": {"condition": "total > 100", "result": True, "path": "then"},
    }

    answer = explainer.answer_question(code, step, "why did it take this branch")

    assert answer == "Because total exceeded 100."
    assert "total > 100" in captured["contents"]
    assert "120" in captured["contents"]
    assert "why did it take this branch" in captured["contents"]
    assert code in captured["contents"]


def test_answer_question_raises_when_key_is_missing(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    step = {"line": 1, "nodeType": "SetStatement", "statementText": "SET x = 1;", "variables": {}}

    with pytest.raises(RuntimeError, match="GEMINI_API_KEY"):
        explainer.answer_question("SET x = 1;", step, "what does this do")
