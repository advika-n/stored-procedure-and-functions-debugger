"""Known, REPORTED-NOT-FIXED bugs, found while building this phase's
testing infrastructure (golden-trace harness / Hypothesis property
tests / hand-written grammar edge cases). Per this phase's own explicit
instruction ("if you find a real bug, stop, flag it clearly, and don't
silently fix it as a side effect -- report it separately from the
testing work"), NONE of these are patched here or anywhere else in this
phase's changes -- this file exists purely to track them as concrete,
minimal, reproducible `xfail(strict=True)` regressions:

  - `strict=True` means this test SUITE will loudly tell you the moment
    someone (a future phase) actually fixes the underlying bug (an
    xfail that unexpectedly PASSES becomes a hard failure, "XPASS"),
    which is exactly the signal a fix should produce -- come update
    this file (remove the xfail) as part of that fix.
  - Until then, `pytest`'s summary shows these as `xfail`, not a normal
    failure, so the rest of the suite (this phase's own golden-trace/
    property-based/grammar-edge-case tests included) stays a reliable
    green safety net for genuinely NEW regressions, instead of being
    permanently red over an already-known, already-reported issue.

See this phase's own written report (handed to the user, and
summarized in `HANDOFF.md`) for the full write-up of each finding.
"""

from __future__ import annotations

import pytest

from app.tests.test_property_based import _run_pipeline

# -- Bug 1: arithmetic on an unset (None) variable crashes with a raw, --
# unstructured TypeError instead of the app's own structured error -----
#
# Found by the Hypothesis property test (`test_property_based.py`) via
# mutation, then reduced by hand to this minimal, entirely ordinary
# 2-line procedure that needs NO mutation at all to reproduce: a
# DECLAREd variable with no DEFAULT starts at `None` (a well-established,
# intentional convention -- see interpreter.py's own `_type_name`, which
# maps it to `"null"`), and `Interpreter._evaluate_binary`'s `+ - * /`
# operators never check for that before handing both operands straight
# to Python's own operators. `None * 2` (or `+`/`-`/`/`) raises Python's
# raw `TypeError: unsupported operand type(s) for *: 'NoneType' and
# 'int'` -- NOT one of this app's three structured error types
# (TokenizerError/ParserError/InterpreterError), so it is NOT caught by
# `app/main.py`'s `/debug` handler's `except InterpreterError` clause,
# and reaches the real endpoint as a raw 500 Internal Server Error with
# no `{"stage", "message", "line"}` body at all -- confirmed directly
# against the real endpoint (`TestClient`), not just at the interpreter
# level, before writing this test.
#
# Real-world reachability: this needs no mutation, no CALL chain, no
# cursor, nothing exotic -- ANY procedure that uses a DECLAREd-but-never-
# assigned variable (or an OUT parameter never SET before some caller
# reads it back, or -- the path Hypothesis actually found first -- an OUT
# parameter left unset because a mutated/miswritten branch never runs
# its SET at all) in an arithmetic expression hits this. Comparisons
# (`= < > !=`) do NOT crash this way (`None == 2` is simply `False` in
# Python) -- only the four arithmetic operators do.
_NONE_ARITHMETIC_CODE = """\
DECLARE x NUMBER;
SET x = x * 2;
"""


@pytest.mark.xfail(
    reason=(
        "Interpreter._evaluate_binary's arithmetic operators (+ - * /) don't guard "
        "against a None operand before handing both sides to Python's own operator, "
        "so a DECLAREd-but-never-assigned variable used in arithmetic crashes with a "
        "raw, unstructured TypeError instead of a clean InterpreterError -- reported, "
        "not fixed, per this phase's own scope. See this module's docstring."
    ),
    strict=True,
)
def test_arithmetic_on_an_unset_variable_should_be_a_structured_error_not_a_crash():
    result = _run_pipeline(_NONE_ARITHMETIC_CODE)
    assert result["status"] != "CRASH", (
        f"Expected a structured InterpreterError, got an unstructured crash instead: "
        f"{type(result.get('error')).__name__}: {result.get('error')}"
    )
