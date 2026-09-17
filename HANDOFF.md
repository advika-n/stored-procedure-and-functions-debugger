# HANDOFF.md

**A snapshot of exactly where the project stands right now.** Fully rewritten at the end
of every session, not appended to — it's a status board, not a diary. Session-by-session
history lives in `git log` and `PROMPT_LOG.md`; stable project facts live in `CLAUDE.md`
(`docs/features.md`/`docs/schema.md` for design detail).

**Last updated**: 2026-09-18, end of the session that added `>=`/`<=`/`<>` comparison
operators (valid everywhere a condition is evaluated — IF/WHILE/CASE) and a new
`SELECT ... INTO` single-row-lookup statement, distinct from both the cursor mechanism and
the standalone-SELECT `SqlStatement` passthrough. Full design rationale: `docs/features.md`'s
"Comparison operators + SELECT...INTO" section; `docs/schema.md`'s `DebugStep` shape gained
one new field (`sql.into`). Backend suite: **552 passing** (up from 505), zero regressions.
Live-verified in-browser, both themes: raw-typed source using all three new operators
(stepped to the final value, hand-checked); the new `LookupOnePlayer` sample's SELECT INTO
found + NOT_FOUND steps, including the new "Assigned: var = value" panel text.

---

## Feature status

**Mandatory (5/5 done)**: Day/Night Mode · Developed By (real photo + name + register
number + Guided By, confirmed via a full functional audit earlier this session — the
"placeholder SVG" gap a previous HANDOFF flagged is resolved, from unrelated prior work) ·
Help tab (accurate for the merged page, confirmed via the same audit) · Learn tab (real
embedded video + real MySQL/Oracle reference citations, confirmed via the same audit — the
`YOUR_VIDEO_ID_HERE`/draft-content gap a previous HANDOFF flagged is also resolved) ·
Download (PDF/DOCX/Text export, all three confirmed to produce valid non-empty files).

**Innovation (3/4 done, 1 dropped)**: SQL Anti-Pattern Advisor · Side-by-Side Run
Comparison · Variable Timeline · Live Parameter Tuning — **dropped**, don't pick back up
without a fresh scoping prompt.

**Tier 1 (4/4 done)**: Breakpoints + Continue/Restart · `CALL` support · Call Stack
panel.

**Extras beyond original scope (all done)**: Text-to-Speech · Test-Case Runner ·
Extended Static Analysis Warnings (advisor: 6→10 checks across all phases) · Function
calls in expressions · CASE statement · LOOP/LEAVE · Persistent user database · Merged
Debugger/SQL Console page + SQL passthrough statements · Comparison operators
`>=`/`<=`/`<>` + `SELECT ... INTO` (this session — see below).

A full functional audit (procedure debugging, plain SQL, merge routing, cross-cutting
persistence, mandatory sections, innovation features, timing, test count) ran at the start
of this session, before either fix — see `PROMPT_LOG.md` for its full pass/fail list. One
finding fed directly into this session's scope: `SELECT ... INTO` didn't exist in the
grammar at all (only `FETCH cursor INTO var` did), and `>=`/`<=`/`<>` were entirely absent
from procedural comparisons (not just a raw-SQL round-trip caveat, the actual documented
grammar). Both are now fixed.

---

## This session's work

Two focused grammar/interpreter fixes, shipped together (the second sample uses the
first's own operators), each independently tested and verified — not a rewrite of
anything, additive to the existing grammar. Full design rationale:
`docs/features.md`'s "Comparison operators + SELECT...INTO" section.

- **Fix 1 — `>=`/`<=`/`<>`**: `app/tokenizer.py` gained `GTE`/`LTE` token patterns (ordered
  BEFORE the bare single-character `OPERATOR` pattern — lexing order matters, or `>=` would
  split into `>` then `=`); `NEQ`'s pattern widened to `!=|<>` (`<>` is simply an alternate
  spelling of `!=` from the tokenizer onward). `app/parser.py`'s `COMPARISON_OPERATORS` set
  gained the three new values — since IF/WHILE/CASE all share the same `_parse_comparison`
  rule and the same `Interpreter._evaluate_binary`, this one change made all three
  constructs accept the new operators with no per-construct code. **Nice side effect**: raw
  SQL passthrough text now round-trips `<=`/`>=`/`<>` correctly too (each is one token now,
  so `_render_raw_query` never splits one across two) — this retroactively fixes a real,
  previously-documented caveat from an earlier session, now corrected in `docs/features.md`.
  **A real bug caught by testing, not inspection**: `app/explainer.py`'s deterministic
  template fallback had its own separate condition-phrasing regex
  (`r"^(.+?)\s*(>|<|!=|=)\s*(.+)$"`) that would have silently mis-split `score >= 90` into
  `score > = 90` (regex alternation tries `>` before it ever gets to try `>=`) — fixed by
  reordering the alternation to try two-character forms first and adding `>=`/`<=`/`<>` to
  `_COMPARISON_PHRASES`. Caught by `test_comparison_operators.py`'s CASE/WHILE spot-checks.
- **Fix 2 — `SELECT ... INTO`**: `SELECT col1, col2, ... INTO var1, var2, ... FROM table
  WHERE condition;` — own AST node (`SelectIntoStatement`), own parsing method
  (`_parse_select_into`), own execution method (`_exec_select_into`); NOT a variant of the
  cursor mechanism (unchanged) or the standalone-SELECT `SqlStatement` passthrough (also
  unchanged). A bare `SELECT` is ambiguous between the two until the parser looks ahead —
  `_select_has_into` scans forward (no consumption) for INTO before the next FROM/`;`.
  Two raw-captured spans (column list, FROM/WHERE clause) sandwich a structurally-parsed
  INTO variable list (same style `_parse_fetch_cursor` already uses for FETCH's own INTO
  list), rejoined into one query with the INTO clause stripped (real SQLite has no
  `SELECT ... INTO` syntax in this position). Executes through the same
  `execute_sql_on_connection` every `SqlStatement`/`POST /sql/execute` call already uses.
  Three outcomes: **one row** assigns columns to targets positionally; **zero rows**
  triggers NOT_FOUND through the EXACT SAME mechanism an exhausted cursor FETCH already
  uses — **no new error path**, so an existing `DECLARE CONTINUE HANDLER FOR NOT_FOUND`
  already catches it, unconditionally non-fatal either way; **more than one row** is a
  distinct, immediately-fatal `InterpreterError`, deliberately never routed through
  NOT_FOUND or any handler. Reuses the `SqlStatement` `sql` DebugStep shape (`kind: "rows"`)
  plus one new field, `into: [str, ...]` — see `docs/schema.md`.
- **`app/advisor.py`**: `_touched_names` (check #9, dead-store safety net) now tracks
  `SelectIntoStatement`'s own `targets` as writes, same treatment `FetchCursorNode`'s
  targets already get — needed so a `SET` right before a `SELECT ... INTO` targeting the
  same variable doesn't false-positive as a dead store. `_statement_exprs` deliberately has
  no case for it (raw `query` text, same boundary `SqlStatement` already has).
- **`app/explainer.py`**: both the Gemini prompt builder (`_describe_sql_step`) and the
  deterministic template fallback gained a case recognizing `sql.into`, phrasing the found/
  NOT_FOUND outcomes distinctly rather than falling through to generic `kind: "rows"` text.
- **`SqlConsolePage.jsx`**: the existing SQL step panel now shows a "SELECT ... INTO"
  heading + an "Assigned: var = value" (or "No row matched ... left unchanged") line
  whenever `currentStep.sql.into` is present — the NOT_FOUND case itself needed no new UI,
  the page's existing generic error-banner already covers it (same as an exhausted FETCH).
- **New samples**: `OperatorShowcase` (`>=`/`<=`/`<>` together, nested IF/ELSE grade
  ladder — this grammar has no ELSEIF sugar); `LookupOnePlayer` (both SELECT INTO outcomes
  in one run — a match and a NOT_FOUND-handled miss, demonstrating the untouched-target
  behavior directly). Both use `CREATE TABLE IF NOT EXISTS` + a leading `DELETE` for
  re-runnability, same convention `InventoryValueReport`/`ManageInventory` already use.
- **Tests**: one existing test rewritten
  (`test_two_char_comparison_operator_does_not_round_trip` →
  `..._now_round_trips_correctly`, since it documented the OLD broken behavior this
  session's Fix 1 fixed as a side effect). Two new files:
  `test_comparison_operators.py` (25 tests — tokenizer lexing order, parser, interpreter
  evaluation, CASE/WHILE spot-checks, the SQL round-trip fix, a still-invalid-operator
  sanity check) and `test_select_into.py` (20 tests — parser dispatch/errors,
  found/zero-row/multi-row/column-mismatch/undeclared-target cases, NOT_FOUND-handler-
  doesn't-catch-multi-row, coexistence with a separate cursor, two real `/debug`
  end-to-end tests). Two new golden fixtures (`OperatorShowcase.json`,
  `LookupOnePlayer.json`); the other 19 samples' fixtures confirmed byte-for-byte
  unchanged. Backend suite: **552 passing** (up from 505), zero regressions.
- **Verification**: `npm run lint`/`npm run build` both clean. Live-verified via headless
  Chrome against a **freshly started** dev backend+frontend (neither was already running
  this session, unlike most prior sessions — started both, verified, cleaned up after).
  Confirmed: `OperatorShowcase` sample loads/runs; hand-typed raw source using all three
  new operators directly (not just the sample) parses, runs, and steps to a hand-verified
  final value (`r = 111`); `LookupOnePlayer`'s step log shows both SELECT INTO steps, the
  second tagged `NOT_FOUND` inline in the step log entry itself; the new SQL step panel
  correctly shows "Assigned: foundScore = 95" for the found case and "No row matched --
  foundScore left unchanged" plus the pre-existing NOT_FOUND error banner for the miss, in
  both themes (screenshots in the scratchpad). Cleaned up 8 real `debug_history.db` rows
  and a real `players` table this session's own live verification created — confirmed
  `user_data.db` back to just its one seeded `products` table afterward.

---

## Testing infrastructure (see `CLAUDE.md` §6 for the mechanics)

- **Golden-trace regression harness** (`backend/app/tests/test_golden_traces.py` +
  `backend/app/tests/golden/*.json`, now **21 fixtures** — `OperatorShowcase`/
  `LookupOnePlayer` added this session): runs every sample through the REAL `/debug`
  endpoint and diffs the resulting step trace against a checked-in baseline. **Run this
  before considering any future tokenizer/parser/interpreter-touching phase done.**
- **Property-based tests** (`backend/app/tests/test_property_based.py`, `hypothesis`):
  mutates the real samples via `demo_db.create_demo_connection()`; two invariants across
  1000 examples each — untouched by this session.
- **Known-bugs tracker** (`backend/app/tests/test_known_bugs.py`): empty of unfixed bugs.
- **Hand-written grammar edge cases** (`backend/app/tests/test_grammar_edge_cases.py`):
  untouched this session (the round-trip caveat test it references now lives in
  `test_sql_passthrough_statement.py`, rewritten — see above).
- **New this session**: `test_comparison_operators.py`, `test_select_into.py`.
- Backend suite: **552 passing, 0 xfailed** (up from 505).

---

## Immediate next steps

1. SQL Anti-Pattern Advisor still doesn't analyze a `ProgramNode` AST at all (a
   `CALL`-based multi-procedure source always shows "no issues"); Download/Compare have
   never been exercised against one either. Pre-existing, unrelated to recent sessions.
2. The SQL Console (whether reached via the flat results view or the debugger UI's `sql`
   step panel) executes exactly one statement per Run click — running multiple
   `;`-separated statements at once fails cleanly rather than running any of them.
   Deliberate scope boundary, not a bug; worth a fresh scoping prompt if multi-statement
   support is ever wanted. Applies equally to `SELECT ... INTO` (one lookup per statement).
3. No server-side constraint enforcement (NOT NULL/PRIMARY KEY) or variable interpolation
   for SQL passthrough statements (`SqlStatement` or `SelectIntoStatement`) — a real,
   documented, deliberate capability loss versus an earlier phase's retired simulated
   feature. If a future phase wants either back, it needs its own scoping (variable
   interpolation in particular would need a real decision about safely substituting a
   value into raw SQL text — naive string splicing is a SQL-injection footgun even in a
   course-project sandbox).
4. `SELECT ... INTO`'s zero-row NOT_FOUND path assigns no target variable at all (they
   keep whatever value they held before) — same convention an exhausted cursor FETCH
   already has, deliberate and tested, not a gap.

---

## Live gotchas

- **`backend/data/debug_history.db` needs manual cleanup after any live-verification
  session** — it auto-rotates at 50 rows but real `/debug` calls during manual testing
  still show up; delete test-run rows afterward (`DELETE /history/{id}` while the backend
  is up). This session added 8 (all from its own live verification); cleaned up, confirmed
  the top of `/history` back to the pre-session state (id 445).
- **`backend/data/user_data.db` is a similarly real, persistent artifact** — any live
  verification that runs CREATE TABLE/INSERT/UPDATE/DELETE (or, this session, a
  `SELECT ... INTO` sample that CREATEs its own lookup table) against the real backend
  leaves real rows/tables behind if not cleaned up. This session's `LookupOnePlayer`
  live-check created a real `players` table — caught it, `DROP TABLE`d it, confirmed
  `user_data.db` back to just `products` afterward. Prefer measuring through pytest
  (isolation for free via `conftest.py`'s autouse fixtures) over a bespoke script whenever
  one would touch this database at all.
- **Neither dev server was already running at the start of this session** (unlike most
  prior sessions, which found both already up) — started a fresh backend
  (`uvicorn app.main:app --port 8000`) and frontend (`npm run dev`, port 5173) for live
  verification. Both were left running at session end; a future session should check with
  `curl`/`netstat` before assuming either state.
- The scratchpad's `cdp.js` raw-CDP driver (`node cdp.js <script.js>`) still works
  unchanged — reused this session for `verify_operators_and_select_into.js`/
  `verify_final_step.js`. Its `BASE` constant needs pointing at whichever host:port the
  frontend actually bound to (`localhost:5173` this session, `[::1]:5173` in an earlier
  one) — check the frontend's own startup log rather than assuming.
- The sample picker is a list of `.sample-card` buttons, NOT a native `<select>` — a
  verification script must `[...document.querySelectorAll('.sample-card')].find(...)
  .click()`, not try to set a `<select>`'s `.value`. The Live State panel is
  `.panel-state` (not `.panel-variables`/`.variables-panel`); the SQL step panel is
  `.table-state-panel` (not `.panel-sql`/`.sql-step-panel`) — verified directly against
  `SqlConsolePage.jsx`'s actual JSX rather than guessed.
- **Chrome's DevTools HTTP endpoint requires `PUT`, not `GET`, for `/json/new`** in
  current Chrome versions — the scratchpad's `cdp.js` driver already does this.
- Interacting with a mounted Monaco editor from a raw-CDP script: `window.monaco` isn't
  guaranteed populated the instant `Page.loadEventFired` fires — poll for
  `window.monaco?.editor.getModels().length` before calling `.setValue(...)`.
- `found`/`notfound` are reserved KEYWORDs in this grammar (the `cur_name%FOUND`/
  `cur_name%NOTFOUND` cursor-attribute suffix) — a variable or OUT parameter literally
  named `found` fails to parse with a confusing "Expected IDENTIFIER (got KEYWORD)"
  error. Learned the hard way writing this session's own tests/samples; use `was_found`/
  `matched`/similar instead.
- Mobile nav overflows horizontally at ~400px width (pre-existing, `.top-nav` has no
  `flex-wrap`) — cosmetic, not blocking. Untouched this session.
