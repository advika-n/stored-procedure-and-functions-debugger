# HANDOFF.md

**A snapshot of exactly where the project stands right now.** Fully rewritten at the end
of every session, not appended to — it's a status board, not a diary. Session-by-session
history lives in `git log` and `PROMPT_LOG.md`; stable project facts live in `CLAUDE.md`
(`docs/features.md`/`docs/schema.md` for design detail).

**Last updated**: 2026-09-17, end of the bug-fix session that fixed both bugs the prior
(testing-infrastructure) session found and deliberately did not fix — see "Bugs fixed
this session" below. A real, scoped interpreter behavior change (unlike the prior
session), but a narrow one: golden traces for all 18 existing samples are unchanged
(verified), since neither fix's trigger condition (arithmetic on a `None` operand; a
genuinely empty procedure body) occurs in any of them.

---

## Feature status

Unchanged this session (a bug-fix phase, not a feature phase — see below).

**Mandatory (5/5 done)**: Day/Night Mode · Developed By (photo still a placeholder SVG,
text is real) · Help tab · Learn tab (**placeholder content** — draft concept text,
`YOUR_VIDEO_ID_HERE`, placeholder references, all badge-flagged — needs real material
before submission) · Download (PDF/DOCX/Text export).

**Innovation (3/4 done, 1 dropped)**: SQL Anti-Pattern Advisor · Side-by-Side Run
Comparison · Variable Timeline · Live Parameter Tuning — **dropped**, don't pick back up
without a fresh scoping prompt.

**Tier 1 (4/4 done)**: Breakpoints + Continue/Restart · `CALL` support · Call Stack
panel.

**Extras beyond original scope (all done)**: Text-to-Speech · Test-Case Runner ·
Extended Static Analysis Warnings (advisor: 6→10 checks across all phases) · Function
calls in expressions · CASE statement · LOOP/LEAVE · User-created tables (CREATE TABLE /
INSERT / UPDATE / DELETE).

---

## Testing infrastructure (built two sessions ago — see `CLAUDE.md` §6 for the mechanics)

- **Golden-trace regression harness** (`backend/app/tests/test_golden_traces.py` +
  `backend/app/tests/golden/*.json`, 18 fixtures, one per built-in sample): runs every
  sample through the REAL `/debug` endpoint and diffs the resulting step trace against a
  checked-in baseline, failing loudly (naming the exact diverging step) on any future
  behavior change. Missing/stale fixtures are hard failures by design (see the module's
  own docstring), not silently skipped or auto-created. **Run this before considering any
  future tokenizer/parser/interpreter-touching phase done.** Re-ran and confirmed
  byte-for-byte unchanged after this session's two bug fixes below (neither fix's
  trigger condition occurs in any of the 18 samples).
- **Property-based tests** (`backend/app/tests/test_property_based.py`, `hypothesis`
  in `requirements.txt`): mutates the 18 real samples (keyword swaps, corrupted
  literals, dropped semicolons, unbalanced BEGIN/END, char-level fuzzing, truncation) and
  checks two invariants across 1000 examples each — never an uncaught exception, and a
  successful run always produces >= 1 step, **both unconditionally now** (the previous
  session's two documented carve-outs for these invariants are exactly the two bugs this
  session fixed — see below; both special-case exclusions have been removed from this
  file's tests, not just left in place unused).
- **Known-bugs tracker** (`backend/app/tests/test_known_bugs.py`): the convention for a
  bug found while testing something else, `xfail(strict=True)` while unfixed. Currently
  empty of unfixed bugs — both bugs it used to track are fixed (see below); the one
  regression test from that era is kept, `xfail` removed, now asserting the fix
  positively.
- **Hand-written grammar edge cases** (`backend/app/tests/test_grammar_edge_cases.py`,
  23 tests): nested/reopened cursors, LEAVE unwinding 50 levels of nested LOOP at once,
  the REAL (not monkeypatched-small) `MAX_LOOP_ITERATIONS`/`MAX_CALL_DEPTH` guards, empty
  procedure bodies (bare and wrapped now produce the same shape — see below), comment-
  like text inside string literals (including a cursor's embedded SELECT round-tripped
  through real SQLite), missing semicolons, mismatched BEGIN/END, and a real, measured
  timing check (9999-iteration loop, 20,001-step trace, ~0.6s through the real endpoint
  — see `docs/schema.md`'s performance table).
- Backend suite: **491 passing, 0 xfailed** (483 passing + 1 xfailed before this
  session's two fixes; net +7 across the fix + its regression coverage, and the one
  xfail is gone since its underlying bug is fixed).

---

## Bugs fixed this session

Both were found (and deliberately left unfixed, per that session's own explicit
instruction) by the testing-infrastructure session described above; this session fixed
both properly, per an explicit follow-up bug-fix prompt.

1. **Arithmetic on a `None`-valued variable used to crash with a raw, unstructured
   `TypeError`.** Fixed: `Interpreter._evaluate_binary` now guards `+ - * /` against a
   `None` operand *before* handing both sides to Python's own operators, raising a
   clean `InterpreterError` ("...has no value yet -- it was declared but never assigned
   (or is an OUT parameter never SET on this code path)") instead — the same structured
   `{"stage": "interpret", "message", "line"}` shape every other runtime error in this
   app already produces, confirmed against the real `/debug` endpoint (400, not 500).
   The `/` operator's pre-existing DIVISION_BY_ZERO check is unaffected and still fires
   first when the divisor is genuinely `0` (not `None`) — regression-tested explicitly
   so the new guard can never mask it. Regression tests: `test_known_bugs.py` (the
   original minimal repro, un-xfailed) and `test_interpreter.py` (each operator
   individually, the DIVISION_BY_ZERO-still-wins case, and a real-endpoint 400 check).
2. **A bare (wrapper-less) procedure with a genuinely empty body used to produce a
   zero-length step trace**, inconsistent with a wrapped empty body's single synthetic
   entry step. Fixed: `Interpreter.run` now gives this exact case (bare form AND an
   empty body — a bare body with at least one statement is completely unaffected) a
   synthetic placeholder step of its own (`nodeType: "Procedure"`, statement text
   `"(empty procedure body)"`), so both forms now produce exactly one step for an empty
   body. Checked whether the frontend actually hits this path first: `DebuggerPage.jsx`
   already guards every `steps`-dependent render behind `hasSteps = steps.length > 0`
   (shows "No steps yet" otherwise), so this was never a live frontend crash risk — no
   frontend change was needed. Regression tests in `test_grammar_edge_cases.py` cover
   both the bare-empty and wrapped-empty cases producing the same shape.

---

## Immediate next steps

1. Get a real student photo (Developed By) and a real video + references (Learn tab) —
   the only two pieces of placeholder content left before submission.
2. SQL Anti-Pattern Advisor still doesn't analyze a `ProgramNode` AST at all (a
   `CALL`-based multi-procedure source always shows "no issues"); Download/Compare have
   never been exercised against one either. Pre-existing, unrelated to recent sessions.
3. User-created tables (`Interpreter.tables`) are entirely simulated and never
   queryable from a cursor's embedded SELECT (which still only ever sees the fixed
   `products` demo table) — a real, separate piece of design work if a future phase
   wants the two to interoperate.

---

## Live gotchas

(Unchanged this session — no frontend/browser work happened; kept for the next session
that does.)

- **`backend/data/debug_history.db` needs manual cleanup after any live-verification
  session** — it auto-rotates at 50 rows but real `/debug` calls during manual testing
  still show up; delete test-run rows afterward (direct SQL is fine if no backend is
  left running) so the user's real history stays clean. (This session's own ad-hoc
  hand-verification scripts — run outside pytest, so NOT covered by `conftest.py`'s
  per-test DB isolation — left a few stray rows; cleaned up back to the established
  baseline, max id 94, 12 rows.)
- **A stray, non-listening process can hold a port's `Bound` reservation on Windows**
  without actually accepting connections (`Get-NetTCPConnection` shows `Bound`, not
  `Listen`; `curl` gets connection refused) — seen on port 8000 in a recent session (a
  leftover system-Python process, not one that session started). Per "leave
  pre-existing processes alone," the fix was NOT to kill it: run a throwaway backend on
  a different port instead, temporarily repoint `frontend/vite.config.js`'s proxy
  targets there for the verification session only, then revert that file back exactly
  (confirm via `git diff` showing no net change) once done. Vite itself may only bind
  `[::1]` (IPv6), not `127.0.0.1` — use `http://[::1]:5173`, not `127.0.0.1`, for
  curl/fetch checks against it.
- **Chrome's DevTools HTTP endpoint requires `PUT`, not `GET`, for `/json/new`** in
  current Chrome versions (`GET` returns a plain-text "Using unsafe HTTP verb" body, not
  JSON) — a raw-CDP driver script needs `{ method: 'PUT' }` on that one call.
- **Check port usage before binding anything** for live verification — a naive
  `startsWith('/debug')` API-route check in a throwaway proxy script will also swallow
  the frontend's own `/debugger` route; match exact-or-slash-prefixed instead.
- Mobile nav overflows horizontally at ~400px width (pre-existing, `.top-nav` has no
  `flex-wrap`) — cosmetic, not blocking, don't need to re-verify it isn't worse unless
  you touch the nav.
