"""Gemini-backed conceptual quiz generation for the standalone /quiz page.

Distinct from the per-step explanations in app/explainer.py (which
narrate one already-executed DebugStep) -- this generates a self-
contained 5-question multiple-choice quiz, in one of two flavors:

  - "theory": general questions about stored procedures/functions,
    control flow (IF/WHILE), cursors, and exception handling -- the
    same concepts the Theory page covers, not tied to any code.
  - "procedure": questions specific to one currently-loaded procedure's
    actual source (e.g. "what would `total` be if `quantity` were 0"),
    grounded in that exact logic rather than generic theory.

Reuses app/explainer.py's Gemini client wiring (_get_gemini_client,
_GEMINI_MODEL) rather than duplicating the client setup.

Gemini is instructed to return ONLY a JSON array (no markdown fences,
no preamble) of exactly 5 questions, each with exactly 4 options, a
0-based `correctIndex`, and a short explanation. Parsing is defensive:
an accidental ```json fence (or bare ``` fence) is stripped before
json.loads, and a parse failure triggers exactly one retry with a
stricter, lower-temperature prompt before the caller sees an error --
in practice Gemini complies with the raw-JSON instruction most of the
time but not always, and a single retry is cheap insurance against
that rather than something the frontend should ever need to know about.
"""

from __future__ import annotations

import json
import re

from google.genai import types

from app.explainer import _GEMINI_MODEL, _get_gemini_client

_JSON_SHAPE_INSTRUCTIONS = (
    "Respond with ONLY a valid JSON array -- no markdown code fences, no "
    "```json wrapper, no preamble or commentary before or after it. "
    "Output must be the raw JSON array and nothing else. Shape:\n"
    "[\n"
    "  {\n"
    '    "question": "...",\n'
    '    "options": ["...", "...", "...", "..."],\n'
    '    "correctIndex": 0,\n'
    '    "explanation": "..."\n'
    "  }\n"
    "]\n"
    "`correctIndex` is a 0-based index into `options` (0, 1, 2, or 3). "
    "Return exactly 5 question objects, each with exactly 4 options and "
    "exactly one correct answer."
)

_THEORY_SYSTEM_PROMPT = (
    "You write multiple-choice quizzes for a student learning stored "
    "procedures and functions in procedural SQL: control flow (IF/ELSE, "
    "WHILE loops), cursors (DECLARE/OPEN/FETCH/CLOSE, %FOUND/%NOTFOUND), "
    "exception handling (DECLARE CONTINUE HANDLER, NOT_FOUND, "
    "DIVISION_BY_ZERO), IN/OUT/INOUT parameters, and the difference "
    "between procedures and functions (RETURN values, RETURNS type). "
    "Write 5 general conceptual questions covering a mix of these "
    "topics -- test understanding of the concepts themselves, not any "
    "specific piece of code. Vary the topics across the 5 questions "
    "rather than clustering on one. " + _JSON_SHAPE_INSTRUCTIONS
)

_THEORY_PROMPT = "Generate the quiz now."

_PROCEDURE_SYSTEM_PROMPT = (
    "You write multiple-choice quizzes about ONE SPECIFIC stored "
    "procedure or function's logic, given its full source code below. "
    "Write 5 questions that require actually tracing through THIS "
    "code's control flow and variable assignments to answer -- for "
    "example 'what would `total` be after this runs with price=200', "
    "'which branch executes when quantity is 0', or 'what does this "
    "loop's exit condition depend on'. Reference the procedure's real "
    "variable and parameter names and real logic. Do not ask generic "
    "theory questions that could apply to any procedure -- every "
    "question must depend on the actual code provided. " + _JSON_SHAPE_INSTRUCTIONS
)


def _build_procedure_prompt(code: str) -> str:
    return (
        "Here is the procedure/function source code to write the quiz "
        f"about:\n\n```sql\n{code}\n```\n\n"
        "Generate the quiz now, with every question grounded in this exact code."
    )


_FENCE_RE = re.compile(r"^```(?:json)?\s*(.*?)\s*```$", re.DOTALL)


def _strip_json_fences(text: str) -> str:
    """Strip an accidental ```json ... ``` or bare ``` ... ``` wrapper.
    Gemini is explicitly told not to do this, but it does often enough
    in practice that the parser has to tolerate it rather than assume
    the instruction was followed."""
    stripped = text.strip()
    match = _FENCE_RE.match(stripped)
    return match.group(1).strip() if match else stripped


def _parse_quiz_json(text: str) -> list[dict]:
    """Parse and validate Gemini's response into exactly 5 well-formed
    question dicts. Raises ValueError/json.JSONDecodeError/TypeError on
    anything malformed -- callers decide whether to retry or give up."""
    data = json.loads(_strip_json_fences(text))
    if not isinstance(data, list):
        raise ValueError("Expected a JSON array of questions")
    if len(data) != 5:
        raise ValueError(f"Expected exactly 5 questions, got {len(data)}")

    questions = []
    for item in data:
        if not isinstance(item, dict):
            raise ValueError("Each question must be a JSON object")
        options = item["options"]
        correct_index = item["correctIndex"]
        if not isinstance(options, list) or len(options) != 4:
            raise ValueError("Each question must have exactly 4 options")
        if not isinstance(correct_index, int) or not (0 <= correct_index < 4):
            raise ValueError("correctIndex must be an integer from 0 to 3")
        questions.append(
            {
                "question": str(item["question"]),
                "options": [str(option) for option in options],
                "correctIndex": correct_index,
                "explanation": str(item["explanation"]),
            }
        )
    return questions


def _call_gemini(prompt: str, system_instruction: str, temperature: float) -> str:
    client = _get_gemini_client()
    response = client.models.generate_content(
        model=_GEMINI_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            system_instruction=system_instruction,
            temperature=temperature,
            max_output_tokens=2500,  # 5 questions + options + explanations
        ),
    )
    text = (response.text or "").strip()
    if not text:
        raise RuntimeError("Gemini returned no text content")
    return text


def generate_quiz(source: str, code: str | None = None) -> list[dict]:
    """Return a list of exactly 5 question dicts. Raises on any failure
    (missing/wrong key, network, an unparseable response even after the
    retry, ...) -- callers (see app/main.py) turn that into a 502."""
    if source == "procedure":
        if not code or not code.strip():
            raise ValueError("code is required when source is 'procedure'")
        system_instruction = _PROCEDURE_SYSTEM_PROMPT
        prompt = _build_procedure_prompt(code)
    elif source == "theory":
        system_instruction = _THEORY_SYSTEM_PROMPT
        prompt = _THEORY_PROMPT
    else:
        raise ValueError(f"Unknown quiz source {source!r}")

    text = _call_gemini(prompt, system_instruction, temperature=0.8)
    try:
        return _parse_quiz_json(text)
    except (json.JSONDecodeError, ValueError, KeyError, TypeError):
        # One retry, with an explicit note about the previous failure and
        # temperature 0 for the most literal, least creative compliance.
        stricter_prompt = (
            prompt
            + "\n\nIMPORTANT: your previous response could not be parsed "
            "as JSON. Respond again with ONLY the raw JSON array -- no "
            "markdown code fences, no ```json, no explanation before or "
            "after it, and no other text whatsoever."
        )
        text = _call_gemini(stricter_prompt, system_instruction, temperature=0.0)
        return _parse_quiz_json(text)  # let this one raise if it still fails
