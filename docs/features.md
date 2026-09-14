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
