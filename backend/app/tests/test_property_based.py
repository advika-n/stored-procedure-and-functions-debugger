"""Property-based tests (Hypothesis) targeting the tokenizer/parser/
interpreter pipeline as a whole.

Per this phase's own instruction, inputs are built by MUTATING the
existing, real sample procedures (`frontend/src/samples.js`, loaded via
`_frontend_samples.load_samples` -- the same 18 real, hand-written
procedures the golden-trace harness in `test_golden_traces.py` already
runs) rather than generating SQL-like text from scratch: swapping a
keyword, corrupting a numeric literal, dropping a semicolon, deleting/
duplicating a character, unbalancing a BEGIN/END, or truncating the
source outright. This has a much higher signal-to-effort ratio for this
specific grammar than a from-scratch SQL generator would -- a mutated
REAL procedure is already "almost valid," which is exactly the shape of
input most likely to slip past one specific parser/interpreter check
while still reaching deep into the pipeline (a from-scratch generator
mostly produces either trivially-rejected garbage or has to re-encode
this grammar's own rules to produce anything meaningful at all).

Two invariants, per this phase's own scope:

  (a) The interpreter never crashes with an uncaught exception on
      malformed input -- tokenize/parse/interpret either succeeds, or
      raises one of exactly three KNOWN, structured error types
      (TokenizerError/ParserError/InterpreterError -- the same three
      app/main.py's own `/debug` handler catches and turns into a
      structured 400 response). Anything else escaping is a real bug:
      a stack trace reaching the user instead of a clean error.
  (b) A run that completes successfully produces a step trace of
      length >= 1, with NO exceptions. (This invariant used to carve
      out a bare/wrapper-less empty-body procedure, which legitimately
      produced a genuinely empty trace -- see
      `test_grammar_edge_cases.py::test_empty_bare_procedure_body_
      now_gets_a_synthetic_step_too`. That inconsistency was found and
      reported here, then FIXED in a dedicated follow-up bug-fix phase:
      `Interpreter.run` now gives that exact case a synthetic
      placeholder step too, so this invariant holds unconditionally --
      see `HANDOFF.md`/`test_known_bugs.py` for the fix's own
      write-up.)

Any genuine crash Hypothesis finds is reported (see this phase's own
summary), never silently patched here -- these tests exist to surface
problems, not fix them. One already was: arithmetic on a DECLAREd-but-
never-assigned (`None`-valued) variable used to raise Python's own raw,
unstructured `TypeError` rather than a clean `InterpreterError` --
FIXED in the same dedicated follow-up bug-fix phase mentioned above
(a `None`-operand guard in `Interpreter._evaluate_binary` now raises a
clean, structured `InterpreterError` instead), so invariant (a) below
no longer needs to carve it out either -- see `test_known_bugs.py`.
"""

from __future__ import annotations

import re

from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from app import demo_db
from app.interpreter import InterpreterError, run
from app.parser import ParserError, parse
from app.tests._frontend_samples import load_samples
from app.tokenizer import TokenizerError, tokenize

_SAMPLES = load_samples()
_SAMPLE_CODES = [s["code"] for s in _SAMPLES]

# -- mutation operators -------------------------------------------------
# Each is a pure function of (code, *drawn params) -> mutated code
# string. Every one degrades gracefully to "return code unchanged" when
# there's nothing of the relevant shape to mutate (e.g. no semicolon in
# an already-truncated string) -- a Hypothesis strategy must never raise
# while generating, only the test body may.

_KEYWORD_SWAP_POOL = [
    "IF", "WHILE", "END", "THEN", "ELSE", "BEGIN", "DECLARE", "SET",
    "LOOP", "LEAVE", "CASE", "WHEN", "RETURN", "CALL", "CREATE",
    "PROCEDURE", "FUNCTION", "TABLE", "INSERT", "UPDATE", "DELETE",
]
_SEMICOLON_RE = re.compile(r";")
_NUMBER_RE = re.compile(r"\b\d+(?:\.\d+)?\b")
_WORD_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")


def _drop_semicolon(code: str, index: int) -> str:
    positions = [m.start() for m in _SEMICOLON_RE.finditer(code)]
    if not positions:
        return code
    pos = positions[index % len(positions)]
    return code[:pos] + code[pos + 1 :]


def _swap_keyword(code: str, index: int, replacement: str) -> str:
    matches = [m for m in _WORD_RE.finditer(code) if m.group().upper() in _KEYWORD_SWAP_POOL]
    if not matches:
        return code
    match = matches[index % len(matches)]
    return code[: match.start()] + replacement + code[match.end() :]


def _corrupt_number_literal(code: str, index: int, delta: int) -> str:
    matches = list(_NUMBER_RE.finditer(code))
    if not matches:
        return code
    match = matches[index % len(matches)]
    try:
        corrupted = str(int(float(match.group())) + delta)
    except ValueError:
        corrupted = match.group()
    return code[: match.start()] + corrupted + code[match.end() :]


def _unbalance_begin_end(code: str, index: int) -> str:
    matches = [m for m in _WORD_RE.finditer(code) if m.group().upper() in ("BEGIN", "END")]
    if not matches:
        return code
    match = matches[index % len(matches)]
    return code[: match.start()] + code[match.end() :]


def _delete_char(code: str, index: int) -> str:
    if not code:
        return code
    pos = index % len(code)
    return code[:pos] + code[pos + 1 :]


def _duplicate_char(code: str, index: int) -> str:
    if not code:
        return code
    pos = index % len(code)
    return code[:pos] + code[pos] + code[pos:]


def _truncate(code: str, fraction: float) -> str:
    return code[: int(len(code) * fraction)]


@st.composite
def _mutated_sample_code(draw) -> str:
    code = draw(st.sampled_from(_SAMPLE_CODES))
    operator = draw(
        st.sampled_from(
            [
                "drop_semicolon",
                "swap_keyword",
                "corrupt_number",
                "unbalance_begin_end",
                "delete_char",
                "duplicate_char",
                "truncate",
            ]
        )
    )
    index = draw(st.integers(min_value=0, max_value=2000))

    if operator == "drop_semicolon":
        return _drop_semicolon(code, index)
    if operator == "swap_keyword":
        replacement = draw(st.sampled_from(_KEYWORD_SWAP_POOL))
        return _swap_keyword(code, index, replacement)
    if operator == "corrupt_number":
        delta = draw(st.integers(min_value=-10_000, max_value=10_000))
        return _corrupt_number_literal(code, index, delta)
    if operator == "unbalance_begin_end":
        return _unbalance_begin_end(code, index)
    if operator == "delete_char":
        return _delete_char(code, index)
    if operator == "duplicate_char":
        return _duplicate_char(code, index)
    return _truncate(code, draw(st.floats(min_value=0.0, max_value=1.0)))


# -- the pipeline under test, with main.py's own error-handling mirrored -

_KNOWN_ERRORS = (TokenizerError, ParserError, InterpreterError)


def _run_pipeline(code: str) -> dict:
    """Mirrors app/main.py's `/debug` handler's own tokenize -> parse ->
    run sequence and error handling exactly (see that module), so this
    test exercises the real contract the endpoint promises callers, not
    a hypothetical one. Returns one of:

        {"status": "ok", "ast": ..., "steps": [...]}
        {"status": "known_error", "error": <TokenizerError|ParserError|InterpreterError>}
        {"status": "CRASH", "error": <anything else>}
    """
    conn = None
    try:
        tokens = tokenize(code)
        ast = parse(tokens)
        conn = demo_db.create_demo_connection()
        steps = run(ast, {}, db_connection=conn)
        return {"status": "ok", "ast": ast, "steps": steps}
    except _KNOWN_ERRORS as exc:
        return {"status": "known_error", "error": exc}
    except Exception as exc:  # noqa: BLE001 -- deliberately broad: this IS the crash detector
        return {"status": "CRASH", "error": exc}
    finally:
        if conn is not None:
            conn.close()


# -- invariant (a): never an uncaught exception --------------------------


@settings(
    max_examples=1000,
    deadline=None,  # a mutated WHILE/LOOP can legitimately run up to MAX_LOOP_ITERATIONS
    suppress_health_check=[HealthCheck.too_slow],
)
@given(code=_mutated_sample_code())
def test_mutated_sample_never_crashes_with_an_uncaught_exception(code):
    result = _run_pipeline(code)
    if result["status"] != "CRASH":
        return
    error = result["error"]
    raise AssertionError(
        "A mutated sample crashed the interpreter with an UNSTRUCTURED exception "
        f"({type(error).__name__}: {error}) instead of a known TokenizerError/"
        f"ParserError/InterpreterError. Offending code:\n{code!r}"
    ) from error


# -- invariant (b): a successful run's trace always has length >= 1 ------


@settings(
    max_examples=1000,
    deadline=None,
    suppress_health_check=[HealthCheck.too_slow],
)
@given(code=_mutated_sample_code())
def test_successful_mutated_run_has_a_nonempty_trace(code):
    result = _run_pipeline(code)
    if result["status"] != "ok":
        return  # invariant (a) covers the crash/known-error cases separately
    assert len(result["steps"]) >= 1, (
        f"A successfully-run mutated sample produced ZERO steps -- AST type "
        f"{result['ast'].get('type')!r}. Offending code:\n{code!r}"
    )
