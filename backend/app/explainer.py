"""Plain-English, one-sentence explanations of a single DebugStep.

Two ways to get a sentence, tried in order:

1. **Gemini** (`google-genai`, model below), when `GEMINI_API_KEY` is
   set and the call succeeds -- genuinely natural language, and able to
   read intent a template can't ("the 10% discount branch").
2. **A deterministic, template-based generator**, used whenever the
   Gemini call fails for *any* reason (missing/wrong key, network
   error, rate limit, timeout, ...). It's grounded in the same step
   data -- actual variable values, the real condition text -- so it
   still reads as specific rather than generic, it's just less fluent.

Explanations are cached by the content of the request (which step,
which prior variable snapshot), so re-visiting a step while stepping
back and forth through a trace never re-generates -- and never re-calls
the API -- for something already explained.
"""

from __future__ import annotations

import hashlib
import json
import os
import re

from dotenv import load_dotenv
from google import genai
from google.genai import types

# Populates os.environ from backend/.env (GEMINI_API_KEY=...) if present.
# Never overrides a variable already set in the real environment, and is
# a no-op if there's no .env file at all.
load_dotenv()

# Checked live against the API on 2026-08-27 (see project chat history) --
# gemini-1.5-flash has been retired. "-latest" tracks Google's current
# lightweight/fast production model without pinning a version that will
# itself eventually go stale.
_GEMINI_MODEL = "gemini-flash-lite-latest"

_SYSTEM_PROMPT = (
    "You are a debugger assistant. Given one executed step of a small "
    "procedural-SQL debugger, write exactly one natural, plain-English "
    "sentence explaining what happened and why, grounded in the actual "
    "statement and variable values provided. Do not restate the raw code "
    "verbatim and do not use generic filler like 'a statement was "
    "executed'. If you can infer what a value represents (e.g. a "
    "percentage, a total), you may say so. Respond with only the "
    "sentence -- no quotes, no preamble, no markdown."
)

_COMPARISON_PHRASES = {
    ">": "exceeded",
    "<": "was less than",
    "!=": "was not equal to",
    "=": "equaled",
}

_cache: dict[str, dict] = {}


def _get_gemini_client() -> genai.Client:
    # Read the key at call time (not once at import) so a fixed/renamed
    # env var takes effect on the next call without needing to touch any
    # cached client object -- restarting the server is still required
    # for a real .env edit to be picked up at all, same as any env var.
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not set")
    return genai.Client(api_key=api_key)


def _cache_key(step: dict, previous_variables: dict | None) -> str:
    payload = {"step": step, "previousVariables": previous_variables}
    return hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode()).hexdigest()


# -- Gemini-backed generation --------------------------------------------


def _build_prompt(step: dict, previous_variables: dict | None) -> str:
    lines = [
        f"Line {step.get('line')}: {step.get('statementText')}",
        f"Node type: {step.get('nodeType')}",
    ]

    branch = step.get("branch")
    if branch:
        lines.append(
            f"Condition `{branch.get('condition')}` evaluated to "
            f"{branch.get('result')}; branch taken: {branch.get('path')}."
        )

    loop = step.get("loop")
    if loop:
        lines.append(
            f"Loop condition `{loop.get('condition')}` evaluated to "
            f"{loop.get('result')} on iteration {loop.get('iteration')}."
        )

    cursor = step.get("cursor")
    if cursor:
        current_row = cursor.get("currentRow")
        if current_row is not None:
            row_desc = f"current row (index {cursor.get('rowIndex')}): {current_row!r}"
        elif step.get("nodeType") == "FetchCursorNode":
            # currentRow is None on a FETCH specifically because it ran
            # past the last row -- distinct from DECLARE/OPEN/CLOSE,
            # where "no row" just means "not applicable right now".
            row_desc = "no row -- cursor exhausted, this FETCH found nothing"
        else:
            row_desc = "no current row yet"
        lines.append(f"Cursor `{cursor.get('name')}` state: {row_desc} (hasMore={cursor.get('hasMore')}).")

    table = step.get("table")
    if table:
        lines.append(
            f"Table `{table.get('name')}` operation: {table.get('operation')}, "
            f"{table.get('rowsAffected')} row(s) affected. Current rows: {table.get('rows')!r}."
        )

    error = step.get("error")
    if error:
        handler = error.get("handler")
        handler_desc = "no handler caught it (unhandled)" if handler == "unhandled" else f"caught by the {handler}"
        lines.append(
            f"IMPORTANT -- this step triggered the {error.get('condition')} condition: "
            f"{error.get('message')}; {handler_desc}. Describe this handler/error event as "
            "the primary thing that happened in this step, not as an ordinary successful "
            "assignment or fetch."
        )

    lines.append("Variables after this step:")
    for name, entry in (step.get("variables") or {}).items():
        marker = " (just changed)" if entry.get("changed") else ""
        lines.append(f"  {name} = {entry.get('value')!r} ({entry.get('type')}){marker}")

    if previous_variables:
        lines.append("Variables just before this step:")
        for name, entry in previous_variables.items():
            lines.append(f"  {name} = {entry.get('value')!r}")

    lines.append("\nExplain in one sentence what this step did and why.")
    return "\n".join(lines)


def generate_gemini_explanation(step: dict, previous_variables: dict | None) -> str:
    """Ask Gemini for the sentence. Raises on any failure (missing/wrong
    key, network, rate limit, empty response, ...) -- callers are
    expected to catch and fall back to `generate_template_explanation`."""
    client = _get_gemini_client()
    response = client.models.generate_content(
        model=_GEMINI_MODEL,
        contents=_build_prompt(step, previous_variables),
        config=types.GenerateContentConfig(
            system_instruction=_SYSTEM_PROMPT,
            temperature=0.4,
            max_output_tokens=200,  # one short sentence -- no need for a long budget
        ),
    )
    text = (response.text or "").strip()
    if not text:
        raise RuntimeError("Gemini returned no text content")
    return text


# -- free-form "Ask AI" -----------------------------------------------------
#
# A separate feature from the automatic per-step explanation above: the user
# types an arbitrary question about the current execution state (e.g. "why
# did it take the else branch", "what would happen if quantity was 0") and
# Gemini answers it grounded in the full procedure source plus the current
# step's line and variable state. No template fallback here -- an open-ended
# question has no sensible deterministic answer, so a failure is surfaced to
# the caller as an error instead of a fabricated response. Reuses the same
# `_get_gemini_client()` / `_GEMINI_MODEL` wiring as the per-step explainer;
# not cached, since each question is answered fresh per the spec.

_ASK_SYSTEM_PROMPT = (
    "You are a debugger assistant helping a student understand a stored "
    "procedure they are stepping through. You are given the full source "
    "code, the current line and variable state, and a free-form question "
    "about the current execution. Answer clearly and specifically, "
    "referencing the actual condition, values, or code involved -- never "
    "give a generic answer that could apply to any procedure. If the "
    "question poses a hypothetical (e.g. 'what if x was 0'), reason "
    "through it step by step using the code's actual logic. Keep the "
    "answer concise -- a few sentences at most, no markdown."
)


def _build_ask_prompt(code: str, step: dict, question: str) -> str:
    lines = [
        "Full procedure source code:",
        "```sql",
        code,
        "```",
        "",
        f"Current execution position -- line {step.get('line')}: {step.get('statementText')}",
        f"Node type: {step.get('nodeType')}",
    ]

    branch = step.get("branch")
    if branch:
        lines.append(
            f"Condition `{branch.get('condition')}` evaluated to "
            f"{branch.get('result')}; branch taken: {branch.get('path')}."
        )

    loop = step.get("loop")
    if loop:
        lines.append(
            f"Loop condition `{loop.get('condition')}` evaluated to "
            f"{loop.get('result')} on iteration {loop.get('iteration')}."
        )

    lines.append("Current variable state:")
    for name, entry in (step.get("variables") or {}).items():
        lines.append(f"  {name} = {entry.get('value')!r} ({entry.get('type')})")

    table = step.get("table")
    if table:
        lines.append(
            f"Table `{table.get('name')}` operation: {table.get('operation')}, "
            f"{table.get('rowsAffected')} row(s) affected. Current rows: {table.get('rows')!r}."
        )

    lines.append("")
    lines.append(f"Question: {question}")
    return "\n".join(lines)


def answer_question(code: str, step: dict, question: str) -> str:
    """Ask Gemini the user's free-form question about the current debug
    state. Raises on any failure (missing/wrong key, network, rate limit,
    empty response, ...) -- callers are expected to catch this and show a
    graceful error, since there's no template fallback for an open-ended
    question."""
    client = _get_gemini_client()
    response = client.models.generate_content(
        model=_GEMINI_MODEL,
        contents=_build_ask_prompt(code, step, question),
        config=types.GenerateContentConfig(
            system_instruction=_ASK_SYSTEM_PROMPT,
            temperature=0.4,
            max_output_tokens=400,
        ),
    )
    text = (response.text or "").strip()
    if not text:
        raise RuntimeError("Gemini returned no text content")
    return text


# -- deterministic fallback ------------------------------------------------


def _format_value(entry: dict | None) -> str:
    if entry is None or entry.get("value") is None:
        return "unset"
    value = entry.get("value")
    if entry.get("type") == "string":
        return f"'{value}'"
    return str(value)


def _describe_condition(condition_text: str, variables: dict) -> str:
    """Best-effort natural phrasing of a `LEFT OP RIGHT` condition,
    substituting the left operand's live value when it's a known
    variable (e.g. "total (120) exceeded 100")."""
    match = re.match(r"^(.+?)\s*(>|<|!=|=)\s*(.+)$", condition_text)
    if not match:
        return f"`{condition_text}`"
    left, op, right = (group.strip() for group in match.groups())
    phrase = _COMPARISON_PHRASES.get(op, op)
    left_entry = variables.get(left)
    left_text = f"{left} ({_format_value(left_entry)})" if left_entry is not None else left
    return f"{left_text} {phrase} {right}"


def _first_changed_variable(variables: dict) -> tuple[str, dict] | None:
    for name, entry in variables.items():
        if entry.get("changed"):
            return name, entry
    return None


def generate_template_explanation(step: dict, previous_variables: dict | None) -> str:
    """Deterministic, no-network fallback. Always succeeds."""
    node_type = step.get("nodeType")
    variables = step.get("variables") or {}

    if node_type == "DeclareStatement":
        changed = _first_changed_variable(variables)
        if changed:
            name, entry = changed
            return f"Declared `{name}` and initialized it to {_format_value(entry)}."
        return f"Declared a variable ({step.get('statementText', '')})."

    if node_type == "SetStatement":
        changed = _first_changed_variable(variables)
        if changed:
            name, entry = changed
            before = (previous_variables or {}).get(name)
            before_text = f" (was {_format_value(before)})" if before is not None else ""
            rhs = step.get("statementText", "").split("=", 1)[-1].strip().rstrip(";").strip()
            return f"Set `{name}` to {_format_value(entry)}{before_text} by evaluating `{rhs}`."
        return f"Updated a variable ({step.get('statementText', '')})."

    if node_type == "IfStatement":
        branch = step.get("branch") or {}
        description = _describe_condition(branch.get("condition", ""), variables)
        path = branch.get("path")
        if path == "then":
            return f"Checked whether {description}; it did, so the THEN branch ran."
        if path == "else":
            return f"Checked whether {description}; it didn't, so the ELSE branch ran."
        return f"Checked whether {description}; it didn't, and there was no ELSE branch to run."

    if node_type == "WhileStatement":
        loop = step.get("loop") or {}
        description = _describe_condition(loop.get("condition", ""), variables)
        if loop.get("result"):
            return f"Checked whether {description} (iteration {loop.get('iteration')}); it did, so the loop body ran again."
        return f"Checked whether {description}; it didn't, so the loop exited."

    if node_type == "LoopStatement":
        # LOOP has no boolean condition of its own (unlike WHILE), so
        # `_describe_condition` -- built for a `LEFT OP RIGHT` comparison
        # -- doesn't apply here; `loop.condition` is just the literal
        # "LOOP"/"LOOP <label>" placeholder text (see
        # interpreter.py's own "LOOP / LEAVE" section).
        loop = step.get("loop") or {}
        return f"Started iteration {loop.get('iteration')} of the LOOP -- it repeats until a LEAVE is executed."

    if node_type == "LeaveStatement":
        label = (step.get("statementText") or "").removeprefix("LEAVE").strip().rstrip(";").strip()
        target = f"the loop labeled '{label}'" if label else "the current loop"
        return f"Executed LEAVE, exiting {target} and resuming with whatever statement follows it."

    if node_type == "CaseStatement":
        # branch.path is "when-<N>" / "else" / "none" here, not
        # IfStatement's "then"/"else"/"none" -- _describe_condition isn't
        # used (it's built for a `LEFT OP RIGHT` comparison; a CASE's own
        # `condition` is just the operand text or the literal "CASE",
        # neither of which matches that shape).
        branch = step.get("branch") or {}
        path = branch.get("path") or ""
        condition_text = branch.get("condition", "CASE")
        if path.startswith("when-"):
            which = int(path.split("-", 1)[1]) + 1
            return f"Evaluated {condition_text} against each WHEN in order; WHEN #{which} matched, so that branch ran."
        if path == "else":
            return f"Evaluated {condition_text} against each WHEN in order; none matched, so the ELSE branch ran."
        return f"Evaluated {condition_text} against each WHEN in order; none matched, and there was no ELSE branch to run."

    if node_type == "CreateTableStatement":
        table = step.get("table") or {}
        columns = ", ".join(table.get("columns") or [])
        return f"Created table `{table.get('name')}` with columns {columns}."

    if node_type == "InsertStatement":
        table = step.get("table") or {}
        row = table.get("row") or {}
        row_desc = ", ".join(f"{k}={v!r}" for k, v in row.items())
        return f"Inserted a new row into `{table.get('name')}` ({row_desc})."

    if node_type == "UpdateStatement":
        table = step.get("table") or {}
        return f"Updated {table.get('rowsAffected', 0)} row(s) in `{table.get('name')}`."

    if node_type == "DeleteStatement":
        table = step.get("table") or {}
        return f"Deleted {table.get('rowsAffected', 0)} row(s) from `{table.get('name')}`."

    return f"Executed line {step.get('line')}: `{step.get('statementText', '')}`."


# -- orchestrator: cache -> Gemini -> template fallback ---------------------


def explain_step(step: dict, previous_variables: dict | None) -> dict:
    """Return {"explanation", "source", "cached"} for one DebugStep.

    `source` is "gemini" or "template" depending on which path produced
    the sentence; `cached` is True when this exact (step, previous
    variables) pair was already explained.
    """
    key = _cache_key(step, previous_variables)
    cached = _cache.get(key)
    if cached is not None:
        return {**cached, "cached": True}

    try:
        explanation = generate_gemini_explanation(step, previous_variables)
        source = "gemini"
    except Exception:
        # Any failure at all (missing/wrong key, network, rate limit,
        # timeout, an empty response, ...) degrades to the deterministic
        # generator rather than breaking the debugger's explanation
        # panel -- this endpoint should never surface a 502 for what's
        # ultimately a nice-to-have feature.
        explanation = generate_template_explanation(step, previous_variables)
        source = "template"

    result = {"explanation": explanation, "source": source}
    _cache[key] = result
    return {**result, "cached": False}
