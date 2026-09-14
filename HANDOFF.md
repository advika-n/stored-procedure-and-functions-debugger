# HANDOFF.md

**A snapshot of exactly where the project stands right now.** This file gets
overwritten/updated at the end of every session — it is not a cumulative log. For
stable project facts (architecture, schema, design tokens) see `CLAUDE.md` instead.

---

## 1. Last updated

**2026-09-14**, end of the session that added **"Continue" and "Restart"** to the step
navigator — a cleanup/completion pass on Tier 1's navigation controls, directly following
the session that built **Breakpoints + Run-to-Breakpoint** (the first Tier 1 addition;
Tier 1 also includes Step controls, Call Stack, and `CALL` support — strengthening the
project beyond the original mandatory/innovation scope, given extra time available). That
session followed the one that built Side-by-Side Run Comparison (the second Innovation
feature), which followed the one that built the SQL Anti-Pattern Advisor (the first
Innovation feature), which followed the Download feature (multi-format report export,
the last mandatory section), which followed the Learn tab session (which created
`PROMPT_LOG.md`), which followed the Help tab session, which followed the session that
created this file/`CLAUDE.md` and built Day/Night Mode + the Developed By modal.

**Re-verified via `git log`/`git status` at the start of this session**: the Breakpoints
work was already committed (`9b4b6e1`), on top of everything else already committed in
`56a629a`. Working tree was fully clean at the start. Backend baseline confirmed at 223
passing before starting (this phase's own required gate) and 223 again at the end — no
backend files were touched.

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

---

## 3. In progress right now

Nothing is genuinely half-built right now — every feature in §2 is code-complete.

- **This session's own Continue/Restart rename is uncommitted** — `frontend/src/pages/
  DebuggerPage.jsx` only (confirmed via `git status --short`); the Breakpoints phase
  before it is already committed (`9b4b6e1`). Same "commit soon" recommendation as every
  prior phase — see §7.
- The student photo in the Developed By modal is still the placeholder inline SVG
  silhouette, not a real photo file (the text content itself is real and committed).
- Day/Night Mode itself was only ever exercised in one headless-Chrome instance during
  its original verification session — not spot-checked in a second browser engine. Not
  blocking, just unverified; noted here since nothing since has re-tested it.

---

## 4. Not started yet

**All 5 mandatory course-graded sections are now code-complete** (§2) — none remain
in this list. What's left is real content for the Learn tab (§6) and everything below:

- **One of the four innovation features** — confirmed absent by grep, no partial code
  anywhere: Variable Timeline/sparklines. (SQL Anti-Pattern Advisor and Side-by-Side Run
  Comparison are both done — see §2.)
- **Live Parameter Tuning — dropped, out of scope.** Explicitly removed from the plan by
  a prior session's own closing instruction rather than left as "not started" — it was
  never begun, no code exists for it, and none should be added later under this name
  without a fresh scoping prompt from the user.
- **Two of the four Tier 1 items** — Call Stack, and `CALL` support (calling one
  procedure/function from another — not currently supported by the grammar at all per
  `parser.py`, so Call Stack likely depends on `CALL` support existing first). Both need
  a fresh scoping prompt before starting, same as Quiz page enhancements below.
  (Breakpoints and Step controls, the other two Tier 1 items, are both done — see §2. A
  genuine Step-Into-vs-Step-Over distinction isn't meaningful until `CALL` support exists
  to step into, so "Step controls" is being treated as satisfied by Previous/Next/
  Continue/Restart together rather than left half-open waiting on that dependency.)

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
3. Variable Timeline/sparklines — not started.
4. ~~Live Parameter Tuning~~ — **dropped, out of scope** (§4), not attempted.

Then the reassessed Tier 1 push (§2's new subsection), given extra time available:

1. ~~Breakpoints + Run-to-Breakpoint~~ — code-complete, thoroughly verified, **committed**
   (`9b4b6e1`). Its "Run to Breakpoint" button was renamed to "Continue" in the very next
   session (below) — same underlying logic, no behavior change.
2. ~~Step controls~~ — **Done**, via this session's "Continue"/"Restart" cleanup pass
   (§2), thoroughly verified, not yet committed (§3/§6). (Call Stack and `CALL` support,
   the other two Step-controls-adjacent Tier 1 items, remain not started — see below.)
3. Call Stack — not started, needs scoping (§4).
4. `CALL` support — not started, needs scoping (§4); no grammar support exists yet.

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
  Code session; the following Breakpoints session was itself committed too (`9b4b6e1`).
  Re-verified via `git status --short`/`git log` at the start of *this* session: the
  working tree was fully clean before this phase started. **What's uncommitted right
  now** is only this session's own Continue/Restart rename — see §3. Lesson keeps
  standing: `git log`/`git status` are ground truth, checked fresh every session,
  never carried over from what the last session's notes said.
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
  session so far has needed this) — live-verification testing against the real dev
  backend always writes real history rows. This session's Continue/Restart testing
  (CDP-driven real mouse clicks against `SumUntilLimit` and `CalculateTotal`, dark +
  light theme) added ids 131-135, deleted afterward via `DELETE /history/{id}`; checked
  first for stragglers past the previous session's own claimed cleanup range (none found
  — ids 128-130 were genuinely all gone). Same reminder as every prior session: hitting
  the *real* running backend during manual verification always needs this cleanup step.
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

1. **Commit this session's Continue/Restart rename** (`frontend/src/pages/
   DebuggerPage.jsx` only — see §3/§6). Small and low-risk; same recommendation as ever:
   commit before starting the next phase rather than letting uncommitted work accumulate.
2. **Small Help-tab follow-up, whenever a Help/Learn-scoped phase is convenient** (§6):
   update the control-reference list item that still says "Reset" to say "Restart," and
   add a line describing breakpoints/Continue — neither was in scope for the phase that
   caused the gap.
3. Get the real student photo for the Developed By modal (the text content itself is
   already real and already committed — §3).
4. Get a real educational video (swap `YOUR_VIDEO_ID_HERE` in `LearnPage.jsx`) and real,
   verified references (replacing every badge-marked placeholder entry) for the Learn
   tab (§2/§6) — and have the concept-explanation draft reviewed against the actual
   course rubric.
5. Continue the Tier 1 push (§5) — Call Stack and `CALL` support are both still unscoped
   (§4) and need a fresh phase prompt each, same as Quiz page enhancements and Variable
   Timeline/sparklines. Live Parameter Tuning stays dropped (§4) and
   shouldn't be picked up under that name without a fresh scoping prompt.
