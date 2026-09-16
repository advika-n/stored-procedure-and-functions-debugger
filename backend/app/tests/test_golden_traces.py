"""Golden-output regression harness -- formalizes the manual "run every
built-in sample through the real pipeline and eyeball the result" sweep
several recent phases have done by hand before committing (see
PROMPT_LOG.md's phase entries), into an automated pytest check with a
real, checked-in, versioned baseline per sample.

For every sample in `frontend/src/samples.js` (loaded via
`_frontend_samples.load_samples`, never hand-copied), this posts to the
REAL `/debug` endpoint (the same one the frontend calls) and compares
the resulting `steps` array against a golden fixture committed at
`backend/app/tests/golden/<name>.json`. Any change to the tokenizer,
parser, interpreter, or the `/debug` route itself that alters a single
sample's step-by-step trace fails this test loudly, naming exactly
which sample and which step first diverged -- a safety net every future
phase should run against before considering itself done, not just this
one.

**Fixtures are data, not something this test invents on the fly.** A
missing fixture is a hard failure (not a silent auto-create), so a new
sample added to `samples.js` with no golden yet is impossible to merge
by accident. To create or deliberately update a fixture (a new sample,
or a reviewed, intentional behavior change), run:

    UPDATE_GOLDENS=1 .venv/Scripts/python.exe -m pytest -q app/tests/test_golden_traces.py

then diff/review the resulting `golden/*.json` changes by hand (`git
diff`) before committing them -- this test file never decides for you
whether a divergence is correct, only whether one happened.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.tests._frontend_samples import load_samples

client = TestClient(app)

GOLDEN_DIR = Path(__file__).parent / "golden"

# Opt-in only -- see module docstring. Any non-empty, non-"0" value
# turns it on, matching common CI-flag convention.
_UPDATE = os.environ.get("UPDATE_GOLDENS", "").strip() not in ("", "0")


def _golden_path(name: str) -> Path:
    return GOLDEN_DIR / f"{name}.json"


def _write_golden(name: str, steps: list) -> None:
    GOLDEN_DIR.mkdir(parents=True, exist_ok=True)
    # Stable, diffable formatting -- sorted keys, real newlines -- so a
    # deliberate fixture update produces a clean, reviewable git diff
    # rather than a one-line JSON blob changing wholesale.
    _golden_path(name).write_text(json.dumps(steps, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _first_divergence(name: str, actual: list, expected: list) -> str | None:
    """None if `actual` == `expected`; otherwise a specific, human-
    readable description of exactly where they first differ -- "fails
    loudly with a diff", not just an opaque assertion failure over a
    potentially 50+-step list."""
    if len(actual) != len(expected):
        return (
            f"'{name}': trace length diverged from its golden fixture -- "
            f"expected {len(expected)} step(s), got {len(actual)}."
        )
    for index, (actual_step, expected_step) in enumerate(zip(actual, expected)):
        if actual_step != expected_step:
            step_number = actual_step.get("stepNumber", index + 1)
            return (
                f"'{name}': trace diverged from its golden fixture at step {step_number} "
                f"(index {index}).\n"
                f"  expected: {json.dumps(expected_step, sort_keys=True)}\n"
                f"  actual:   {json.dumps(actual_step, sort_keys=True)}"
            )
    return None


@pytest.mark.parametrize("sample", load_samples(), ids=lambda s: s["name"])
def test_sample_trace_matches_golden_fixture(sample):
    response = client.post(
        "/debug",
        json={"code": sample["code"], "params": {}, "name": sample["name"]},
    )
    assert response.status_code == 200, (
        f"'{sample['name']}' failed to run at all through /debug: {response.json()}"
    )
    actual_steps = response.json()["steps"]

    golden_path = _golden_path(sample["name"])
    if not golden_path.exists():
        if _UPDATE:
            _write_golden(sample["name"], actual_steps)
            return
        pytest.fail(
            f"No golden fixture exists for '{sample['name']}' at {golden_path}. This is a "
            "hard failure by design (see this module's docstring) -- a new sample must get "
            "a reviewed baseline, not an auto-created one. Run with UPDATE_GOLDENS=1 to "
            "create it, review the new file, then commit it."
        )

    if _UPDATE:
        # Deliberate, explicit regeneration -- see module docstring.
        _write_golden(sample["name"], actual_steps)
        return

    expected_steps = json.loads(golden_path.read_text(encoding="utf-8"))
    divergence = _first_divergence(sample["name"], actual_steps, expected_steps)
    assert divergence is None, divergence


def test_every_sample_has_exactly_one_golden_fixture():
    """Catches the OTHER failure mode a per-sample parametrized test
    can't: a stale fixture left behind for a sample that no longer
    exists in samples.js (renamed/removed), which would otherwise sit
    there silently forever, never run, never noticed."""
    sample_names = {sample["name"] for sample in load_samples()}
    fixture_names = {path.stem for path in GOLDEN_DIR.glob("*.json")}
    stale = fixture_names - sample_names
    assert not stale, (
        f"Golden fixture(s) {sorted(stale)} exist in {GOLDEN_DIR} but no longer match any "
        "sample in samples.js -- delete the stale fixture file(s) (the sample was probably "
        "renamed or removed)."
    )
