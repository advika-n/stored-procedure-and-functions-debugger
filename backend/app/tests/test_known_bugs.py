"""Bugs found while building the testing-infrastructure phase (golden-
trace harness / Hypothesis property tests / hand-written grammar edge
cases), reported separately from that phase's own work per its explicit
instruction not to silently fix them as a side effect.

Both bugs originally tracked here have since been FIXED, in a dedicated
follow-up bug-fix phase (see `HANDOFF.md` and `PROMPT_LOG.md` for that
phase's own write-up):

  - Bug 1 (below): arithmetic on a `None`-valued variable crashing with
    a raw, unstructured `TypeError` -- fixed in
    `Interpreter._evaluate_binary` (a `None`-operand guard on `+ - * /`
    that raises a clean, structured `InterpreterError` instead). This
    module's own regression test is kept here, `xfail` REMOVED, so it
    now asserts the fix positively rather than merely "stopped
    crashing" -- see `test_interpreter.py` for the broader set of
    regression tests added alongside the fix (each operator
    individually, plus confirming `/` by zero still reports
    DIVISION_BY_ZERO and not this new guard).
  - Bug 2: a bare (wrapper-less) empty procedure body producing a
    zero-length step trace, inconsistent with a wrapped empty body's
    single synthetic entry step -- fixed in `Interpreter.run`, which
    now gives the bare-empty-body case its own synthetic placeholder
    step too. See `test_grammar_edge_cases.py`'s empty-procedure-body
    tests for the regression coverage (both forms now produce the same
    "exactly 1 step" shape).

This file is kept (rather than deleted) as the project's established
place to track a real bug found while testing something else, and its
`xfail(strict=True)` pattern is still the convention for any FUTURE
bug that gets reported-not-fixed -- see `CLAUDE.md` §6.
"""

from __future__ import annotations

from app.tests.test_property_based import _run_pipeline

# -- Bug 1 (FIXED): arithmetic on an unset (None) variable used to -------
# crash with a raw, unstructured TypeError instead of the app's own -----
# structured error ---------------------------------------------------
#
# Found by the Hypothesis property test (`test_property_based.py`) via
# mutation, then reduced by hand to this minimal, entirely ordinary
# 2-line procedure that needs NO mutation at all to reproduce: a
# DECLAREd variable with no DEFAULT starts at `None` (a well-established,
# intentional convention -- see interpreter.py's own `_type_name`, which
# maps it to `"null"`). Before the fix, `Interpreter._evaluate_binary`'s
# `+ - * /` operators never checked for that before handing both
# operands straight to Python's own operators, so `None * 2` raised
# Python's raw `TypeError: unsupported operand type(s) for *: 'NoneType'
# and 'int'` -- NOT one of this app's three structured error types
# (TokenizerError/ParserError/InterpreterError) -- and reached the real
# `/debug` endpoint as a raw 500 with no `{"stage", "message", "line"}`
# body at all (confirmed directly against the real endpoint via
# `TestClient` before the fix). Now guarded: this exact input produces a
# clean, structured `InterpreterError` instead.
_NONE_ARITHMETIC_CODE = """\
DECLARE x NUMBER;
SET x = x * 2;
"""


def test_arithmetic_on_an_unset_variable_is_now_a_structured_error_not_a_crash():
    result = _run_pipeline(_NONE_ARITHMETIC_CODE)
    assert result["status"] == "known_error", (
        f"Expected a structured InterpreterError (this bug is fixed), got: "
        f"{result['status']} ({type(result.get('error')).__name__}: {result.get('error')})"
    )
    assert "no value yet" in str(result["error"])
