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
  call?:     { procedureName, depth, stack }        // only for steps INSIDE a called procedure/function
}
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

No measurable overhead from any of these phases. Re-time via the live-server approach
(loop the sample list, hit `/debug`, measure wall time) if the interpreter, cursor
handling, or history-write path changes again, and append a new row here.
