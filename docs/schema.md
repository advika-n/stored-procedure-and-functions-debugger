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
  sql?:      { keyword, statement, description, kind, columns?, rows?, rowCount?,
               rowsAffected?, tableName?, snapshot?, into? }  // SqlStatement AND
}                                                              // SelectIntoStatement -- see below
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

`sql` is present only on a `SqlStatement` step — `CREATE TABLE`/`INSERT`/`UPDATE`/
`DELETE`/`SELECT`, raw SQL run straight against `app.user_db`'s persistent database (see
`docs/features.md`'s "Persistent user database + SQL Console" and "Merged Debugger/SQL
Console page + SQL passthrough statements" sections). **Replaces** an earlier phase's
`table` field (and the `CreateTableStatement`/`InsertStatement`/`UpdateStatement`/
`DeleteStatement` node types that produced it) — that field/those types no longer exist;
this is a genuine breaking change to the wire contract, not an addition alongside the old
one. `keyword` is `"CREATE" | "INSERT" | "UPDATE" | "DELETE" | "SELECT"`; `statement` is
the raw SQL text that ran; `description` is a human-readable one-liner (same convention
`POST /sql/execute` already uses — see `app/sql_console.py`); `kind` is `"rows"` (a
SELECT) or `"write"` (everything else), and decides which of the remaining fields are
present:
- `kind: "rows"` → `columns` (result column names), `rows` (result rows, each a plain
  array in column order — NOT column-keyed objects), `rowCount`.
- `kind: "write"` → `rowsAffected`; `tableName` (best-effort regex-extracted table name,
  `null` if not determinable — see `app.sql_console.extract_table_name`); `snapshot`
  (`{columns, rows}` — the affected table's FULL current row set right after this
  operation, `null` if `tableName` couldn't be determined) mirrors `variables`' own
  "always current, not just what changed" convention, the same reasoning the retired
  `table.rows` field already followed.

There is no server-side constraint enforcement (NOT NULL/PRIMARY KEY) or variable
interpolation for these statements any more — see `docs/features.md` for the full
retirement/replacement writeup and what capability was deliberately traded away.

`sql` is ALSO present on a `SelectIntoStatement` step (`SELECT col1, col2, ... INTO var1,
var2, ... FROM table WHERE condition;` — a single-row lookup, own AST node, distinct from
both the cursor mechanism and the plain-SELECT `SqlStatement` above; see
`docs/features.md`'s "Comparison operators + SELECT...INTO" section), reusing this exact
same `kind: "rows"` shape rather than inventing a second one, plus one extra field:
- `into`: `[str, ...]` — the INTO target variable names, positionally paired with
  `columns`/`rows[0]` (present only on a `SelectIntoStatement` step, `undefined` on a
  plain `SqlStatement` SELECT).

On the zero-row (NOT_FOUND) path, `rows`/`rowCount` are `[]`/`0` and the step's `error`
field carries the same `{condition: "NOT_FOUND", message, handler}` shape an exhausted
cursor FETCH's own step already carries — no new error shape was added for this case, it
reuses FETCH's existing one. A row-count of exactly one assigns each column to its INTO
target positionally; more than one row is a distinct, immediately-fatal `InterpreterError`
(never reaches this DebugStep shape at all — the run aborts at that statement, same as any
other hard interpreter error).

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
| Merged Debugger/SQL Console page + SQL passthrough statements (cursor/CREATE TABLE/INSERT/UPDATE/DELETE/SELECT now hit REAL SQLite via `app.user_db`, not the old `:memory:` demo_db/pure-Python simulation) | `InventoryValueReport` (23 steps, 1 table, 3 INSERTs, 1 UPDATE, a 3-row cursor loop) in-process; all 19 samples through the REAL `/debug` endpoint (HTTP + JSON + real SQLite file I/O + `history.save_run`) | 26.0ms (up from sub-1ms pre-this-phase — expected, now doing real disk I/O per write instead of a pure Python dict mutation); 363.5ms combined, ~19ms/sample average |
| `POST /sql/execute` (new endpoint, same real `app.user_db`) | `SELECT * FROM products` via curl against a live server | ~13–25ms |

No measurable overhead from any phase through "Testing infrastructure" (all comfortably
sub-millisecond in-process). The merged-page/SQL-passthrough phase below that is the
first genuinely measurable jump (real SQLite file I/O per write, not a pure Python dict
mutation) — still 2-3 orders of magnitude under the 2s budget, just no longer
"sub-millisecond." The one deliberately extreme measurement above that — a trace
300-1000x larger than any real sample procedure produces — exists specifically to
stress-test the 2s budget at a scale no hand-written sample reaches on its own; see
`backend/app/tests/test_grammar_edge_cases.py::test_large_loop_count_stays_under_the_2s_nfr`
for the checked-in, always-re-measured version of this same check (asserted against a
looser 1.8s ceiling, not the exact number above, so ordinary machine variance doesn't
make it flaky). Re-time via the live-server approach (loop the sample list, hit
`/debug`, measure wall time) if the interpreter, cursor handling, or history-write path
changes again, and append a new row here.
