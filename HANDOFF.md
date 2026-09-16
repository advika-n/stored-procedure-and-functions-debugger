# HANDOFF.md

**A snapshot of exactly where the project stands right now.** Fully rewritten at the end
of every session, not appended to — it's a status board, not a diary. Session-by-session
history lives in `git log` and `PROMPT_LOG.md`; stable project facts live in `CLAUDE.md`
(`docs/features.md`/`docs/schema.md` for design detail).

**Last updated**: 2026-09-14, end of the testing-infrastructure session (golden-trace
harness, Hypothesis property tests, hand-written grammar edge cases — no parser/
interpreter/frontend behavior changed this session, per its own explicit scope).

---

## Feature status

Unchanged this session (testing infrastructure only — see below, not a feature phase).

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

## Testing infrastructure (new this session — see `CLAUDE.md` §6 for the mechanics)

- **Golden-trace regression harness** (`backend/app/tests/test_golden_traces.py` +
  `backend/app/tests/golden/*.json`, 18 fixtures, one per built-in sample): runs every
  sample through the REAL `/debug` endpoint and diffs the resulting step trace against a
  checked-in baseline, failing loudly (naming the exact diverging step) on any future
  behavior change. Missing/stale fixtures are hard failures by design (see the module's
  own docstring), not silently skipped or auto-created. **Run this before considering any
  future tokenizer/parser/interpreter-touching phase done.**
- **Property-based tests** (`backend/app/tests/test_property_based.py`, `hypothesis`
  added to `requirements.txt`): mutates the 18 real samples (keyword swaps, corrupted
  literals, dropped semicolons, unbalanced BEGIN/END, char-level fuzzing, truncation) and
  checks two invariants across 1000 examples each — never an uncaught exception, and a
  successful run always produces >= 1 step (with one hand-verified, documented
  exception — see next section). **Found one real bug** — see below.
- **Known, reported-not-fixed bugs** (`backend/app/tests/test_known_bugs.py`,
  `xfail(strict=True)` so a future fix flips it loudly): see "Bugs found this session,
  NOT fixed" below.
- **Hand-written grammar edge cases** (`backend/app/tests/test_grammar_edge_cases.py`,
  22 tests): nested/reopened cursors, LEAVE unwinding 50 levels of nested LOOP at once,
  the REAL (not monkeypatched-small) `MAX_LOOP_ITERATIONS`/`MAX_CALL_DEPTH` guards, empty
  procedure bodies (bare vs. wrapped — see finding below), comment-like text inside
  string literals (including a cursor's embedded SELECT round-tripped through real
  SQLite), missing semicolons, mismatched BEGIN/END, and a real, measured timing check
  (9999-iteration loop, 20,001-step trace, ~0.6s through the real endpoint — see
  `docs/schema.md`'s performance table).
- Backend suite: **483 passing + 1 xfailed** (440 before this session; +44 new tests
  across the four files above). `.hypothesis/` (Hypothesis's local example-cache dir)
  added to `backend/.gitignore`.

---

## Bugs found this session, NOT fixed (per this session's own explicit instruction)

1. **Arithmetic on a `None`-valued variable crashes with a raw, unstructured
   `TypeError` instead of the app's own structured error.** `Interpreter._evaluate_
   binary`'s `+ - * /` never check for a `None` operand before handing both sides
   straight to Python's own operators. Minimal repro (no mutation, no CALL, nothing
   exotic needed):
   ```
   DECLARE x NUMBER;
   SET x = x * 2;
   ```
   `x` starts at `None` (a DECLAREd variable with no DEFAULT — an established,
   intentional convention elsewhere in this interpreter). Confirmed directly against
   the real `/debug` endpoint: this returns a raw **500 Internal Server Error** with no
   body at all, not the `{"stage", "message", "line"}` structured error every other
   failure mode in this app produces. Real-world reachable with zero mutation/fuzzing —
   any procedure that does arithmetic on an unset local or an OUT param never SET on
   some code path hits this. Comparisons (`= < > !=`) do NOT crash this way (`None ==
   2` is simply `False` in Python) — only the four arithmetic operators do. Tracked as
   an `xfail(strict=True)` regression in `test_known_bugs.py` (will loudly flip to a
   failure the moment a future phase fixes it — remove the `xfail` then). **Worth its
   own follow-up phase** if you want it fixed: the natural fix is a `None`-operand
   check in `_evaluate_binary` raising a clear `InterpreterError` instead.

2. **A bare (wrapper-less) procedure with a genuinely empty body produces a
   ZERO-length step trace**, not the `>= 1` you might otherwise expect from every other
   procedure shape. Confirmed directly: `POST /debug` with `code: ""` (or whitespace-
   only) returns `200 {"steps": []}`. This is NOT a crash and arguably not even wrong —
   a wrapped `CREATE PROCEDURE ... BEGIN END` DOES get a synthetic entry step even with
   an empty body (see `interpreter.py`'s "Functions" section), so this is specific to
   the bare/legacy form having no such step at all. Not fixed (this session's scope was
   testing infra, not behavior), but flagged because a frontend that assumes
   `steps[0]` always exists (e.g. jumping straight to a first step after Debug) could
   misbehave on this exact input — not verified against the frontend one way or the
   other this session, just flagged as a real, hand-confirmed edge case worth knowing
   about. Documented (not just discovered and dropped) in `test_grammar_edge_cases.py::
   test_empty_bare_procedure_body_produces_zero_steps`.

---

## Immediate next steps

1. Decide whether bug #1 above (arithmetic on `None` crashing with a raw 500) is worth
   a dedicated follow-up phase — it's a real, easily-reachable gap in the "every error
   is structured" contract this app otherwise holds throughout.
2. Commit this session's work — clean, isolated, no behavior changes (tests + a new
   `hypothesis` dependency + doc updates only).
3. Get a real student photo (Developed By) and a real video + references (Learn tab) —
   the only two pieces of placeholder content left before submission.
4. SQL Anti-Pattern Advisor still doesn't analyze a `ProgramNode` AST at all (a
   `CALL`-based multi-procedure source always shows "no issues"); Download/Compare have
   never been exercised against one either. Pre-existing, unrelated to recent sessions.
5. User-created tables (`Interpreter.tables`) are entirely simulated and never
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
