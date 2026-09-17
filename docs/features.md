# Feature design notes

Detailed per-feature rationale, moved out of `CLAUDE.md` (which stays a lean, high-level
orientation doc) so it doesn't load into every prompt. `CLAUDE.md` §2 lists each feature
in one line with a pointer here. For the `DebugStep` wire-contract shape and performance
history, see `docs/schema.md` instead.

Organized in shipped order (oldest first).

---

## Breakpoints + Continue/Restart

`frontend/src/pages/DebuggerPage.jsx` — a frontend-only consumption-layer feature on top
of the existing step trace, not an interpreter/backend capability. A breakpoint is just a
source line number (`Set<number>` in component state); **"Continue"**
(`continueExecution`, originally built and briefly labeled "Run to Breakpoint" before a
same-phase-family cleanup pass renamed it) fast-forwards `currentStepIndex` from wherever
it currently is to the next step in the *already-computed* trace whose `line` is in that
set (falling through to the last step, i.e. run-to-completion, when none match — the
deliberate no-breakpoints behavior). **"Restart"** (`restartTrace`, originally labeled
"Reset") jumps `currentStepIndex` back to 0 of the same trace with no re-fetch. Uses
Monaco's own glyph margin (`glyphMargin: true`) rather than custom gutter UI; clicking the
glyph margin or the line-number column (`editor.onMouseDown`, told apart via Monaco's
`MouseTargetType`) toggles a breakpoint. Breakpoints persist across new Debug runs/sample
loads (editor-level state, not tied to one run) and are tracked by raw line number, not a
Monaco decoration ID — heavy edits above a breakpoint can leave it on now-different code,
an accepted simplification.

## SQL Anti-Pattern Advisor

`backend/app/advisor.py` — a static linter-style pass over the AST alone (never the
execution trace), reusing the exact AST `app.parser.parse()` already produces. Not a
separate endpoint: `POST /debug` computes `analyze(ast)` right after a successful parse
and returns the findings as an `issues` array alongside `ast`/`steps`, so the check runs
automatically on every Debug click at no extra network round trip. Nine anti-patterns/
warnings detected — the original six (`select-star`, `cursor-could-be-set-based`,
`nested-loops`, `missing-error-handling`, `magic-number`, `cursor-not-closed`) plus three
**Extended static analysis warnings** added in a later phase:

- `unreachable-code` — dead code after an unconditional RETURN or LEAVE (see "LOOP /
  LEAVE" below), or an IF/searched-CASE-WHEN branch whose condition is a compile-time
  constant.
- `unused-variable` — a DECLAREd local never read by any expression; assignment alone
  doesn't count.
- `never-read-variable` — a "dead store": a SET's value is unconditionally clobbered by a
  later SET to the same name before anything reads it, distinct from `unused-variable`
  since the variable IS read at some *other* point.

See the module's own docstring for what's detectable from this grammar's AST and, just as
deliberately, what isn't (no dynamic-SQL/injection check: this grammar has no
EXECUTE/EXEC-IMMEDIATE construct at all; `DECLARE ... DEFAULT` is deliberately never
treated as a dead-store's "first write" — that idiom is used throughout this app's own
sample library).

## Side-by-Side Run Comparison

`frontend/src/pages/ComparePage.jsx`, route `/compare` — two independent Monaco editor
panes, each calling `POST /debug` on its own; no backend changes at all, since that
endpoint is already stateless per request. Once both sides have a trace, one shared step
control drives a `sharedStepIndex` both panes read from (a shorter trace freezes on its
last step once the index passes its own length, rather than erroring).
`frontend/src/compareTraces.js`'s `computeDivergence()` is a pure, execution-free diff
over the two `DebugStep` arrays: it walks them by shared index and reports the first
difference in line/error/branch/shared-variable-value, or a `length` divergence if the
traces match all the way through but end at different lengths; `null` means fully
identical. Deliberately doesn't touch the flowchart or the Anti-Pattern Advisor's
`issues` — only the step trace itself is compared.

## Report export

`backend/app/report.py`, `/debug/report` — PDF via **reportlab** (chosen over weasyprint
— no native GTK/Pango/Cairo dependency to install on this Windows dev environment), DOCX
via **python-docx**, plain text via stdlib only. The flowchart image is rasterized to PNG
**client-side** (`frontend/src/svgToPng.js`, via `<canvas>`) from the Mermaid SVG the
Debugger has already rendered and sent to this endpoint as-is — converting Mermaid's
`<foreignObject>`-heavy SVG server-side has no reliable lightweight option. Stateless: it
formats whatever `DebugStep` trace the frontend already has from its last `/debug` call,
never re-parses/re-interprets.

## `CALL` support (procedure calling procedure)

The first Tier 1 phase to touch the interpreter core. A submission can now chain multiple
`CREATE PROCEDURE`/`CREATE FUNCTION` definitions back to back; `parser.parse()` wraps 2+
of them in a new `{"type": "ProgramNode", "definitions": [...]}` node (exactly one
definition still parses to a bare `ProcedureNode`/`FunctionNode`, unchanged) — **the LAST
definition in source order is the entry point** that actually runs; every definition
(entry included, enabling self-recursion) is registered by name for `CallStatement`
(`CALL name(args);`) to resolve at runtime. A `CALL` target must be a `ProcedureNode`
specifically (calling a `FunctionNode`'s name via `CALL` is a clear error — see "Function
calls in expressions" below for how a `FunctionNode` actually IS invoked).
`interpreter._exec_call` gives the callee a **fully isolated**
scope/cursors/handlers/changed-value-baseline (saved and restored around the nested call,
via `Interpreter.run()` called recursively so the whole call chain lands in one
continuous `self.steps` list) — only explicit IN/OUT/INOUT parameters cross the boundary;
an OUT/INOUT argument must be a plain Identifier (can't write back into an expression).
`MAX_CALL_DEPTH` (50) guards recursion with a clear `InterpreterError`, never a hang. See
`docs/schema.md` for the `call` DebugStep field this adds.

## Function calls in expressions

Added in a later phase than `CALL` — the expression-position counterpart to `CALL`:
`name(args)` is now valid anywhere `expr` is (an assignment's right-hand side, an
IF/WHILE condition, another call's own argument, ...), parsed at the `primary` grammar
level as `FunctionCallExpr` and disambiguated from a plain `Identifier`/`%FOUND` check by
a one-token `(` lookahead in `parser._parse_primary`.
`interpreter._evaluate_function_call` **reuses `_exec_call`'s exact
scope-isolation/call-depth/call-stack machinery** (not a second implementation) — the
differences are narrow: the target must be a `FunctionNode` (calling a `ProcedureNode`
this way is a clear error, symmetric to `CALL`'s own restriction), every argument binds
like a plain IN (a `FunctionNode`'s params never carry a mode, so there's no OUT/INOUT
propagation), and `Interpreter.run()` is called with `require_return=True` — the callee's
`RETURN`ed value is captured via `self._last_return_value` (set by `_exec_return`
immediately before it raises `_ReturnSignal`) and substituted directly into the calling
expression. **No `DebugStep`/Call Stack schema change was needed** — a called function's
own steps carry the exact same `call: {procedureName, depth, stack}` field a called
procedure's already do (the field's own name predates this and was deliberately left
as-is rather than renamed, since `DebugStep` is a wire contract — see `docs/schema.md`),
so the existing Call Stack panel and Variable Timeline render a function call correctly
with **zero frontend changes**; only `frontend/src/cfg.js`'s own mirrored `renderExpr`
needed a `FunctionCallExpr` case (for the flowchart's node labels) since it duplicates
the backend's rendering logic client-side. Recursion, mutual recursion, and
function-calling-function all work by the same generalized mechanism (verified directly,
not assumed — see `backend/app/tests/test_function_call_expression.py`).

## CASE statement

Added in a later phase than function calls — both simple (`CASE expr WHEN v THEN ...`)
and searched (`CASE WHEN cond THEN ...`) forms, as ONE AST node type (`CaseStatement`),
not two: a simple CASE is just a searched CASE where each WHEN's own test is "equals the
operand" instead of an independent boolean, so `interpreter._exec_case` and
`parser._parse_case` each need only one code path. `_parse_case` disambiguates the two
forms with a one-token lookahead (a WHEN right after CASE means searched); every
WHEN/ELSE body is parsed via `_parse_block` — **the same block-parsing helper IF/WHILE
already use**. Missing ELSE is a silent no-op, confirmed to match `_exec_if`'s own
established convention by reading it first, not invented fresh; DIVISION_BY_ZERO while
evaluating the operand/a WHEN expression stops evaluation immediately and falls through
to ELSE/none, same as IF's own "condition couldn't be evaluated" behavior generalized to
a sequence. **Reuses IfStatement's own `branch` DebugStep field verbatim** (`path` is
`"when-<N>"`/`"else"`/`"none"` instead of IF's fixed `"then"`/`"else"`/`"none"`) — no new
DebugStep field.

Needed real cross-cutting fixes in more places than `FunctionCallExpr` did:
`frontend/src/cfg.js`'s flowchart builder had **zero** CASE support before this (would
have silently dropped every WHEN/ELSE body from the diagram) — fixed with a diamond node
+ one labeled edge per WHEN (open-ended, not fixed like IF's then/else) plus ELSE;
`backend/app/advisor.py` needed five separate fixes (three shared AST walkers plus two
hand-rolled ones — `_check_nested_loops`'s own walker and `_find_unguarded_fetch` — that
don't use the shared ones); `backend/app/explainer.py`'s template fallback had no
CaseStatement case at all. All verified directly by reading each file, not assumed
generic by analogy — see `backend/app/tests/test_case_statement.py` and the expanded
`test_advisor.py`.

## LOOP / LEAVE

Added in a later phase than CASE — `[label:] LOOP ... END LOOP [label];`, exited only via
`LEAVE [label];`. Two new AST node types (`LoopStatement`, `LeaveStatement`), not a
variant of `WhileStatement` — LOOP has no condition of its own at all, unlike WHILE.
Labels are optional MySQL-style (`':'` became a real token for this — the only construct
in this grammar that uses one); `_parse_statement` tells a labeled LOOP apart from every
other statement with a one-token `IDENT ':'` lookahead (unambiguous: no other statement
here starts with a bare IDENTIFIER). `interpreter._exec_loop` reuses `WhileStatement`'s
own `MAX_LOOP_ITERATIONS` guard verbatim (reuse, not reinvention) and reuses its `loop:
{condition, result, iteration}` DebugStep field too — `condition` is the literal
`"LOOP"`/`"LOOP <label>"` text, `result` is always `True` (a LOOP never "fails" a check;
the only exits are an executed LEAVE or the iteration cap raising instead).
`_exec_leave` validates its target (unlabeled → innermost enclosing loop; labeled → that
exact label, searched outward) against a new `Interpreter._loop_stack`, records its own
step, then raises an internal `_LeaveSignal` that `_exec_loop` either catches (stops that
loop) or re-raises unchanged (keeps unwinding outward) — this is what makes `LEAVE
<label>` from two loop levels deep correctly skip the innermost loop entirely, not just
stop there. `_loop_stack` is isolated per CALL/function-call frame exactly like
`cursors`/`handlers` already are (LOOP/LEAVE nesting is a purely lexical,
single-procedure concept — a callee must never be able to LEAVE a label still sitting on
the caller's own stack purely because the caller is paused inside a CALL).

**Cross-cutting fixes needed in the same shape the CASE phase found**:
`frontend/src/cfg.js`'s flowchart builder threads a `loopStack` accumulator through
`emitBlock` so every LEAVE (regardless of nesting depth/IF-WHILE-CASE-LOOP in between)
contributes its own exit edge (`kind: 'leave'`) into whatever follows its *target* LOOP
specifically, not just the nearest one; `backend/app/advisor.py` needed the three shared
walkers PLUS both hand-rolled ones (`_check_nested_loops`, `_find_unguarded_fetch`) fixed
again, plus a new `unreachable-code` sub-case (code positioned after an unconditional
LEAVE, same "dead by position" reasoning as after a RETURN) and a documented, deliberate
non-extension of `cursor-could-be-set-based` to LOOP-based cursor loops (a LOOP's own
idiomatic guard is retrospective `FETCH; IF cur%NOTFOUND THEN LEAVE; END IF;`, not
predictive `%FOUND`, which this check doesn't recognize as a guard — a real, accepted
false positive, not a bug); `backend/app/explainer.py`'s template fallback got new
LoopStatement/LeaveStatement cases. Predict Mode's branch-guessing UI checks `nodeType
=== 'IfStatement'` specifically, so LOOP/LEAVE steps correctly, gracefully offer no
prediction prompt, same documented scope decision CASE already established.

New sample **`FindPairSum`** (a labeled LOOP nested inside another labeled LOOP)
exercises both an unlabeled `LEAVE;` (breaks only the innermost loop) and a labeled
`LEAVE outer;` fired from inside the inner loop (jumps straight past both loops at once)
— see `backend/app/tests/test_loop_statement.py`.

## User-created tables (CREATE TABLE / INSERT / UPDATE / DELETE)

Added in a later phase than LOOP/LEAVE — the biggest single-phase change to the
project's scope, since before this the app had exactly one table (`products`, fixed,
read-only, cursor-only). Four new statement types (`CreateTableStatement`,
`InsertStatement`, `UpdateStatement`, `DeleteStatement`), all parseable anywhere any
other statement is. A column definition is `name TYPE [NOT NULL] [PRIMARY KEY]` — `TYPE`
is never validated against a fixed set, matching the exact same "advisory, unenforced"
treatment a DECLARE's own `var_type` already gets, so no new type system was invented
for this. `NOT NULL`/`PRIMARY KEY` ARE enforced at runtime (`Interpreter.
_validate_row_constraints`): a NULL value for either is a clear InterpreterError, and a
PRIMARY KEY value must stay unique across the table (checked by linear scan — this
grammar's tables are course-project-scale, not something needing an index).

**Deliberately simulated, not a second real database** — per this project's own
"execution is simulated" convention (see CLAUDE.md §2), a table's rows are a plain
Python `{"columns": [...], "rows": [{col: value, ...}, ...]}`, kept in `Interpreter.
tables`, entirely separate from both `self.scope` (not SQL variables) and the real
`sqlite3.Connection` cursors query (`self._db` — still only ever the fixed `products`
demo table; a user-created table is never queryable from a cursor's embedded SELECT,
and vice versa — the two mechanisms don't talk to each other at all). A WHERE clause
(UPDATE/DELETE, both optional — omitted means "every row") is evaluated by
`_evaluate_with_row`, a thin wrapper that layers a row's own column values on top of the
current scope and calls the *exact same* `_evaluate` an IF/WHILE condition already uses
— reused, not reimplemented, per this phase's own instruction. This is also what lets a
WHERE/SET expression reference a scope variable and a column in the same expression
(`WHERE price > minPrice`).

**Scope: global for the whole run, never isolated per CALL/function-call frame** —
checked against the existing `products`/`self._db` convention first (never swapped
around a callee) rather than inventing new semantics: `self.tables` follows the exact
same rule, so a table one procedure in a CALL chain creates is immediately visible to
every other procedure in that chain, and (like every other run-scoped state in this
interpreter) resets to empty at the start of the next run.

**Step-trace: a genuine new DebugStep field, not force-fit into an existing one** — every
existing field was checked and ruled out first (see `docs/schema.md` for the `table`
field's own shape and why `variables`/`cursor` don't fit): `variables` is scope-only
(stuffing table rows in there would also break Variable Timeline/report export, which
assume every entry is one scalar), and `cursor` describes a read-only SELECT cursor's
single buffered row, an incompatible shape for a whole table's row list. `table` is
present only on a CREATE TABLE/INSERT/UPDATE/DELETE step, carrying a FULL current row
snapshot (not a diff) — "table mutations visible the same way variable mutations already
are" means the table's current state is always fully visible on the step that touched
it, mirroring how `variables` itself always shows every variable's current value.

**Cross-cutting fixes needed, same shape every prior phase's found**: `frontend/src/
cfg.js` needed `renderStatementHeader`/`renderExpr` cases (a `NullLiteral` — the new INSERT-
value literal, evaluating to Python `None` — and the four new statement types); no
`emitBlock` change was needed since none of the four branch or loop, so they fall
straight through to the existing plain-rect-node case every non-branching statement
already uses. `backend/app/advisor.py` needed `_statement_exprs` cases (InsertStatement's
`values`, UpdateStatement's `assignments`/`where`, DeleteStatement's `where`) so every
check built on top of it (magic-number, unused-variable, never-read-variable,
missing-error-handling's division check) sees inside these statements too, plus one
genuinely new check: **`missing-where-clause`** (severity "warning") — an UPDATE/DELETE
with no WHERE touches every row in the table, a classic footgun. `backend/app/
explainer.py`'s template fallback got new CreateTableStatement/InsertStatement/
UpdateStatement/DeleteStatement cases, and `_build_prompt`/`_build_ask_prompt` both now
forward a step's `table` field so Gemini (or its template fallback) describes a table
mutation specifically rather than generically, matching how `cursor`/`error` are already
forwarded.

**Predict Mode**: deliberately NOT extended, documented the same way CASE/LOOP/LEAVE
already are — none of the four statement types change a scope variable (so the
"predict the next changed variable" check never fires) and none carry a boolean branch
to guess, so a step involving one simply offers no prediction prompt, exactly like a
cursor FETCH already doesn't.

**Variable Timeline**: needed zero changes, verified rather than assumed — it's built
purely from each step's `variables` entries, and a table's rows live in the separate
`table` field, so a table-only procedure (no DECLAREd scalars at all) correctly renders
its own "This run never declared any variables" empty state rather than crashing or
showing garbage (confirmed live against `ManageInventory`, not just read as obviously
true).

New sample **`ManageInventory`** exercises all four statement types together against
one table — restocks low-quantity rows (UPDATE), discounts high-priced ones (a second,
independent UPDATE), then discontinues one product by id (DELETE) — with the final row
state hand-derived and cross-checked against a real interpreter run (see `backend/app/
tests/test_table_crud.py` and `frontend/src/testCaseExpectations.js`, which gained an
additive, optional `tables: { name: [row, ...] }` field alongside `variables`/
`returnValue` for exactly this — checked by `TestCaseRunner.jsx`'s `findFinalTableState`
against the LAST step whose own `table.name` matches, not just whatever the very last
step overall happens to be).

## Persistent user database + SQL Console

`backend/app/user_db.py`, `backend/app/sql_console.py`, `frontend/src/pages/
SqlConsolePage.jsx` (route `/sql-console`) — replaces the old `app.demo_db`-per-request
`:memory:` connection in the live `/debug` request path with a real, file-backed SQLite
database (`backend/data/user_data.db`) that persists across requests and across a backend
restart. `products(name, price)` is seeded once, the first time the table doesn't already
exist (`user_db._ensure_seed_data`) — a `DROP TABLE products` re-triggers seeding on next
open, but deleting/editing its rows does not, so a user's own changes via the console
survive a reopen. `app.demo_db` itself is unchanged and kept around on purpose, now purely
as a deterministic `:memory:` fixture for interpreter-level unit tests that want a seeded
connection without touching disk — it's simply no longer wired into `app.main`'s `/debug`
handler.

New endpoint `POST /sql/execute` (`app/sql_console.py`) is a raw SQL passthrough: one
statement, run exactly as typed straight through the `sqlite3` driver against
`user_db.get_connection()` — deliberately bypassing `app.tokenizer`/`app.parser`/
`app.interpreter` entirely, since that pipeline exists to interpret this project's own
procedural dialect, not plain SQL. `cursor.description is not None` is the sole signal
used to branch the response shape (`{"kind": "rows", "columns", "rows", "rowCount",
"description"}` vs `{"kind": "write", "rowsAffected", "description"}`) — keyword sniffing
(`_first_keyword`, skipping leading `--`/`/* */` comments) only decides the human-readable
`description` text, never how the statement actually executes, so a statement it can't
classify still runs correctly with a slightly generic description. A `sqlite3.Error` (bad
table name, syntax error, running more than one statement at once, ...) is caught and
re-raised as `SqlExecutionError`, surfaced by `main.py` as a 400 with `str(exc)` — SQLite's
own error text is already human-readable, so no separate message-cleanup step was needed.

Because `app.interpreter`'s cursor OPEN/FETCH path (`self._db.execute(...)`) and the SQL
Console both now read the *same* `user_db.get_connection()` source, a row written through
the console is immediately visible to a cursor's embedded SELECT and vice versa —
confirmed live, not just by construction (see `backend/app/tests/test_sql_endpoint.py`'s
`test_sql_console_and_cursor_share_one_source_of_truth`, and a live-browser check: an
INSERT via the SQL Console, then a cursor-based procedure summing exactly that new row).

`frontend/src/pages/SqlConsolePage.jsx` reuses the Debugger's Monaco setup/theme
(`vs`/`vs-dark`, same font/options) and the app's existing `.error-banner`/`.status`/
`.cursor-table` styling wholesale rather than inventing page-specific equivalents — a
result table's columns/rows render straight into `.cursor-table`, a write's `description`
into `.status.status-ok`, and a `SqlExecutionError` message into the same
`.error-banner-unhandled` coral styling every other error display in the app already
uses. Deliberately a separate page/route from the Debugger (`/sql-console`, not part of
`/debugger`) — no step trace, no breakpoints, just run-and-see-result. `vite.config.js`
needed a `/sql` proxy entry with the same `bypassNavigations` guard as `/debug`/
`/debugger` and `/history`, since `/sql` (the `/sql/execute` API prefix) is also a
path-prefix match for the page's own `/sql-console` route.

**Superseded by the next section below**: a later phase merged this page with the
Debugger into one page/route — `/debugger` no longer exists (redirects to `/sql-console`)
and the SQL Console is no longer "a separate page from the Debugger." Left this section's
own narrative as written (it's still an accurate account of what shipped at the time) —
see "Merged Debugger/SQL Console page + SQL passthrough statements" for what changed and
why.

Test isolation follows the exact pattern `_isolated_history_db` already established in
`conftest.py`: an autouse `_isolated_user_db` fixture monkeypatches `user_db.DB_PATH` to a
per-test `tmp_path` file, so the suite never reads or writes the real
`backend/data/user_data.db` a developer might be using locally.

## Merged Debugger/SQL Console page + SQL passthrough statements

Two changes shipped together, deliberately: a frontend routing/UI consolidation, and a
backend grammar extension that only makes sense once the frontend can show its result.

**Frontend merge.** `frontend/src/pages/DebuggerPage.jsx` was renamed to `SqlConsolePage.jsx`
(overwriting the standalone SQL Console page from the previous section — its results-panel
JSX moved into this file, not deleted) and now owns both capabilities behind one Monaco
editor and one Run button. `/debugger` no longer exists as a real page — `App.jsx` redirects
it to `/sql-console` (`<Navigate to="/sql-console" replace />`) for old bookmarks/links, and
`Layout.jsx`'s nav has exactly one entry, "SQL Console," where "Debugger" and "SQL Console"
used to be two. Every other page that used to `navigate('/debugger', ...)` — `HistoryPage.jsx`
(replaying a saved run), `HomePage.jsx`'s CTA — now targets `/sql-console` directly. Internal
CSS class names and the component's own former identity (`DebuggerPage`, `debugger-page`,
`debugger-grid`, `panel-editor`, ...) were deliberately left unchanged — renaming every one
of them was pure churn with no functional benefit; only the file name, exported component
name, and route/nav-facing identity actually changed.

**Detection logic** (`handleRun`, replacing the old `handleDebug`): POST `/debug` first,
always — the same endpoint and tokenize→parse→interpret pipeline the Debugger always used,
completely unchanged. Three outcomes:
1. **200 OK** → a procedure/function. Render the full existing debugger UI, unchanged.
2. **400 with `detail.stage === "interpret"`** → this genuinely parsed as a procedure/
   function; the failure is a real runtime error INSIDE it. Stays on the debugger UI's own
   error display (`debugError`, `.status-error`) — exactly how a failed Debug run always
   looked, before or after this merge.
3. **400 with `detail.stage` `"tokenize"` or `"parse"`** → not a procedure/function at all.
   `looksLikePlainSql(code)` (a heuristic, not a parse — the real parse already ran and
   already failed) checks: does the trimmed text start with CREATE/INSERT/UPDATE/DELETE/
   SELECT/DROP/ALTER, with no BEGIN/END/DECLARE anywhere in it? If yes, POST `/sql/execute`
   and render the SQL Console's results view (`mode: 'sql'`) in place of the debugger UI. If
   no, show one combined error (the parse failure plus "doesn't look like plain SQL either")
   rather than guessing which path to take.

**A significant, foreseeable consequence of the grammar extension below**: CREATE TABLE/
INSERT/UPDATE/DELETE/SELECT are now ALL valid bare-procedure-body statements too (see the
grammar section below), so input starting with one of those five almost always already
parses successfully at step 1 and never reaches the heuristic at all — it lands in the full
debugger UI (as a 1-or-more-step procedure trace with a `sql` step), not the flat SQL Console
results view. In practice, the heuristic/SQL-Console-results path now mostly serves DROP/
ALTER (not part of the procedure grammar) and SQL this tokenizer can't even tokenize (e.g.
backtick-quoted identifiers) — confirmed live, not just reasoned about (see "Verification"
below): a bare `CREATE TABLE ...;` or `SELECT ...;` renders the debugger UI's `sql` step
panel; a `DROP TABLE ...;` renders the flat SQL Console results panel.

**UI restructuring inside the merged page**: a new `mode` state (`null | 'debugger' | 'sql'`)
drives which results UI renders below the editor. `mode !== 'sql'` gates the step-navigator,
breakpoint hint, Predict Mode panel, the Live State column's real content (call stack,
cursor/SQL-step panel, variables, flowchart, explanation), the Ask AI panel, and the
Anti-Pattern Advisor panel — all completely unchanged internally, just conditionally
rendered now, falling back to a one-line "not applicable" placeholder in the Live State
column when `mode === 'sql'` instead of showing four now-meaningless empty panels. A new
`{mode === 'sql' && (...)}` block renders the SQL Console's exact results view (a
`.cursor-table` for SELECT rows, `.status.status-ok` for a write's description, an
`.error-banner.error-banner-unhandled` for a `SqlExecutionError`) in their place. The Run
button, its Ctrl/Cmd+Enter binding (added to `handleEditorMount`), and the
`debugError`/`sqlError` display are the only pieces always visible regardless of `mode`.

## Backend grammar extension: SQL passthrough statements

**Replaced, not added alongside**: an earlier phase's `CreateTableStatement`/
`InsertStatement`/`UpdateStatement`/`DeleteStatement` node types — each deeply parsed
(column defs, a real `expr` for every VALUES/SET/WHERE value) and executed by
`Interpreter.tables`, a pure-Python simulation that never touched real SQLite, and for
exactly that reason was never visible to a cursor's embedded SELECT — are gone. In their
place, ONE new node type, `SqlStatement`, covers all of `CREATE TABLE`/`INSERT`/`UPDATE`/
`DELETE`/`SELECT` (the last one is a genuinely new capability — a standalone SELECT,
outside a cursor declaration, didn't exist in any form before). This was a deliberate,
consequential decision, not a default — the user was asked explicitly whether to replace
the simulated feature or keep both approaches coexisting under different syntax, and chose
replacement, since only replacement closes the actual gap (a cursor's SELECT couldn't see a
procedure's own CREATE TABLEd data) and matches "raw passthrough, no SQL parsing of our
own" for all five keywords, not just the new one.

**Parsing** (`app/parser.py`'s `_parse_sql_passthrough`): exactly like a cursor's embedded
query capture (`_parse_declare_cursor`) — tokens are captured verbatim from the leading
keyword (inclusive, unlike the cursor path which starts capture only after `CURSOR FOR`) up
to the next top-level `;`, then reassembled via the same `_render_raw_query` helper. No
structure is parsed at all: no column-definition grammar, no VALUES/SET/WHERE expression
grammar, nothing. This means: (1) ~~the same round-trip caveat a cursor's query already
has — `<=`/`>=`/`<>` don't reconstruct correctly~~ **fixed** in the "Comparison operators +
SELECT...INTO" section below — every comparison operator this grammar's tokenizer knows now
lexes as one token, `<=`/`>=`/`<>` included, so raw-passthrough text round-trips cleanly for
all of them; (2) **no variable interpolation** — a DECLAREd variable's name inside one of these
statements means a literal SQL identifier (almost always "no such column"), never a
substitution of its current value, a genuine capability loss versus the retired feature's
VALUES/WHERE expression parsing, traded deliberately for real SQL/real database
interoperability; (3) a missing `;` no longer fails to PARSE the way the old structured
grammar did — it silently merges with whatever follows into one nonsensical `sql` string,
which then fails at INTERPRET time instead (a real SQLite syntax error) — a real, tested,
documented behavior difference (see `test_grammar_edge_cases.py`'s
`test_missing_semicolon_after_a_sql_passthrough_statement_does_not_raise`).

**Execution** (`app/interpreter.py`'s `_exec_sql_statement`): hands `node["sql"]` straight to
`app.sql_console.execute_sql_on_connection(self._db, ...)` — the exact same function `POST
/sql/execute` uses, refactored out of the previous phase's `execute_sql` (which is now a
thin open-connection/close-connection wrapper around it) specifically so the console and a
procedure's embedded SQL share one execution path, not two. `self._db` is the same
connection a cursor's OPEN already queries — genuinely one database underneath both, so a
table a procedure `CREATE`s and `INSERT`s into is immediately visible to a cursor's `SELECT`
later in that same run (the flagship new sample, `InventoryValueReport`, demonstrates
exactly this). A `sqlite3.Error`/`SqlExecutionError` becomes an ordinary `InterpreterError`
at the statement's line — a real, loud, run-stopping error (the same treatment a cursor
query against a nonexistent table already got), not a new error category. There is no
NOT NULL/PRIMARY KEY enforcement written in this interpreter any more; whatever real SQLite
itself does with a given CREATE TABLE's constraints is authoritative (verified directly:
`test_no_constraint_enforcement_written_in_this_interpreter_any_more` confirms a
non-INTEGER PRIMARY KEY column does NOT reject NULL by itself, a well-known SQLite quirk the
old simulation used to paper over by enforcing it itself).

**New `sql` DebugStep field** (replacing the retired `table` field) — see `docs/schema.md`
for the exact shape. For a write statement, `_exec_sql_statement` makes a best-effort
attempt (`app.sql_console.extract_table_name` — a small regex per keyword, not a real
parse) to find the affected table's name, then runs one more read-only
`SELECT * FROM <name>` on the same connection (`_snapshot_table`) to capture that table's
full current row set for the step — a convenience for the step panel; a name the regex
can't find, or a snapshot query that itself fails, just means no snapshot (`null`), never
incorrect statement execution.

**`app/advisor.py` changes**: `_statement_exprs` lost its `InsertStatement`/
`UpdateStatement`/`DeleteStatement` cases entirely — there's no expression tree to walk
inside raw `sql` text any more (magic-number/unused-variable/never-read-variable can no
longer see inside these statements — the same scope boundary a cursor's own embedded query
already had, verified directly by a rewritten test rather than assumed).
`_check_missing_where_clause` still exists but now regexes `stmt["sql"]` for a literal
`WHERE` instead of checking a parsed `where` field for `None`. `_check_select_star` gained a
second case for the new standalone-SELECT `SqlStatement` (regexing `stmt["sql"]` the same
way it already regexed a cursor's `query`), alongside its original cursor-query case,
unchanged.

**`app/explainer.py` changes**: the four `CreateTableStatement`/`InsertStatement`/
`UpdateStatement`/`DeleteStatement` template-fallback cases collapsed into one
`SqlStatement` case branching on `sql.keyword`, plus a new `SELECT` case (the retired
feature had no SELECT at all). `_build_prompt`/`_build_ask_prompt` both now forward a new
`_describe_sql_step(sql)` one-liner instead of reading the retired `table` field.

**Frontend (`cfg.js`, the flowchart renderer)**: the four `CreateTableStatement`/
`InsertStatement`/`UpdateStatement`/`DeleteStatement` cases (plus their `renderColumnDef`
helper) collapsed into one `SqlStatement` case — `` `${node.sql};` `` — since `sql` already
IS the full statement text, nothing to reconstruct. Still falls through to the same plain
rect-node shape every non-branching statement already used; no flowchart-specific change
needed.

**New sample, `InventoryValueReport`** (`frontend/src/samples.js`) — the flagship
end-to-end demo: `CREATE TABLE IF NOT EXISTS` + three `INSERT OR REPLACE INTO` + one
`UPDATE` (raw SQL passthrough) followed by a cursor that reads back those exact rows and
sums `qty * price`, all inside one run. This could NOT have worked under the retired
simulated feature (a cursor's SELECT never saw `Interpreter.tables`). `IF NOT EXISTS`/
`OR REPLACE` are used specifically so the sample stays safely re-runnable against the real,
persistent database — unlike a one-shot script, clicking Run on the same sample twice must
not fail with a real SQLite "table already exists"/UNIQUE-constraint error. `ManageInventory`
(the previous phase's demo of the now-retired simulated feature) was migrated to the same
`IF NOT EXISTS`/`OR REPLACE` pattern for the same reason — its actual SQL text needed no
other change, since it was already valid, standard SQL (the retired simulation's own
constraint/positional-VALUES semantics happened to already match real SQLite's), and its
final row state (`Widget(13, 10)`, `Gizmo(15, 13)`) is unchanged and confirmed idempotent
across repeated runs against the same database file. `TestCaseRunner.jsx`'s
`findFinalTableState` was updated to read `sql.tableName`/`sql.kind === 'write'`/
`sql.snapshot` (zipping `snapshot.columns` with each `snapshot.rows` entry back into a
column-keyed object) instead of the retired `table.name`/`table.rows`, keeping
`testCaseExpectations.js`'s own dict-based expectation format unchanged.

**Verification**: full backend suite 505 passing (up from 491 across the two
Persistent-DB-and-SQL-Console-phase sessions), zero regressions — including a rewritten
`test_sql_passthrough_statement.py` (parser + interpreter + end-to-end `/debug` coverage:
each keyword parsing correctly, execution against a real connection, the cursor-sees-raw-
INSERT interop test, a clean SQLite-error-surfaces-as-InterpreterError test, the no-
interpolation and no-constraint-enforcement documentation tests, the round-trip-caveat
test) replacing the retired `test_table_crud.py`. `npm run lint`/`npm run build` both clean.
Live-verified via headless Chrome against an already-running dev backend+frontend: nav
shows exactly one "SQL Console" entry; `/debugger` redirects to `/sql-console`; a full
procedure input renders the debugger UI (confirmed in both themes); a bare `CREATE TABLE`/
`SELECT` input ALSO renders the debugger UI (parses as a bare procedure) with its new `sql`
step panel correctly showing the table snapshot/query results; a `DROP TABLE` input (not
part of the procedure grammar) renders the flat SQL Console results panel; input matching
neither shows the combined clear-error message; the Compare page still runs two procedures
side by side unaffected; the sample selector still loads sample code into the editor
correctly. Cleaned up the real, already-running dev backend's `debug_history.db` rows (this
session's own curl/browser verification, plus an ad-hoc in-process benchmarking script that
was NOT run under pytest's isolation and so hit the real `user_data.db` directly) and
dropped the `inventory`/`stock` tables that benchmarking script left behind, confirming
`user_data.db` was back to just its one seeded `products` table afterward.

## Comparison operators (`>=`/`<=`/`<>`) + SELECT ... INTO

Two focused grammar/interpreter fixes, shipped together (the second sample below uses the
first's own operators), each independently tested and verified.

**Fix 1 — `>=`/`<=`/`<>`**: `app/tokenizer.py`'s `_TOKEN_SPEC` gained two new patterns,
`GTE` (`>=`) and `LTE` (`<=`), each ordered BEFORE the existing bare single-character
`OPERATOR` pattern (`[+\-*/><=%]`) — without that ordering, `>=` would lex as a `>` token
immediately followed by a separate `=` token, exactly the old, broken behavior this fix
replaces. `NEQ`'s own pattern was widened from `!=` to `!=|<>`, so `<>` is simply an
alternate spelling of `!=` from the tokenizer onward — no separate "NEQ2" concept exists
anywhere past that point. `app/parser.py`'s `COMPARISON_OPERATORS` set gained the three new
values (`{">", "<", "=", "!=", ">=", "<=", "<>"}`); since IF/WHILE/CASE conditions and every
other comparison expression in this grammar all route through the same `_parse_comparison`
rule and the same `Interpreter._evaluate_binary` evaluator, this one change is what makes
all three constructs accept the new operators — no per-construct code was needed.
`_evaluate_binary` gained `>=`/`<=`/`<>` branches (`<>` evaluates identically to `!=`, kept
as its own `if` branch rather than folded in, matching this method's existing one-branch-
per-operator style). A genuinely nice side effect: raw-passthrough SQL text (`SqlStatement`/
a cursor's embedded query) now round-trips `<=`/`>=`/`<>` correctly too, since
`_render_raw_query` just joins token values and each is now one token — this retroactively
fixes the round-trip caveat the "Backend grammar extension" section above used to document
as a real limitation (see that section's own strikethrough note). **A real bug this surfaced
and fixed in passing**: `app/explainer.py`'s deterministic template fallback had its own,
separate regex for phrasing an IF/WHILE condition in plain English
(`_describe_condition`'s `r"^(.+?)\s*(>|<|!=|=)\s*(.+)$"`) — with the new operators live, a
condition like `score >= 90` would have matched `>` first (regex alternation tries
alternatives left to right, and `>` is a prefix of `>=`), silently mis-splitting it into
`score > = 90`. Fixed by reordering the alternation to try the two-character forms first
(`r"^(.+?)\s*(>=|<=|<>|!=|>|<|=)\s*(.+)$"`) and adding `>=`/`<=`/`<>` entries to
`_COMPARISON_PHRASES`. This was caught by writing `test_comparison_operators.py` before
assuming the fix was complete, not by inspection.

**Fix 2 — `SELECT ... INTO`**: `SELECT col1, col2, ... INTO var1, var2, ... FROM table
WHERE condition;` — a single-row lookup, own AST node (`SelectIntoStatement`), own parsing
method (`app/parser.py`'s `_parse_select_into`), own execution method
(`app/interpreter.py`'s `_exec_select_into`) — explicitly NOT a variant of either the cursor
mechanism (DECLARE CURSOR/OPEN/FETCH/CLOSE, entirely unchanged) or the standalone-SELECT
`SqlStatement` passthrough (a whole result set as one DebugStep, nothing assigned to a
variable) already documented above. **Dispatch**: a bare `SELECT` keyword is ambiguous
between the two statement types until the parser looks further ahead — `_select_has_into`
scans forward (no consumption) for an INTO keyword appearing before the next FROM or the
statement-ending `;`; found routes to `_parse_select_into`, not found falls through to the
existing `_parse_sql_passthrough("SELECT")` unchanged. **Parsing**: two spans are captured
verbatim (the column list before INTO, the FROM/WHERE clause after the INTO variable list),
exactly like `_parse_sql_passthrough`/`_parse_declare_cursor` already capture their own raw
SQL text, with the INTO variable list itself parsed structurally in between — token-for-
token the same way `_parse_fetch_cursor` already parses a FETCH's own `INTO var1, var2`
list. The two raw spans are rejoined into one ready-to-execute query with the INTO clause
stripped out entirely (real SQLite has no `SELECT ... INTO ...` syntax in this position —
it's borrowed procedural sugar, never handed to SQLite verbatim). **Execution**: runs
through the exact same `execute_sql_on_connection(self._db, ...)` every `SqlStatement`/
`POST /sql/execute` call already goes through — same connection, same error-message
convention. Three outcomes: exactly one row assigns each column to its INTO target
*positionally* (same convention `_exec_fetch_cursor` already uses for FETCH ... INTO, not
by column name); a column-count mismatch is an ordinary immediately-fatal
`InterpreterError` (a programming error, not a data condition — same treatment
`_exec_fetch_cursor` gives its own mismatch); zero rows triggers NOT_FOUND through the
EXACT SAME mechanism an exhausted cursor FETCH already triggers it
(`_condition_error_info`/`_run_handler_if_triggered`) — **no new error path was added**, so
an existing `DECLARE CONTINUE HANDLER FOR NOT_FOUND` already catches it with zero changes of
its own, and it's unconditionally non-fatal whether handled or not, exactly like an
exhausted FETCH; more than one row is a distinct, immediately-fatal error
("expects exactly one row but the query matched N"), deliberately NOT routed through
NOT_FOUND or any handler at all — "too much data" and "no data" are different problems a
handler shouldn't quietly conflate. **Step-trace**: reuses the `SqlStatement` `sql` field
shape (`kind: "rows"`) rather than inventing a second one — execution-wise it's still just a
SELECT — extended with one new field, `into: [str, ...]`, the INTO target names positionally
paired with `columns`/`rows[0]`; see `docs/schema.md` for the exact shape. On the zero-row
path `rows`/`rowCount` are `[]`/`0` and the step's `error` field carries the same shape an
exhausted FETCH's own step already carries.

**`app/advisor.py`**: `_statement_exprs` deliberately has NO case for `SelectIntoStatement`
(its `query` is raw text, same scope boundary `SqlStatement` already has), but
`_touched_names` (check #9, never-read/dead-store) DOES add `SelectIntoStatement`'s own
`targets` to its conservative "might write this" set — same treatment `FetchCursorNode`'s
own `targets` already gets, and necessary for correctness: without it, a `SET` immediately
before a `SELECT ... INTO` targeting the same variable could false-positive as a dead store.
**`app/explainer.py`**: `_describe_sql_step` and the template fallback's
`generate_template_explanation` both gained a case recognizing `sql.into` — a distinct,
readable sentence ("found one row, assigned X = ..." / "matched no row ... left
unchanged") rather than falling through to the generic `kind: "rows"` phrasing.
**Frontend (`SqlConsolePage.jsx`)**: the existing SQL step panel (`table-state-panel`) now
shows a distinct "SELECT ... INTO" heading and an "Assigned: var = value" (or "No row
matched ... left unchanged") line whenever `currentStep.sql.into` is present, ahead of the
existing description/columns/rows table it already rendered for every `kind: "rows"` step —
the NOT_FOUND case itself needed no new UI at all, since the page's existing generic
`error-banner` (driven by any step's `error` field) already covers it, exactly as it already
did for an exhausted cursor FETCH.

**New samples**: `OperatorShowcase` (`frontend/src/samples.js`) — `>=`/`<=`/`<>` together
in one procedure, nested IF/ELSE (this grammar has no ELSEIF sugar) forming a grade ladder;
`score = 82` lands on `grade = 'B'` (`>= 90` false, `>= 75` true), `isPerfect = 0` (`<> 100`
true). `LookupOnePlayer` — both `SELECT ... INTO` outcomes in one run: a match
(`foundScore = 95`, Ada's real seeded score) and a miss (`missingHandled = 1`, via a
registered NOT_FOUND handler; `foundScore` stays exactly 95, untouched by the miss, same as
an exhausted FETCH leaves its own targets alone) — `CREATE TABLE IF NOT EXISTS` + a leading
`DELETE` keep it safely re-runnable, same convention `InventoryValueReport`/
`ManageInventory` already use.

**Verification**: full backend suite 552 passing (up from 505), zero regressions — one
existing test (`test_two_char_comparison_operator_does_not_round_trip`) was rewritten
(`..._now_round_trips_correctly`) since it had documented the OLD broken behavior this
phase's Fix 1 fixed as a side effect; two new dedicated files,
`test_comparison_operators.py` (25 tests: tokenizer lexing-order, parser, interpreter
evaluation across all three new operators plus regression checks that `>`/`<`/`=`/`!=` are
unaffected, a CASE/WHILE spot-check, the SQL-passthrough round-trip fix, and a still-invalid-
operator sanity check) and `test_select_into.py` (20 tests: parser dispatch/error cases,
found/zero-row/multi-row/column-mismatch/undeclared-target interpreter cases, the
NOT_FOUND-handler-doesn't-catch-multi-row check, coexistence with a separately declared
cursor in the same run, and two real `/debug`-endpoint end-to-end tests). Two new golden
fixtures (`OperatorShowcase.json`, `LookupOnePlayer.json`); the other 19 samples' fixtures
were confirmed byte-for-byte unchanged (only the two new ones needed
`UPDATE_GOLDENS=1`). `npm run lint`/`npm run build` both clean. Live-verified via headless
Chrome against a freshly started dev backend+frontend (none was already running this
session): `OperatorShowcase` loads and runs; hand-typed raw source using all three new
operators directly (not just the sample) parses, runs, and steps to a hand-verified final
value (`r = 111`, cross-checked against the automated tests); `LookupOnePlayer`'s step log
shows both `SELECT ... INTO` steps, the second tagged `NOT_FOUND` inline; the new SQL step
panel correctly shows "Assigned: foundScore = 95" for the found case and "No row matched --
foundScore left unchanged" plus the existing NOT_FOUND error banner for the miss, in both
themes. Cleaned up the real, already-running dev backend's `debug_history.db` rows (8, all
from this session's own live verification) and dropped the real `players` table that
verification created, confirming `user_data.db` was back to just its one seeded `products`
table afterward.
