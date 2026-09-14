# CLAUDE.md

Persistent context for this repo — read this first, then **read `HANDOFF.md` immediately
after** for current status before making any changes (see §7).

This file describes what the project *is* and how it's built; it should rarely change.
Day-to-day status, in-progress work, and known bugs belong in `HANDOFF.md`, not here.

---

## 1. Project identity

**Stored Procedure & Function Debugger** — a solo DBMS course project: a mini SQL
interpreter with step-by-step execution visualization, built as a monorepo (`backend/` +
`frontend/`).

Graded out of **30 marks**: Functionality (10), Visualization (5), UI/UX (5),
Documentation (5), Innovation (5).

---

## 2. Architecture

- **Backend**: Python, FastAPI (`backend/app/main.py`), SQLite for persistence.
- **Frontend**: React 19 + Vite, Monaco Editor (SQL input), Mermaid.js (control-flow
  flowcharts), React Router.
- **AI**: Google Gemini (`gemini-flash-lite-latest`, via the `google-genai` SDK) for
  step explanations, free-form Q&A, and quiz generation — with a deterministic
  template-based fallback whenever the API is unavailable/unconfigured. Client wiring
  lives once in `backend/app/explainer.py` (`_get_gemini_client()`, `_GEMINI_MODEL`) and
  is reused (not duplicated) by `backend/app/quiz.py`.
- **Breakpoints + Continue/Restart** (`frontend/src/pages/DebuggerPage.jsx`) — a
  frontend-only consumption-layer feature on top of the existing step trace, not an
  interpreter/backend capability. A breakpoint is just a source line number
  (`Set<number>` in component state); **"Continue"** (`continueExecution`, originally
  built and briefly labeled "Run to Breakpoint" before a same-phase-family cleanup pass
  renamed it) fast-forwards `currentStepIndex` from wherever it currently is to the next
  step in the *already-computed* trace whose `line` is in that set (falling through to
  the last step, i.e. run-to-completion, when none match — the deliberate no-breakpoints
  behavior). **"Restart"** (`restartTrace`, originally labeled "Reset") jumps
  `currentStepIndex` back to 0 of the same trace with no re-fetch. Uses Monaco's own
  glyph margin (`glyphMargin: true`) rather than custom gutter UI; clicking the glyph
  margin or the line-number column (`editor.onMouseDown`, told apart via Monaco's
  `MouseTargetType`) toggles a breakpoint. Breakpoints persist across new Debug
  runs/sample loads (editor-level state, not tied to one run) and are tracked by raw line
  number, not a Monaco decoration ID — heavy edits above a breakpoint can leave it on
  now-different
  code, an accepted simplification.
- **SQL Anti-Pattern Advisor** (`backend/app/advisor.py`) — a static linter-style pass
  over the AST alone (never the execution trace), reusing the exact AST
  `app.parser.parse()` already produces. Not a separate endpoint: `POST /debug` computes
  `analyze(ast)` right after a successful parse and returns the findings as an `issues`
  array alongside `ast`/`steps`, so the check runs automatically on every Debug click at
  no extra network round trip. Nine anti-patterns/warnings detected — the original six
  (`select-star`, `cursor-could-be-set-based`, `nested-loops`, `missing-error-handling`,
  `magic-number`, `cursor-not-closed`) plus three **Extended static analysis warnings**
  added in a later phase (`unreachable-code` — dead code after an unconditional RETURN,
  or an IF branch whose condition is a compile-time constant; `unused-variable` — a
  DECLAREd local never read by any expression, assignment alone doesn't count;
  `never-read-variable` — a "dead store": a SET's value is unconditionally clobbered by a
  later SET to the same name before anything reads it, distinct from `unused-variable`
  since the variable IS read at some *other* point) — see the module's own docstring for
  what's detectable from this grammar's AST and, just as deliberately, what isn't (no
  dynamic-SQL/injection check: this grammar has no EXECUTE/EXEC-IMMEDIATE construct at
  all; no LEAVE/EXIT unreachable-code case: this grammar has no such statement, only
  RETURN; `DECLARE ... DEFAULT` is deliberately never treated as a dead-store's "first
  write" — that idiom is used throughout this app's own sample library).
- **Side-by-Side Run Comparison** (`frontend/src/pages/ComparePage.jsx`, route
  `/compare`) — two independent Monaco editor panes, each calling `POST /debug` on its
  own; no backend changes at all, since that endpoint is already stateless per request.
  Once both sides have a trace, one shared step control drives a `sharedStepIndex` both
  panes read from (a shorter trace freezes on its last step once the index passes its own
  length, rather than erroring). `frontend/src/compareTraces.js`'s `computeDivergence()`
  is a pure, execution-free diff over the two `DebugStep` arrays: it walks them by shared
  index and reports the first difference in line/error/branch/shared-variable-value, or a
  `length` divergence if the traces match all the way through but end at different
  lengths; `null` means fully identical. Deliberately doesn't touch the flowchart or the
  Anti-Pattern Advisor's `issues` — only the step trace itself is compared.
- **Report export** (`backend/app/report.py`, `/debug/report`): PDF via **reportlab**
  (chosen over weasyprint — no native GTK/Pango/Cairo dependency to install on this
  Windows dev environment), DOCX via **python-docx**, plain text via stdlib only. The
  flowchart image is rasterized to PNG **client-side** (`frontend/src/svgToPng.js`, via
  `<canvas>`) from the Mermaid SVG the Debugger has already rendered and sent to this
  endpoint as-is — converting Mermaid's `<foreignObject>`-heavy SVG server-side has no
  reliable lightweight option. Stateless: it formats whatever `DebugStep` trace the
  frontend already has from its last `/debug` call, never re-parses/re-interprets.
- **Core pipeline**: `backend/app/tokenizer.py` → `backend/app/parser.py` (hand-rolled
  recursive-descent — chosen deliberately over a parser-generator for documentation
  clarity/control, matching this project's Documentation grading criterion) → AST (plain
  dicts, JSON-serializable) → `backend/app/interpreter.py` (tree-walking) → a
  `DebugStep` trace (see §4).
- **`CALL` support (procedure calling procedure)** — the first Tier 1 phase to touch the
  interpreter core. A submission can now chain multiple `CREATE PROCEDURE`/`CREATE
  FUNCTION` definitions back to back; `parser.parse()` wraps 2+ of them in a new
  `{"type": "ProgramNode", "definitions": [...]}` node (exactly one definition still
  parses to a bare `ProcedureNode`/`FunctionNode`, unchanged) — **the LAST definition in
  source order is the entry point** that actually runs; every definition (entry
  included, enabling self-recursion) is registered by name for `CallStatement` (`CALL
  name(args);`) to resolve at runtime. A `CALL` target must be a `ProcedureNode`
  specifically (calling a `FunctionNode`'s name via `CALL` is a clear error — see
  "Function calls in expressions" below for how a `FunctionNode` actually IS invoked).
  `interpreter._exec_call` gives the callee a
  **fully isolated** scope/cursors/handlers/changed-value-baseline (saved and restored
  around the nested call, via `Interpreter.run()` called recursively so the whole call
  chain lands in one continuous `self.steps` list) — only explicit IN/OUT/INOUT
  parameters cross the boundary; an OUT/INOUT argument must be a plain Identifier (can't
  write back into an expression). `MAX_CALL_DEPTH` (50) guards recursion with a clear
  `InterpreterError`, never a hang. See §4 for the `call` DebugStep field this adds.
- **Function calls in expressions (added in a later phase than `CALL`)** — the
  expression-position counterpart to `CALL`: `name(args)` is now valid anywhere `expr`
  is (an assignment's right-hand side, an IF/WHILE condition, another call's own
  argument, ...), parsed at the `primary` grammar level as `FunctionCallExpr` and
  disambiguated from a plain `Identifier`/`%FOUND` check by a one-token `(` lookahead in
  `parser._parse_primary`. `interpreter._evaluate_function_call` **reuses `_exec_call`'s
  exact scope-isolation/call-depth/call-stack machinery** (not a second
  implementation) — the differences are narrow: the target must be a `FunctionNode`
  (calling a `ProcedureNode` this way is a clear error, symmetric to `CALL`'s own
  restriction), every argument binds like a plain IN (a `FunctionNode`'s params never
  carry a mode, so there's no OUT/INOUT propagation), and `Interpreter.run()` is called
  with `require_return=True` — the callee's `RETURN`ed value is captured via
  `self._last_return_value` (set by `_exec_return` immediately before it raises
  `_ReturnSignal`) and substituted directly into the calling expression. **No `DebugStep`/
  Call Stack schema change was needed** — a called function's own steps carry the exact
  same `call: {procedureName, depth, stack}` field a called procedure's already do (the
  field's own name predates this and was deliberately left as-is rather than renamed,
  since `DebugStep` is a wire contract — see §4), so the existing Call Stack panel and
  Variable Timeline render a function call correctly with **zero frontend changes**;
  only `frontend/src/cfg.js`'s own mirrored `renderExpr` needed a `FunctionCallExpr` case
  (for the flowchart's node labels) since it duplicates the backend's rendering logic
  client-side. Recursion, mutual recursion, and function-calling-function all work by
  the same generalized mechanism (verified directly, not assumed — see
  `backend/app/tests/test_function_call_expression.py`).
- **CASE statement (added in a later phase than function calls)** — both simple
  (`CASE expr WHEN v THEN ...`) and searched (`CASE WHEN cond THEN ...`) forms, as ONE
  AST node type (`CaseStatement`), not two: a simple CASE is just a searched CASE where
  each WHEN's own test is "equals the operand" instead of an independent boolean, so
  `interpreter._exec_case` and `parser._parse_case` each need only one code path.
  `_parse_case` disambiguates the two forms with a one-token lookahead (a WHEN right
  after CASE means searched); every WHEN/ELSE body is parsed via `_parse_block` — **the
  same block-parsing helper IF/WHILE already use**. Missing ELSE is a silent no-op,
  confirmed to match `_exec_if`'s own established convention by reading it first, not
  invented fresh; DIVISION_BY_ZERO while evaluating the operand/a WHEN expression stops
  evaluation immediately and falls through to ELSE/none, same as IF's own "condition
  couldn't be evaluated" behavior generalized to a sequence. **Reuses IfStatement's own
  `branch` DebugStep field verbatim** (`path` is `"when-<N>"`/`"else"`/`"none"` instead
  of IF's fixed `"then"`/`"else"`/`"none"`) — no new DebugStep field. Needed real
  cross-cutting fixes in more places than `FunctionCallExpr` did: `frontend/src/cfg.js`'s
  flowchart builder had **zero** CASE support before this (would have silently dropped
  every WHEN/ELSE body from the diagram) — fixed with a diamond node + one labeled edge
  per WHEN (open-ended, not fixed like IF's then/else) plus ELSE; `backend/app/
  advisor.py` needed five separate fixes (three shared AST walkers plus two
  hand-rolled ones — `_check_nested_loops`'s own walker and `_find_unguarded_fetch` —
  that don't use the shared ones); `backend/app/explainer.py`'s template fallback had no
  CaseStatement case at all. All verified directly by reading each file, not assumed
  generic by analogy — see `backend/app/tests/test_case_statement.py` and the expanded
  `test_advisor.py`.
- **Execution is simulated, not hooked into a real DB engine.** The interpreter
  evaluates procedural-SQL constructs (DECLARE/SET/IF/WHILE/CASE/cursors/handlers) itself; the
  one place real SQL actually runs is cursor `SELECT` queries, executed against a small,
  fixed, auto-seeded in-memory SQLite dataset (`backend/app/demo_db.py`: one table,
  `products(name, price)`, 3 rows, reseeded fresh every `/debug` call — no
  schema-authoring feature, a documented scope boundary not a bug).
- **SQLite has two distinct, unrelated jobs** — don't conflate them:
  1. `backend/app/history.py` — a real on-disk file, `backend/data/debug_history.db`,
     one `debug_history` table, persists the 50 most recent **successful** `/debug` runs
     (failed tokenize/parse/interpret attempts are never logged).
  2. `backend/app/demo_db.py` — an ephemeral `:memory:` connection, recreated per
     request, backing cursor queries only. Nothing here persists between runs.

### Backend file map (`backend/app/`)
| File | Role |
|---|---|
| `tokenizer.py` | Source text → token list |
| `parser.py` | Tokens → AST (grammar documented in its module docstring) |
| `interpreter.py` | AST → `DebugStep` list (tree-walking); also `DebugStep`/`render_expr`/`render_statement_header`/`render_definition_header` |
| `advisor.py` | SQL Anti-Pattern Advisor — static `analyze(ast)` pass, nine checks (six original + three extended static-analysis warnings), rides along on every `/debug` response as `issues` |
| `explainer.py` | Gemini client wiring + per-step explanation (`/explain`) + free-form Q&A (`/ask`) + template fallback |
| `quiz.py` | Gemini-backed 5-question MCQ quiz generation (`/quiz/generate`), reuses `explainer.py`'s client |
| `demo_db.py` | Ephemeral cursor demo dataset |
| `history.py` | Persistent run history (SQLite) |
| `report.py` | Multi-format (PDF/DOCX/TXT) report export (`/debug/report`) — builds one format-agnostic IR from a `DebugStep` trace, then renders it three ways (reportlab / python-docx / plain text) |
| `main.py` | FastAPI app + all routes |
| `tests/` | pytest suite, one `test_*.py` per module above plus `test_*_endpoint.py` per route |

### Endpoints (`backend/app/main.py`)
`GET /health` · `POST /debug` · `POST /debug/report` · `POST /explain` · `POST /ask` ·
`POST /quiz/generate` · `GET /history` · `GET /history/{id}` · `DELETE /history/{id}` ·
`DELETE /history`

### Frontend file map (`frontend/src/`)
| File | Role |
|---|---|
| `App.jsx` | Router + route table + wraps everything in `ThemeProvider` |
| `Layout.jsx` | Site header: brand, nav tabs, theme toggle + Developed-By trigger cluster |
| `ThemeContext.jsx` | Day/Night Mode context/provider (see §3) |
| `DevelopedByModal.jsx` | The "Developed By" modal |
| `theme.css` | All CSS custom properties (dark + light token sets) |
| `App.css` | Every component style, all `var(--...)`-driven, no hard-coded theme colors left |
| `index.css` | Reset only |
| `mermaidColors.js` | Hand-mirrored dark/light hex palette for Mermaid (see §3 — it can't read CSS vars) |
| `cfg.js` | AST → Mermaid flowchart graph + definition (`buildFlowchartGraph`, `renderMermaidDefinition`) |
| `svgToPng.js` | Client-side `<canvas>` rasterization of a rendered Mermaid SVG to a PNG data URL, for the Download Report feature's PDF/Document exports |
| `compareTraces.js` | Pure `computeDivergence(leftSteps, rightSteps)` — the Side-by-Side Run Comparison feature's step-by-step trace diff, no execution of its own |
| `lastProcedure.js` | sessionStorage bridge: lets `/quiz`'s "This Procedure" option see the Debugger's current code without a global store |
| `samples.js` | Built-in sample procedures/functions shown in the Debugger's library panel |
| `pages/DebuggerPage.jsx` | The main debugger UI — editor, breakpoints/Continue/Restart, step navigator, variables, flowchart, SQL Anti-Pattern Advisor panel, Predict Mode, Ask AI, TTS, Download Report |
| `pages/ComparePage.jsx` | `/compare` page — two independent Monaco editor panes, each running its own `POST /debug`, stepped together and diffed via `compareTraces.js` |
| `pages/QuizPage.jsx` | Standalone `/quiz` page (distinct from Predict Mode — see below) |
| `pages/HistoryPage.jsx`, `History.jsx` | `/history` page |
| `pages/HomePage.jsx`, `pages/AboutPage.jsx` | Landing + About |
| `pages/HelpPage.jsx` | `/help` page — full user manual |
| `pages/LearnPage.jsx` | `/learn` page — the mandatory Learn tab (concept explanation + video + references) |
| `Theory.jsx`, `theoryContent.jsx`, `theoryTopics.js` | `/theory` page — concept write-ups with runnable examples (six topics). **Not** the same as the Learn tab above — no video, no references section, not top-right-positioned in nav; reusable content, but a separate page. |

### Known repo cruft
`New/` at the project root is a stray, fully-duplicated snapshot of an earlier
backend+frontend state (tracked in git, ~54 files, committed in "Third commit"). It is
**not** referenced by any build/run script and is not part of the live app — the live
app is `backend/` and `frontend/` at the root. Leave it alone unless the user explicitly
asks to remove it; don't edit files under `New/` thinking they're live.

---

## 3. Design system — "Debugger Notebook"

Dark navy palette is the default/Night theme. Fonts: **IBM Plex Mono** (code/data) +
**Space Grotesk** (display) + IBM Plex Sans (body). Exactly three semantic accents
(amber/teal/coral), hairline borders instead of shadows, flat surfaces, an animated
gutter caret (`▸`, `.editor-caret` in `App.css`) that glides to the current line as you
step.

**Day/Night Mode** (added — see `HANDOFF.md` for status) is CSS-custom-property-driven,
not per-component overrides. Every token is defined twice in `frontend/src/theme.css`:
once on bare `:root` (dark/Night, the default, byte-identical to the pre-theming
values) and once under `:root[data-theme="light"]` (light/Day). `ThemeContext.jsx`
(`ThemeProvider`/`useTheme()`) tracks which is active, persists the choice to
`localStorage` (`spdebugger:theme`), and applies it via a `data-theme` attribute on
`<html>`. `frontend/index.html` has a tiny inline script that applies the stored value
before first paint (same storage key) to avoid a flash of the wrong theme.

**Exact token names** (defined in both blocks in `theme.css`):
```
--bg-base  --bg-panel  --bg-panel-raised
--text-primary  --text-muted
--accent-amber  --accent-teal  --accent-coral
--accent-amber-bg  --accent-teal-bg  --accent-coral-bg
--border-hairline
--editor-bg  --current-line-bg  --chip-scrim-bg
--font-display  --font-mono  --font-body
--radius
```
Light-mode accent colors are a **darkened** shade of the same hue (for text/border use —
the bright dark-mode hex fails WCAG AA on a light background) while `--accent-*-bg` keeps
the original bright hue as a translucent wash. This was verified with the actual WCAG
contrast formula against real composited (alpha-blended) backgrounds, not assumed — see
the comments in `theme.css` right above the light block, including one specific fix
(`--accent-teal` darkened from `#0f766e` to `#0c645d` after an audit caught it undershooting
AA on its own badge tint).

**Monaco and Mermaid do not read CSS custom properties** — Monaco needs its `theme` prop
switched explicitly (`vs-dark` / `vs`, done in `DebuggerPage.jsx`'s `<Editor>`), and
Mermaid's `classDef`/`linkStyle` mini-grammar **rejects `var(...)` outright** (confirmed by
hitting the parse error directly — don't attempt to pass a CSS variable into a Mermaid
color string again). `mermaidColors.js` hand-mirrors the same dark/light hex values in
JS for this reason; keep it in sync with `theme.css` by hand when either changes.

---

## 4. Key technical facts to preserve

- **`DebugStep` is the central contract.** Defined as a dataclass in
  `backend/app/interpreter.py` (`class DebugStep`, ~line 226), serialized to camelCase via
  its `to_dict()` method (~line 239). Every frontend feature — the step navigator, variable
  table, flowchart highlighting, explanations, Ask AI, Predict Mode, History replay, Export
  — is driven by this exact shape. Changing a field name or removing one has wide ripple
  effects across the frontend; changing it requires auditing all of the above.

  Shape (camelCase, as sent over the wire):
  ```
  {
    stepNumber, line, nodeType, statementText,
    variables: { [name]: { value, type, changed, isOutput } },
    branch?:   { condition, result, path },        // IfStatement AND CaseStatement steps
    loop?:     { condition, result, iteration },    // WhileStatement steps only
    cursor?:   { name, rowIndex, currentRow, hasMore },
    error?:    { condition, message, handler },
    returnValue?: { value, type },                  // FunctionNode final RETURN only
    call?:     { procedureName, depth, stack }       // only for steps INSIDE a called procedure/function -- see §2
  }
  ```
  (`variables` entry shape is built by `_snapshot_variables()`, ~line 798 of the same file.)
  `call` was added in the CALL-support phase: present only when `depth >= 1` (a step
  genuinely executing inside a `CALL`ed procedure or, since the "function calls in
  expressions" phase, an invoked `FunctionNode`), omitted entirely for every top-level
  step — so every trace that predates CALL support, and every trace that never uses it,
  is byte-for-byte unchanged. `stack` is the full chain of enclosing procedure/function
  names, outermost first (`stack[-1] == procedureName`, `len(stack) == depth`).
  `procedureName` keeps that name (chosen when only procedures could be invoked this way)
  even though it may now hold a function's name — a deliberate non-rename, not an
  oversight; see §2's "Function calls in expressions" entry for why.

- **Gemini explainer accuracy depends on complete context.** `explainer.py`'s
  `_build_prompt()` (~line 82) explicitly forwards a step's `error` and `cursor` fields
  into the prompt, with an `"IMPORTANT --"` steering line when an error/handler fired —
  this is what makes NOT_FOUND/DIVISION_BY_ZERO steps get explained as "this failed and
  was caught" rather than a generic "a statement ran". If any future change trims what
  gets sent to `/explain` (e.g. stripping `error`/`cursor` before the request), Gemini's
  explanations on those steps will silently degrade to wrong/generic text — there is no
  automated check that would fail if this regresses, so review this by hand.

- **Non-functional requirement: `/debug` must stay under 2s.** Measured directly against
  a live local server (the original 10 built-in `samples.js` procedures, via a Python
  timing script against `POST http://127.0.0.1:8000/debug`): **22.5–76.2ms per call,
  ~30ms average** — comfortably under budget. Not re-verified against the live server
  since (`samples.js` has grown several more samples since — see `HANDOFF.md` — but each
  is a small, fast procedure with no reason to behave differently). The CALL-support
  phase *did* touch the interpreter and re-measured directly (tokenize→parse→run,
  in-process, bypassing the network/live-server layer entirely): a plain no-CALL
  procedure and a two-procedure CALL-based one both averaged **well under 1ms** per run —
  no measurable overhead from the CALL-support changes. The "function calls in
  expressions" phase touched the interpreter core again and re-measured the same way:
  `CheckoutTotal` (two function-call-expression invocations) averaged **0.607ms**, a
  5-level self-recursive function-call chain (`Fact`) averaged **0.478ms** — both still
  well under 1ms, no measurable overhead from this phase either. The CASE statement
  support phase touched the interpreter core a third time and re-measured the same way:
  `ClassifyOrder` (both CASE forms, two separate CaseStatement evaluations) averaged
  **0.407ms** — still well under 1ms. Re-time via the live-server approach (loop the
  sample list, hit `/debug`, measure wall time) if the interpreter, cursor handling, or
  history-write path changes again, and note the new numbers here.

---

## 5. Mandatory course-graded website sections

These five are graded requirements. **Status of each (done/in-progress/not-started) is
tracked in `HANDOFF.md`, not here** — this section only defines what's required:

1. **Learn tab** — concept explanation + video + references, positioned top-right in nav.
   Not the same as the existing `/theory` page (six write-ups, no video, no references
   section, not top-right) — see `pages/LearnPage.jsx` in the frontend file map above.
2. **Developed By** — photo, name, register number, "Guided By: Dr. Swaminathan A,
   Assistant Professor".
3. **Help tab** — full user manual.
4. **Download** — PDF/Document/Text export of inputs, steps, intermediate results,
   output, and graphs.
5. **Day/Night mode toggle.**

---

## 6. Working conventions

- **Phased build**: one Claude Code prompt per phase, worked sequentially. Scope
  creep/gaps discovered mid-phase get fixed with additive, non-breaking patches rather
  than deferred silently.
- **AI prompt log**: **`PROMPT_LOG.md`** at the project root — every phase's actual
  prompt text, in chronological order (with the handful of pre-log phases backfilled as
  clearly-marked reconstructions — see its own header). Keep appending to it at the end
  of each phase; don't let it go stale.
- **Testing**: backend has a thorough pytest suite (`backend/app/tests/`, one file per
  module/endpoint) — run via `cd backend && .venv/Scripts/python.exe -m pytest -q` (or
  activate the venv first). Frontend has no test suite, only `npm run lint` (oxlint) and
  `npm run build` as the correctness gate — treat both as required before considering a
  frontend phase done.
- **Live-verification habit**: this project's sessions have consistently driven the
  actual running app (headless Chrome from the scratchpad — via puppeteer-core when
  available, or a small dependency-free raw-CDP driver script over Node's native
  `fetch`/`WebSocket` when it isn't, as in the Download-feature and SQL Anti-Pattern
  Advisor sessions — not just unit tests) to confirm UI changes really work, and measured
  things (contrast ratios, endpoint timing) rather than assuming — continue that
  standard.

---

## 7. Instruction to future Claude Code sessions

**Always read `HANDOFF.md` immediately after this file**, before making any changes, to
get the actual current status of every section above, in-progress work, and known
bugs/TODOs. This file (`CLAUDE.md`) intentionally does not track that — it will go stale
if status gets written here instead of there.
