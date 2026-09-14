# HANDOFF.md

**A snapshot of exactly where the project stands right now.** This file gets
overwritten/updated at the end of every session — it is not a cumulative log. For
stable project facts (architecture, schema, design tokens) see `CLAUDE.md` instead.

---

## 1. Last updated

**2026-09-14**, end of the session that built **function calls inside procedures** — a
procedure (or another function) can now invoke a FUNCTION from within an expression
(an assignment, an IF/WHILE condition, another call's own argument) and use its RETURNed
value, not just a standalone CALL of a procedure; see §2's new entry and
`PROMPT_LOG.md` §17 for full detail. It followed the session that built **Extended Static
Analysis Warnings** — three more checks (`unreachable-code`, `unused-variable`,
`never-read-variable`) added directly into the existing SQL Anti-Pattern Advisor's own
AST-analysis pass (`backend/app/advisor.py`), not a parallel analysis or a new panel; see
§2's own entry and `PROMPT_LOG.md` §16. That followed the session that built the
**Test-Case Runner** — a pass/fail regression panel over the built-in sample library,
layered on top of (not part of) the original 5 mandatory sections / 4 innovation
features / Tier 1 plan; see §2's Test-Case Runner entry and `PROMPT_LOG.md` §15. That
followed the session that built the **Variable Timeline** — the second of the four
Innovation features to ship
(Variable Timeline/sparklines), leaving only Live Parameter Tuning (dropped, out of
scope — §4) unaddressed from that original list. That followed the session that built
the **Call Stack panel** (the fourth and final Tier 1 item, completing Tier 1 entirely),
which followed the session that built **`CALL` support (procedure calling procedure)** —
the third Tier 1 addition, and the first Tier 1 phase to touch the interpreter core —
which followed the session that added "Continue" and "Restart" to the step navigator,
which directly followed the session that built Breakpoints + Run-to-Breakpoint (the
first Tier 1 addition). Tier 1 (Breakpoints, Step controls, Call Stack, `CALL` support)
was a reassessed push strengthening the project beyond the original mandatory/innovation
scope, given extra time available; it followed the session that built Side-by-Side Run
Comparison (the second Innovation feature at the time), which followed the SQL
Anti-Pattern Advisor session (the first Innovation feature), which followed the Download
feature (the last mandatory section), which followed the Learn tab session (which
created `PROMPT_LOG.md`), which followed the Help tab session, which followed the
session that created this file/`CLAUDE.md` and built Day/Night Mode + the Developed By
modal.

**Re-verified via `git log`/`git status` at the start of this session, and again at the
end** — `24ee5d8` ("Added Call Stack and Variable Timeline") is still genuinely the most
recent commit; no external commit landed mid-session this time. What's uncommitted right
now is **three** sessions' worth layered together: the Test-Case Runner session's own
work (`App.jsx`/`Layout.jsx`/`App.css` edits, `TestCaseRunner.jsx`/
`testCaseExpectations.js`/`pages/TestRunnerPage.jsx`), the Extended Static Analysis
Warnings session's own work (`backend/app/advisor.py`/`backend/app/tests/
test_advisor.py`/`frontend/src/samples.js`/`CLAUDE.md` edits), and this session's own work
(`backend/app/parser.py`/`backend/app/interpreter.py`/`backend/app/advisor.py` again/
`frontend/src/cfg.js`/`frontend/src/samples.js` again/`testCaseExpectations.js` again, plus
the new `backend/app/tests/test_function_call_expression.py`) — see §3. Backend suite:
**270 passing** at the start of this session (confirming the previous phase's own
baseline), **305 passing** at the end (270 + 33 new `test_function_call_expression.py`
tests + 2 more `test_advisor.py` regression tests for a cross-cutting fix this phase's own
grammar change required — see §2). This is the second phase in a row to genuinely touch
the interpreter/parser core (after `CALL` support itself), so this is a real correctness
gate, not a sanity check on an untouched backend.

**One real environment snag worth recording, not glossed over**: port 8000 (this
project's own conventional dev-backend port) was already bound by a **pre-existing**
`uvicorn --reload` process (PID 932, genuinely found via `Get-NetTCPConnection`/
`Get-CimInstance`, not another "unverifiable-PID" case this time) that predates this
session — it wasn't started by this session's own launches (none of which used
`--reload`), so per this phase's own explicit instruction ("kill by the specific PID you
launched, not a blanket kill"), **it was left running, untouched**, rather than assumed
to be safe cruft. Verification instead used a throwaway backend on port 8001 plus a
small dependency-free static-file-server-and-same-origin-proxy (serving the already-built
`frontend/dist/`, proxying API paths to 8001) — the same pattern a prior session
established for this exact kind of situation — rather than editing `vite.config.js`'s
proxy target. See §2 for what this actually verified.

---

## 2. Done

Verified against the actual repo (code present, and where noted, builds/tests green) —
not restated from memory:

- **Core pipeline**: tokenizer → recursive-descent parser → interpreter → `DebugStep`
  trace, covering DECLARE/SET/IF-ELSE/WHILE, cursors (DECLARE/OPEN/FETCH/CLOSE,
  `%FOUND`/`%NOTFOUND`), exception handlers (`CONTINUE HANDLER FOR NOT_FOUND |
  DIVISION_BY_ZERO`), functions (`CREATE FUNCTION ... RETURNS ... RETURN`) and
  procedures in **both** the bare-statement form and the `CREATE PROCEDURE(...)
  BEGIN...END` wrapper form with `IN`/`OUT`/`INOUT` params.
- **Backend endpoints**: `/health`, `/debug`, `/debug/report`, `/explain`, `/ask`,
  `/quiz/generate`, `/history` (GET/GET-one/DELETE-one/DELETE-all) — all implemented, all
  covered by `backend/app/tests/`. Full suite: **223 tests passing** as of this session
  (199 before this session's 24 new `advisor.py`/`/debug`-`issues`-field tests; 176
  before the Download-feature session before that).
- **Debugger page**: Monaco editor, step navigator (Prev/Next/Reset/scrubber/step log),
  live variable watch table (`changed`/`isOutput` badges), animated gutter caret +
  cause→effect connector lines to changed variables, Mermaid control-flow diagram kept in
  sync with the step trace, error banner (handled vs. unhandled), cursor panel, return-value
  panel, Ask AI free-form chat, "⭳ Download Report" format picker (PDF/Document/Text —
  see the new Download feature entry below; this **replaced** the old JSON-only "Export
  Run" button, it isn't an addition alongside it).
- **Flowchart rendering fixes** (`cfg.js`): `ReturnNode` renders readable text
  (`RETURN <expr>;`) in a distinct teal stadium shape with no outgoing edge (execution
  ends there); the function/procedure entry node renders the real signature
  (`Name(params)`) in amber, for both `FunctionNode` and `ProcedureNode`.
- **Text-to-Speech** — `speechSynthesis`-based read-aloud for step explanations, plus an
  "Auto-read explanations" toggle, in `DebuggerPage.jsx`. **This is done, not pending** —
  correcting the original phase plan, which listed TTS under "not started."
- **Predict Mode** (`DebuggerPage.jsx`, UI-labeled "Predict Mode" — internal
  state/class names still literally say `quiz*`, deliberately, to stay distinct from the
  standalone Quiz page below; see the comment on `DebuggerPage.jsx`'s theme state hooks)
  — inline "guess the next value/branch before it's revealed" mode with a running score.
- **Standalone Quiz page** (`/quiz`, `pages/QuizPage.jsx` + `backend/app/quiz.py`) —
  General Theory or This-Procedure 5-question Gemini MCQ quiz, defensive JSON parsing
  (fence-stripping + one retry), results review with teal/coral correct/incorrect
  highlighting, "Try another quiz."
- **Day/Night Mode** — `ThemeContext.jsx`, full light/dark token set in `theme.css`,
  toggle in the nav, Monaco + Mermaid both synced to the active theme, contrast-audited
  (one real AA miss found and fixed — light-mode `--accent-teal`). Code-complete **and
  committed** (`a80392c`).
- **Developed By modal** — trigger + modal, dismissible via close button/backdrop/Escape,
  theme-aware, committed (`a80392c`). **Real content has since been filled in** (name and
  register number are no longer `[NAME]`/`[REGISTER NUMBER]` placeholders — see
  `DevelopedByModal.jsx`) — that specific edit is the one small uncommitted loose end
  called out in §3.
- **Help tab** (`frontend/src/pages/HelpPage.jsx`, route `/help`) — full step-by-step user
  manual, seven accordion sections (`<details>`/`<summary>`, native, keyboard/screen-reader
  friendly, no JS state): what the app does, what inputs it accepts, how to provide input,
  every real button/control (enumerated by reading `Layout.jsx`/`DebuggerPage.jsx`/
  `History.jsx`/`QuizPage.jsx` directly, not invented), how processing works in plain
  language, how to interpret the output, and a pointer to the other pages. Nav entry sits
  in the top-right utility cluster next to the theme toggle and Developed By trigger (its
  own `.help-nav-trigger`/`.help-nav-trigger-active` styling, matching the amber active
  state the main nav tabs use) rather than in the page-tab row, since it's a persistent
  cross-page reference. Fully theme-aware — new CSS in `App.css`'s "Help page" block, no
  hard-coded colors, uses only existing `theme.css` tokens. Live-verified via a headless
  Chrome screenshot against the actual running dev server in both collapsed and expanded
  states (accordion, code chips, the parameters callout, the active nav state all render
  correctly); light-mode was not separately screenshotted this session (see §3) but reuses
  only tokens already contrast-audited elsewhere.
  **One accurate scope note baked into the content itself**: the manual correctly
  documents that there is currently no UI for entering external `IN` parameter values
  before running (the frontend always sends `params: {}` — see `DebuggerPage.jsx`'s
  `handleDebug`) — it tells the user to self-contain values via `DECLARE ... DEFAULT`
  rather than describing a parameter-input control that doesn't exist.
- **Learn tab** (`frontend/src/pages/LearnPage.jsx`, route `/learn`) — **Done
  (placeholder content — needs real video + references before submission).** Three
  always-visible panel sections, not an accordion (unlike Help — this is graded content
  meant to be read in order): CONCEPT EXPLANATION (a draft write-up of "Stored Procedures
  &amp; Functions in Databases, and Debugging Them" — what they are, why they exist,
  procedure-vs-function differences via a comparison table, and why debugging them is
  non-trivial — flagged both with a file-level code comment and a visible `DRAFT` badge
  in the UI), ANIMATED VIDEO (a real, working YouTube iframe embed pointed at the literal
  placeholder `YOUR_VIDEO_ID_HERE`, marked with a code `TODO` and a visible coral
  "PLACEHOLDER" badge so it can't ship unnoticed), and REFERENCES (all five required
  categories — Books/Websites/Research Papers/Educational Resources/Videos — 2-3 entries
  each in correct citation format, every single entry individually badge-marked as a
  placeholder needing a real source). Nav entry added as the **rightmost main tab**
  (`Layout.jsx`'s `NAV_ITEMS`, next to the Help/theme/Developed-By cluster — i.e. the
  actual top-right of the header), with its own permanent amber-outlined
  `.top-nav-item-emphasize` styling (solid amber fill when active) so it stands out from
  its muted siblings per the course's "must be prominent" requirement, rather than only
  `.top-nav-item-active`'s already-existing amber styling. Fully theme-aware — new CSS in
  `App.css`'s "Learn page" block, no hard-coded colors. Live-verified via headless-Chrome
  screenshots in **both** dark and light mode this time (unlike the Help phase, which
  only screenshotted dark), plus a 400px phone-width check.
- **Download feature — multi-format report export** (`backend/app/report.py`,
  `POST /debug/report`; `frontend/src/svgToPng.js`; the Debugger page's new "⭳ Download
  Report" picker) — **Done**, meets the actual graded spec this time (previously
  JSON-only, no graph — see the old §4/§6 entries this replaces).
  - **PDF library: reportlab**, not weasyprint — weasyprint needs the native
    GTK/Pango/Cairo libraries installed on the system to do its HTML-to-PDF conversion,
    which aren't guaranteed present and are painful to install reliably on Windows (this
    project's dev environment); reportlab is pure Python, pip-installs cleanly anywhere,
    and this project's "simplest to integrate" criterion pointed at it once weasyprint's
    OS-dependency risk was weighed. DOCX via **python-docx** (the only real option).
    Added to `backend/requirements.txt`: `reportlab==5.0.1`, `python-docx==1.2.0`,
    `pillow==12.3.0` (reportlab's raster-image handling dependency).
  - **Architecture**: one format-agnostic intermediate representation
    (`ReportSection`/`ReportBlock` in `report.py`) built once from a `DebugStep` trace,
    then rendered three separate ways (reportlab / python-docx / plain text) — so the
    three formats' *content* can't drift apart; only layout differs per renderer.
    Deliberately **stateless and re-execution-free**: the endpoint takes the exact
    `code`/`params`/`steps` the frontend already has from its last `/debug` call and only
    formats them, never re-tokenizes/parses/interprets (verified by a dedicated test that
    monkeypatches `interpreter.run` to explode if the report endpoint ever calls it).
  - **Report content** covers all five required parts: User Inputs (the real SQL +
    params, with an honest "no parameter-input UI exists yet" note when params is empty
    rather than fabricating a value — same scope note the Help tab already documents),
    Processing Steps (every real step, line/type/statement/branch-loop-cursor-error
    detail), Intermediate Results (one row per variable per step, changed/output flags),
    Final Output (the function's return value, or the unhandled-error message, or the
    final variable state table), and Graphs/Tables/Figures (the flowchart image when
    available, plus a steps-by-statement-type table).
  - **Flowchart image**: rasterized **client-side** (`svgToPng.js`, via an offscreen
    `<canvas>`, always on a white background regardless of active theme since the image
    is headed into a printable document) from the Mermaid SVG the Debugger page has
    already rendered, then sent to the backend as a PNG data URL. Deliberately not
    attempted server-side: Mermaid's SVG relies on `<foreignObject>` HTML labels that no
    lightweight Python SVG-to-raster path renders reliably.
  - **Frontend UI**: the old single "⭳ Export Run" JSON button is fully replaced by a
    "⭳ Download Report" trigger that opens a small anchored dropdown (`.report-download-
    menu` in `App.css`) with three options — Download PDF / Download Document / Download
    Text — dismissible by outside click, Escape, or picking an option, matching this
    app's existing modal-dismiss convention. Theme-aware, no hard-coded colors.
  - **Verified thoroughly, not just unit-tested**: 23 new backend tests (`test_report.py`,
    `test_report_endpoint.py`) all built on **real** interpreter-produced `DebugStep`
    traces, never hand-written fixtures. Beyond tests, this session also: (1) hit the
    live backend directly with two different real sample procedures
    (`SafeAverageWithHandlers` — cursors, both handler types, a genuine NOT_FOUND and a
    genuine DIVISION_BY_ZERO firing — and `ComputeTax` — an OUT param) and rendered the
    resulting PDFs to images (via PyMuPDF, a temporary local dev tool only, not added to
    `requirements.txt`) to eyeball actual layout/content correctness; (2) opened the
    generated DOCX files with `python-docx` to confirm real tables/paragraphs/an embedded
    image; (3) drove the **actual running app** end-to-end via raw Chrome DevTools
    Protocol (no puppeteer-core/playwright/chromium-cli available in this environment, so
    a small dependency-free driver script was written using Node 24's native
    `fetch`/`WebSocket`) — loaded `/debugger`, picked a sample, ran Debug, opened the
    format-picker dropdown, and clicked all three downloads for real: zero console
    errors, all three `POST /debug/report` calls returned 200 with the correct
    content-type. A screenshot of the open dropdown confirms the UI itself. Test-run
    entries this created in the real `backend/data/debug_history.db` (ids 95-101) were
    deleted afterward via the app's own `DELETE /history/{id}` endpoint so this session's
    manual testing left no residue in the user's real run history.
- **SQL Anti-Pattern Advisor** (`backend/app/advisor.py`; the Debugger page's new "SQL
  ANTI-PATTERN ADVISOR" panel) — **Done**, the first of the four Innovation features.
  - **Reuses the existing AST, no second parser.** `advisor.analyze(ast)` only reads the
    exact AST `app.parser.parse()` already produces (per this phase's explicit
    requirement) — no new tokenizing/parsing of its own.
  - **Trigger chosen: automatic, on the same action as clicking Debug** (not a separate
    "Analyze" button) — `/debug` already parses the code and already needs to return
    `ast` for the flowchart, so `main.py`'s handler now also computes `issues =
    analyze_anti_patterns(ast)` right after a successful parse and returns it alongside
    `ast`/`steps` in the same response, at zero extra network round trips. One accepted
    scope edge: if interpretation then fails, the whole `/debug` call still 400s as
    before (unchanged interpreter/debugger error-handling contract, out of this phase's
    scope) and the frontend never sees that run's `issues` either — this only shows up
    for a run that both parses *and* executes successfully. A history replay also shows
    no advisor result (issues reset to `null`, same as a fresh page) since old saved runs
    predate this feature and never had issues computed/stored for them.
  - **Six anti-patterns actually implemented** (exactly what's detectable from the
    existing AST — see `advisor.py`'s module docstring for the full reasoning on each):
    1. `select-star` — `SELECT *` in a cursor's query (string-matched against
       `CursorDeclNode.query`).
    2. `cursor-could-be-set-based` — a cursor loop whose body is *only* FETCH +
       accumulator-style `SET x = x + ...` statements, suggesting a single
       `SUM()`/`COUNT()` query instead.
    3. `nested-loops` — a `WHILE` nested inside another `WHILE` (O(n²) risk).
    4. `missing-error-handling` — two asymmetric sub-checks matching
       `interpreter.py`'s own documented asymmetry between the two handler conditions: a
       division with no `DIVISION_BY_ZERO` handler is a **warning** (unhandled division
       really does abort the run), while a cursor `FETCH` with neither a
       `cursor%FOUND` loop guard nor a `NOT_FOUND` handler is only a **suggestion**
       (this interpreter treats unhandled `NOT_FOUND` as always non-fatal — flagging it
       as a hard warning would have been factually wrong, so it isn't one). The `%FOUND`
       loop-guard idiom itself (`ProductPriceTotal`'s own pattern) is correctly never
       flagged — it's the safe alternative to a handler, not a missing one.
    5. `magic-number` — the same non-trivial (excludes 0 and 1) numeric literal
       hard-coded more than once anywhere in the procedure.
    6. `cursor-not-closed` — an `OPEN`ed cursor with no matching `CLOSE` anywhere.
  - **One candidate explicitly NOT implemented, and said so rather than faked**:
    "dynamic SQL string concatenation (SQL injection risk)" — this grammar has no
    `EXECUTE`/`EXEC IMMEDIATE` construct at all and no way to build a SQL string from
    concatenated variables and run it; every cursor query is fixed literal text captured
    verbatim at parse time. There is nothing of that shape in this language, so no check
    was written for it (documented in `advisor.py`'s module docstring rather than left
    unexplained).
  - **Output**: a new full-width panel in `DebuggerPage.jsx` (`.panel-advisor`), placed
    between Ask AI and Control Flow. Each finding renders as a card with a
    severity badge (coral **Warning** / amber **Suggestion** — this app's existing
    two-tier accent language, not new colors), a title, a line number, a plain-language
    explanation, and a suggested fix. A clean run shows a teal "✓ No anti-patterns
    detected" positive confirmation rather than an empty panel (a "no data" placeholder
    is shown separately, only before the first Debug run). Theme-aware, no hard-coded
    colors.
  - **Verified against all 10 real built-in samples** (not fabricated data): 8 are clean
    (`CalculateTotal`, `CalculateDiscount`, `GradeClassifier`, `SumUntilLimit`,
    `TieredPricingCalculator`, `ComputeTax`, `GetDiscountedPrice`, `FindFirstOverLimit`);
    `ProductPriceTotal` and `SafeAverageWithHandlers` both genuinely trigger
    `cursor-could-be-set-based` under real execution — the only one of the six patterns
    any pre-existing sample happens to contain. **Honestly disclosed, not silently
    forced**: since the other five patterns had zero coverage among the existing 10
    samples, they're verified instead by 22 dedicated `test_advisor.py` unit tests (each
    against a real tokenizer/parser-produced AST, never a hand-built dict) plus a new,
    clearly-flagged-as-new sample, **`AntiPatternShowcase`** (added to `samples.js` with
    an explicit "Added specifically for the SQL Anti-Pattern Advisor phase" comment) that
    deliberately contains all six patterns in one runnable procedure — live-verified via
    the same raw-CDP driver approach as the Download phase (loaded the sample, clicked
    Debug, confirmed all 7 findings render with zero console errors, in both dark and
    light theme). It still executes to completion successfully (45 steps, a real
    computed average) — the point is a structurally-bad-but-working procedure, not a
    crashing one. Test-run entries this created in the real history DB were deleted
    afterward, same as the Download phase's own cleanup habit.
- **Side-by-Side Run Comparison** (`frontend/src/pages/ComparePage.jsx`, route
  `/compare`; `frontend/src/compareTraces.js`) — **Done**, the second of the four
  Innovation features.
  - **No backend changes at all.** Reuses `POST /debug` exactly as the main Debugger
    page and the Anti-Pattern Advisor already do — each pane calls it independently with
    its own `code`; since the endpoint is already stateless per request (a fresh
    `demo_db` connection per call, no shared server-side session), two concurrent calls
    need nothing extra from FastAPI. `backend/app/main.py` is untouched by this phase.
  - **UI**: a new nav tab ("Compare", between Debugger and Theory) leads to a page with
    two independent panes ("RUN A"/"RUN B"), each with its own sample-picker `<select>`,
    its own Monaco editor (the same `@monaco-editor/react` component the main Debugger
    page uses, just without that page's caret/connector-line overlay — out of scope
    here), and its own **Debug** button/error message. Both start on the same first
    sample by default, so simply clicking both Debug buttons demonstrates the
    "identical, no divergence" case with zero setup.
  - **Shared stepping**: once both sides have a completed trace, a single "SYNCHRONIZED
    STEPPING" panel appears below both panes with one Previous/Next/Reset/scrubber set
    (reusing `.step-navigator`/`.step-scrubber` as-is) driving a single `sharedStepIndex`
    that both panes read from. A side whose trace is shorter **freezes on its last real
    step** once the shared index runs past its own length — shown grayed with an explicit
    "This run finished after N steps" note — rather than erroring or going blank.
  - **Divergence detection** (`compareTraces.js`, pure functions, no execution of its
    own — just compares two already-computed `DebugStep` arrays): walks both traces by
    shared index and reports the *first* point they differ, checked in this order per
    step: which source line ran, whether one side hit an error the other didn't (or a
    different error condition), which `IfStatement` branch was taken, then any variable
    name the two traces happen to share whose value differs. If every shared step matches
    but the two traces end up different lengths, that itself is reported as a distinct
    "one run finished, the other kept going" divergence. Returns `null` (not an empty
    object) when the traces are identical as far as compared.
  - **Output**: a persistent divergence banner in the stepping panel — teal "✓ No
    divergence detected" when `null`, or a coral-accented card naming the step number,
    the divergence kind, and a plain-language one-line summary (e.g. `Variable
    total differs: 15 (left) vs 20 (right).`) with a "Jump to this step" button. Below
    that, both panes' current-step view (line + statement text, error banner if any, full
    variable table) render side by side; at the exact diverged step both panes get a
    coral outline, and — for a variable-kind divergence specifically — the one differing
    row gets its own coral highlight, reusing the existing amber/teal/coral accent
    language rather than inventing new colors.
  - **Verified live** (not just read-through) via the same raw-CDP driver approach as the
    two prior phases: (a) `CalculateTotal` vs `GradeClassifier` — two real, differently-
    behaving samples — correctly reports a `branch` divergence at step 4 ("Left took the
    'none' branch; right took the 'then' branch"), and "Jump to this step" correctly
    outlines both panes there; (b) `CalculateTotal` run against itself unchanged
    correctly shows the teal "no divergence" confirmation for the full 8-step trace. Both
    checked in dark theme (default) and again in light theme, plus a genuine 400px-wide
    check — `.compare-grid` correctly collapses to one column and the page's own content
    causes no horizontal scroll; the only overflow present is the pre-existing top-nav
    bug (see §6), not made structurally worse by this phase's one extra nav word beyond
    the same acceptable growth the Learn-tab phase already established as precedent.
    Zero console errors across all runs. Test-run history rows this created (ids 119-127
    — including one leftover row from the previous session's own final verification pass
    that had escaped that session's cleanup) were all deleted via `DELETE /history/{id}`
    afterward.
  - **Live Parameter Tuning dropped** — the fourth planned Innovation feature is out of
    scope per this phase's own closing instruction (see §4/§5); it was never started, so
    nothing needed removing from the code, only from the planning lists.
- **Variable Timeline** (`frontend/src/VariableTimeline.jsx`, wired into
  `frontend/src/pages/DebuggerPage.jsx`'s new "VARIABLE TIMELINE" panel) — **Done**, the
  third of the four originally-planned Innovation features (Live Parameter Tuning stays
  dropped — §4). A sparkline per variable, plotting its value across the **full**
  step-trace of the current run (not just the current step's frame, unlike the Variables
  table) — purely a frontend view over the exact `DebugStep` shape `/debug` already
  returns; **no backend/schema changes, no new endpoint** (confirmed by `git status
  --short`: zero files under `backend/` touched, and the full suite re-run before/after
  as a sanity check anyway — 252/252, unchanged).
  - **Self-contained component, deliberately decoupled from its panel placement** (per
    this phase's own instruction, anticipating a future layout rework): `VariableTimeline`
    takes only `steps`, `currentStepIndex`, and `onStepSelect` — it computes its own
    variable grouping/ordering internally and renders its own empty/placeholder states,
    so it doesn't trust or depend on anything `DebuggerPage.jsx` already computes (its
    existing `variableOrder` memo, for instance). The actual JSX wired into the Debugger
    page is a thin `<div className="panel panel-timeline">` wrapper (heading + one
    subtitle line + the component) — that's the only part a future redesign would need to
    touch to re-house this somewhere else.
  - **A real design subtlety worked through, not glossed over (this phase's own
    instruction was to flag schema insufficiencies rather than silently work around
    them)**: a variable name is only unique *within one call frame*, and the same name can
    legitimately belong to several unrelated invocations over one trace — self-recursion
    (`RecursiveFactorial`'s `Fact` declares a fresh `sub`/`result` at every recursion
    level), or two separate sequential `CALL Foo(); CALL Foo();` statements. Naively
    joining every step where a name appears into one line would silently stitch together
    values that have nothing to do with each other — concretely demonstrated against this
    app's own `RecursiveFactorial` sample, where `result` appears in literally every
    single step of the trace (once inside `ComputeFactorial`, once per `Fact` recursion
    level — 6 unrelated variables sharing one name). **The `DebugStep.call` field has no
    unique per-invocation id to key off** — flagged rather than silently patched around by
    enlarging the schema — but on inspection none is actually needed: the interpreter can
    only be at one depth at a time, and a `CALL` always increases `depth` by exactly 1
    relative to the previous step (see `_exec_call`), so a fresh call frame is
    unambiguously identifiable purely from "depth just increased since the last step," and
    returning to a shallower depth always resumes an existing ancestor frame, never
    fabricates a new one. `assignFrameInstances` (in `VariableTimeline.jsx`) replays the
    trace once on exactly that rule -- a pure function of `call.depth` and step order,
    needing no new field -- and correctly reunites a paused frame's own before/after-its-
    nested-call steps into one segment while never merging two genuinely separate
    invocations that happen to share a name, depth, and procedure. Verified live: the
    `result` row on `RecursiveFactorial` correctly shows **×6** separate instances,
    `n`/`sub` show **×5** each (one per `Fact` recursion level) — rendered as visually
    distinct sparkline segments sharing one x-axis, never one misleading merged line.
  - **Non-numeric variables**: a row plots as an actual line for `number`/`boolean` values
    (`boolean` mapped 0/1); a `null` snapshot (a DECLAREd-but-not-yet-SET variable) is
    treated as a gap, not a value of 0, and a segment breaks across it rather than
    interpolating through unknown territory. A variable that's ever a `string` renders as
    a row of small tick marks at each step the existing `changed` flag says its value
    changed (reusing that field directly rather than diffing values itself), plus its
    exact current value as text — a plain numeric line wouldn't be meaningful for text.
    Verified live against `SafeAverageWithHandlers`' `item_name` (a STRING variable):
    renders 0 lines, 1 tick, no crash.
  - **In sync with the rest of the debugger's step navigation, with zero new plumbing for
    it**: the whole component is a pure `useMemo`/render off `currentStepIndex`, so
    Previous/Next/Continue/Restart/the scrubber/step log/breakpoints all update every
    sparkline's current-step marker automatically — verified live, not assumed. Each
    sparkline also has its own hover crosshair (a muted dashed guide, distinct from the
    solid amber current-step guide) with a caption naming the hovered step's line/
    statement text, and clicking a sparkline jumps `currentStepIndex` there via
    `onStepSelect` — the same click-to-jump affordance the Step Log panel and Compare
    page's "Jump to this step" already establish as this app's convention.
  - **Styled to match the Debugger Notebook system, no new colors**: teal for the line
    itself (this app's "at rest/visited" accent), amber for "this value just changed"
    markers and the current-step guide (the same accent as `.var-row-changed`, the editor
    caret, and the Call Stack panel's current-frame highlighting), hairline borders, no
    shadows, `font-mono` for all data. New CSS lives in `App.css`'s "Variable Timeline"
    block.
  - **Verified live**, via a real (not throwaway) backend + Vite dev server this
    session started fresh — both were found stopped at the start of this session (no
    lingering unverifiable-PID quirk this time) and were stopped again afterward to leave
    the environment as found. Confirmed via the same raw-CDP driver approach as every
    prior phase: `CalculateDiscount` (no `CALL` involved) shows plain, single-instance
    sparklines with correct final values (`total` → 108); clicking near the start of a
    sparkline correctly jumps to step 1; Previous/Next/Continue/Restart all still work
    correctly with the panel present. `RecursiveFactorial` demonstrates the ×6/×5
    multi-instance case (above) at both a mid-recursion step and the final unwound step.
    Screenshotted in both dark and light theme (light mode reuses only already
    contrast-audited tokens, no new risk). Explicitly checked the panel's own contribution
    to the pre-existing 400px nav-overflow bug (§6): `.panel-timeline`'s own
    `scrollWidth` measured 350px, fully inside a 400px viewport — the overflow measured at
    that width (`body.scrollWidth` 686px) is entirely attributable to `.top-nav` (625px),
    confirmed directly rather than assumed, so this phase does not make that pre-existing
    bug any worse. Zero console errors throughout. Test-run history rows this session's
    verification created (ids 148-155) were deleted afterward via direct SQL delete
    (mirroring the Call Stack session's own cleanup approach, since no backend was left
    running at cleanup time), confirmed the surviving max id (94) matches every prior
    session's own baseline.
- **Test-Case Runner** (`frontend/src/TestCaseRunner.jsx`,
  `frontend/src/testCaseExpectations.js`, `frontend/src/pages/TestRunnerPage.jsx`, route
  `/tests`) — **Done**, an extra addition beyond the original mandatory/innovation/Tier 1
  scope (like the Variable Timeline's sibling additions, this wasn't on the original
  4-innovation-feature list). A pass/fail regression panel: runs every built-in sample
  through the real `/debug` pipeline (no second execution path) and checks the final
  `DebugStep`'s variable state / return value against a hand-verified expected outcome.
  **No backend changes at all** (confirmed by `git status --short`; full 252-test backend
  suite re-run as a sanity check anyway — unchanged).
  - **Finding reported before implementing, per this phase's own instruction**: no
    expected-output data existed anywhere in the repo, and `samples.js` now holds **13**
    samples, not the 10 the phase's own prompt assumed (two later phases — Call Stack,
    Anti-Pattern Advisor — each added one/two since that framing was last true:
    `OrderTotal`, `RecursiveFactorial`, `AntiPatternShowcase`). Rather than inventing
    values or silently dropping the 3 newer samples from coverage, all 13 samples' expected
    final state was **hand-derived from their own deterministic source** (every sample
    self-contains its values via `DECLARE ... DEFAULT`; the cursor samples' `products`
    table is fixed — Widget/10, Gadget/25, Gizmo/15), then **cross-checked against a real
    run of the actual interpreter pipeline** — all 13 matched exactly. Full derivation is
    documented inline in `testCaseExpectations.js`. See `PROMPT_LOG.md` §15 for the full
    writeup.
  - **Self-contained component, same reasoning as `VariableTimeline.jsx`**: takes no
    required props (defaults to the real `samples.js`/`testCaseExpectations.js`), owns its
    own run state, sequential `/debug` calls, diffing (float-epsilon-tolerant), and
    rendering — a future redesign only touches `pages/TestRunnerPage.jsx`'s thin wrapper.
    A sample with no expectation entry surfaces its own "NO EXPECTED OUTPUT" status,
    excluded from the pass/fail denominator rather than silently skipped or assumed
    passing.
  - **Own page/nav tab** (`/tests`, between Compare and Theory), not bolted onto the
    Debugger page — same precedent Compare already set, since a fixed 13-sample sweep
    doesn't depend on whatever's currently loaded in the Debugger's one editor.
  - **Verified live**: real dev servers started fresh (both found stopped at session
    start), driven via the same raw-CDP approach this project's history has used
    throughout — confirmed **13 / 13 passed** against the real backend. The fail-diff path
    was verified by temporarily breaking one expected value (`CalculateTotal`'s `total` to
    999): correctly reported **12 / 13 passed** with a coral card showing
    `total | 999 | 108`; reverted. The no-expectation path was verified by temporarily
    removing `ComputeTax`'s entry: correctly reported **12 / 12 passed, 1 sample skipped**
    with the flagged badge/message; reverted, then a final run reconfirmed the clean
    13/13 state. Screenshotted in both dark and light theme; 400px-width check confirmed
    the panel's own `scrollWidth` (350px) fits the viewport, not adding to the
    pre-existing `.top-nav` overflow (§6). Zero console errors across every run. `npm run
    lint`/`npm run build` both clean (same 2 pre-existing warnings).
  - **Cleanup**: 164 test-run history rows this session's verification created (ids
    95-258) deleted via direct SQL delete afterward, confirmed the surviving max id (94)
    matches every prior session's baseline; both dev servers stopped afterward. One
    process-hygiene note: this session's Chrome cleanup used `taskkill /IM chrome.exe /T`,
    which kills every Chrome process on the machine rather than just the one launched for
    verification — overly broad, flagged rather than repeated silently (see
    `PROMPT_LOG.md` §15); a future session should kill by the specific launched PID
    instead.
- **Extended Static Analysis Warnings** (`backend/app/advisor.py`) — **Done**, another
  extra addition beyond the original scope, hooked directly into the existing SQL
  Anti-Pattern Advisor's own AST traversal rather than a parallel analysis pass or a new
  UI panel, per this phase's own explicit instruction. Three new checks, taking the
  Advisor from 6 to 9 total; **zero frontend changes needed at all** (confirmed by
  `git status --short`: only `backend/app/advisor.py`/`backend/app/tests/
  test_advisor.py`/`frontend/src/samples.js`/`CLAUDE.md` changed) — the existing
  `.advisor-issue`/`.advisor-severity-badge` rendering in `DebuggerPage.jsx` is fully
  generic over `severity`/`title`/`line`/`message`/`suggestion`, with no per-category
  logic anywhere, so three new categories using only the existing "warning"/"suggestion"
  severities render correctly with the code that already existed.
  - **`unreachable-code`** (severity "warning", both sub-cases) — two distinct,
    purely-AST-provable patterns:
    1. Any statement positionally after a RETURN within the SAME statement list — a new
       `_iter_statement_lists` walker (unlike the existing `_iter_statements`, which
       flattens the whole tree, this preserves block boundaries) finds the first RETURN
       in each block and flags everything after it in that same block as dead, anchored
       at the first dead line. **LEAVE/EXIT are NOT implemented**: this grammar has no
       such statement at all (confirmed directly against `app.parser`'s own grammar,
       not assumed) — RETURN is the only unconditional-exit construct that exists.
    2. An IF whose condition is a compile-time constant (`IF 1 > 2 THEN ...`) — a new
       `_fold_constant` evaluator mirrors `Interpreter._evaluate_binary` exactly (same
       `+ - * / > < = !=` operator set) and returns `None` the instant anything isn't a
       literal (an Identifier, a %FOUND check, ...), so an ordinary data-dependent
       condition — the overwhelming common case — is correctly left alone. Deliberately
       NOT extended to WHILE (a constant-false WHILE never running is rarer and more
       contrived; IF/ELSE branch-level dead code is the well-scoped, high-value case).
  - **`unused-variable`** (severity "suggestion") — a DECLAREd local never read by ANY
    expression anywhere in the procedure/function (a condition, another statement's
    right-hand side, a RETURN, or a CALL argument) — being assigned one or more times
    does not count as "used", per this phase's own explicit instruction. A
    self-referencing accumulation (`SET x = x + 1;`) correctly counts as reading `x`, so
    it's never flagged (this app's own WHILE-loop counters/running-totals are all exactly
    this shape). **Deliberately scoped to DECLAREd locals only, not procedure/function
    parameters** — this grammar's parameter nodes carry no line number of their own (see
    `app.parser._parse_procedure_param`/`_parse_function_param`), so there's no single
    unambiguous line to point at the way there is for a DECLARE; a future phase could
    extend this against the procedure/function's own header line if it turns out to
    matter. This scoping choice also means an OUT parameter (write-only by design) is
    never at risk of a spurious "unused" flag, without needing any special-case code for
    OUT specifically.
  - **`never-read-variable`** (severity "warning") — "dead store" detection: a SET
    assigns a value, then a LATER SET to the same name overwrites it before anything
    reads the first value. **Genuinely distinguishable from unused-variable in this
    grammar, not a collapse into the same case** (the phase's own instruction asked to
    judge this): a dead-stored variable can still be read *elsewhere* in the procedure —
    being read at all is exactly what keeps it off the unused-variable list — so the two
    checks catch different, non-overlapping situations (proven directly by a dedicated
    test asserting a variable flagged `never-read-variable` is NOT also flagged
    `unused-variable`). Deliberately scoped to a straight-line run within ONE statement
    list — this grammar has no cross-branch/cross-loop-iteration dataflow analysis (a
    real liveness analysis needs a fixed-point computation over the control-flow graph,
    out of scope here), so any IF/WHILE/handler/CALL encountered between two writes is
    treated as a conservative barrier (a new `_touched_names` helper) rather than
    analyzed — it stops tracking whatever names that statement could plausibly touch,
    rather than risk a wrong accusation. **`DECLARE x TYPE DEFAULT expr;` is deliberately
    NOT treated as a "first write" the way a SET is** — `DECLARE total NUMBER DEFAULT 0;
    SET total = price * quantity;` is the standard, idiomatic initialize-then-compute
    pattern used throughout this app's own sample library (CalculateTotal,
    CalculateDiscount, TieredPricingCalculator, and more); treating it as a dead store
    would fire on a large fraction of completely normal code. This was not assumed —
    verified directly by running the extended Advisor against all 13 pre-existing
    samples (see below) before finalizing this scoping decision.
  - **Verified against all 13 pre-existing samples, not just imagined**: three
    previously-"clean" samples now genuinely, correctly surface new findings —
    `GradeClassifier` (`grade` computed via 3 separate IF/ELSE branches but never read
    anywhere — a real, accurate finding, not a bug in the check), `ProductPriceTotal` and
    `SafeAverageWithHandlers` (`item_name`, FETCHed from the cursor but never used; the
    latter's `average` also never read). All three were investigated and confirmed as
    genuine true positives under the phase's own literal definition ("assignment-only
    doesn't count as used"), not suppressed to keep old samples artificially quiet. Every
    one of the other 10 (including `AntiPatternShowcase`, whose 7 pre-existing findings
    are completely unchanged, plus 2 new genuine ones) produced **zero** false positives
    from any of the three new checks — confirmed by an in-process script running the real
    tokenizer/parser/`advisor.analyze()` against every sample's actual source, not
    hand-reasoned. `OrderTotal`/`RecursiveFactorial` (`ProgramNode`-shaped, multi-
    definition sources) still produce zero issues from any check, old or new — a
    pre-existing, documented limitation from the `CALL` support phase (`ast.get("body",
    [])` degrades to `[]` for a `ProgramNode`) that every new check inherits unchanged
    rather than silently working around.
  - **One pre-existing test fixture broke, correctly** — `test_advisor.py`'s
    `test_clean_procedure_has_no_issues` used a stripped-down `CalculateTotal` snippet
    that (unlike the real sample) never read `total` a second time, so it now correctly
    triggers `unused-variable` — fixed by extending the fixture to actually read `total`
    again (`SET total = total + 1;`), the same way the real sample does via `SET tax =
    total * 0.08;`. Not a bug in the new checks; a stale test fixture exposed by them.
  - **New sample added**: `StaticAnalysisShowcase` (`frontend/src/samples.js`), mirroring
    `AntiPatternShowcase`'s precedent — deliberately bad on purpose, all four new-finding
    shapes in one small, still-successfully-executing procedure (the interpreter genuinely
    reaches and fires the early `RETURN 0;`, then stops — 8 real steps, no error). Gives
    the three new checks a live, permanent, discoverable home in the sample library
    instead of only being provable via backend unit tests.
  - **Testing**: 18 new `test_advisor.py` unit tests (isolated ASTs, both true-positive
    and true-negative cases per check — self-reference not flagged, a normal
    data-dependent condition not flagged, writes in different IF branches not flagged, an
    unrelated statement between two writes doesn't block detection, a `ProgramNode`
    source still produces nothing). Full backend suite: **270 passing** (252 before this
    phase + 18 new).
  - **Verified live**, not just via pytest: real dev servers started fresh (both found
    stopped at session start; backend/frontend PIDs noted explicitly this time), a raw-CDP
    driver (same dependency-free approach as every prior phase) loaded `/debugger`,
    selected each of `GradeClassifier`/`ProductPriceTotal`/`SafeAverageWithHandlers`/
    `AntiPatternShowcase`/`StaticAnalysisShowcase`, clicked Debug, and read the real
    rendered Advisor panel DOM — every new finding's severity/title/line matched the
    pytest-level predictions exactly, word for word. All other 9 samples (including
    `OrderTotal`/`RecursiveFactorial`) confirmed to still show the clean "No anti-patterns
    detected" state. `StaticAnalysisShowcase` screenshotted in both dark and light theme —
    the coral "Warning" badge/left-border styling (the exact same classes
    `cursor-not-closed`/the division-by-zero check already use) renders correctly in both
    with zero new CSS. Zero console errors across every sample/run. `npm run lint`/`npm
    run build` both clean (same 2 pre-existing warnings).
  - **Process hygiene, per this phase's own explicit instruction (a direct callback to
    the previous phase's own noted learning)**: Chrome was launched with
    `--remote-debugging-port`, the exact PID that ended up owning that port was confirmed
    via `netstat`/`tasklist` before use, and cleanup killed **only that specific PID**
    (`taskkill /F /PID <n>`) — never a blanket `taskkill /IM chrome.exe`. Confirmed this
    mattered for real, not just in theory: `tasklist` immediately after showed ~27 other
    `chrome.exe` processes still running (the user's own real browser session/its
    multi-process architecture) that a blanket kill would have taken down. The backend and
    frontend dev servers were likewise stopped by their own specific PIDs.
  - **Cleanup**: history rows created during this session's live verification (ids
    95-273) deleted via direct SQL delete afterward, confirmed the surviving max id (94)
    still matches the established baseline; both dev servers and the specific Chrome PID
    stopped afterward.
- **Function calls inside procedures** (`backend/app/parser.py`, `backend/app/
  interpreter.py`) — **Done**, another extra addition beyond the original scope (like
  Extended Static Analysis Warnings before it). A procedure (or another function) can now
  invoke a FUNCTION from *within an expression* — an assignment's right-hand side, an
  IF/WHILE condition, another call's own argument — and use its RETURNed value, not just
  a standalone `CALL` of a procedure. **Deliberately reuses `_exec_call`'s exact
  scope-isolation/call-depth/call-stack machinery, not a second implementation** — per
  this phase's own explicit instruction.
  - **Parser**: `name(args)` is now valid anywhere `expr` is, parsed at the `primary`
    grammar level (`_parse_primary`) as a new `FunctionCallExpr` node
    (`{"type", "name", "args", "line"}`, same shape as `CallStatement`'s own `args`).
    Disambiguated from a plain `Identifier`/`%FOUND`-check by a simple one-token `(`
    lookahead — the three are mutually exclusive by construction, so there's no real
    ambiguity to resolve.
  - **Interpreter**: a new `_evaluate_function_call` (dispatched from `_evaluate` on
    `FunctionCallExpr`) mirrors `_exec_call` almost line for line — same
    save/swap/restore of `scope`/`_previous_values`/`_output_param_names`/`cursors`/
    `handlers`, same `_call_depth`/`_call_stack` push/pop, same `MAX_CALL_DEPTH` guard.
    The differences are narrow: the target must be a `FunctionNode` (calling a
    `ProcedureNode` this way, or `CALL`ing a `FunctionNode`, are both clear
    `InterpreterError`s — verified, not just designed, via dedicated tests both
    directions), every argument binds like a plain IN (a `FunctionNode`'s params never
    carry a mode, so there's no OUT/INOUT unwind needed), and `run()` is called with
    `require_return=True`. **A new `self._last_return_value` instance attribute** carries
    the callee's `{value, type}` out — set by `_exec_return` immediately before it raises
    `_ReturnSignal`, read by `_evaluate_function_call` immediately after the *matching*
    `run()` call returns; proven safe for nested calls specifically (a RETURN's own value
    expression containing another function call resolves and is fully consumed before
    that RETURN's own `_exec_return` runs), not just asserted.
  - **DIVISION_BY_ZERO handling needed zero new code** — a signal raised while evaluating
    a function-call argument simply propagates up through `_evaluate` like any other
    deep-expression division, caught by whichever *enclosing statement's* own try/except
    is already watching for it; a signal raised inside the callee's own body is handled
    (or not) entirely by that callee's own isolated `handlers`, exactly like a CALLed
    procedure's own internal handler already works. Both directions verified live via
    dedicated tests, not assumed from the design alone.
  - **Step-trace / Call Stack schema: verified to need NO change, per this phase's own
    "flag it if the schema can't represent this... rather than force-fitting it"
    instruction** — `_current_call_info`/`_record_step` are already fully generic over
    *what* is on the call stack, so a called function's own steps get the identical
    `call: {procedureName, depth, stack}` shape a called procedure's steps already do,
    confirmed by direct inspection of the actual trace output (not just code-read) before
    writing a single line of frontend code. The one deliberate, documented non-change:
    the field stays named `call.procedureName` even though it may now hold a function's
    name — renaming it would ripple through every DebugStep consumer (Call Stack panel,
    Variable Timeline, Download reports) for a purely cosmetic gain, and `DebugStep` is
    this app's central wire contract (CLAUDE.md §4).
  - **Zero changes needed to the Call Stack panel or Variable Timeline** — both already
    read the generic `call` field with no procedure-specific branching, confirmed live
    (see below), not just by code inspection. **One real frontend gap found and fixed**:
    `frontend/src/cfg.js` keeps its own mirrored, client-side copy of `render_expr` (for
    the flowchart's node labels) and had no `FunctionCallExpr` case, which would have
    rendered `SET y = ?;` instead of `SET y = Square(x);` — fixed with the matching case.
  - **One cross-cutting correctness gap found and fixed in `backend/app/advisor.py`**
    (from the *previous* phase, Extended Static Analysis Warnings): its shared `_iter_exprs`
    walker didn't know about `FunctionCallExpr`'s `args`, so a variable used ONLY as a
    function-call argument would have been wrongly flagged `unused-variable` by that
    phase's own new checks. Fixed at the single shared walker (not per-check), covered by
    2 new regression tests. Confirmed via a full sweep against all 15 samples that this
    introduced zero new findings on any sample that predates function calls.
  - **New sample**: `CheckoutTotal` (`frontend/src/samples.js`) — a FUNCTION
    (`ComputeDiscountedPrice`) called TWICE from a PROCEDURE, once in an IF's own
    condition and once more in the taken branch's assignment, proving the mechanism is
    genuinely re-entrant (two separate invocations, not a cached one-shot call). Its
    `price`/`rate` parameter names deliberately collide with `CheckoutTotal`'s own local
    `price` — an accidental-but-kept demonstration that scope isolation and the Variable
    Timeline's multi-instance-per-name logic both handle a same-name collision across a
    function call correctly, confirmed live (see below). `testCaseExpectations.js` got a
    matching entry, hand-derived and cross-checked against a real interpreter run,
    following the same rigor the Test-Case Runner phase established.
  - **Testing**: 33 new `backend/app/tests/test_function_call_expression.py` tests
    (parser: every valid expression position, disambiguation from a plain
    Identifier/%FOUND check, a malformed-call parse error; interpreter: basic
    substitution in an assignment/IF/WHILE condition, multiple/zero arguments, an
    arbitrary expression as an argument, function-calling-a-different-function, self-
    recursion — verified against a real 5-level-deep `Fact`, mutual recursion between two
    functions, mixing CALL+function-call-expression in one chain, both infinite-recursion
    depth-guard directions, all 4 DIVISION_BY_ZERO combinations (argument vs. inside the
    body, handled vs. not), scope isolation including same-named variables, and the
    step-trace `call` field's exact shape both one level deep and nested two levels deep)
    plus 2 new `test_advisor.py` regression tests for the cross-cutting fix. Full backend
    suite: **305 passing** (270 before this phase + 33 + 2 new).
  - **Verified live**, not just via pytest, including a real environment snag worked
    through rather than worked around (see §1): `CheckoutTotal` loaded and Debugged
    against a throwaway backend/static-proxy setup, stepped to inside
    `ComputeDiscountedPrice`'s own frame — the Call Stack panel correctly showed
    "ComputeDiscountedPrice (current)" / "CheckoutTotal (caller)" with the Variables
    table correctly scoped to just `price`/`rate`, in both dark and light theme,
    zero frontend code changes needed for either. The Variable Timeline correctly showed
    `price ×3` (CheckoutTotal's own local plus the two separate function-call
    invocations, visually distinct segments) and `rate ×2` (the two different rate
    arguments, 0.1 and 0.2) — a real, live exercise of the exact same-name-across-frames
    logic the Variable Timeline phase built for recursion, now proven to generalize to
    function calls too. The flowchart panel rendered without crashing and its node text
    genuinely contained `ComputeDiscountedPrice(...)` (confirmed by reading the rendered
    DOM text, not assumed from the code fix). The Test-Case Runner correctly reported
    `CheckoutTotal` as a 12-step PASS alongside the other 13 samples with expectations
    (14/14 passed, `StaticAnalysisShowcase` still correctly flagged as having no expected
    output defined — a pre-existing gap from the phase before, not this phase's to fix).
    Zero console errors across every run. `npm run lint`/`npm run build` both clean (same
    2 pre-existing warnings).
  - **Process hygiene, per this phase's own explicit instruction**: every process this
    session launched (a throwaway backend on port 8001, a small static-file-server-plus-
    proxy on port 5175, headless Chrome) was tracked by its own specific PID and killed
    individually at cleanup (`taskkill /F /PID <n>`) — confirmed via `tasklist` before
    each kill that the PID was genuinely the process just launched. The **pre-existing**
    process found bound to port 8000 (PID 932, a `uvicorn --reload` this session never
    started) was deliberately left running, untouched — not assumed to be safe cruft
    just because it looked like leftover dev-server debris.
  - **Cleanup**: history rows created during this session's live verification deleted via
    direct SQL delete afterward, confirmed the surviving max id (94) still matches the
    established baseline.

### Tier 1 additions (beyond the original mandatory/innovation scope)

A reassessed push (Breakpoints, Step controls, Call Stack, `CALL` support) added given
extra time available, on top of the 5 mandatory sections and 4 innovation features above.

- **Breakpoints + Run-to-Breakpoint** (`frontend/src/pages/DebuggerPage.jsx`) — **Done**,
  the first Tier 1 addition. **Note**: the button originally labeled "Run to Breakpoint"
  here was renamed to **"Continue"** in the very next session (see the entry directly
  below) — every mention of it below is left as originally written for an accurate
  build history, but the live UI today shows "Continue," not "Run to Breakpoint."
  - **Purely a frontend consumption-layer feature, exactly as scoped.** No backend files
    touched at all (confirmed by `git status --short` showing only `DebuggerPage.jsx` and
    `App.css` changed this phase). Breakpoints are a `Set<lineNumber>` in component state;
    "Run to Breakpoint" is nothing more than fast-forwarding `currentStepIndex` forward
    through the *already-computed* step trace to the next step whose `line` is in that
    set — the interpreter, `/debug`, and step-trace generation are all untouched, per the
    phase's explicit instruction (and it genuinely was possible without backend changes,
    so nothing was reported back as blocked).
  - **UI**: Monaco's built-in glyph margin (`glyphMargin: true` in editor options, no
    custom line-number UI built) shows a coral dot (`.breakpoint-glyph`, a CSS `::before`
    circle centered in the cell Monaco allocates) on any breakpointed line. Clicking
    either the glyph margin or the line-number column itself (both real Monaco
    `MouseTargetType`s, told apart in `editor.onMouseDown`) toggles that line's
    breakpoint. A "⏵ Run to Breakpoint" control sits between Next and Reset in the
    existing step-navigator row, plus a small hint line under the editor showing how many
    breakpoints are currently set.
  - **No-breakpoints behavior — chosen explicitly, one of two options the phase spec
    offered**: "Run to Breakpoint" stays enabled and simply runs to the end of the trace
    when no breakpoints are set, rather than being disabled with an explanatory tooltip.
    Chosen because the same search-forward loop naturally falls through to the last step
    when nothing matches — no separate code path needed, and it reads as "run" doing what
    a user would expect regardless of whether they've set anything yet.
  - **Visual distinction between "paused at a breakpoint" and an ordinary step landing on
    the same line**: the current-line decoration gets a second class,
    `debug-current-line-breakpoint` (coral tint, overriding the normal amber-ish
    `--current-line-bg`), plus a `⏸ Paused at breakpoint` badge next to the step counter
    — both only when `breakpoints.has(currentStep.line)`, so navigating there normally
    (Previous/Next/scrubber/step log) without ever pressing Run to Breakpoint looks
    exactly as it always has.
  - **Breakpoints deliberately survive `resetRunState`** (new sample loads, a fresh Debug
    run) rather than being cleared — they're an editor-level concept independent of any
    one run, matching how a real debugger keeps breakpoints across re-runs. Known,
    accepted simplification: breakpoints track a raw line **number**, not a Monaco
    decoration ID tied to that specific code, so heavily editing lines above a breakpoint
    (adding/removing lines) can leave the marker sitting on now-different code — the
    phase's own spec asked for "a set of line numbers," not edit-tracking, so this wasn't
    built out further.
  - **Verified live** via a raw-CDP driver dispatching *real* mouse clicks
    (`Input.dispatchMouseEvent`) at the actual on-screen coordinates of the target line's
    gutter cell — not a fake JS call into component internals — so this exercised the
    real `onMouseDown` handler: (a) `CalculateTotal`, breakpoint on line 8, "Run to
    Breakpoint" correctly stopped at Step 7 of 8 with the coral tint/badge showing and the
    step log confirming line 8; (b) toggled that breakpoint back off, Reset, "Run to
    Breakpoint" again correctly ran all the way to Step 8 of 8 (the no-breakpoints/
    run-to-completion case); (c) confirmed Previous/Next/Reset still behave exactly as
    before (Step 1 → 2 → 1); (d) `GradeClassifier`, breakpoint on line 9 (inside the
    ELSE of a nested IF), correctly stopped there too. All four checked again in light
    theme. Zero console errors throughout. Backend suite re-run before this phase started
    (223 passed, confirming the required baseline) and again after finishing (still 223
    passed, confirming the "untouched" claim rather than just asserting it) — the
    explicit gate this phase's own prompt required. `npm run lint`/`npm run build` both
    clean (same 2 pre-existing warnings, unrelated to this phase). Test-run history rows
    created during verification (ids 128-130) were deleted afterward via
    `DELETE /history/{id}`, same established habit as every prior phase.
- **"Continue" + "Restart"** (`frontend/src/pages/DebuggerPage.jsx`) — **Done**, a
  cleanup/completion pass on Tier 1's navigation controls, requested to round out
  Previous/Next/Reset/Run-to-Breakpoint into a coherent, non-redundant set. **Note on
  wording**: this phase's closing instruction said to record "Step Over/Continue/
  Restart" as done, but the phase body (its numbered steps 1-5) only ever specified
  Continue and Restart — no distinct "Step Over" behavior was described anywhere in it.
  No new Step Over control was built: Previous/Next already serve that role (advance
  exactly one step), and a real Step-Into-vs-Step-Over distinction isn't meaningful yet
  since this grammar has no `CALL`/procedure-invocation support to step into (see the
  still-not-started `CALL` support item below) — inventing a control for a distinction
  that can't yet exist would have been guessing at an unspecified feature rather than
  following what was actually asked. Treating "Step controls" (the Tier 1 category) as
  satisfied by Previous/Next/Continue/Restart together, not by a fabricated fifth button.
  - **Key discovery this phase — both requested "new" controls already existed under a
    less accurate name, so this was a rename-in-place, not two new buttons:**
    1. **"Continue"**: the prompt asked for a control that "advances forward to the next
       breakpoint... from wherever you currently are," and said to check whether
       "Run to Breakpoint" already did this or always restarted from step 0. Inspection
       of `runToBreakpoint`'s loop (`for (let i = currentStepIndex + 1; ...)`) confirmed
       it already searched forward from the current position, not from 0 — it was always
       "Continue" in standard debugger terms (VS Code/gdb: resume from wherever you
       paused), just mislabeled as a fresh "run." **No logic change was needed** — only a
       rename: `runToBreakpoint` → `continueExecution`, button label "⏵ Run to
       Breakpoint" → "⏵ Continue", tooltip reworded to "Resume execution from here..."
       instead of "Run forward through this trace...".
    2. **"Restart"**: the prompt asked for a control that "resets execution back to step
       0 of the CURRENT trace... without needing to re-click Debug or re-fetch," and said
       to check what the existing "Reset" button actually did. Inspection of
       `resetSteps` showed it only ever called `setCurrentStepIndex(0)` (plus clearing
       Predict Mode score state) — it never touched `steps`/`ast`/`code` at all, so it
       was already exactly "Restart" in behavior; the name "Reset" just read as if it
       might clear the editor/trace entirely, which it never did. **No logic change was
       needed** — only a rename: `resetSteps` → `restartTrace`, button label "Reset" →
       "↺ Restart", tooltip added ("Jump back to step 1 of this same trace -- no re-run,
       nothing re-fetched").
  - **Final control order**: `◀ Previous | Next ▶ | ⏵ Continue | ↺ Restart` — four
    controls, not six. The phase's own illustrative order
    ("Previous | Next | Continue | Run to Breakpoint | Restart | Reset") was explicitly
    only an example pending the merge-redundancy check in steps 1-2; once that check
    found both "new" controls already existed under old names, keeping a separate
    "Run to Breakpoint" alongside an identical "Continue" (or a separate "Reset" alongside
    an identical "Restart") would have been two visibly duplicate buttons doing the exact
    same thing — merged instead, per the phase's own "merge/rename rather than just
    appending more buttons" instruction.
  - **No new CSS was needed** — same button element, same `.step-navigator` styling,
    only the label/handler names changed, so `App.css` is untouched by this phase
    (confirmed via `git status --short`: only `DebuggerPage.jsx` changed).
  - **Known, explicitly out-of-scope side effect of the rename**: `HelpPage.jsx`'s
    control-reference list still says `<strong>Reset</strong> -- jumps back to step 1 of
    the current trace without re-running Debug` — that description is still factually
    accurate for what the button *does*, but the button is no longer *labeled* "Reset,"
    and the Help tab still says nothing about breakpoints/Continue at all (a gap carried
    over from the Breakpoints phase, which also excluded Help). Left untouched since this
    phase's own instructions excluded Help/Learn tabs — flagged here rather than silently
    left inconsistent; see §6.
  - **Verified live** via the same raw-CDP driver approach: loaded `SumUntilLimit` (a
    5-iteration WHILE loop), set one breakpoint on the loop body's `SET total = ...`
    line, clicked Debug, then Continue twice in a row — first stopped at Step 5 of 19
    (the loop's first pass through that line), a **second** Continue click from there
    advanced to Step 8 of 19 (the loop's *next* pass, not a repeat of Step 5 and not a
    restart) — this is the concrete proof that Continue resumes from wherever you are,
    not from the top. Clicked Restart from Step 8: landed on Step 1 of 19, and a
    monitored `Network.requestWillBeSent` log confirmed **zero** additional `/debug`
    requests fired (only the original Debug click's single POST exists for the whole
    session) — Restart genuinely never re-fetches. Previous/Next confirmed still working
    unchanged (Step 1 → 2 → 1). Toggled the breakpoint off, Restarted, clicked Continue
    again: correctly ran to Step 19 of 19 (end of trace), confirming the merged
    no-breakpoints behavior survived the rename. All of the above re-checked in light
    theme. Zero console errors throughout. Backend suite: 223 passing before this phase
    started (the required baseline) and 223 again after (backend genuinely untouched —
    `git status --short` shows only `DebuggerPage.jsx` changed). `npm run lint`/
    `npm run build` both clean (same 2 pre-existing warnings). Test-run history rows
    created during verification (ids 131-135) deleted afterward via `DELETE /history/{id}`.
- **`CALL` support (procedure calling procedure)** — **Done**, the third Tier 1 item, and
  the first one to touch `tokenizer.py`/`parser.py`/`interpreter.py`. Full details below
  since this is exactly the grammar/AST/step-trace schema info the NEXT phase (Call
  Stack) needs.
  - **Findings reported before implementing, per this phase's own instruction**: the
    parser could only ever produce ONE top-level definition per submission — there was no
    multi-procedure "program" concept and no procedure registry anywhere, so `CALL` had no
    way to find a callee at all until that was added. The interpreter had exactly one flat
    `scope`/`cursors`/`handlers`/change-baseline per run, with no way to isolate a nested
    invocation's variables from its caller's.
  - **Grammar/parser changes** (`backend/app/tokenizer.py`, `backend/app/parser.py`):
    - `CALL` added as a keyword.
    - New statement: `CALL name(arg1, arg2, ...);` → `{"type": "CallStatement", "name",
      "args", "line"}` (`args` is a list of ordinary expression nodes — any expression is
      syntactically valid; the interpreter is what later requires an OUT/INOUT argument
      specifically to be an Identifier). Parseable anywhere any other statement is
      (top level, inside IF/WHILE, inside a handler's action).
    - **`parse()` now accepts multiple chained `CREATE PROCEDURE`/`CREATE FUNCTION`
      definitions in one submission.** Exactly one definition still returns the bare
      `ProcedureNode`/`FunctionNode` shape, byte-identical to before this phase (verified
      by a dedicated test, and by all 223 pre-existing tests still passing unmodified) —
      **zero risk to any existing single-procedure sample or History entry.** Two or more
      chained definitions are wrapped in a new top-level node:
      `{"type": "ProgramNode", "definitions": [ProcedureNode | FunctionNode, ...], "line"}`.
    - **Convention: the LAST definition in source order is the entry point** — the one
      actually executed. Every definition (including the entry one itself) is registered
      by name so `CALL` can find it; registering the entry under its own name is what
      makes self-recursion work with no extra syntax. Definition order does NOT affect
      which sibling a `CALL` can reach (the whole registry is built before anything
      executes) — only WHICH definition is the entry point depends on position.
    - The bare/legacy Procedure form (no `CREATE` wrapper) is **completely unaffected** —
      it has no name, so it can never be a `CALL` target, and mixing it with `CREATE`-
      wrapped multi-procedure sources in one submission isn't supported (an honest
      limitation, documented in `parser.py`'s own module docstring, not a bug).
  - **Interpreter changes** (`backend/app/interpreter.py`):
    - `Interpreter._exec_call` resolves the target by name in a registry
      (`Interpreter._procedures`, built once by the module-level `run()` from every
      `CREATE` definition in the source), and only accepts a `ProcedureNode` target —
      calling a `FunctionNode`'s name via `CALL` is a clear `InterpreterError`, not
      silently allowed (this grammar has no expression-position function calls at all —
      out of scope for "procedure calling procedure").
    - **Scope isolation is total.** The callee gets a completely fresh
      `scope`/`cursors`/`handlers`/changed-value-baseline — none of the caller's
      variables, cursors, or handlers are visible to it, and vice versa. Only explicit
      parameter binding crosses the boundary: IN/INOUT argument expressions are evaluated
      once in the CALLER's scope before the callee's frame is installed; OUT/INOUT
      parameters' final values are written back into the caller's variables after the
      callee returns. **An OUT/INOUT argument must be a plain Identifier** (there's no way
      to "write back" into an expression like `x + 1`) — a clear `InterpreterError` if
      violated. Implemented by saving/restoring five `Interpreter` attributes around a
      **recursive call to `Interpreter.run()` itself** for the callee's body (reusing its
      existing entry-step + `_ReturnSignal` handling unchanged) — `self.steps`/
      `self._step_number` are deliberately NEVER swapped, so the whole call chain
      (including recursive/mutual recursion) lands in ONE continuous, flat trace, not a
      separate trace per procedure.
    - **Recursion is allowed** (self-recursion and mutual recursion through a chain of
      procedures both work — both are covered by tests). `MAX_CALL_DEPTH = 50` guards it:
      exceeding it raises a clear `InterpreterError` ("exceeded the maximum call depth"),
      never a hung server or a Python `RecursionError`.
    - **Target-not-found / wrong-target-type / wrong-argument-count / non-Identifier-OUT-
      argument** all raise BEFORE anything is recorded (matching every other statement's
      existing "structural problems raise before the step" pattern, e.g. `_exec_set`'s
      "variable not declared" check). Only a genuinely dynamic problem — a
      `DIVISION_BY_ZERO` while evaluating an argument expression — is attached to the
      `CALL` statement's own step; if a handler makes it non-fatal, the call itself is
      simply skipped entirely (the callee's body never runs), mirroring `_exec_set`'s
      "the assignment simply didn't happen."
  - **Step-trace schema addition (this is the part the next phase, Call Stack, depends
    on)**: every `DebugStep` recorded while inside a CALLed procedure's own execution
    (including its synthetic entry step) now carries an extra, **optional** field:
    ```
    call?: { procedureName: string, depth: number, stack: string[] }
    ```
    `stack` is the full chain of enclosing procedure names, outermost first
    (`stack[-1] === procedureName`, `stack.length === depth`) — included so a future
    frontend can render "what's currently on the call stack" directly from one step,
    without replaying the whole trace and tracking depth deltas itself. **Omitted
    entirely (not `null`, not present at all) for every step at the top level** (depth 0)
    — exactly like `branch`/`loop`/`cursor`/`error` already are when not applicable — so
    **every trace that existed before this phase, and every trace that never uses `CALL`,
    has a completely unchanged wire shape.** The `CALL` statement's own step (e.g. "CALL
    Foo(a, b);") is recorded in the CALLER's frame, at the caller's own depth, BEFORE the
    callee's frame is installed — so it only carries `call` if the caller itself is
    already nested.
  - **No backend endpoint/other-module changes needed at all** — confirmed by inspection,
    not assumed: `main.py`'s `/debug` handler passes `ast`/`steps` straight through
    regardless of shape (unmodified, zero risk to Download/History); `history.py` only
    ever `json.dumps`/`json.loads`s `ast`/`steps` generically (unmodified); the SQL
    Anti-Pattern Advisor's `analyze()` does `ast.get("body", [])`, which returns `[]` for
    a `ProgramNode` (no `"body"` key) — confirmed by direct test to return `[]` with no
    crash, a graceful, deliberate degradation rather than a fix (out of this phase's
    scope) — so a `CALL`-based submission today shows "no anti-patterns detected" rather
    than erroring, simply because the Advisor doesn't understand this AST shape yet. The
    frontend's flowchart builder (`cfg.js`) and the Compare page likewise don't recognize
    `ProgramNode`/`CallStatement` yet — out of this phase's explicit scope (frontend
    untouched entirely) — see §6 for the consequence.
  - **Testing** (`backend/app/tests/test_call_statement.py`, new, 28 tests; one new test
    in `test_debug_endpoint.py`): tokenizer/parser coverage (CALL parses with/without
    args, inside an IF body, missing semicolon/paren errors, multi-definition chaining,
    the last-definition-is-entry convention, single-definition backward compatibility);
    interpreter coverage (two-level CALL with OUT propagation, INOUT propagation across
    two sequential calls, an arbitrary expression as an IN argument, caller/callee scope
    isolation with a same-named variable, a callee NOT inheriting the caller's handler or
    cursor, calling a nonexistent procedure, calling a FunctionNode via CALL, wrong
    argument count, non-Identifier OUT/INOUT arguments, self-recursion computing a correct
    result (5! via `Fact` calling itself) with the expected max depth reached, direct
    infinite recursion hitting the depth guard, MUTUAL recursion (A calls B calls A ...)
    also hitting the depth guard, unhandled and handled `DIVISION_BY_ZERO` in a CALL
    argument) plus one `/debug`-endpoint test confirming the whole pipeline end-to-end
    with no `main.py` changes. **The new "sample procedure pair"** this phase's own spec
    asked for (`ComputeSubtotal`/`OrderTotal`) is a backend test fixture, not a
    `frontend/src/samples.js` addition — see the note in the test file itself for why
    (frontend explicitly out of scope, and `ProgramNode`/`CallStatement` wouldn't render
    meaningfully in the flowchart/Advisor UI yet anyway). Full suite: **252 passing**
    (223 before this phase + 29 new).
  - **Performance**: re-measured directly (tokenize→parse→run, in-process, bypassing the
    stale live dev server — see below) since this phase touched the interpreter, per
    `CLAUDE.md` §4's own policy — both a no-CALL and a CALL-based procedure averaged well
    under 1ms per run; no measurable overhead introduced.
  - **One environment quirk hit and left alone**: the long-running local dev backend
    (port 8000) did not pick up these code changes even after several seconds/retries —
    `netstat` shows it listening under a PID that no process-inspection tool (`tasklist`,
    PowerShell `Get-Process`/`Get-CimInstance`) can actually find, an unverifiable-PID
    quirk this environment has surfaced before (see the SQL Anti-Pattern Advisor
    session's own notes). Did **not** attempt to kill/restart it, since the actual PID
    couldn't be confirmed and this phase's real verification gate is the pytest suite
    (which imports the current source directly via FastAPI's `TestClient`, not the stale
    external process) — fully satisfied regardless. If the user wants to try `CALL`
    support live via curl or the running app, the dev backend process likely needs a
    manual restart to pick up these changes.
- **Call Stack panel** (`frontend/src/pages/DebuggerPage.jsx`, `frontend/src/App.css`) —
  **Done**, the fourth and final Tier 1 item. **Purely a frontend consumption-layer
  feature, exactly as scoped** — no interpreter/backend files touched at all (confirmed
  by `git status --short`: only `DebuggerPage.jsx`/`App.css`/`samples.js` changed), and
  the backend suite was re-run before and after as a sanity check anyway (252/252,
  unchanged).
  - **What it displays**: a new "Call Stack" panel in the Debugger's LIVE STATE column,
    right above the error banner/Variables table. Reads the `call` field the `CALL`
    support phase already produces per `DebugStep` (`{ procedureName, depth, stack }`,
    present only once execution is inside a CALLed procedure) — no new backend data
    needed.
  - **One display detail worth documenting for future sessions**: the interpreter's own
    `stack` only ever lists procedures reached *via a CALL* — it does not include the
    entry procedure itself (the one that started running when Debug was clicked), since
    the interpreter's own `_call_stack` list only grows on a `CALL`. To show a true
    "1 frame at top level, 2 frames once inside a nested call" picture (matching how a
    real debugger's call stack always includes the outermost frame), the frontend
    prepends the entry procedure's name itself — read from `ast` (`ast.name` for a bare
    `ProcedureNode`/`FunctionNode`, or `ast.definitions[last].name` for a `ProgramNode`,
    `null` for the legacy bare/wrapper-less Procedure form, which has no name and can
    never be a `CALL` target anyway) — onto the `call.stack` array before rendering. This
    is a pure display computation (`entryProcedureName`/`callStackFrames`, both
    `useMemo`s in `DebuggerPage.jsx`), not a change to the trace data itself.
  - **Rendering**: innermost (currently executing) frame first — reads as "what's running
    right now, and what called it" without reading bottom-up. The current frame gets an
    amber-accented card + "current" badge (same amber this app already uses for
    "current"/"changed" everywhere else — the current-line highlight, `.var-row-changed`,
    `.changed-badge`); every caller above it in the list gets a muted card + "caller"
    badge and a depth number. A procedure with no `CALL`s at all (i.e. every pre-existing
    sample) still shows a 1-frame list with its own name marked current, rather than an
    empty panel — this reads as "here's what's executing" at all times rather than only
    appearing once `CALL` is used, and was a deliberate choice over a fully collapsed/
    blank top-level state. The one genuinely collapsed case is the legacy bare-Procedure
    form (no name, no `entryProcedureName`) with no active `call` — it shows a plain
    "Top level — not inside a CALL." line instead of a list, since there's no name to
    put in a frame there.
  - **Live-updates automatically as the user steps** — Previous/Next/Continue/Restart/the
    scrubber/step-log/breakpoints all already funnel through `currentStepIndex`, and the
    panel is a pure `useMemo` off `currentStep`, so **no new plumbing was needed** for any
    of them; this was verified live, not just assumed (see below).
  - **A real crash bug was found and fixed in the course of this phase, in
    `frontend/src/cfg.js`'s caller** (not in `cfg.js` itself — see below): `cfg.js`'s
    `buildFlowchartGraph(ast)` only ever understood a single procedure/function body
    (`ast.body`) and had never been taught about the `CALL`-support phase's `ProgramNode`
    wrapper (`{ type: "ProgramNode", definitions: [...] }`, no top-level `body` key at
    all). Since this phase is the first to put a `ProgramNode`-shaped AST in front of a
    live Debug run (via the two new samples below), clicking Debug on either one would
    have thrown inside `buildFlowchartGraph` (`for (const stmt of statements)` over
    `undefined`) with **no error boundary anywhere in this app** to catch it — a hard
    whole-page crash, confirmed by first reproducing it, not just reasoned about.
    **Fixed without touching `cfg.js`'s own graph-building/rendering logic at all** (per
    this phase's explicit "don't touch flowchart generation" scope): `DebuggerPage.jsx`
    now derives a `flowchartAst` — the entry definition itself (last one, per the
    last-definition-is-entry convention) for a `ProgramNode`, or the AST unchanged
    otherwise — and passes that to `buildFlowchartGraph`, wrapped in a `try/catch` as a
    last-resort guard. The resulting diagram shows the entry procedure's own control flow
    only (a `CALL Foo(...)` line renders as a plain rect labeled "CallStatement" via
    `cfg.js`'s existing default case, since it still doesn't recognize that node type
    specifically — a cosmetic gap, not a crash, and still out of this phase's scope to
    polish). Confirmed live: `OrderTotal` now renders a correct, non-crashing flowchart.
  - **Two new samples added to `frontend/src/samples.js`**, per this phase's own
    instruction to move the `CALL` demo out of the backend test suite and into the real
    sample library now that the frontend understands it:
    1. **`OrderTotal`** — `ComputeSubtotal`/`OrderTotal` (the same pair the `CALL`
       support phase used as a backend test fixture), rewritten as a zero-external-param
       entry point (`OrderTotal()` self-contains its values via `DECLARE ... DEFAULT`,
       same constraint every other sample already documents — the frontend has no
       IN-param-collection UI) that CALLs `ComputeSubtotal` with an OUT argument.
       Demonstrates the 1-frame → 2-frame → 1-frame cycle.
    2. **`RecursiveFactorial`** — `Fact`/`ComputeFactorial`, self-recursion (`Fact` CALLs
       itself, registered under its own name per the `CALL` support phase's registry
       convention) computing 5! via a zero-param entry point. Demonstrates the panel past
       depth 2. **One deliberate addition beyond the interpreter test's original shape**:
       a trailing `SET result = result + 0;` no-op after the `CALL` in `ComputeFactorial`
       — without it, the trace's very last step would land deep inside `Fact`'s own frame
       (whose OUT-propagated value never gets a step of its own back in
       `ComputeFactorial`'s frame, since there'd be nothing left to execute there), so the
       demo would never actually show the panel unwinding back to 1 frame with a visible
       final answer. Documented inline in `samples.js` for why it's there.
  - **Verified live**, not just read-through — and this took real troubleshooting worth
    recording for future sessions:
    - The real dev backend (port 8000) is confirmed **genuinely occupied** this session
      (a fresh `uvicorn` bind attempt on it failed with `WinError 10048`, proving a real
      listener), yet still the same unverifiable-PID quirk as every prior session
      (`Get-Process`/`Get-CimInstance` find nothing for the PID `netstat` reports) — so a
      cross-origin throwaway backend was started on port 8001 instead, purely for this
      session's own verification, and shut down again afterward.
    - Pointing the real Vite dev server (port 5173) at that throwaway backend would have
      meant editing `vite.config.js`'s proxy target and restarting the dev server —
      **the restart attempt was correctly blocked by the permission classifier**
      (stopping a live process the user is running), so that path was abandoned; the
      `vite.config.js` edit was reverted immediately, confirmed via `git status --short`
      showing no diff.
    - Instead, a small **dependency-free static-file-server-plus-same-origin-proxy**
      (plain Node `http`, no dependencies) was written to serve the already-built
      `frontend/dist/` (via `npm run build`, already required as this phase's frontend
      gate) and same-origin-proxy the API paths to the throwaway backend — avoiding both
      the blocked dev-server restart and the cross-origin CORS/preflight issues hit when
      trying to fetch port 8001 directly from the port 5173 origin in headless Chrome.
      This, plus the same raw-CDP driver approach (Node's native `fetch`/`WebSocket`,
      Chrome headless) this project's history has used throughout, drove the **actual
      built app**: loaded `OrderTotal`, clicked Debug, confirmed the panel shows exactly
      1 frame (`OrderTotal`, current) at step 1; stepped to inside the `CALL`, confirmed
      exactly 2 frames (`ComputeSubtotal` current, `OrderTotal` caller) with the Variables
      table correctly scoped to the callee only; clicked Continue, confirmed it unwound
      back to exactly 1 frame; clicked Restart, confirmed the panel and step counter both
      correctly reset. Loaded `RecursiveFactorial`, clicked Debug, scrubbed to a
      depth-5 step: confirmed **exactly 6 frames** (5×`Fact` + `ComputeFactorial`,
      innermost `Fact` marked current, correct descending depth numbers 5→0), then
      scrubbed to the final step: confirmed it unwound back to exactly 1 frame
      (`ComputeFactorial`, current). Confirmed Previous/Next/Continue/Restart/the
      scrubber all still work correctly against the new panel with zero JS console
      errors throughout. Screenshotted in both dark (default) and light theme — the
      amber "current"-frame styling reads cleanly in both. Also confirmed the flowchart
      panel (post-fix, see above) and the SQL Anti-Pattern Advisor both render without
      crashing for the new `ProgramNode`-based `OrderTotal` sample (Advisor correctly,
      harmlessly shows "no anti-patterns detected" — the same documented degradation from
      the `CALL` support phase, not a new gap this phase introduced).
    - **9 test-run history rows this verification created** (ids 139-147 — the throwaway
      backend writes to the exact same real `backend/data/debug_history.db`, since
      `history.py`'s `DB_PATH` is resolved relative to the module file, not the process's
      working directory) were deleted afterward via direct SQL delete (equivalent to the
      usual `DELETE /history/{id}` cleanup — no backend was left running to call that
      endpoint through at cleanup time), confirmed the surviving max id (94) matches
      exactly what every prior session's own cleanup already left behind.
  - **`cfg.js`/the Anti-Pattern Advisor still don't fully understand `CALL`-based
    procedures** — only the one crash was fixed (see above); the flowchart still doesn't
    render the callee's own control flow inline, and the Advisor still can't analyze a
    `ProgramNode` at all. Both remain an accepted, documented gap (§6) for a future
    frontend-facing phase, not something this phase's own scope ("displaying existing
    call-trace data... don't touch interpreter/backend logic") asked for.

---

## 3. In progress right now

Nothing is genuinely half-built right now — every feature in §2 is code-complete.

- **Three sessions' worth of work is now uncommitted, layered together** (Call Stack +
  Variable Timeline were committed by the user partway through the Test-Case Runner
  session — `24ee5d8` — see §1, and nothing new has been committed since). What's left
  uncommitted right now:
  - From the **Test-Case Runner** session: edits to `frontend/src/App.jsx`,
    `frontend/src/Layout.jsx`, `frontend/src/App.css` (the `/tests` route/nav tab +
    styling), the new `frontend/src/TestCaseRunner.jsx`,
    `frontend/src/testCaseExpectations.js`, `frontend/src/pages/TestRunnerPage.jsx`.
  - From the **Extended Static Analysis Warnings** session: `backend/app/advisor.py`,
    `backend/app/tests/test_advisor.py`, `frontend/src/samples.js` (the
    `StaticAnalysisShowcase` sample), `CLAUDE.md`.
  - From **this session** (**function calls inside procedures**): `backend/app/parser.py`,
    `backend/app/interpreter.py`, `backend/app/advisor.py` again (the
    `FunctionCallExpr`/`_iter_exprs` fix), `frontend/src/cfg.js`, `frontend/src/
    samples.js` again (`CheckoutTotal`), `frontend/src/testCaseExpectations.js` again,
    `CLAUDE.md` again, plus the new `backend/app/tests/test_function_call_expression.py`.
  - All three sessions' doc updates (`HANDOFF.md`/`PROMPT_LOG.md`).

  Confirmed via `git status --short`. Three phases deep on top of each other now,
  including two that touched the interpreter/parser core — worth committing before it
  grows further. See §7.
- The student photo in the Developed By modal is still the placeholder inline SVG
  silhouette, not a real photo file (the text content itself is real and committed).
- Day/Night Mode itself was only ever exercised in one headless-Chrome instance during
  its original verification session — not spot-checked in a second browser engine. Not
  blocking, just unverified; noted here since nothing since has re-tested it.

---

## 4. Not started yet

**All 5 mandatory course-graded sections are now code-complete** (§2) — none remain
in this list. What's left is real content for the Learn tab (§6) and everything below:

**Three of the four originally-planned innovation features are now done** (SQL
Anti-Pattern Advisor, Side-by-Side Run Comparison, Variable Timeline — see §2):

- **Live Parameter Tuning — dropped, out of scope.** Explicitly removed from the plan by
  a prior session's own closing instruction rather than left as "not started" — it was
  never begun, no code exists for it, and none should be added later under this name
  without a fresh scoping prompt from the user. This is now the only originally-planned
  feature (mandatory or innovation) not either done or deliberately dropped.

**All four Tier 1 items are also done** — Breakpoints, Step controls, `CALL` support, and
Call Stack (§2) — Tier 1 is complete. A genuine Step-Into-vs-Step-Over distinction was
never built as part of "Step controls" (Previous/Next already serve that role); worth
reconsidering only under a fresh, explicitly-scoped prompt, not assumed here.

---

## 5. Agreed build order

All 5 mandatory sections, in the agreed order — **every one is code-complete and
committed**:

1. ~~Day/Night mode + Developed By~~ — code-complete, **committed** (`a80392c`); real
   Developed-By content also committed since (`56a629a`).
2. ~~Help tab~~ — code-complete, **committed** (`49bcd98`).
3. ~~Learn tab~~ — code-complete, **committed** (`49bcd98`), **placeholder content**
   (draft concept explanation, placeholder video ID, placeholder references — §2) still
   needs real material before submission.
4. ~~Download feature upgrade~~ — code-complete, thoroughly verified, **committed**
   (`56a629a`).

Then, per the original plan: Quiz page enhancements (if any beyond the current
General-Theory/This-Procedure version — undefined, needs the user to scope), then the
innovation features:

1. ~~SQL Anti-Pattern Advisor~~ — code-complete, thoroughly verified, **committed**
   (`56a629a`).
2. ~~Side-by-Side Run Comparison~~ — code-complete, thoroughly verified, **committed**
   (`56a629a`).
3. ~~Variable Timeline/sparklines~~ — **Done** this session, thoroughly verified (§2),
   not yet committed (§3).
4. ~~Live Parameter Tuning~~ — **dropped, out of scope** (§4), not attempted.

Then the reassessed Tier 1 push (§2's new subsection), given extra time available:

1. ~~Breakpoints + Run-to-Breakpoint~~ — code-complete, thoroughly verified, **committed**
   (`9b4b6e1`). Its "Run to Breakpoint" button was renamed to "Continue" in the very next
   session — same underlying logic, no behavior change.
2. ~~Step controls~~ — **Done**, via the "Continue"/"Restart" cleanup pass (§2),
   thoroughly verified, **committed** (`5bb3534`).
3. ~~`CALL` support~~ — **Done**, thoroughly verified (§2 has the full grammar/AST/
   step-trace details), **committed** since (see §6's commit-status history).
4. ~~Call Stack~~ — **Done** this session, thoroughly verified (§2), not yet committed
   (§3). **Tier 1 is now fully complete.**

See §7 for what has to happen *before* moving further down this list, though.

**Text-to-Speech is already done** (§2) — it was in the original "later" queue in the
plan but has already been built.

---

## 6. Known bugs, TODOs, and cruft

Scanned directly (`grep` for `TODO`/`FIXME`/`XXX`/`HACK`/placeholder markers across
`backend/app` and `frontend/src`, plus manual inspection) rather than assumed:

- **No `TODO`/`FIXME` comments anywhere in `backend/app` or `frontend/src`** — the
  codebase itself is clean of inline markers. The gaps below are structural/process gaps,
  not code-level TODOs.
- **`New/` at the project root is stray, committed duplicate cruft.** A near-complete
  second copy of an earlier backend+frontend snapshot (~54 files), tracked in git since
  "Third commit," not referenced by any build/run script, not part of the live app.
  Recommend deleting it in a future session — **has not been touched**, since removing
  tracked files wasn't in scope for this doc-writing session and deleting things needs
  explicit confirmation.
- **`PROMPT_LOG.md` exists** (created in the Help Tab session, at the project root) —
  every phase from "Help Tab" onward is logged there with the literal prompt text; the
  three initial commits and the Day/Night+Developed-By phase are backfilled as
  reconstructed summaries (rebuilt from `git show` diffs and this file's own history,
  clearly marked as reconstructed since no literal prompt was recorded for them at the
  time). Keep appending to it — don't let it go stale.
- **Help tab now describes a button by a label that no longer exists.** `HelpPage.jsx`'s
  control-reference list still says `<strong>Reset</strong> -- jumps back to step 1 of
  the current trace without re-running Debug` — that's still exactly what the button
  *does*, but this session renamed it to "Restart," so the Help tab now names a control
  that isn't on screen anymore. It also still says nothing about breakpoints or
  "Continue" at all (that gap dates back to the Breakpoints phase, which also excluded
  Help). **Deliberately left untouched** — both the Breakpoints phase and this one
  explicitly excluded Help/Learn tabs from scope — but flagged here rather than left
  silently inconsistent. A small, Help-tab-scoped follow-up phase should update that one
  list item and add a line about breakpoints/Continue.
- **Commit-status history, for context**: this file wrongly kept claiming Day/Night+
  Developed-By and Help+Learn were uncommitted across three sessions before the
  Anti-Pattern Advisor session corrected it via `git log`. The session after that
  (Side-by-Side Run Comparison) then left the Download feature, the Anti-Pattern Advisor,
  the Developed-By content edit, and its own Compare work all genuinely uncommitted — and
  **all of that was committed since**, in one commit (`56a629a`) made outside a Claude
  Code session; the following Breakpoints, Continue/Restart, and `CALL` support sessions
  were each committed too — except that claim was **wrong for the Call Stack session**:
  `git log` shows `CALL` support did get committed (`8a7cc35`), but the Call Stack
  session's own frontend changes were never committed despite that session's HANDOFF
  entry describing the tree as freshly clean — an actual case of the exact mistake this
  lesson keeps warning about, caught this session by checking `git log`/`git status`
  directly rather than trusting the previous entry (see §1's correction). **What's
  uncommitted right now** is the Call Stack session's work plus this session's own
  Variable Timeline work, layered together — see §3. Lesson keeps standing, reinforced
  by a real miss this time: `git log`/`git status` are ground truth, checked fresh every
  session, never carried over from what the last session's notes said — and a HANDOFF
  entry claiming "nothing to commit"/"tree is clean" should still be spot-checked against
  `git log`, not taken on faith.
- **`ProgramNode`/`CallStatement` are now partially understood by the frontend** — this
  session (Call Stack) taught `DebuggerPage.jsx` enough about `ProgramNode` to display the
  call stack and to avoid crashing the flowchart panel (see §2), but did not do a full
  audit of every consumer, since that was explicitly out of this phase's scope too
  ("displaying existing call-trace data... don't touch interpreter/backend logic," and
  Download/Compare were both on the explicit do-not-touch list). Concretely, as of now:
  the flowchart (`cfg.js`, via `DebuggerPage.jsx`'s new `flowchartAst` derivation) shows
  the entry procedure's own control flow correctly (confirmed not to crash — see §2 — with
  one cosmetic gap: a `CALL` statement renders as a generic rect labeled "CallStatement"
  rather than "CALL Foo(args);", since `cfg.js`'s own `renderStatementHeader` still
  doesn't have a case for it); the SQL Anti-Pattern Advisor still degrades to "no issues
  found" rather than actually analyzing a `ProgramNode` (unchanged from the `CALL` support
  phase, confirmed still non-crashing); the Download report and Side-by-Side Comparison
  pages have still never been exercised against this AST shape at all — Compare has no
  flowchart of its own so it's structurally unaffected by the crash this session fixed,
  but Download does rasterize the flowchart image client-side and hasn't been specifically
  checked against a `ProgramNode`-based sample. Worth a follow-up phase if `CALL`-based
  procedures are meant to be fully first-class across every page, not just the main
  Debugger.
- **Learn tab ships with placeholder content by design** (§2) — draft concept-explanation
  prose (unreviewed against the actual course rubric), a literal `YOUR_VIDEO_ID_HERE`
  video embed, and placeholder references in every category. All three are visibly
  flagged in the UI (a `DRAFT` badge and coral `PLACEHOLDER` badges) so this can't be
  mistaken for finished content, but it still needs a real video ID and real, verified
  references before submission.
- **Pre-existing mobile nav overflow, surfaced again (still not fixed) this session**:
  at ~400px viewport width the top nav (`.top-nav` in `App.css`, no `flex-wrap`)
  overflows horizontally instead of wrapping onto a second line. Predates the Learn tab
  (confirmed via `git show HEAD:frontend/src/App.css` in an earlier session); this
  session added one more nav item (`Compare`) which, same as the Learn tab's own
  precedent, makes an already-tight row overflow a little more without introducing or
  worsening the underlying cause. Explicitly checked this session that the Compare
  page's *own* content does not add to this — at 400px width `.compare-grid` collapses
  cleanly to one column and contributes no horizontal scroll of its own; the only
  page-level horizontal overflow measured came from the nav row itself. Left unfixed
  again since it's shared header layout, out of scope for this phase too (the phase
  prompt explicitly says "don't fix that bug, just don't make it worse" — verified it
  wasn't); worth a small dedicated fix later (e.g. `flex-wrap: wrap` on `.top-nav`
  itself, not just `.site-header-right`).
- **`backend/data/debug_history.db` needed manual cleanup again this session** (every
  session so far has needed this) — ids 148-155 (8 rows, from this session's live-browser
  verification against a real backend this session started fresh on port 8000) were
  deleted via direct SQL delete afterward (both dev servers had already been stopped by
  the time cleanup ran, so no backend was left running to go through
  `DELETE /history/{id}`); checked first for stragglers past the previous session's own
  claimed cleanup range (none found — ids up to 147 were genuinely all gone, surviving max
  id was 94, matching every prior session's own baseline exactly). Same reminder as every
  prior session: any real run of this app's backend during manual verification always
  needs this cleanup step.
- **Variable Timeline shows every variable that ever appeared anywhere in the run, not
  just ones reachable from the current frame** — a deliberate difference from the
  Variables table (§2): the table is scoped to "what's in scope right now," the Timeline
  is scoped to "everything that happened this run." A variable declared only inside a
  procedure that was CALLed gets a row even while the current step is back at the caller
  (its sparkline just shows nothing at the current-step x-position, correctly, since it's
  out of scope there) — this is intentional, not a bug, but worth knowing if it looks odd
  next to the Variables table showing fewer rows for the same step.
- **Anti-Pattern Advisor doesn't cover a history-replayed run** (§2) — `issues` is only
  ever set from a live `/debug` response; replaying a saved History entry restores
  `ast`/`steps` but leaves `issues` at `null`, so the Advisor panel shows its
  "Run Debug" placeholder even though a trace is already on screen. Deliberate, scoped
  choice (recomputing would mean either persisting `issues` in `history.py`, out of this
  phase's scope, or duplicating `advisor.py`'s logic in JS) rather than an oversight —
  but worth fixing later if History replay + Advisor together turn out to matter.
- **No frontend automated test suite** — `npm run lint` (oxlint) + `npm run build` are
  the only frontend correctness gates today; all frontend verification in this project's
  history has been manual/live-browser-driven (puppeteer-core scripts), not codified as
  regression tests. Not necessarily a problem for a course project, but worth knowing
  before assuming "the frontend is tested."
- **`/debug` timing was measured once**, in the Anti-Pattern Advisor session (~30ms avg,
  well under the 2s budget — see `CLAUDE.md` §4) — not wired into CI/tests as an ongoing
  check. Re-measure after any interpreter/cursor/history changes. This session's Compare
  feature calls the same endpoint twice per comparison but adds no new endpoint and no
  server-side state, so there's no new timing concern to measure here.
- **Compare mode doesn't reuse a live Debugger-page trace or a History entry** — both
  Compare panes always start from a sample or freshly-typed code and always call
  `/debug` themselves; there's no "send this run to Compare" link from the main Debugger
  page or from History. Deliberate, scoped choice (this phase's prompt described two
  independent editor panes, not a bridge from existing pages) rather than an oversight,
  but worth adding later if a "compare this against a saved run" workflow turns out to
  matter.
- **Compare mode has no flowchart or Anti-Pattern Advisor output of its own** — it only
  ever renders the two `DebugStep` traces (line/statement/variables/error), not the
  Mermaid diagram or `issues` array `/debug` also returns. Deliberate scope boundary
  (the phase prompt scoped this feature to step-trace comparison and explicitly said not
  to touch the Advisor or flowchart generation), not a gap to fill silently later without
  a fresh scoping decision.

---

## 7. Immediate next step

1. **Commit the Test-Case Runner + Extended Static Analysis Warnings + function-calls-
   inside-procedures work together** (Call Stack + Variable Timeline were already
   committed by the user mid-session, `24ee5d8` — see §1/§3): `frontend/src/App.jsx`,
   `frontend/src/Layout.jsx`, `frontend/src/App.css`, `frontend/src/TestCaseRunner.jsx`,
   `frontend/src/testCaseExpectations.js`, `frontend/src/pages/TestRunnerPage.jsx`,
   `backend/app/advisor.py`, `backend/app/tests/test_advisor.py`,
   `frontend/src/samples.js`, `backend/app/parser.py`, `backend/app/interpreter.py`,
   `frontend/src/cfg.js`, `backend/app/tests/test_function_call_expression.py`,
   `CLAUDE.md` (and this doc/`PROMPT_LOG.md`). Both **Tier 1** (Breakpoints, Step
   controls, `CALL` support, Call Stack) and all four **Innovation features** (Advisor —
   now with 9 checks, not the original 6 — Compare, Variable Timeline; Live Parameter
   Tuning stays deliberately dropped, §4), plus the Test-Case Runner and function calls
   inside procedures, are now fully complete — a good, natural commit boundary, and
   overdue given three sessions have accumulated uncommitted.
2. **Restart the local dev backend before trying `CALL`/Call Stack live** (§2/§6) — the
   long-running process on port 8000 still hadn't picked up the `CALL` support changes as
   of the Call Stack session (the unverifiable-PID quirk); this session found both dev
   servers stopped entirely and started fresh ones purely for its own verification,
   stopping them again afterward (§2) — so this is still open for whoever runs the app
   next.
3. **Small Help-tab follow-up, whenever a Help/Learn-scoped phase is convenient** (§6):
   update the control-reference list item that still says "Reset" to say "Restart," and
   add a line describing breakpoints/Continue/the Call Stack panel/the Variable Timeline
   panel — none were in scope for the phases that caused these gaps.
4. Get the real student photo for the Developed By modal (the text content itself is
   already real and already committed — §3).
5. Get a real educational video (swap `YOUR_VIDEO_ID_HERE` in `LearnPage.jsx`) and real,
   verified references (replacing every badge-marked placeholder entry) for the Learn
   tab (§2/§6) — and have the concept-explanation draft reviewed against the actual
   course rubric.
6. **Only Live Parameter Tuning remains from the original innovation-feature list, and
   it's deliberately dropped** (§4) — don't pick it up under that name without a fresh
   scoping prompt. Still unscoped: Quiz page enhancements. A future frontend-facing phase
   should also consider the remaining `ProgramNode`/`CallStatement` gaps neither the Call
   Stack nor Variable Timeline sessions closed (§6): `cfg.js` labeling `CALL` statements
   generically, the Anti-Pattern Advisor not analyzing `ProgramNode` at all, and
   Download/Compare never having been exercised against a `CALL`-based sample — only if
   `CALL`-based procedures are meant to be fully first-class across every page, not just
   the main Debugger.
