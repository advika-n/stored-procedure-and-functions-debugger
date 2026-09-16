# `DebugStep` wire contract + performance history

Moved out of `CLAUDE.md` (which stays a lean, high-level orientation doc) so it doesn't
load into every prompt. `CLAUDE.md` §4 has a one-line pointer here. See `docs/features.md`
for the per-feature design rationale that produces these steps.

---

## `DebugStep` shape

Defined as a dataclass in `backend/app/interpreter.py` (`class DebugStep`), serialized to
camelCase via its `to_dict()` method. Every frontend feature — the step navigator,
variable table, flowchart highlighting, explanations, Ask AI, Predict Mode, History
replay, Export — is driven by this exact shape. Changing a field name or removing one has
wide ripple effects across the frontend; changing it requires auditing all of the above.

Shape (camelCase, as sent over the wire):
```
{
  stepNumber, line, nodeType, statementText,
  variables: { [name]: { value, type, changed, isOutput } },
  branch?:   { condition, result, path },         // IfStatement AND CaseStatement steps
  loop?:     { condition, result, iteration },     // WhileStatement AND LoopStatement steps
  cursor?:   { name, rowIndex, currentRow, hasMore },
  error?:    { condition, message, handler },
  returnValue?: { value, type },                   // FunctionNode final RETURN only
  call?:     { procedureName, depth, stack },       // only for steps INSIDE a called procedure/function
  table?:    { name, operation, columns, rowsAffected, row, rows }  // CreateTableStatement/
}                                                    // InsertStatement/UpdateStatement/DeleteStatement only
```
(`variables` entry shape is built by `_snapshot_variables()`.)

`call` is present only when `depth >= 1` (a step genuinely executing inside a `CALL`ed
procedure or an invoked `FunctionNode`), omitted entirely for every top-level step — so
every trace that never uses `CALL`/function-calls-in-expressions is byte-for-byte
unchanged. `stack` is the full chain of enclosing procedure/function names, outermost
first (`stack[-1] == procedureName`, `len(stack) == depth`). `procedureName` keeps that
name (chosen when only procedures could be invoked this way) even though it may now hold
a function's name — a deliberate non-rename, not an oversight; see `docs/features.md`'s
"Function calls in expressions" section for why.

`table` is present only on a `CreateTableStatement`/`InsertStatement`/`UpdateStatement`/
`DeleteStatement` step (a genuinely new field, added for user-created tables — see
`docs/features.md`'s section of the same name for why no existing field fit):
`operation` is `"CREATE" | "INSERT" | "UPDATE" | "DELETE"`; `columns` is the table's
column names in CREATE-TABLE-declared order; `rowsAffected` is 0 for CREATE, 1 for a
successful INSERT, or the matched-row count for UPDATE/DELETE (0 if a handled
DIVISION_BY_ZERO made the statement a no-op); `row` is the just-inserted row (INSERT
only, else `null`); `rows` is the table's FULL current row snapshot right after this
operation (not a diff — mirrors `variables`' own "always current, not just what
changed" convention).

## Performance: `/debug` must stay under 2s

Measured directly against a live local server (the original 10 built-in `samples.js`
procedures): **22.5–76.2ms per call, ~30ms average** — comfortably under budget. Every
phase since that has touched the interpreter has re-measured in-process
(tokenize→parse→run, bypassing the network layer) and logged the result here:

| Phase | Sample(s) measured | Result |
|---|---|---|
| `CALL` support | plain no-CALL vs. two-procedure CALL-based | both well under 1ms |
| Function calls in expressions | `CheckoutTotal`; 5-level self-recursive `Fact` | 0.607ms; 0.478ms |
| CASE statement | `ClassifyOrder` (both CASE forms) | 0.407ms |
| LOOP/LEAVE | `FindPairSum` (58 steps, nested labeled loops) | 0.532ms (200-run avg) |
| User-created tables (CREATE TABLE/INSERT/UPDATE/DELETE) | `ManageInventory` (8 steps, 1 table, 3 rows, 2 UPDATEs, 1 DELETE); all 18 samples | 0.462ms; 8.3ms combined |
| Testing infrastructure (golden traces / property-based / grammar edge cases) | Real `WHILE` loop at 9,999 iterations (20,001-step trace) through the REAL `/debug` endpoint (HTTP + JSON + `history.save_run` included, not just in-process) | **617ms** — the largest trace ever measured against this NFR, still comfortably under budget |

No measurable overhead from any of these phases (all comfortably sub-millisecond
in-process). The one deliberately extreme measurement above — a trace 300-1000x larger
than any real sample procedure produces — exists specifically to stress-test the 2s
budget at a scale no hand-written sample reaches on its own; see
`backend/app/tests/test_grammar_edge_cases.py::test_large_loop_count_stays_under_the_2s_nfr`
for the checked-in, always-re-measured version of this same check (asserted against a
looser 1.8s ceiling, not the exact number above, so ordinary machine variance doesn't
make it flaky). Re-time via the live-server approach (loop the sample list, hit
`/debug`, measure wall time) if the interpreter, cursor handling, or history-write path
changes again, and append a new row here.
