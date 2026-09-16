r"""Loads the frontend's built-in sample library (`frontend/src/samples.js`)
into Python, for backend tests that want to exercise the REAL, full
sample set through the real tokenizer -> parser -> interpreter pipeline
-- see `test_golden_traces.py` and `test_property_based.py`.

Not a test module itself (no `test_` prefix, so pytest never collects
it) -- a small piece of test-support infrastructure, formalizing the
same "load every sample, run it through the real pipeline" pattern
several recent phases already used as a one-off manual verification
script (see PROMPT_LOG.md), but as a real, importable, reusable piece
of the test suite instead.

`samples.js` is a JS ES module (a `SAMPLES` array of `{name, kind,
description, code}` objects, `code` a backtick template literal) --
there is no Node runtime dependency at pytest time, so this is a small,
precise regex extraction rather than a real JS parse. This is safe
specifically because of two facts about this exact file, not in
general:

  1. `code:` is a stable, literal field-name anchor that appears
     exactly once per entry, immediately before the code block itself.
  2. The SQL-like grammar this app's tokenizer/parser/interpreter
     understands never contains a literal backtick character (see
     `app.tokenizer`'s own token spec -- backtick isn't a token this
     language has at all), so the FIRST backtick after `code: \`` is
     guaranteed to be that entry's own closing backtick, no matter what
     a `description` string earlier in the same entry contains (some
     genuinely do contain backticks around an identifier, e.g.
     ProductPriceTotal's description mentions `` `products` `` --
     `.*?` between `description:` and `code:` skips past those safely,
     since it only needs to find the next LITERAL "code:" text, not
     balance backticks itself).

If `samples.js`'s own shape changes enough to break this (a renamed
field, a restructured entry), `load_samples()` raises loudly (zero
samples parsed) rather than silently returning a wrong or partial list
-- a test built on top of an empty/partial sample list would either
trivially "pass" or fail in a confusing way, neither of which is
acceptable for a regression safety net.
"""

from __future__ import annotations

import re
from pathlib import Path

# backend/app/tests/_frontend_samples.py -> repo root is 3 parents up.
_REPO_ROOT = Path(__file__).resolve().parents[3]
SAMPLES_JS_PATH = _REPO_ROOT / "frontend" / "src" / "samples.js"

_ENTRY_RE = re.compile(
    r"name:\s*'([^']+)',\s*kind:\s*'(PROCEDURE|FUNCTION)',\s*description:.*?code:\s*`(.*?)`,\s*\n\s*\},",
    re.DOTALL,
)


def load_samples() -> list[dict]:
    """Every sample in `frontend/src/samples.js`, as `{"name", "kind",
    "code"}` dicts, in source order. Raises RuntimeError if extraction
    finds zero entries (see module docstring) -- never returns an empty
    list silently."""
    text = SAMPLES_JS_PATH.read_text(encoding="utf-8")
    matches = _ENTRY_RE.findall(text)
    if not matches:
        raise RuntimeError(
            f"No samples could be parsed out of {SAMPLES_JS_PATH} -- its shape may have "
            "changed enough to break _frontend_samples.py's extraction regex. Fix the "
            "regex (or this loader) rather than letting tests silently run against an "
            "empty sample list."
        )
    return [{"name": name, "kind": kind, "code": code} for name, kind, code in matches]
