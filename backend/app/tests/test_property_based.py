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
      length >= 1 -- **with one hand-verified, documented exception**:
      a bare (wrapper-less) procedure whose body is empty (see
      `test_grammar_edge_cases.py::test_empty_bare_procedure_body_
      produces_zero_steps`) legitimately parses AND runs successfully
      with a genuinely empty trace (`steps == []`) -- there is no
      synthetic "entry" step for the bare form the way a wrapped
      `ProcedureNode`/`FunctionNode` always gets one (see
      `interpreter.py`'s own "Functions" section). This was hand-
      verified directly against the real endpoint before writing this
      test, not assumed -- see this phase's own report for the full
      finding (flagged separately, not silently special-cased away).
      Mutation trivially reaches this case (e.g. `truncate` cutting a
      bare sample down to nothing, or enough `delete_char` calls
      hollowing one out) -- excluding it here means invariant (b) tests
      something real (a WRAPPED definition, or an unwrapped one that
      still has statements, never silently drops to zero steps),
      instead of being falsified by already-understood behavior on the
      very first run.

Any genuine crash Hypothesis finds is reported (see this phase's own
summary), never silently patched here -- these tests exist to surface
problems, not fix them. One already was: arithmetic on a DECLAREd-but-
never-assigned (`None`-valued) variable raises Python's own raw,
unstructured `TypeError` rather than a clean `InterpreterError` --
narrowly excluded from invariant (a) below by its exact message shape
(not "every TypeError"), and separately tracked as a minimal,
`xfail(strict=True)` regression in `test_known_bugs.py`, so this
general fuzz test keeps doing its real job (surfacing NEW crashes)
instead of permanently re-reporting the same already-known one.
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

# Matches Python's own message shape for e.g. `None * 2` --
# "unsupported operand type(s) for *: 'NoneType' and 'int'" -- the
# EXACT ALREADY-FOUND-AND-REPORTED bug in `Interpreter._evaluate_binary`
# (arithmetic on a DECLAREd-but-never-assigned/never-SET variable; see
# `test_known_bugs.py` for the full write-up and a minimal, tracked
# `xfail(strict=True)` regression). Excluded here narrowly -- by this
# EXACT message shape, not "every TypeError" -- so this general fuzz
# test keeps doing its real job (surfacing NEW, not-yet-known crashes)
# instead of permanently failing on one already-diagnosed root cause
# every run reaches by a different random mutation path.
_KNOWN_NONE_ARITHMETIC_BUG_RE = re.compile(
    r"unsupported operand type\(s\) for [-+*/]: .*NoneType"
)


def _is_the_known_none_arithmetic_bug(error: Exception) -> bool:
    return isinstance(error, TypeError) and bool(_KNOWN_NONE_ARITHMETIC_BUG_RE.search(str(error)))


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
    if _is_the_known_none_arithmetic_bug(error):
        return  # already found, reported, and tracked -- see test_known_bugs.py
    raise AssertionError(
        "A mutated sample crashed the interpreter with an UNSTRUCTURED exception "
        f"({type(error).__name__}: {error}) instead of a known TokenizerError/"
        f"ParserError/InterpreterError. Offending code:\n{code!r}"
    ) from error


# -- invariant (b): a successful run's trace has length >= 1, except the -
# one hand-verified, documented exception (see module docstring) --------


def _is_the_documented_zero_step_exception(ast: dict) -> bool:
    """A bare (wrapper-less) `Procedure` with a genuinely empty body is
    the ONE known, hand-verified way to legitimately reach a
    zero-length trace -- see the module docstring and
    `test_grammar_edge_cases.py`. Every other AST shape
    (`ProcedureNode`/`FunctionNode`/`ProgramNode`, or any bare
    `Procedure` with at least one statement) always produces >= 1 step."""
    return ast.get("type") == "Procedure" and ast.get("body") == []


@settings(
    max_examples=1000,
    deadline=None,
    suppress_health_check=[HealthCheck.too_slow],
)
@given(code=_mutated_sample_code())
def test_successful_mutated_run_has_a_nonempty_trace_unless_the_body_is_genuinely_empty(code):
    result = _run_pipeline(code)
    if result["status"] != "ok":
        return  # invariant (a) covers the crash/known-error cases separately
    if _is_the_documented_zero_step_exception(result["ast"]):
        return
    assert len(result["steps"]) >= 1, (
        f"A successfully-run mutated sample produced ZERO steps despite a non-empty/"
        f"wrapped AST ({result['ast'].get('type')!r}) -- this is a genuinely new case, "
        f"not the documented bare-empty-body exception. Offending code:\n{code!r}"
    )
