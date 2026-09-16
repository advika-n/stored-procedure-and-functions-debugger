"""Tree-walking interpreter for the AST produced by :mod:`app.parser`.

Executes a ProcedureNode statement by statement against a variable
scope, and after *every* statement emits a :class:`DebugStep` — a
snapshot of "what just happened" that a frontend debugger UI can step
through one at a time.

Entry point::

    run(ast, initial_params) -> list[DebugStep]

Each DebugStep captures:
    stepNumber      -- 1-based order of execution
    line            -- source line the executed statement started on
    nodeType        -- AST node type that produced this step
    statementText   -- the statement rendered back to readable source
    variables       -- {name: {value, type, changed}} for every
                       variable currently in scope
    table           -- for CreateTableStatement/InsertStatement/
                       UpdateStatement/DeleteStatement steps only: the
                       affected table's name/operation/rowsAffected plus
                       a full current row snapshot -- see "User-created
                       tables" below
    branch          -- for IfStatement AND CaseStatement steps:
                       {condition, result, path} describing which way
                       the branch went; None for every other step (see
                       "CASE statement" below for CaseStatement's own
                       `path` values)

WhileStatement gets the same per-statement step treatment, plus one
extra step per loop-condition check carrying an analogous `loop`
object ({condition, result, iteration}) -- not part of the original
spec (which only calls out IfNode), but a natural extension so a
WHILE loop is traceable the same way an IF is. LoopStatement (LOOP ...
END LOOP, see "LOOP / LEAVE" below) reuses this exact same `loop` field
for its own per-iteration step, with `result` always True (a LOOP never
"fails" a condition check the way WHILE can) and `condition` a literal
`"LOOP"` / `"LOOP <label>"` string in place of a real boolean expression
(LOOP has none). To keep runaway procedures from hanging the
interpreter, loops are capped at MAX_LOOP_ITERATIONS -- LOOP reuses this
exact same cap rather than a separate one.

-- CASE statement -------------------------------------------------------

A CaseStatement (see app.parser's "CASE statement" section) covers both
common SQL CASE forms with ONE evaluation path, not two, since a simple
CASE (`CASE expr WHEN v1 THEN ... END CASE`) is just a searched CASE
(`CASE WHEN cond1 THEN ... END CASE`) where each WHEN's own test is
"does it equal the operand" instead of an independent boolean --
`_exec_case` evaluates `node["operand"]` once up front (only present
for simple CASE) and then, for each WHEN clause in order, compares it
against that WHEN's own value (`when_value == operand_value`) or, for
searched CASE (`operand is None`), just truthiness-checks the WHEN
expression directly (`bool(when_value)`) -- exactly the same `bool()`
coercion `_exec_if` already applies to its own condition. The FIRST
matching WHEN wins; its body runs and no later WHEN is even evaluated,
let alone run -- this is the same "short-circuit at the first match"
behavior every SQL CASE has, not a design choice specific to this
interpreter.

**Missing ELSE follows IF's own established convention, not a new
one**: no matching WHEN and no ELSE present is a silent no-op -- the
CaseStatement's own DebugStep is still recorded (so the decision point
itself is visible in the trace, exactly like an IF whose condition was
false with no ELSE branch), but no statement runs, and no
InterpreterError is raised. This mirrors `_exec_if` exactly (never
raising just because a condition didn't match and there was nothing
else to do) rather than adopting some other SQL dialect's
"CASE_NOT_FOUND"-style hard error, since introducing a new "this
particular statement can raise just by falling through" behavior would
be inconsistent with how every other decision point in this grammar
already works.

**Step-trace: reuses IfStatement's own `branch` field verbatim, per
this phase's own "reuse that mechanism" instruction** -- no new
DebugStep field was added or needed. `branch.condition` is the
operand's rendered text for simple CASE, or the literal string `"CASE"`
for searched CASE (there's no single boolean expression to render the
way an IF has exactly one condition); `branch.result` is `True` unless
nothing matched and there was no ELSE (`path == "none"`); `branch.path`
is `"when-<N>"` (0-based index of the matched WHEN clause), `"else"`,
or `"none"` -- the exact same three-way shape IfStatement's own
`"then"`/`"else"`/`"none"` already is, just with an open-ended
`"when-<N>"` in place of `"then"` to name WHICH of the (possibly many)
branches matched. Every existing consumer of `branch` needed to be
checked for whether it was actually generic over `path`'s possible
values or silently assumed IfStatement's exact two-value vocabulary --
verified directly, not assumed (see `frontend/src/cfg.js` and
`backend/app/explainer.py`, both of which needed a real fix; see their
own comments at the fixed call sites).

**DIVISION_BY_ZERO while evaluating the operand or any WHEN
expression** stops evaluation immediately (mirrors `_exec_if`'s "the
condition couldn't be evaluated -- don't guess a branch" exactly, just
generalized to a whole sequence of evaluations instead of one): no
further WHEN is checked, `matched_index` stays `None`, and the
statement falls through to ELSE/none -- even a WHEN clause several
positions later that would have matched is never reached, since a
handled DIVISION_BY_ZERO already means "this decision could not be
fully determined," not "skip just this one WHEN and keep going."

-- LOOP / LEAVE ----------------------------------------------------------

A LoopStatement (see app.parser's "LOOP / LEAVE" section) is executed by
`_exec_loop`, which is deliberately simpler than `_exec_while` in one
respect and reuses its exact machinery in another:

  - **Simpler**: LOOP has no condition of its own to evaluate each pass
    (unlike WHILE), so there is no per-iteration `_DivisionByZeroSignal`
    handling to do at the loop-header level at all -- only whatever
    statements are actually inside the body can raise one, and each of
    those is handled by its own statement executor exactly as it would
    be anywhere else in the procedure.
  - **Reused, not reinvented, per this phase's own instruction**: the
    runaway-loop safeguard is the *exact same* `MAX_LOOP_ITERATIONS`
    constant and cap-check `_exec_while` already uses -- a LOOP with no
    LEAVE (or one whose LEAVE never actually triggers) hits the same
    guard WHILE does, raising a clear InterpreterError rather than
    hanging.

Each pass through the body gets its own DebugStep, reusing WHILE's own
`loop: {condition, result, iteration}` field verbatim (no new DebugStep
field) so the existing step-trace UI needs no changes to show LOOP
iterations -- `condition` is the literal string `"LOOP"` (or `"LOOP
<label>"` for a labeled loop, since there's no single boolean expression
to render the way WHILE has exactly one condition) and `result` is
always `True` (a LOOP, by construction, never "fails" a condition check
the way a WHILE can -- the only ways out are an executed LEAVE, whose
own step is recorded separately below, or the MAX_LOOP_ITERATIONS guard
raising instead of ever recording a "false" iteration).

A LeaveStatement (`_exec_leave`) validates its target BEFORE recording
anything, matching every other statement's "structural problems raise
before the step" convention (e.g. `_exec_call`'s unknown-target check):
an unlabeled `LEAVE;` requires at least one currently-enclosing LOOP
(`self._loop_stack` non-empty); a labeled `LEAVE mylabel;` requires that
exact label to currently be somewhere on `self._loop_stack`. Once
validated, the LEAVE's own DebugStep is recorded (so the exit itself is
visible in the trace, symmetric with how a RETURN's own step is recorded
right before it unwinds), and an internal `_LeaveSignal(label)` is
raised. `_exec_loop` wraps its own body execution in a
`try/except _LeaveSignal`: an unlabeled signal, or one whose label
matches this exact loop, is caught here and simply stops the loop
(`break`); any other labeled signal is re-raised unchanged, so it keeps
unwinding outward through however many enclosing LOOPs it takes to reach
the one it actually names -- this is what makes `LEAVE outer;` from two
levels of LOOP nesting deep correctly skip the innermost loop entirely
rather than just stopping there. A validated LEAVE is therefore
*guaranteed* to be caught by some enclosing `_exec_loop` frame before it
could ever propagate past `Interpreter.run()` uncaught -- the validation
in `_exec_leave` and the push/pop discipline in `_exec_loop` keep
`self._loop_stack` an accurate mirror of "which labels are genuinely
still on the Python call stack" at every point.

**`self._loop_stack` is isolated per CALL/function-call frame**, exactly
like `cursors`/`handlers` already are (see "Procedure calls (CALL)"
below) -- saved and replaced with a fresh empty list around a callee's
own execution, restored afterward. This matters for real, not just
defensively: LOOP/LEAVE nesting is a purely lexical, single-procedure
concept (a LEAVE can only be *written* inside its own enclosing LOOP's
source), so without this isolation a callee could otherwise "LEAVE" a
label that happens to still be sitting on the caller's own
`_loop_stack` from an enclosing loop the callee's source has no lexical
relationship to at all -- clearly wrong, and now impossible by
construction.

-- User-created tables (CREATE TABLE / INSERT / UPDATE / DELETE) ----------

CreateTableStatement / InsertStatement / UpdateStatement / DeleteStatement
(see app.parser's own section of the same name) are executed against
``Interpreter.tables`` -- a plain Python dict, kept entirely separate
from both ``self.scope`` (these aren't SQL variables) and ``self._db``
(the real ``sqlite3.Connection`` cursor statements query -- see
"Cursors" below). **This is a deliberate simulation, not a second real
database**: per this phase's own "execution is simulated, not a real DB
engine" project convention, a table's rows are just a list of plain
dicts (`{"columns": [...], "rows": [{col: value, ...}, ...]}`), and a
WHERE clause is evaluated by `_evaluate_with_row` -- a thin wrapper that
temporarily layers a row's own column values on top of the current
scope and calls the *exact same* `_evaluate` every IF/WHILE condition
already uses, not a second expression-evaluation path. This is also why
a user-created table's rows are NOT queryable from a cursor's embedded
SELECT (that still only ever sees `self._db`'s fixed `products` demo
table -- see "Cursors" below): a real SQL engine round-trip was
deliberately not built for this feature, matching every other
"simulated, not real" construct in this interpreter.

**Scope: global for the whole run, never isolated per CALL/function-call
frame** -- unlike `cursors`/`handlers`/`_loop_stack` (all reset to a
fresh, empty per-invocation state around a callee -- see "Procedure
calls (CALL)" below), `self.tables` is treated exactly like `self._db`
already is: never saved/swapped in `_exec_call`/`_evaluate_function_call`
at all, so a table CREATEd or mutated by one procedure in a CALL chain is
immediately visible to every other procedure in that same chain, and
persists for the rest of the run. This is not a new convention invented
for this feature -- it's the exact same "global for the run, reset fresh
at the start of the next one" behavior `products`/`self._db` already
had (see app.demo_db's own module docstring), just followed rather than
reinvented, per this phase's own instruction to check that convention
first.

A column definition carries `name`/`col_type`/`not_null`/`primary_key`
(see app.parser). `col_type` is never validated against a fixed set (the
same "advisory, not enforced" treatment a DECLARE's own `var_type` or a
parameter's `type` already gets); `not_null`/`primary_key` ARE enforced,
by `_validate_row_constraints`, called from both INSERT and UPDATE:

  - A NULL value (the literal `NullLiteral`/Python `None`, or simply an
    omitted INSERT column) for a NOT NULL or PRIMARY KEY column is a
    clear InterpreterError -- PRIMARY KEY always implies NOT NULL, since
    a NULL primary key could never uniquely identify anything.
  - A PRIMARY KEY column's value must be unique across every OTHER row
    already in the table -- checked by linear scan (this grammar's
    tables are small course-project-scale data, not something needing
    an index), comparing by value, not row identity. UPDATE's own check
    excludes the row currently being updated from that scan (via
    `ignore_row`), so `UPDATE t SET id = id;` (a no-op rewrite of a
    PRIMARY KEY column back to its own existing value) is correctly
    NOT flagged as a duplicate of itself.

INSERT's column list is optional (see app.parser); when omitted,
`_exec_insert` binds `values` positionally against `self.tables[name]`'s
own CREATE-TABLE-declared column order -- the parser has no schema to
resolve that against, only the interpreter does, at the moment the
table actually exists. Every column not named by an explicit INSERT
column list (or by name, when the list IS given but omits some columns)
starts that row at `None`, exactly like an unsupplied DECLARE default --
subject to the same NOT NULL/PRIMARY KEY check immediately after.

UPDATE evaluates every matched row's SET assignments against that row's
ORIGINAL values -- standard SQL UPDATE semantics, not this interpreter's
own invention: `UPDATE t SET a = b, b = a;` swaps `a`/`b` rather than
letting the first assignment's new value leak into the second's
evaluation. All matched rows' new values are computed (and constraint-
checked) BEFORE any of them are actually written, so a constraint
violation partway through leaves every row completely unmodified. DELETE
removes matched rows by object identity (`id(row)`), never by structural
equality -- two rows that happen to hold identical values are still two
distinct rows, and a WHERE matching one of them must not also silently
remove the other.

Both UPDATE and DELETE support an optional WHERE clause (omitted means
"every row"); evaluating it via `_evaluate_with_row` is what actually
reuses the IF/WHILE condition-evaluation path per this phase's own
instruction (see above) -- a WHERE can reference the row's own columns
(`WHERE price > 100`) and/or any scalar variable already in scope
(`WHERE price > minPrice`) in the same expression, since the row's
values are layered ON TOP OF (and shadow, by name, same-named) the
current scope rather than replacing it. A DIVISION_BY_ZERO while
evaluating a WHERE, or any UPDATE assignment's own value expression,
follows the exact same statement-boundary handling every other statement
already uses (`_handle_division_by_zero`) -- non-fatal only if a handler
is registered, and if so, the statement's own step still records `error`
but zero rows end up affected, mirroring `_exec_set`'s "the assignment
simply didn't happen."

**Step-trace: a new `table` DebugStep field was genuinely needed, not
force-fit into an existing one** -- checked directly against every
existing field first: `variables` is `self.scope` only (a table's rows
aren't scope variables, and stuffing them in there would also break
Variable Timeline/report export, which assume every `variables` entry is
a single scalar); `cursor` describes a *read-only* SELECT cursor's
position, a different concept (reading vs. writing) with an incompatible
shape (one buffered row at a time, not a whole table's row list). The
new field, present only on a CREATE TABLE/INSERT/UPDATE/DELETE step
(omitted otherwise, exactly like `cursor`/`branch`/`loop` already are):

    table: {
        "name": str,
        "operation": "CREATE" | "INSERT" | "UPDATE" | "DELETE",
        "columns": [str, ...],       # column names, in CREATE TABLE order
        "rowsAffected": int,          # 0 for CREATE; 1 for a successful INSERT; the
                                      # matched-row count for UPDATE/DELETE (0 if
                                      # DIVISION_BY_ZERO made the statement a no-op)
        "row": {col: value, ...} | None,   # the just-inserted row (INSERT only)
        "rows": [{col: value, ...}, ...],  # the table's FULL current row snapshot,
    }                                       # right after this operation

`rows` is a full snapshot (not a diff) on purpose, mirroring how
`variables` itself always shows every variable's current value rather
than just the one that changed -- "table mutations visible in DebugStep
the same way variable mutations already are," per this phase's own
instruction, means the table's current state is always fully visible on
the step that touched it, not left for a client to reconstruct by
replaying every prior INSERT/UPDATE/DELETE itself.

-- Cursors ------------------------------------------------------------

CursorDeclNode / OpenCursorNode / FetchCursorNode / CloseCursorNode
(see app.parser) are executed against a real ``sqlite3.Connection`` --
by default a private in-memory one the Interpreter creates for itself,
or one the caller supplies (e.g. a test that has pre-seeded a table).
There is no schema-authoring feature yet, so a cursor's query against
the default connection will simply fail with SQLite's own "no such
table" error at OPEN time -- a deliberate, documented scope boundary,
not a bug.

Cursor state lives in ``Interpreter.cursors`` (keyed by cursor name),
kept entirely separate from ``self.scope``: cursors aren't SQL
variables and never appear in a DebugStep's `variables` snapshot or
the frontend's variable watch table. Each DebugStep for a cursor
statement instead carries a `cursor` object -- see DebugStep.to_dict.

OPEN eagerly runs the query and buffers every row (simplest possible
correct behavior for the small result sets this debugger deals with;
a real driver would stream). FETCH walks that buffered list one row
at a time; running past the end does not raise -- it's recorded as a
normal DebugStep with `cursor.hasMore = False` and no assignment to
the target variables, exactly like a real FETCH exhausting a cursor.

`cur%FOUND` and `cur%NOTFOUND` are NOT simple negations of each other
here, on purpose -- they're read predictively vs. retrospectively to
match how each is actually used idiomatically:

  - %FOUND is *predictive*: "is there a row ready for the next FETCH
    right now" (same value as `cursor.hasMore`). This is what makes
    `WHILE cur%FOUND DO ... FETCH ... END WHILE` work as an ordinary
    WHILE-checks-then-runs loop -- checked *before* each FETCH.
  - %NOTFOUND is *retrospective*: "did the most recently completed
    FETCH fail to find a row". This is what makes the
    `FETCH ...; IF cur%NOTFOUND THEN SET done = 1; ...` fallback
    pattern work -- checked *after* a FETCH, inside the loop body.

Deriving %NOTFOUND as `not %FOUND` would misfire: a FETCH that just
found the very last real row leaves nothing for *next* time, so
predictive %FOUND is already false, and `not %FOUND` would wrongly
read as "that FETCH failed" when it just succeeded. So each cursor
tracks its last FETCH's own outcome (`last_fetch_found`) separately
from its position, and %NOTFOUND reads that instead.

-- Exception handlers ---------------------------------------------------

`DECLARE CONTINUE HANDLER FOR NOT_FOUND <stmt>` and
`DECLARE CONTINUE HANDLER FOR DIVISION_BY_ZERO <stmt>` (see app.parser)
register a single statement to auto-run when that condition is
triggered. Handlers are procedure-scoped and registered in
``Interpreter.handlers`` (condition -> action AST) the moment their
DECLARE actually executes -- see app.parser's module docstring for why
there's no block scoping here.

When a condition triggers, the *triggering* statement's own DebugStep
always gets an `error` field: ``{condition, message, handler}``, where
`handler` names the registered handler or is the literal string
``"unhandled"``. If a handler *is* registered, its action statement runs
immediately after, as its own separate DebugStep -- so the trace reads
"the thing that failed" followed by "the handler responding to it".

The two conditions are NOT symmetric in how a missing handler behaves,
and that asymmetry is deliberate:

  - NOT_FOUND is always non-fatal, handled or not (this was already
    true before handlers existed at all -- a FETCH running past the
    end of a cursor was never a Python-level error, see "Cursors"
    above). An unhandled NOT_FOUND is fully visible in a live trace
    with `error.handler == "unhandled"`.
  - DIVISION_BY_ZERO keeps its pre-existing behavior when unhandled: it
    still raises InterpreterError and aborts the run, exactly as it did
    before handlers existed (so existing procedures that rely on a
    division mistake being loudly fatal keep working). It only becomes
    non-fatal -- recorded on the triggering step, target assignment
    skipped, handler action runs next -- once a
    `DECLARE CONTINUE HANDLER FOR DIVISION_BY_ZERO` is actually
    registered. Because of this, `error.handler == "unhandled"` for
    DIVISION_BY_ZERO is only ever a theoretical value (the interpreter
    raises before that step could be returned to a caller); the
    frontend still renders it correctly for consistency and in case a
    future caller wants a partial trace.

-- Functions ------------------------------------------------------------

A FunctionNode (see app.parser) runs through the exact same
`_execute_block`/`_execute_statement` machinery as a Procedure's body --
the only new piece is ReturnNode. Executing one evaluates its
expression, records a DebugStep with a `returnValue` field
(``{value, type}``), and then raises the internal `_ReturnSignal` to
unwind out of however many nested IF/WHILE blocks it's inside,
stopping the function immediately -- no statement after a RETURN ever
runs, even other statements later in the same block. `run()` is the
only place that catches `_ReturnSignal`.

Whether "the body finished without ever returning" is an error depends
on what's being run: a *function* must return something (its whole
point is to produce a value), so the module-level `run()` requires one
and raises InterpreterError if the body completes with no RETURN
having executed -- never a silent `None`. A *procedure* has no return
concept at all and is never held to this; `require_return` is only
ever set when the AST root is a FunctionNode.

A FunctionNode's own `CREATE FUNCTION ... RETURNS ... BEGIN` line isn't
itself a body statement, so without special handling it would never
appear in the trace at all -- step 1 would jump straight to whatever
the first body statement happens to be. `Interpreter.run()`'s
`entry_node` parameter fixes this: when set, one extra DebugStep is
recorded *before* the body's own first step, at the definition's own
line, with `nodeType` equal to the AST's own `"type"` (`"FunctionNode"`
or `"ProcedureNode"`) and `statementText` rendered by
`render_definition_header`. Its `variables` snapshot reflects whatever
`initial_params`/OUT-seeding already put in scope (see "Procedures with
declared params" below) -- i.e. what's true *at* entry, before any
DECLARE/SET in the body has run. The bare/legacy Procedure form has no
such line and never gets one; see the module-level `run()`.

-- Procedures with declared params ---------------------------------------

A ProcedureNode's params (see app.parser) carry a mode, and the
module-level `run()` treats each one differently before the
Interpreter ever starts executing statements:

  - IN params get no special treatment at all -- their value has to
    already be in the caller-supplied `initial_params`, same as any
    externally-referenced variable in a bare Procedure body has always
    worked. Referencing one that wasn't supplied is the same "not
    declared" InterpreterError it always was.
  - OUT params are auto-seeded to `None` if `initial_params` didn't
    already supply a value -- exactly like a DECLAREd variable with no
    DEFAULT -- since a pure output naturally starts with nothing from
    the caller. The procedure body is expected to SET it before the
    run ends, but nothing forces that; an OUT param that's never
    assigned just stays `None` in the final snapshot, same as any
    other declared-but-unset variable would.
  - INOUT params behave like IN for their starting value (must already
    be supplied) but are ALSO tracked as an output, same as OUT.

Being an output is purely informational: every DebugStep's `variables`
snapshot marks OUT/INOUT names with `isOutput: true` (see
`_snapshot_variables`), so a caller can tell which scope variables are
this procedure's declared outputs -- there is no runtime behavior
difference between an "output" variable and any other; a plain
Procedure or FunctionNode's variables are simply never marked this way
(`isOutput` is always `false` for them, since neither has OUT/INOUT
params by construction).

-- Procedure calls (CALL) -----------------------------------------------

A CallStatement (see app.parser) invokes another procedure -- looked up
by name in `Interpreter._procedures`, a registry built once by the
module-level `run()` from every CREATE PROCEDURE/CREATE FUNCTION
definition in the source (see app.parser's "CALL and multi-procedure
sources" section for how a submission gets more than one definition in
the first place, and why the entry procedure is registered under its
own name too, enabling self-recursion). `CALL` can only target a
ProcedureNode -- calling a FunctionNode's name, or a name nothing
defines, is a clear InterpreterError, not a crash.

**Scope isolation is total.** The callee does not see the caller's
variables, cursors, or handlers at all, and vice versa -- the ONLY
things that cross the boundary are the explicit argument values bound
to the callee's declared parameters (by mode, exactly like a top-level
call's `initial_params`/OUT-seeding already works -- see "Procedures
with declared params" above) and, after the callee returns, its
OUT/INOUT parameters' final values written back into the caller's own
variables. `_exec_call` implements this by saving the caller's current
`scope`/`_previous_values`/`_output_param_names`/`cursors`/`handlers`,
replacing them with fresh ones for the callee, recursively invoking
`Interpreter.run()` on the callee's body (reusing its entry-step and
`_ReturnSignal` handling unchanged -- a procedure invoked via CALL can
contain a bare RETURN to stop early, exactly like any other procedure
body already could), and restoring the caller's saved state once the
callee returns -- `self.steps`/`self._step_number` are NEVER swapped,
so the whole call chain accumulates into one continuous, flat trace.

An OUT or INOUT argument must be a plain Identifier (a variable already
in the caller's scope) -- there is no way to "write back" into an
arbitrary expression like `x + 1`, so passing one for an OUT/INOUT
parameter is a clear InterpreterError raised before anything executes.
An IN argument can be any expression, evaluated once in the CALLER's
scope before the callee's frame is installed.

**Recursion is allowed** (a procedure calling itself, directly or
through a chain of other procedures) -- `Interpreter._call_depth`
counts how many CALLs are currently nested, and `MAX_CALL_DEPTH` caps
it, raising a clear InterpreterError (not a runaway Python recursion
crash / hung server) if a call would exceed it.

**Division-by-zero while evaluating a CALL's own arguments** follows
the same "the statement's own DebugStep gets recorded, then the caller
decides what happens next" pattern every other statement already uses:
if a registered DIVISION_BY_ZERO handler makes it non-fatal, the CALL
statement's own step still gets recorded (with the `error` field, and
the handler's action runs right after, exactly as elsewhere) but the
call itself simply never happens -- the callee's body never executes --
mirroring `_exec_set`'s "the assignment simply didn't happen." If
unhandled, it raises and aborts the whole run, same as anywhere else.

**Step-trace visibility into the call** (so a future call-stack UI can
be built on top of this data without any interpreter changes): every
DebugStep recorded while `_call_depth > 0` -- i.e. every step belonging
to a CALLed procedure's own execution, including its synthetic entry
step -- carries an extra `call` field:

    call: { "procedureName": str, "depth": int, "stack": [str, ...] }

`stack` is the full chain of enclosing procedure names from outermost
to innermost (its own last element is always `procedureName`, and
`len(stack) == depth`) -- included so a future frontend doesn't need to
replay the whole trace and track depth deltas itself just to know which
procedures are "currently on the stack" at any given step. A step that
executes at the TOP level (never inside any CALL, `_call_depth == 0`,
which is every trace that existed before this feature) has NO `call`
key at all -- omitted, exactly like `branch`/`loop`/`cursor`/`error`
already are when not applicable, so every pre-existing trace's wire
shape is completely unchanged. The CALL statement's OWN step (e.g.
"CALL Foo(a, b);") is recorded in the CALLER's frame, at the caller's
own depth, BEFORE the callee's frame is installed -- so if the caller
itself is top-level, the CALL statement's step has no `call` field
either; only steps genuinely running *inside* Foo get depth >= 1.

-- Function calls in expressions ----------------------------------------

A FunctionCallExpr (see app.parser's "Function calls in expressions"
section) is the expression-position counterpart to CALL: it can appear
anywhere an expression can (an assignment's right-hand side, an
IF/WHILE condition, a RETURN's own value, another call's argument, ...)
and evaluates to the callee's RETURNed value, substituted directly into
the surrounding expression -- `SET total = ComputeTax(price) + fee;`
runs the whole ComputeTax function and uses its result exactly like any
other sub-expression.

`_evaluate_function_call` deliberately reuses the *exact same*
scope-isolation/call-depth/call-stack machinery `_exec_call` already
established for CALL -- not a second implementation of any of it. The
differences from `_exec_call` are narrow and specific to being an
expression rather than a statement:

  - The target must be a FunctionNode, not a ProcedureNode (calling a
    ProcedureNode's name this way, or CALLing a FunctionNode's name
    the other way, are both clear InterpreterErrors -- the two
    mechanisms are deliberately kept exclusive, matching how a real
    SQL dialect keeps "invoke for a value" and "invoke for a side
    effect" as genuinely different operations).
  - A FunctionNode's params never carry a mode (see app.parser's
    "Functions" section) -- every argument is evaluated once in the
    CALLER's scope and bound like an IN argument; there is no
    OUT/INOUT propagation to unwind afterward, so `_evaluate_function_
    call`'s cleanup is correspondingly simpler than `_exec_call`'s.
  - `run()` is invoked with `require_return=True` (a function must
    RETURN something, exactly like a top-level function call already
    requires) instead of the `False` a procedure CALL uses, and the
    RETURNed value is captured via `self._last_return_value` --
    `_exec_return` stores its own `{value, type}` there immediately
    before raising `_ReturnSignal`, and `_evaluate_function_call` reads
    it back immediately after the matching `run()` call returns
    (`_ReturnSignal` only ever unwinds as far as the nearest catching
    `run()` frame -- the one this exact call just started -- so no
    other RETURN, at any depth, can overwrite it in between; a nested
    function call evaluated while building that RETURN's own value
    resolves and is fully consumed before this RETURN's `_exec_return`
    ever runs).

**A DIVISION_BY_ZERO while evaluating one of a FunctionCallExpr's own
argument expressions needs no special handling at all** -- unlike
CALL (a statement, so it needs its own try/except to decide whether a
registered handler makes it non-fatal right there), a FunctionCallExpr
is just one more sub-expression; `_DivisionByZeroSignal` simply
propagates up through `_evaluate` exactly like it already does from
deep inside any other compound expression (e.g. `(a / b) + 1`), and is
caught by whichever *enclosing statement's* own try/except is already
watching for it (`_exec_set`, `_exec_if`, ...) -- attached to that
statement's DebugStep, not a step of its own. An unhandled
InterpreterError from anywhere inside the callee's own body (including
one from a DIVISION_BY_ZERO with no handler registered *inside that
callee*) is likewise not caught here -- it propagates all the way up
and aborts the whole run, exactly like an unhandled error inside a
CALLed procedure already does; `_evaluate_function_call`'s `finally`
block only ever restores scope/cursors/handlers state, it never
swallows an error.

**Step-trace / Call Stack schema: no change needed, verified rather
than assumed.** `_evaluate_function_call` increments `_call_depth` and
pushes onto `_call_stack` exactly like `_exec_call` does, so
`_current_call_info`/`_record_step` -- already fully generic over
*what* is on the stack -- produce the identical `call` shape for a
step running inside a called FUNCTION as they already do for a called
PROCEDURE, with zero code changes to either. The one naming wrinkle,
flagged rather than silently ignored: the field is still called
`call.procedureName` (a name chosen back when only procedures could be
CALLed) even though it may now hold a *function's* name -- deliberately
NOT renamed, since `DebugStep` is this app's central wire contract
(see CLAUDE.md SS4) and a field rename ripples through every consumer
(the Call Stack panel, the Variable Timeline, Download reports, ...)
for a purely cosmetic gain; the value itself (whichever definition is
currently executing) is exactly what every existing consumer already
wants, and a future caller that specifically needs to know "is this
frame a function or a procedure" can already answer that by cross-
referencing the name against `ast`'s own definitions client-side --
exactly what the frontend's `entryProcedureName` derivation already
does for the entry frame, so no interpreter data is actually missing.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field

MAX_LOOP_ITERATIONS = 10_000

# How many CALLs may be nested at once (see module docstring's
# "Procedure calls (CALL)" section) -- generous enough for any
# legitimate course-project-scale recursion, but low enough to fail
# with a clear InterpreterError, not a hung server or a Python
# RecursionError, well before Python's own default recursion limit
# (each nested CALL costs a handful of real Python stack frames, since
# `_exec_call` recurses through `run`/`_execute_block`/
# `_execute_statement`).
MAX_CALL_DEPTH = 50


class InterpreterError(RuntimeError):
    """Raised for runtime errors while executing the AST (undefined
    variable, division by zero, a runaway loop, ...)."""

    def __init__(self, message: str, line: int | None = None):
        if line is not None:
            message = f"{message} (line {line})"
        super().__init__(message)
        self.line = line


class _DivisionByZeroSignal(Exception):
    """Internal control-flow signal, never surfaced to callers: raised
    by `_evaluate_binary` on a `/` by zero, and caught at each
    top-level statement boundary (_exec_declare, _exec_set, _exec_if,
    _exec_while) so that boundary can decide -- per the module
    docstring's "Exception handlers" section -- whether a registered
    CONTINUE HANDLER makes this non-fatal, or whether it should still
    become the ordinary, procedure-aborting InterpreterError it always
    was before handlers existed."""

    def __init__(self, line: int | None):
        super().__init__("Division by zero")
        self.line = line


_HANDLER_LABELS = {
    "NOT_FOUND": "NOT_FOUND handler",
    "DIVISION_BY_ZERO": "DIVISION_BY_ZERO handler",
}


class _ReturnSignal(Exception):
    """Internal control-flow signal, never surfaced to callers: raised
    by `_exec_return` once its DebugStep has been recorded, to unwind
    out of any nested IF/WHILE blocks and stop executing further
    statements. Caught only in `Interpreter.run()`. See the module
    docstring's "Functions" section."""


class _LeaveSignal(Exception):
    """Internal control-flow signal, never surfaced to callers: raised
    by `_exec_leave` once its DebugStep has been recorded and its target
    validated, to unwind out of however many nested IF/WHILE/CASE/LOOP
    blocks it takes to reach the LOOP it names. Caught only by
    `_exec_loop`, which either stops that loop (an unlabeled signal, or
    one whose label matches this exact loop) or re-raises it unchanged
    to keep unwinding outward. See the module docstring's "LOOP / LEAVE"
    section."""

    def __init__(self, label: str | None):
        super().__init__(f"LEAVE {label}" if label else "LEAVE")
        self.label = label


@dataclass
class DebugStep:
    step_number: int
    line: int
    node_type: str
    statement_text: str
    variables: dict
    branch: dict | None = None
    loop: dict | None = None
    cursor: dict | None = None
    error: dict | None = None
    return_value: dict | None = None
    call: dict | None = None
    table: dict | None = None

    def to_dict(self) -> dict:
        """Serialize using the camelCase keys the frontend expects."""
        step = {
            "stepNumber": self.step_number,
            "line": self.line,
            "nodeType": self.node_type,
            "statementText": self.statement_text,
            "variables": self.variables,
        }
        if self.branch is not None:
            step["branch"] = self.branch
        if self.loop is not None:
            step["loop"] = self.loop
        if self.cursor is not None:
            step["cursor"] = self.cursor
        if self.error is not None:
            step["error"] = self.error
        if self.return_value is not None:
            step["returnValue"] = self.return_value
        if self.call is not None:
            step["call"] = self.call
        if self.table is not None:
            step["table"] = self.table
        return step


# -- rendering AST nodes back to readable source text ------------------------

_BINARY_OPERATOR_TEXT = {"+", "-", "*", "/", ">", "<", "=", "!="}


def render_expr(node: dict) -> str:
    """Render an expression node back into SQL-ish source text."""
    kind = node["type"]
    if kind == "NumberLiteral":
        return str(node["value"])
    if kind == "StringLiteral":
        return f"'{node['value']}'"
    if kind == "NullLiteral":
        return "NULL"
    if kind == "Identifier":
        return node["name"]
    if kind == "UnaryExpr":
        return f"{node['operator']}{render_expr(node['operand'])}"
    if kind == "BinaryExpr":
        return (
            f"{render_expr(node['left'])} {node['operator']} "
            f"{render_expr(node['right'])}"
        )
    if kind == "CursorFoundExpr":
        return f"{node['cursor']}%FOUND"
    if kind == "CursorNotFoundExpr":
        return f"{node['cursor']}%NOTFOUND"
    if kind == "FunctionCallExpr":
        args = ", ".join(render_expr(arg) for arg in node["args"])
        return f"{node['name']}({args})"
    raise InterpreterError(f"Cannot render unknown expression node {kind!r}")


def render_statement_header(node: dict) -> str:
    """Render just the statement's own line (no nested block body)."""
    kind = node["type"]
    if kind == "DeclareStatement":
        text = f"DECLARE {node['name']} {node['var_type']}"
        if node["default"] is not None:
            text += f" DEFAULT {render_expr(node['default'])}"
        return text + ";"
    if kind == "SetStatement":
        return f"SET {node['target']} = {render_expr(node['value'])};"
    if kind == "IfStatement":
        return f"IF {render_expr(node['condition'])} THEN"
    if kind == "WhileStatement":
        return f"WHILE {render_expr(node['condition'])} DO"
    if kind == "CaseStatement":
        return f"CASE {render_expr(node['operand'])}" if node["operand"] is not None else "CASE"
    if kind == "LoopStatement":
        return f"{node['label']}: LOOP" if node["label"] else "LOOP"
    if kind == "LeaveStatement":
        return f"LEAVE {node['label']};" if node["label"] else "LEAVE;"
    if kind == "CursorDeclNode":
        return f"DECLARE {node['name']} CURSOR FOR {node['query']};"
    if kind == "OpenCursorNode":
        return f"OPEN {node['name']};"
    if kind == "FetchCursorNode":
        return f"FETCH {node['name']} INTO {', '.join(node['targets'])};"
    if kind == "CloseCursorNode":
        return f"CLOSE {node['name']};"
    if kind == "HandlerDeclNode":
        # render_statement_header(action) already ends in ';' -- no
        # extra trailing punctuation needed here.
        return f"DECLARE CONTINUE HANDLER FOR {node['condition']} {render_statement_header(node['action'])}"
    if kind == "ReturnNode":
        return f"RETURN {render_expr(node['value'])};"
    if kind == "CallStatement":
        args = ", ".join(render_expr(arg) for arg in node["args"])
        return f"CALL {node['name']}({args});"
    if kind == "CreateTableStatement":
        columns = ", ".join(_render_column_def(c) for c in node["columns"])
        return f"CREATE TABLE {node['name']} ({columns});"
    if kind == "InsertStatement":
        columns = f" ({', '.join(node['columns'])})" if node["columns"] is not None else ""
        values = ", ".join(render_expr(v) for v in node["values"])
        return f"INSERT INTO {node['table']}{columns} VALUES ({values});"
    if kind == "UpdateStatement":
        assignments = ", ".join(f"{a['column']} = {render_expr(a['value'])}" for a in node["assignments"])
        where = f" WHERE {render_expr(node['where'])}" if node["where"] is not None else ""
        return f"UPDATE {node['table']} SET {assignments}{where};"
    if kind == "DeleteStatement":
        where = f" WHERE {render_expr(node['where'])}" if node["where"] is not None else ""
        return f"DELETE FROM {node['table']}{where};"
    raise InterpreterError(f"Cannot render unknown statement node {kind!r}")


def _render_column_def(column: dict) -> str:
    """Render one CREATE TABLE column definition back to source text --
    used only by render_statement_header's own CreateTableStatement case
    above."""
    text = f"{column['name']} {column['col_type']}"
    if column.get("not_null"):
        text += " NOT NULL"
    if column.get("primary_key"):
        text += " PRIMARY KEY"
    return text


def render_definition_header(ast: dict) -> str:
    """Render the CREATE FUNCTION/CREATE PROCEDURE signature line
    itself -- the one line in a wrapped definition that isn't a body
    statement, so it has no node of its own for render_statement_header
    to handle. Used only to label the synthetic "entry" DebugStep (see
    Interpreter.run) recorded once, before the body's own first step."""
    kind = ast["type"]
    if kind == "FunctionNode":
        params = ", ".join(f"{p['name']} {p['type']}" for p in ast.get("params") or [])
        return f"CREATE FUNCTION {ast['name']}({params}) RETURNS {ast['returnType']}"
    if kind == "ProcedureNode":
        params = ", ".join(f"{p.get('mode', 'IN')} {p['name']} {p['type']}" for p in ast.get("params") or [])
        return f"CREATE PROCEDURE {ast['name']}({params})"
    raise InterpreterError(f"Cannot render an entry step for AST type {kind!r}")


# -- value <-> debugger type name ---------------------------------------------


def _type_name(value) -> str:
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, (int, float)):
        return "number"
    if isinstance(value, str):
        return "string"
    if value is None:
        return "null"
    return type(value).__name__


class Interpreter:
    def __init__(
        self,
        initial_params: dict,
        db_connection: sqlite3.Connection | None = None,
        output_param_names: set[str] | None = None,
        procedures: dict[str, dict] | None = None,
    ):
        self.scope: dict = dict(initial_params)
        self.steps: list[DebugStep] = []
        self._step_number = 0
        # Baseline for diffing "changed": start from the params as given,
        # so a param that's never touched shows changed=False throughout.
        self._previous_values: dict = dict(initial_params)

        # Names of ProcedureNode OUT/INOUT params (see module
        # docstring's "Procedures with declared params" section) --
        # purely informational, surfaced per-variable as `isOutput` in
        # every DebugStep's snapshot so a caller can identify which
        # scope variables are this procedure's outputs, without the
        # interpreter otherwise treating them any differently.
        self._output_param_names: set[str] = set(output_param_names or ())

        # Cursors, keyed by name -- deliberately separate from `scope`
        # (see module docstring's "Cursors" section). Each entry:
        # {"query": str, "rows": [dict, ...], "pos": int, "open": bool}.
        self.cursors: dict[str, dict] = {}

        # Exception handlers, keyed by condition ("NOT_FOUND" or
        # "DIVISION_BY_ZERO") -> that handler's action statement AST.
        # See module docstring's "Exception handlers" section.
        self.handlers: dict[str, dict] = {}

        # User-created tables (see module docstring's "User-created
        # tables" section), keyed by name -- {"columns": [...], "rows":
        # [{col: value, ...}, ...]}. Deliberately GLOBAL for the whole
        # run, never saved/swapped around a CALL/function-call frame
        # (unlike cursors/handlers/_loop_stack above) -- follows the
        # exact same "shared across the whole call chain, reset fresh
        # next run" convention `self._db` (below) already established
        # for the fixed `products` demo table, per this phase's own
        # instruction to check that convention first rather than invent
        # a new one.
        self.tables: dict[str, dict] = {}

        # Own a private in-memory connection unless the caller supplies
        # one (e.g. a test that pre-seeded a table) -- closed again in
        # the module-level `run()` below, only if we're the ones who
        # opened it.
        self._db = db_connection if db_connection is not None else sqlite3.connect(":memory:")
        self._owns_db = db_connection is None

        # CALL support (see module docstring's "Procedure calls" section).
        # `_procedures` is the name -> ProcedureNode/FunctionNode registry
        # a CALL statement resolves against, built once by the
        # module-level `run()` before any statement executes. `_call_depth`
        # / `_call_stack` track how deep the current CALL chain is and
        # which procedure names are on it (outermost first) -- both stay
        # at their starting values (0 / []) for any run that never uses
        # CALL, so they never affect step recording for the common case.
        self._procedures: dict[str, dict] = procedures or {}
        self._call_depth = 0
        self._call_stack: list[str] = []

        # LOOP/LEAVE nesting (see module docstring's "LOOP / LEAVE"
        # section) -- innermost-last list of currently-active LOOP
        # labels (None for an unlabeled LOOP), pushed/popped by
        # `_exec_loop`. Isolated per CALL/function-call frame exactly
        # like `cursors`/`handlers` (saved/replaced around a callee's
        # own execution -- see `_exec_call`/`_evaluate_function_call`),
        # since loop nesting is a purely lexical, single-procedure
        # concept. Stays empty for any run that never uses LOOP.
        self._loop_stack: list[str | None] = []

        # The most recently RETURNed `{value, type}` (see module
        # docstring's "Function calls in expressions" section) -- set by
        # `_exec_return` immediately before it raises `_ReturnSignal`,
        # and read by `_evaluate_function_call` immediately after the
        # matching `run()` call returns. Never read at the top level
        # (nothing there calls `_evaluate_function_call`), so this has
        # no effect on any run that never uses an expression-position
        # function call.
        self._last_return_value: dict | None = None

    # -- public API -----------------------------------------------------------

    def run(
        self,
        body: list[dict],
        require_return: bool = False,
        function_name: str | None = None,
        entry_node: dict | None = None,
    ) -> list[DebugStep]:
        # A wrapped CREATE FUNCTION/CREATE PROCEDURE definition gets one
        # extra DebugStep first, for the CREATE .../BEGIN signature line
        # itself -- there's no AST node inside `body` for that line, so
        # without this, step 1 would jump straight to whatever the first
        # body statement happens to be (its DECLARE, if it has one, or
        # further still if it doesn't) and the definition line would
        # never appear in the trace at all. The bare/legacy Procedure
        # form (no CREATE wrapper) has no such line to represent, so
        # `entry_node` is None for it and this is skipped entirely --
        # its first step is exactly what it always was.
        if entry_node is not None:
            self._record_step(entry_node, render_definition_header(entry_node))
        elif not body:
            # The bare/legacy form has no CREATE header line to give an
            # entry step to (see above) -- but when its body is ALSO
            # completely empty, that used to mean a genuinely
            # zero-length trace: a `Procedure` node with no statements
            # falls straight through the loop below and never touches
            # `self.steps` at all. That was an inconsistency with the
            # wrapped forms just above, which always get >= 1 step even
            # with an empty body (their entry step). Fixed by giving
            # this one specific case -- and ONLY this case, so a bare
            # body with at least one statement is completely unaffected
            # and every existing golden trace stays byte-for-byte the
            # same -- a synthetic step of its own, using a placeholder
            # node (there's no real source line to point at) rather than
            # `render_definition_header`, which only knows how to render
            # a FunctionNode/ProcedureNode's signature line.
            self._record_step({"type": "Procedure", "line": 1}, "(empty procedure body)")

        returned = False
        try:
            self._execute_block(body)
        except _ReturnSignal:
            returned = True

        if require_return and not returned:
            label = f"Function '{function_name}'" if function_name else "This function"
            raise InterpreterError(f"{label} completed without executing a RETURN statement")

        return self.steps

    # -- statement execution ----------------------------------------------

    def _execute_block(self, statements: list[dict]) -> None:
        for statement in statements:
            self._execute_statement(statement)

    def _execute_statement(self, node: dict) -> None:
        kind = node["type"]
        if kind == "DeclareStatement":
            self._exec_declare(node)
        elif kind == "SetStatement":
            self._exec_set(node)
        elif kind == "IfStatement":
            self._exec_if(node)
        elif kind == "WhileStatement":
            self._exec_while(node)
        elif kind == "CaseStatement":
            self._exec_case(node)
        elif kind == "CursorDeclNode":
            self._exec_declare_cursor(node)
        elif kind == "OpenCursorNode":
            self._exec_open_cursor(node)
        elif kind == "FetchCursorNode":
            self._exec_fetch_cursor(node)
        elif kind == "CloseCursorNode":
            self._exec_close_cursor(node)
        elif kind == "HandlerDeclNode":
            self._exec_declare_handler(node)
        elif kind == "ReturnNode":
            self._exec_return(node)
        elif kind == "CallStatement":
            self._exec_call(node)
        elif kind == "LoopStatement":
            self._exec_loop(node)
        elif kind == "LeaveStatement":
            self._exec_leave(node)
        elif kind == "CreateTableStatement":
            self._exec_create_table(node)
        elif kind == "InsertStatement":
            self._exec_insert(node)
        elif kind == "UpdateStatement":
            self._exec_update(node)
        elif kind == "DeleteStatement":
            self._exec_delete(node)
        else:
            raise InterpreterError(
                f"Don't know how to execute node type {kind!r}", node.get("line")
            )

    def _exec_declare(self, node: dict) -> None:
        value = None
        error_info = None
        if node["default"] is not None:
            try:
                value = self._evaluate(node["default"])
            except _DivisionByZeroSignal as signal:
                error_info = self._handle_division_by_zero(signal)
        self.scope[node["name"]] = value
        self._record_step(node, render_statement_header(node), error=error_info)
        self._run_handler_if_triggered(error_info)

    def _exec_set(self, node: dict) -> None:
        target = node["target"]
        if target not in self.scope:
            raise InterpreterError(
                f"Variable '{target}' is not declared", node["line"]
            )
        error_info = None
        try:
            self.scope[target] = self._evaluate(node["value"])
        except _DivisionByZeroSignal as signal:
            # Target keeps its previous value -- the assignment simply
            # didn't happen, same as the expression never completing.
            error_info = self._handle_division_by_zero(signal)
        self._record_step(node, render_statement_header(node), error=error_info)
        self._run_handler_if_triggered(error_info)

    def _exec_if(self, node: dict) -> None:
        error_info = None
        try:
            condition_value = self._evaluate(node["condition"])
            result = bool(condition_value)
        except _DivisionByZeroSignal as signal:
            error_info = self._handle_division_by_zero(signal)
            result = False  # condition couldn't be evaluated -- don't guess a branch

        if result:
            path = "then"
        elif node["else_body"] is not None:
            path = "else"
        else:
            path = "none"

        branch = {
            "condition": render_expr(node["condition"]),
            "result": result,
            "path": path,
        }
        self._record_step(node, render_statement_header(node), branch=branch, error=error_info)
        self._run_handler_if_triggered(error_info)

        if result:
            self._execute_block(node["then_body"])
        elif node["else_body"] is not None:
            self._execute_block(node["else_body"])

    def _exec_case(self, node: dict) -> None:
        """Execute a CaseStatement (both simple and searched CASE -- see
        the module docstring's "CASE statement" section). Reuses the
        exact same `branch` DebugStep field IfStatement already uses,
        just with a `path` of `"when-<index>"` instead of `"then"` --
        every existing `branch` consumer (the Call Stack/step-trace UI,
        explainer.py, report.py, cfg.js's flowchart highlighting) reads
        `path` as a plain string, so this needed no new field, per this
        phase's own "reuse that mechanism" instruction."""
        error_info = None
        matched_index = None
        try:
            operand_value = self._evaluate(node["operand"]) if node["operand"] is not None else None
            for index, clause in enumerate(node["when_clauses"]):
                when_value = self._evaluate(clause["when"])
                matches = when_value == operand_value if node["operand"] is not None else bool(when_value)
                if matches:
                    matched_index = index
                    break
        except _DivisionByZeroSignal as signal:
            # Mirrors _exec_if exactly: couldn't finish evaluating the
            # operand or one of the WHEN expressions, so don't guess a
            # match -- fall through to ELSE/none, same as an IF whose
            # condition itself couldn't be evaluated.
            error_info = self._handle_division_by_zero(signal)
            matched_index = None

        if matched_index is not None:
            path = f"when-{matched_index}"
        elif node["else_body"] is not None:
            path = "else"
        else:
            path = "none"

        branch = {
            "condition": render_expr(node["operand"]) if node["operand"] is not None else "CASE",
            "result": path != "none",
            "path": path,
        }
        self._record_step(node, render_statement_header(node), branch=branch, error=error_info)
        self._run_handler_if_triggered(error_info)

        if matched_index is not None:
            self._execute_block(node["when_clauses"][matched_index]["body"])
        elif node["else_body"] is not None:
            self._execute_block(node["else_body"])

    def _exec_while(self, node: dict) -> None:
        iteration = 0
        while True:
            error_info = None
            try:
                condition_value = self._evaluate(node["condition"])
                result = bool(condition_value)
            except _DivisionByZeroSignal as signal:
                error_info = self._handle_division_by_zero(signal)
                result = False  # can't evaluate the condition -- exit rather than spin

            iteration += 1
            if iteration > MAX_LOOP_ITERATIONS:
                raise InterpreterError(
                    f"WHILE loop exceeded {MAX_LOOP_ITERATIONS} iterations "
                    "(possible infinite loop)",
                    node["line"],
                )

            loop = {
                "condition": render_expr(node["condition"]),
                "result": result,
                "iteration": iteration,
            }
            self._record_step(node, render_statement_header(node), loop=loop, error=error_info)
            self._run_handler_if_triggered(error_info)

            if not result:
                break
            self._execute_block(node["body"])

    def _exec_loop(self, node: dict) -> None:
        """Execute a LoopStatement -- see the module docstring's "LOOP /
        LEAVE" section for the full design. Unlike `_exec_while`, there
        is no condition to evaluate each pass (so no per-iteration
        DIVISION_BY_ZERO handling at this level); the runaway-loop
        safeguard is the same `MAX_LOOP_ITERATIONS` cap `_exec_while`
        already uses, reused rather than reinvented."""
        label = node["label"]
        self._loop_stack.append(label)
        try:
            iteration = 0
            while True:
                iteration += 1
                if iteration > MAX_LOOP_ITERATIONS:
                    loop_desc = f"LOOP {label}" if label else "LOOP"
                    raise InterpreterError(
                        f"{loop_desc} exceeded {MAX_LOOP_ITERATIONS} iterations (possible "
                        "infinite loop -- use LEAVE to exit)",
                        node["line"],
                    )

                loop_info = {
                    "condition": f"LOOP {label}" if label else "LOOP",
                    "result": True,
                    "iteration": iteration,
                }
                self._record_step(node, render_statement_header(node), loop=loop_info)

                try:
                    self._execute_block(node["body"])
                except _LeaveSignal as signal:
                    if signal.label is None or signal.label == label:
                        break
                    raise  # targets a different (outer) loop -- keep unwinding
        finally:
            self._loop_stack.pop()

    def _exec_leave(self, node: dict) -> None:
        """Execute a LeaveStatement -- see the module docstring's "LOOP /
        LEAVE" section. Target validation happens BEFORE anything is
        recorded, matching every other statement's "structural problems
        raise before the step" pattern (e.g. `_exec_call`'s unknown-
        target check); once validated, the step is recorded (so the exit
        itself is visible in the trace) and `_LeaveSignal` unwinds to the
        matching `_exec_loop` frame."""
        label = node["label"]
        if label is None:
            if not self._loop_stack:
                raise InterpreterError("LEAVE used outside of any LOOP", node["line"])
        elif label not in self._loop_stack:
            raise InterpreterError(
                f"LEAVE {label}: no enclosing LOOP is labeled '{label}'", node["line"]
            )

        self._record_step(node, render_statement_header(node))
        raise _LeaveSignal(label)

    # -- user-created tables (CREATE TABLE / INSERT / UPDATE / DELETE) ------
    # See the module docstring's own section of the same name for the full
    # design (scope, constraint enforcement, WHERE evaluation, the `table`
    # DebugStep field).

    def _require_table(self, name: str, line: int | None) -> dict:
        table = self.tables.get(name)
        if table is None:
            raise InterpreterError(f"Table '{name}' is not declared", line)
        return table

    def _table_step_info(
        self, name: str, operation: str, rows_affected: int, row: dict | None = None
    ) -> dict:
        table = self.tables[name]
        return {
            "name": name,
            "operation": operation,
            "columns": [c["name"] for c in table["columns"]],
            "rowsAffected": rows_affected,
            "row": dict(row) if row is not None else None,
            "rows": [dict(r) for r in table["rows"]],
        }

    def _validate_row_constraints(
        self, table_name: str, table: dict, row: dict, line: int | None, ignore_row: dict | None
    ) -> None:
        """Enforce NOT NULL/PRIMARY KEY for one candidate row (already
        merged with its own new values -- the caller decides what `row`
        actually contains). Called from both INSERT (a brand-new row,
        `ignore_row=None`) and UPDATE (a row's prospective new values,
        `ignore_row` set to that same row object so it isn't compared
        against itself in the PRIMARY KEY uniqueness scan)."""
        for column in table["columns"]:
            name = column["name"]
            value = row.get(name)
            if value is None and (column.get("not_null") or column.get("primary_key")):
                raise InterpreterError(
                    f"Column '{name}' of table '{table_name}' is NOT NULL and cannot be NULL",
                    line,
                )
            if column.get("primary_key"):
                for existing in table["rows"]:
                    if existing is ignore_row:
                        continue
                    if existing.get(name) == value:
                        raise InterpreterError(
                            f"Duplicate value {value!r} for PRIMARY KEY column '{name}' of "
                            f"table '{table_name}'",
                            line,
                        )

    def _evaluate_with_row(self, node: dict, row: dict):
        """Evaluate an ordinary expression (see app.parser's `expr`
        grammar) with `row`'s own column values additionally available
        by name, layered on top of (and shadowing, by name) the current
        scope -- reuses `_evaluate` verbatim rather than a second
        expression-evaluation path, per this phase's own "reuse whatever
        conditions/IF already use" instruction. Backs UPDATE/DELETE's
        WHERE clause and UPDATE's own SET value expressions, both of
        which need a row's column values visible alongside whatever
        scalar variables the enclosing procedure already has in scope
        (e.g. `WHERE price > minPrice`, `SET price = price * 1.1`)."""
        saved_scope = self.scope
        self.scope = {**self.scope, **row}
        try:
            return self._evaluate(node)
        finally:
            self.scope = saved_scope

    def _exec_create_table(self, node: dict) -> None:
        name = node["name"]
        if name in self.tables:
            raise InterpreterError(f"Table '{name}' is already declared", node["line"])

        seen_names: set[str] = set()
        for column in node["columns"]:
            if column["name"] in seen_names:
                raise InterpreterError(
                    f"Table '{name}' has a duplicate column '{column['name']}'", node["line"]
                )
            seen_names.add(column["name"])

        self.tables[name] = {"columns": [dict(c) for c in node["columns"]], "rows": []}
        table_info = self._table_step_info(name, "CREATE", rows_affected=0)
        self._record_step(node, render_statement_header(node), table=table_info)

    def _exec_insert(self, node: dict) -> None:
        name = node["table"]
        table = self._require_table(name, node["line"])
        column_names = [c["name"] for c in table["columns"]]

        if node["columns"] is not None:
            target_columns = node["columns"]
            for column in target_columns:
                if column not in column_names:
                    raise InterpreterError(f"Table '{name}' has no column '{column}'", node["line"])
        else:
            # No explicit column list -- bind positionally to the
            # table's own CREATE-TABLE-declared order (see app.parser's
            # "User-created tables" section).
            target_columns = column_names

        if len(node["values"]) != len(target_columns):
            raise InterpreterError(
                f"INSERT INTO '{name}' supplies {len(node['values'])} value(s) for "
                f"{len(target_columns)} column(s)",
                node["line"],
            )

        error_info = None
        values: list = []
        try:
            values = [self._evaluate(value_node) for value_node in node["values"]]
        except _DivisionByZeroSignal as signal:
            error_info = self._handle_division_by_zero(signal)

        if error_info is not None:
            # Mirrors _exec_set's "the assignment simply didn't happen" --
            # the statement's own step still records the error, but no
            # row is ever inserted.
            table_info = self._table_step_info(name, "INSERT", rows_affected=0)
            self._record_step(node, render_statement_header(node), table=table_info, error=error_info)
            self._run_handler_if_triggered(error_info)
            return

        row = {column: None for column in column_names}
        for column, value in zip(target_columns, values):
            row[column] = value
        self._validate_row_constraints(name, table, row, node["line"], ignore_row=None)

        table["rows"].append(row)
        table_info = self._table_step_info(name, "INSERT", rows_affected=1, row=row)
        self._record_step(node, render_statement_header(node), table=table_info)

    def _match_where(self, node: dict, table: dict) -> tuple[list[dict], dict | None]:
        """Every row currently in `table` whose WHERE clause (or, if
        `node["where"] is None`, every row unconditionally) evaluates
        truthy -- shared by UPDATE and DELETE. Returns `(matched_rows,
        error_info)`; a DIVISION_BY_ZERO while evaluating WHERE stops
        evaluation immediately and reports zero matched rows, mirroring
        `_exec_if`'s own "the condition couldn't be evaluated -- don't
        guess" handling generalized across a whole row set."""
        if node["where"] is None:
            return list(table["rows"]), None
        matched: list[dict] = []
        try:
            for row in table["rows"]:
                if bool(self._evaluate_with_row(node["where"], row)):
                    matched.append(row)
        except _DivisionByZeroSignal as signal:
            return [], self._handle_division_by_zero(signal)
        return matched, None

    def _exec_update(self, node: dict) -> None:
        name = node["table"]
        table = self._require_table(name, node["line"])
        column_names = {c["name"] for c in table["columns"]}
        for assignment in node["assignments"]:
            if assignment["column"] not in column_names:
                raise InterpreterError(
                    f"Table '{name}' has no column '{assignment['column']}'", node["line"]
                )

        matched_rows, error_info = self._match_where(node, table)

        if error_info is None:
            try:
                # Every assignment is evaluated against each matched
                # row's ORIGINAL values (standard SQL UPDATE semantics --
                # see module docstring), and every row's new values are
                # constraint-checked BEFORE any of them are written, so a
                # violation partway through leaves the table untouched.
                planned: list[tuple[dict, dict]] = []
                for row in matched_rows:
                    new_values = {
                        a["column"]: self._evaluate_with_row(a["value"], row) for a in node["assignments"]
                    }
                    planned.append((row, new_values))
                for row, new_values in planned:
                    candidate = {**row, **new_values}
                    self._validate_row_constraints(name, table, candidate, node["line"], ignore_row=row)
                for row, new_values in planned:
                    row.update(new_values)
            except _DivisionByZeroSignal as signal:
                error_info = self._handle_division_by_zero(signal)
                matched_rows = []

        rows_affected = len(matched_rows) if error_info is None else 0
        table_info = self._table_step_info(name, "UPDATE", rows_affected=rows_affected)
        self._record_step(node, render_statement_header(node), table=table_info, error=error_info)
        self._run_handler_if_triggered(error_info)

    def _exec_delete(self, node: dict) -> None:
        name = node["table"]
        table = self._require_table(name, node["line"])

        matched_rows, error_info = self._match_where(node, table)

        if error_info is None:
            # By object identity (id()), never structural equality -- two
            # rows holding identical values are still two distinct rows;
            # a WHERE matching one of them must not remove the other.
            matched_ids = {id(row) for row in matched_rows}
            table["rows"] = [row for row in table["rows"] if id(row) not in matched_ids]

        rows_affected = len(matched_rows) if error_info is None else 0
        table_info = self._table_step_info(name, "DELETE", rows_affected=rows_affected)
        self._record_step(node, render_statement_header(node), table=table_info, error=error_info)
        self._run_handler_if_triggered(error_info)

    def _exec_return(self, node: dict) -> None:
        error_info = None
        try:
            value = self._evaluate(node["value"])
        except _DivisionByZeroSignal as signal:
            # Same DIVISION_BY_ZERO handling as every other statement
            # boundary: non-fatal only if a handler is registered, else
            # this re-raises as the ordinary InterpreterError.
            error_info = self._handle_division_by_zero(signal)
            value = None

        return_value = {"value": value, "type": _type_name(value)}
        # Recorded before the step itself, and unconditionally (even if
        # this RETURN belongs to a plain top-level run that nothing will
        # ever read it back from) -- see the module docstring's
        # "Function calls in expressions" section for why this is safe:
        # only the nearest enclosing `_evaluate_function_call` call, if
        # any, ever reads it, immediately after this exact RETURN's
        # `_ReturnSignal` unwinds to the matching `run()` frame.
        self._last_return_value = return_value
        self._record_step(node, render_statement_header(node), error=error_info, return_value=return_value)
        self._run_handler_if_triggered(error_info)

        # Stops the function immediately -- unwinds out of however many
        # nested IF/WHILE blocks this RETURN is inside, all the way up
        # to Interpreter.run(). No statement after this one ever runs,
        # even a later one in the same block.
        raise _ReturnSignal()

    # -- procedure calls (CALL) --------------------------------------------

    def _exec_call(self, node: dict) -> None:
        """Execute a CallStatement -- see the module docstring's
        "Procedure calls (CALL)" section for the full design. Structural/
        static problems (unknown target, wrong target type, wrong
        argument count, an OUT/INOUT argument that isn't a plain
        variable, or exceeding MAX_CALL_DEPTH) all raise BEFORE anything
        is recorded, matching every other statement's existing pattern
        (e.g. _exec_set's "variable not declared" check). Only a dynamic
        per-value problem -- DIVISION_BY_ZERO while evaluating an
        argument expression -- gets attached to this statement's own
        DebugStep, exactly like any other statement boundary."""
        name = node["name"]

        if self._call_depth >= MAX_CALL_DEPTH:
            raise InterpreterError(
                f"CALL to '{name}' exceeded the maximum call depth of {MAX_CALL_DEPTH} "
                "(possible infinite recursion)",
                node["line"],
            )

        target = self._procedures.get(name)
        if target is None:
            raise InterpreterError(f"Procedure '{name}' is not defined", node["line"])
        if target.get("type") != "ProcedureNode":
            raise InterpreterError(
                f"'{name}' is not a procedure and cannot be CALLed "
                "(only CREATE PROCEDURE definitions are valid CALL targets)",
                node["line"],
            )

        params: list[dict] = target.get("params") or []
        args: list[dict] = node["args"]
        if len(args) != len(params):
            raise InterpreterError(
                f"Procedure '{name}' expects {len(params)} argument(s) but {len(args)} "
                "were given",
                node["line"],
            )

        for param, arg in zip(params, args):
            mode = param.get("mode", "IN")
            if mode in ("OUT", "INOUT") and arg["type"] != "Identifier":
                raise InterpreterError(
                    f"Argument for {mode} parameter '{param['name']}' of '{name}' must "
                    "be a variable, not an expression",
                    node["line"],
                )

        error_info = None
        arg_values: list = []
        try:
            for arg in args:
                arg_values.append(self._evaluate(arg))
        except _DivisionByZeroSignal as signal:
            # Raises here (aborting the whole run) if unhandled -- see
            # _handle_division_by_zero. If a handler IS registered, this
            # statement's own step still gets recorded with the error
            # below, but the call itself is skipped entirely (mirrors
            # _exec_set's "the assignment simply didn't happen").
            error_info = self._handle_division_by_zero(signal)

        self._record_step(node, render_statement_header(node), error=error_info)
        self._run_handler_if_triggered(error_info)
        if error_info is not None:
            return

        # -- bind the callee's fresh, fully isolated scope -------------
        callee_scope: dict = {}
        output_names: set[str] = set()
        for param, value in zip(params, arg_values):
            mode = param.get("mode", "IN")
            if mode == "OUT":
                callee_scope[param["name"]] = None
                output_names.add(param["name"])
            else:  # IN or INOUT
                callee_scope[param["name"]] = value
                if mode == "INOUT":
                    output_names.add(param["name"])

        # Swap in the callee's frame; scope/cursors/handlers/the changed-
        # value baseline are ALL per-invocation (see module docstring) --
        # self.steps/self._step_number are deliberately NOT touched, so
        # the callee's steps land in the same continuous trace.
        saved_scope = self.scope
        saved_previous = self._previous_values
        saved_outputs = self._output_param_names
        saved_cursors = self.cursors
        saved_handlers = self.handlers
        saved_loop_stack = self._loop_stack

        self.scope = callee_scope
        self._previous_values = dict(callee_scope)
        self._output_param_names = output_names
        self.cursors = {}
        self.handlers = {}
        self._loop_stack = []
        self._call_depth += 1
        self._call_stack.append(name)
        try:
            self.run(target["body"], entry_node=target, function_name=name)
        finally:
            self._call_depth -= 1
            self._call_stack.pop()
            # Capture OUT/INOUT final values BEFORE restoring the
            # caller's scope, from whichever scope is currently active
            # (the callee's -- this always runs, success or exception).
            out_values = {pname: self.scope.get(pname) for pname in output_names}
            self.scope = saved_scope
            self._previous_values = saved_previous
            self._output_param_names = saved_outputs
            self.cursors = saved_cursors
            self.handlers = saved_handlers
            self._loop_stack = saved_loop_stack

        # Propagate OUT/INOUT final values back into the caller's own
        # variables -- already validated above to be plain Identifiers.
        for param, arg in zip(params, args):
            mode = param.get("mode", "IN")
            if mode in ("OUT", "INOUT"):
                self.scope[arg["name"]] = out_values[param["name"]]

    # -- function calls in expressions -------------------------------------

    def _evaluate_function_call(self, node: dict):
        """Evaluate a FunctionCallExpr -- see the module docstring's
        "Function calls in expressions" section for the full design.
        Reuses `_exec_call`'s scope-isolation/call-depth/call-stack
        machinery verbatim; the differences are: the target must be a
        FunctionNode, every argument binds like a plain IN (a
        FunctionNode's params never carry a mode, so there's no
        OUT/INOUT propagation to unwind), `run()` is called with
        `require_return=True`, and the callee's RETURNed value --
        captured via `self._last_return_value` -- is returned to the
        caller instead of discarded."""
        name = node["name"]

        if self._call_depth >= MAX_CALL_DEPTH:
            raise InterpreterError(
                f"Call to '{name}' exceeded the maximum call depth of {MAX_CALL_DEPTH} "
                "(possible infinite recursion)",
                node["line"],
            )

        target = self._procedures.get(name)
        if target is None:
            raise InterpreterError(f"Function '{name}' is not defined", node["line"])
        if target.get("type") != "FunctionNode":
            raise InterpreterError(
                f"'{name}' is not a function and cannot be called in an expression -- "
                f"only a CREATE FUNCTION definition can be (did you mean CALL {name}(...); ?)",
                node["line"],
            )

        params: list[dict] = target.get("params") or []
        args: list[dict] = node["args"]
        if len(args) != len(params):
            raise InterpreterError(
                f"Function '{name}' expects {len(params)} argument(s) but {len(args)} "
                "were given",
                node["line"],
            )

        # Every argument is evaluated once, here, in the CALLER's scope
        # -- a DIVISION_BY_ZERO signal raised while doing so is NOT
        # caught here; it propagates up to whichever enclosing
        # statement's own try/except is already watching for one (see
        # the module docstring for why that's correct, not an
        # oversight).
        arg_values = [self._evaluate(arg) for arg in args]
        callee_scope = {param["name"]: value for param, value in zip(params, arg_values)}

        # Swap in the callee's fully isolated frame -- identical to
        # `_exec_call`'s own swap, minus the OUT/INOUT bookkeeping a
        # FunctionNode's params never need.
        saved_scope = self.scope
        saved_previous = self._previous_values
        saved_outputs = self._output_param_names
        saved_cursors = self.cursors
        saved_handlers = self.handlers
        saved_loop_stack = self._loop_stack

        self.scope = callee_scope
        self._previous_values = dict(callee_scope)
        self._output_param_names = set()
        self.cursors = {}
        self.handlers = {}
        self._loop_stack = []
        self._call_depth += 1
        self._call_stack.append(name)
        try:
            self.run(target["body"], require_return=True, entry_node=target, function_name=name)
            return self._last_return_value["value"]
        finally:
            self._call_depth -= 1
            self._call_stack.pop()
            self.scope = saved_scope
            self._previous_values = saved_previous
            self._output_param_names = saved_outputs
            self.cursors = saved_cursors
            self.handlers = saved_handlers
            self._loop_stack = saved_loop_stack

    # -- exception handlers -----------------------------------------------

    def _exec_declare_handler(self, node: dict) -> None:
        condition = node["condition"]
        if condition in self.handlers:
            raise InterpreterError(
                f"A CONTINUE HANDLER FOR {condition} is already declared", node["line"]
            )
        self.handlers[condition] = node["action"]
        self._record_step(node, render_statement_header(node))

    def _condition_error_info(self, condition: str, message: str) -> dict:
        """Build the `error` dict for a triggered condition. Does NOT
        run the handler itself -- see `_run_handler_if_triggered`,
        called separately (and later) so the *triggering* statement's
        own DebugStep is recorded before the handler action's step."""
        handler = self.handlers.get(condition)
        label = _HANDLER_LABELS[condition] if handler is not None else "unhandled"
        return {"condition": condition, "message": message, "handler": label}

    def _handle_division_by_zero(self, signal: "_DivisionByZeroSignal") -> dict:
        """Build DIVISION_BY_ZERO's `error` info, or re-raise as the
        ordinary, procedure-aborting InterpreterError it always was
        before handlers existed if nothing is registered to catch it
        (see module docstring's "Exception handlers" section for why
        this differs from NOT_FOUND, which is unconditionally
        non-fatal)."""
        error_info = self._condition_error_info("DIVISION_BY_ZERO", "Division by zero")
        if error_info["handler"] == "unhandled":
            raise InterpreterError("Division by zero", signal.line) from signal
        return error_info

    def _run_handler_if_triggered(self, error_info: dict | None) -> None:
        """After the triggering statement's own DebugStep has been
        recorded, actually run the registered handler's action (as its
        own subsequent DebugStep). No-op if nothing triggered, or if
        what triggered was unhandled."""
        if error_info is None:
            return
        action = self.handlers.get(error_info["condition"])
        if action is not None:
            self._execute_statement(action)

    # -- cursors --------------------------------------------------------------

    def _require_cursor(self, name: str, line: int | None) -> dict:
        state = self.cursors.get(name)
        if state is None:
            raise InterpreterError(f"Cursor '{name}' is not declared", line)
        return state

    def _cursor_has_more(self, name: str, line: int | None) -> bool:
        """Whether `name`'s cursor is open and has a row ready to FETCH
        right now. Backs the DebugStep `cursor.hasMore` field and the
        *predictive* %FOUND expression -- see the module docstring for
        why %FOUND means this rather than Oracle's retrospective "did
        the last FETCH succeed"."""
        state = self._require_cursor(name, line)
        return state["open"] and state["pos"] < len(state["rows"])

    def _cursor_last_fetch_not_found(self, name: str, line: int | None) -> bool:
        """Whether `name`'s most recently completed FETCH found no row.

        Deliberately NOT `not _cursor_has_more(...)`: %FOUND is
        predictive (checked *before* a FETCH, in a WHILE condition) but
        %NOTFOUND is retrospective (checked *after* a FETCH, inside the
        loop body -- see CURSOR_EXPLICIT_FLAG_PROCEDURE-style tests).
        Treating them as simple negations of each other would make a
        FETCH that just found the very last real row report %NOTFOUND
        as true (nothing is left for *next* time), which is wrong --
        that FETCH succeeded. So this tracks the last FETCH's own
        outcome directly instead of deriving it from `pos`."""
        state = self._require_cursor(name, line)
        return state["last_fetch_found"] is False

    def _exec_declare_cursor(self, node: dict) -> None:
        name = node["name"]
        if name in self.cursors:
            raise InterpreterError(f"Cursor '{name}' is already declared", node["line"])
        self.cursors[name] = {
            "query": node["query"],
            "rows": [],
            "pos": 0,
            "open": False,
            "last_fetch_found": None,  # None = no FETCH has run yet
        }
        cursor_info = {"name": name, "currentRow": None, "rowIndex": 0, "hasMore": False}
        self._record_step(node, render_statement_header(node), cursor=cursor_info)

    def _exec_open_cursor(self, node: dict) -> None:
        name = node["name"]
        state = self._require_cursor(name, node["line"])
        if state["open"]:
            raise InterpreterError(f"Cursor '{name}' is already open", node["line"])

        try:
            db_cursor = self._db.execute(state["query"])
            columns = [d[0] for d in db_cursor.description] if db_cursor.description else []
            rows = [dict(zip(columns, row)) for row in db_cursor.fetchall()]
        except sqlite3.Error as exc:
            raise InterpreterError(f"Cursor '{name}' query failed: {exc}", node["line"]) from exc

        state["rows"] = rows
        state["pos"] = 0
        state["open"] = True
        state["last_fetch_found"] = None  # reset: no FETCH since this OPEN yet
        cursor_info = {"name": name, "currentRow": None, "rowIndex": 0, "hasMore": len(rows) > 0}
        self._record_step(node, render_statement_header(node), cursor=cursor_info)

    def _exec_fetch_cursor(self, node: dict) -> None:
        name = node["name"]
        state = self._require_cursor(name, node["line"])
        if not state["open"]:
            raise InterpreterError(f"Cursor '{name}' is not open", node["line"])

        targets = node["targets"]
        rows = state["rows"]
        pos = state["pos"]
        error_info = None

        if pos < len(rows):
            row = rows[pos]
            values = list(row.values())
            if len(values) != len(targets):
                raise InterpreterError(
                    f"Cursor '{name}' returns {len(values)} column(s) but "
                    f"FETCH names {len(targets)} target variable(s)",
                    node["line"],
                )
            for target, value in zip(targets, values):
                if target not in self.scope:
                    raise InterpreterError(f"Variable '{target}' is not declared", node["line"])
                self.scope[target] = value

            state["pos"] = pos + 1
            state["last_fetch_found"] = True
            cursor_info = {
                "name": name,
                "currentRow": row,
                "rowIndex": pos,
                "hasMore": state["pos"] < len(rows),
            }
        else:
            # Exhausted -- NOT a Python exception. Recorded as an
            # ordinary DebugStep with hasMore=False and no target
            # assignment, same as a real driver's FETCH-past-the-end.
            # NOT_FOUND is unconditionally non-fatal (unlike
            # DIVISION_BY_ZERO) -- see module docstring.
            state["last_fetch_found"] = False
            cursor_info = {"name": name, "currentRow": None, "rowIndex": pos, "hasMore": False}
            error_info = self._condition_error_info(
                "NOT_FOUND", f"Cursor '{name}' has no more rows to fetch"
            )

        self._record_step(node, render_statement_header(node), cursor=cursor_info, error=error_info)
        self._run_handler_if_triggered(error_info)

    def _exec_close_cursor(self, node: dict) -> None:
        name = node["name"]
        state = self._require_cursor(name, node["line"])
        if not state["open"]:
            raise InterpreterError(f"Cursor '{name}' is not open", node["line"])

        state["open"] = False
        cursor_info = {"name": name, "currentRow": None, "rowIndex": state["pos"], "hasMore": False}
        self._record_step(node, render_statement_header(node), cursor=cursor_info)

    # -- expression evaluation ----------------------------------------------

    def _evaluate(self, node: dict):
        kind = node["type"]
        if kind == "NumberLiteral":
            return node["value"]
        if kind == "StringLiteral":
            return node["value"]
        if kind == "NullLiteral":
            return None
        if kind == "Identifier":
            name = node["name"]
            if name not in self.scope:
                raise InterpreterError(
                    f"Variable '{name}' is not declared", node["line"]
                )
            return self.scope[name]
        if kind == "UnaryExpr":
            operand = self._evaluate(node["operand"])
            if node["operator"] == "-":
                return -operand
            raise InterpreterError(
                f"Unknown unary operator {node['operator']!r}", node["line"]
            )
        if kind == "BinaryExpr":
            return self._evaluate_binary(node)
        if kind == "CursorFoundExpr":
            return self._cursor_has_more(node["cursor"], node.get("line"))
        if kind == "CursorNotFoundExpr":
            return self._cursor_last_fetch_not_found(node["cursor"], node.get("line"))
        if kind == "FunctionCallExpr":
            return self._evaluate_function_call(node)
        raise InterpreterError(
            f"Cannot evaluate unknown expression node {kind!r}", node.get("line")
        )

    def _evaluate_binary(self, node: dict):
        left = self._evaluate(node["left"])
        right = self._evaluate(node["right"])
        op = node["operator"]
        line = node["line"]

        # `+ - * /` are the only operators that hand their operands
        # straight to Python's own numeric operators, so they're the
        # only ones a None operand (a DECLAREd-but-never-assigned
        # variable, or an OUT param never SET on some code path -- both
        # established, intentional conventions elsewhere in this
        # interpreter) can crash: Python raises an unstructured
        # TypeError for `None * 2`, which would otherwise surface as a
        # raw 500 with no body, breaking this app's "every runtime
        # error is a structured {stage, message, line}" contract. The
        # comparison operators below are unaffected (`None == 2` is
        # simply `False` in Python) and deliberately not guarded here.
        if op in ("+", "-", "*", "/") and (left is None or right is None):
            raise InterpreterError(
                f"Cannot use {op!r}: a variable used in this expression has "
                "no value yet -- it was declared but never assigned (or is "
                "an OUT parameter never SET on this code path)",
                line,
            )

        if op == "+":
            return left + right
        if op == "-":
            return left - right
        if op == "*":
            return left * right
        if op == "/":
            if right == 0:
                # Not raised as InterpreterError directly -- caught at
                # the enclosing statement boundary, which decides (via
                # _handle_division_by_zero) whether a registered
                # CONTINUE HANDLER makes this non-fatal. See module
                # docstring's "Exception handlers" section.
                raise _DivisionByZeroSignal(line)
            return left / right
        if op == ">":
            return left > right
        if op == "<":
            return left < right
        if op == "=":
            return left == right
        if op == "!=":
            return left != right
        raise InterpreterError(f"Unknown operator {op!r}", line)

    # -- DebugStep recording ----------------------------------------------

    def _snapshot_variables(self) -> dict:
        snapshot = {}
        for name, value in self.scope.items():
            previous = self._previous_values.get(name, _UNSET)
            snapshot[name] = {
                "value": value,
                "type": _type_name(value),
                "changed": previous is _UNSET or previous != value,
                "isOutput": name in self._output_param_names,
            }
        self._previous_values = dict(self.scope)
        return snapshot

    def _current_call_info(self) -> dict | None:
        """The `call` field for whatever step is about to be recorded --
        see the module docstring's "Procedure calls (CALL)" section.
        None (omitted entirely from the DebugStep) at the top level
        (`_call_depth == 0`), so every trace that never uses CALL is
        completely unaffected."""
        if self._call_depth == 0:
            return None
        return {
            "procedureName": self._call_stack[-1],
            "depth": self._call_depth,
            "stack": list(self._call_stack),
        }

    def _record_step(
        self,
        node: dict,
        statement_text: str,
        branch: dict | None = None,
        loop: dict | None = None,
        cursor: dict | None = None,
        error: dict | None = None,
        return_value: dict | None = None,
        table: dict | None = None,
    ) -> DebugStep:
        self._step_number += 1
        step = DebugStep(
            step_number=self._step_number,
            line=node["line"],
            node_type=node["type"],
            statement_text=statement_text,
            variables=self._snapshot_variables(),
            branch=branch,
            loop=loop,
            cursor=cursor,
            error=error,
            return_value=return_value,
            call=self._current_call_info(),
            table=table,
        )
        self.steps.append(step)
        return step


_UNSET = object()


def _build_procedure_registry(definitions: list[dict]) -> dict[str, dict]:
    """Name -> AST-node registry a CALL statement resolves against (see
    app.parser's "CALL and multi-procedure sources" and this module's
    "Procedure calls (CALL)" docstring sections). Includes every
    definition passed in, by name -- the entry procedure/function is
    registered too, which is exactly what makes self-recursion work
    with no extra syntax. A bare Procedure (no "name" key at all) is
    silently skipped rather than erroring, since `run()` below calls
    this with `[ast]` unconditionally for the single-definition case."""
    return {d["name"]: d for d in definitions if d.get("name")}


def run(
    ast: dict,
    initial_params: dict | None = None,
    db_connection: sqlite3.Connection | None = None,
) -> list[DebugStep]:
    """Execute a Procedure, ProcedureNode, FunctionNode, or (multi-
    procedure source) ProgramNode AST and return its full DebugStep
    trace.

    Args:
        ast: the root produced by ``app.parser.parse`` -- one of
            ``{"type": "Procedure", "body": [...]}`` (bare, no params),
            ``{"type": "ProcedureNode", "name", "params", "body"}``
            (wrapped, params carry a "mode"), ``{"type": "FunctionNode",
            "name", "params", "returnType", "body"}`` (params never
            carry a mode), or ``{"type": "ProgramNode", "definitions":
            [...]}`` -- two or more chained CREATE definitions, of which
            the LAST is the one actually executed (see app.parser's
            "CALL and multi-procedure sources" section); every
            definition, entry included, is registered by name so a
            CallStatement (see app.interpreter's "Procedure calls
            (CALL)" section) anywhere in the executed body can find it.
        initial_params: starting values for the procedure/function's
            variables and parameters (e.g. ``{"price": 20, "quantity":
            6}``). IN and INOUT params are looked up here by name, the
            exact same mechanism a bare procedure body's externally-
            referenced variables and a FunctionNode's params already
            use -- referencing one that wasn't supplied raises the
            usual "not declared" InterpreterError. A ProcedureNode's
            OUT params are the one exception: they're auto-seeded to
            `None` if not already present in `initial_params`, exactly
            like a DECLAREd variable with no DEFAULT, since a pure
            output naturally has no caller-supplied starting value.
        db_connection: the SQLite connection cursor statements run
            their queries against. Defaults to a fresh, empty
            in-memory database (closed again once this run finishes) --
            pass a pre-seeded connection (e.g. in a test) so OPEN
            actually has a table to query.

    Returns:
        One DebugStep per executed statement (and, for WHILE, one
        extra DebugStep per condition check), in execution order,
        INCLUDING every statement any CALLed procedure executes -- the
        whole call chain is one flat, continuous list, not a separate
        trace per procedure (see "Procedure calls (CALL)" above for the
        `call` field that marks which steps belong to a nested call).
        For a FunctionNode or ProcedureNode (the entry one, for a
        ProgramNode), step 1 is an extra "entry" step for the CREATE
        .../BEGIN line itself (see the module docstring's "Functions"
        section) -- the bare/legacy Procedure form has no such step, and
        its trace is exactly what it always was, UNLESS its body is
        completely empty, in which case it gets one synthetic
        placeholder step of its own (a fixed, non-source `"(empty
        procedure body)"` line) rather than a genuinely zero-length
        trace -- see `Interpreter.run`. Every step's
        `variables` entries carry an `isOutput` flag, True only for a
        ProcedureNode's declared OUT/INOUT params -- so an OUT param's
        final value is visible (and identifiable as an output) in the
        last step's snapshot, the same way any other variable's final
        value already is. For a FunctionNode, execution stops at the
        first RETURN -- see the module docstring's "Functions" section
        -- so no step after that one appears, even if there was more
        source left unexecuted.

    Raises:
        InterpreterError: on undefined variables, an unhandled
            division by zero (see module docstring's "Exception
            handlers" section -- a *handled* one does not raise), a
            WHILE or LOOP that exceeds MAX_LOOP_ITERATIONS, a LEAVE
            (labeled or unlabeled) with no currently-enclosing LOOP to
            match it (see "LOOP / LEAVE" above), a cursor error
            (undeclared/already-open/not-open cursor, a query that
            fails against the database, or a FETCH whose target count
            doesn't match the query's column count), a duplicate
            CONTINUE HANDLER for the same condition, a CALL naming a
            procedure that isn't defined or that names a FunctionNode
            instead of a ProcedureNode, a CALL whose argument count
            doesn't match the target's parameter count, a CALL passing a
            non-Identifier expression for an OUT/INOUT parameter, a CALL
            chain exceeding MAX_CALL_DEPTH, or -- for a FunctionNode only
            -- a body that completes without ever executing a RETURN.
            NOT_FOUND never raises -- see "Cursors" above.
    """
    initial_params = dict(initial_params or {})
    output_param_names: set[str] = set()

    # ProgramNode: multiple chained CREATE definitions -- the LAST one is
    # the entry point (see app.parser), every one (including entry) goes
    # into the CALL registry. Otherwise (the single-definition case,
    # unchanged from before ProgramNode existed) `entry` is just `ast`
    # itself, and it's registered too -- solely so it can CALL itself
    # (self-recursion) with no other syntax needed; a bare Procedure has
    # no "name" and contributes nothing to the registry either way.
    if ast.get("type") == "ProgramNode":
        definitions = ast["definitions"]
        entry = definitions[-1]
        procedures = _build_procedure_registry(definitions)
    else:
        entry = ast
        procedures = _build_procedure_registry([ast])

    # Only a ProcedureNode's params carry a mode at all (a bare
    # Procedure has no "params" key, and a FunctionNode's params never
    # have OUT/INOUT semantics -- see parser module docstring), so this
    # is a no-op for both of those.
    if entry.get("type") == "ProcedureNode":
        for param in entry.get("params") or []:
            mode = param.get("mode", "IN")
            if mode in ("OUT", "INOUT"):
                output_param_names.add(param["name"])
            if mode == "OUT" and param["name"] not in initial_params:
                initial_params[param["name"]] = None

    interpreter = Interpreter(
        initial_params,
        db_connection=db_connection,
        output_param_names=output_param_names,
        procedures=procedures,
    )
    try:
        require_return = entry.get("type") == "FunctionNode"
        # Only the two wrapped forms have a CREATE .../BEGIN line to
        # give its own entry step -- the bare/legacy Procedure form
        # (no "name"/"params" at all) is intentionally excluded, so its
        # trace is byte-for-byte what it always was.
        entry_node = entry if entry.get("type") in ("FunctionNode", "ProcedureNode") else None
        return interpreter.run(
            entry["body"],
            require_return=require_return,
            function_name=entry.get("name"),
            entry_node=entry_node,
        )
    finally:
        if interpreter._owns_db:
            interpreter._db.close()
