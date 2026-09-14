# AI Prompt Log

Required deliverable for this course project (see `CLAUDE.md` §6 / `HANDOFF.md` §6): a
record of the prompts used to build this project with Claude Code, in chronological
order.

**This file did not exist before 2026-09-13.** Entries for every phase before that date
are **reconstructed**, not transcribed — no literal prompt text was recorded at the time,
so those entries are rebuilt from `git log`/`git show` diffs and `HANDOFF.md`'s §2 "Done"
descriptions and are marked as such below. Every entry from the Help Tab phase onward is
the actual prompt text, recorded at the time it was given.

---

## 1. Initial commit — core pipeline + backend scaffold

**Date:** 2026-08-28 · **Commit:** `324e6b0` "Initial commit"

**Prompt:** *Reconstructed — no literal prompt recorded.* Rebuilt from the commit's diff
(tokenizer/parser/interpreter/explainer/history/demo_db/main.py all added in one shot,
each with a matching `tests/test_*.py`, plus a bare Vite+React frontend scaffold) and
`HANDOFF.md` §2's description of the core pipeline. The evident ask: build a backend that
tokenizes, parses, and tree-walks a procedural-SQL subset into a step trace, with a
persistent run-history store and a Gemini-backed (with fallback) step explainer, backed
by a full pytest suite from the start.

**What shipped:** `backend/app/{tokenizer,parser,interpreter,explainer,history,demo_db,
main}.py` + one test file per module; a default Vite+React frontend with no custom pages
yet.

---

## 2. Second commit — full Debugger UI + richer grammar

**Date:** 2026-08-28 · **Commit:** `bff7635` "Second commit"

**Prompt:** *Reconstructed — no literal prompt recorded.* Rebuilt from the diff (the
tokenizer/parser/interpreter/explainer all grew substantially — cursor and exception-
handler support, by cross-reference with `HANDOFF.md` §2's grammar list — and the
frontend gained its first real pages: `DebuggerPage.jsx` at 829 new lines, `Layout.jsx`,
`AboutPage.jsx`, `HistoryPage.jsx`, `HomePage.jsx`, `theme.css`, a much larger `App.css`,
and an expanded `samples.js`). The evident ask: turn the bare backend from commit 1 into
an actual working debugger application — step navigator, variable table, sample library,
history page, About page — and extend the grammar to cover cursors and handlers.

**What shipped:** the Debugger page's step-by-step UI in essentially its first complete
form; About/History/Home pages; the "Debugger Notebook" design system's first version in
`App.css`/`theme.css`; cursor (`DECLARE ... CURSOR FOR SELECT`, `OPEN`/`FETCH`/`CLOSE`,
`%FOUND`/`%NOTFOUND`) and exception-handler (`CONTINUE HANDLER FOR NOT_FOUND |
DIVISION_BY_ZERO`) support in the interpreter/parser/tokenizer.

---

## 3. Third commit — Quiz feature + Predict Mode/TTS-era Debugger changes

**Date:** 2026-08-28 · **Commit:** `e80f788` "Third commit"

**Prompt:** *Reconstructed — no literal prompt recorded.* Rebuilt from the diff: a new
`backend/app/quiz.py` + two test files, a new `pages/QuizPage.jsx` + `lastProcedure.js`
bridge, `DebuggerPage.jsx` growing by 256 lines (consistent with `HANDOFF.md` §2's
Predict Mode and Text-to-Speech both landing around this point), and `cfg.js` (the
flowchart builder) gaining 82 lines. The evident ask: add a standalone AI-generated quiz
feature and continue building out the Debugger page's interactive features.

**What shipped:** `/quiz/generate` backend endpoint + the standalone `/quiz` page
(General Theory / This-Procedure Gemini MCQ quiz); per `HANDOFF.md` §2, Predict Mode and
Text-to-Speech in the Debugger page date from around here.

**Known issue introduced in this commit:** a `New/` directory — a near-complete, ~54-file
duplicate snapshot of the backend+frontend at an earlier point — was accidentally
committed alongside the real changes and has stayed in the repo since (tracked in
`CLAUDE.md`'s "Known repo cruft" section and `HANDOFF.md` §6; not referenced by any
build/run script, not part of the live app, left alone pending explicit confirmation to
delete it).

---

## 4. Day/Night Mode + Developed By modal (+ `CLAUDE.md`/`HANDOFF.md` creation)

**Date:** 2026-09-13 · **Commit:** `a80392c` "Add Day/Night mode and Developed By modal;
add session docs"

**Prompt:** *Reconstructed — no literal prompt recorded* (this predates `PROMPT_LOG.md`
by one session). Rebuilt from `HANDOFF.md` §2/§3 as they stood at the end of that
session. The evident ask: convert every hard-coded theme color to a CSS custom property,
add a persisted Day/Night toggle that also drives Monaco and Mermaid, add a "Developed
By" modal (photo/name/register number/guide — a course grading requirement), and write
up `CLAUDE.md` + `HANDOFF.md` as the project's first persistent-context docs.

**What shipped:** `ThemeContext.jsx`, the full light/dark token set in `theme.css`,
`mermaidColors.js`, `DevelopedByModal.jsx`, the theme toggle + Developed By trigger in
`Layout.jsx`'s header, a contrast audit (one real WCAG AA miss found and fixed —
light-mode `--accent-teal`), and `CLAUDE.md`/`HANDOFF.md` themselves. Developed By
content shipped as placeholder (`[NAME]`, `[REGISTER NUMBER]`) — still not filled in as
of this entry.

---

## 5. Help Tab — full step-by-step user manual

**Date:** 2026-09-13 · **Committed** (`49bcd98`, together with the Learn Tab phase below
— accurate as of 2026-09-14; was uncommitted when this entry was first written)

**Prompt (verbatim):**

> PHASE: Help Tab (User Manual)
>
> Context: Read CLAUDE.md and HANDOFF.md first for full project context before starting.
>
> Add a "Help" section to the site that functions as a complete step-by-step user manual —
> a first-time user with zero context should be able to operate the entire debugger by
> reading it. This is a mandatory, graded course requirement.
>
> 1. Add a "Help" item to the top navigation, alongside Learn/Developed By/Day-Night toggle.
>    Route to a dedicated page (this one warrants a full page, not a modal, given the amount
>    of content).
>
> 2. IMPORTANT — do this before writing any content: scan the current frontend components
>    (Layout.jsx, DebuggerPage.jsx, and any others) to build an accurate list of every real
>    control that exists in the UI right now — Run/Debug button, Step Forward/Back, Reset,
>    Predict Mode, Quiz page link, Day/Night toggle, Developed By modal trigger, Download
>    button, etc. Don't invent controls or omit any that exist.
>
> 3. Structure the content as a clear step-by-step walkthrough covering: (a) what the
>    application does, (b) what inputs are available, (c) how to provide inputs, (d) what
>    each button/control does, (e) how processing takes place, (f) how to interpret the
>    output.
>
> 4. Use a clean numbered/sectioned layout (numbered steps or accordion sections per
>    topic) — this feeds into the System Design & UI/UX grading criterion, so keep it
>    scannable, not a wall of text.
>
> 5. Make the Help page theme-aware — use the existing ThemeContext/CSS variables from the
>    Day/Night mode work, don't hardcode colors.
>
> Don't touch interpreter/debugger logic, flowchart generation, or the quiz page — this
> phase is scoped to adding the new Help page and its content only.
>
> After finishing: update HANDOFF.md to move Help tab from "Not started" to "Done", and
> add a note in the AI prompt log for this phase.

**What shipped:** `frontend/src/pages/HelpPage.jsx` (new) — seven `<details>`/`<summary>`
accordion sections covering exactly the six required topics plus an "Other pages"
section; every control listed was read directly off `Layout.jsx`/`DebuggerPage.jsx`/
`History.jsx`/`QuizPage.jsx` rather than invented. Nav entry added to the top-right
utility cluster (`.help-nav-trigger`/`.help-nav-trigger-active` in `App.css`). Fully
theme-aware — no hard-coded colors, only existing `theme.css` tokens. Live-verified via a
headless-Chrome screenshot of the running dev server (collapsed + expanded states, both
themes not fully cross-checked — see `HANDOFF.md` §2 for the exact caveat).

---

## 6. Learn Tab — concept explanation, video slot, references

**Date:** 2026-09-13 · **Committed** (`49bcd98`, together with the Help Tab phase above
— accurate as of 2026-09-14; was uncommitted when this entry was first written)

**Prompt (verbatim):**

> Add a "Learn" tab to the site — must be prominent in navigation, positioned top-right
> (course requirement). This is a mandatory, graded course requirement.
>
> 1. Add "Learn" as a nav item, top-right, alongside the other tabs.
> 2. Route to a dedicated Learn page with three sections:
>
>    a. CONCEPT EXPLANATION
>       Draft a crisp, well-organized explanation of "Stored Procedures & Functions in
>       Databases, and Debugging Them" — the assigned topic. Cover: what a stored
>       procedure/function is, why they exist (reusability, performance, encapsulating
>       logic in the DB layer), the difference between the two, and why debugging them is
>       non-trivial compared to regular application code (no standard breakpoint/step
>       tooling in most DB engines — which is exactly the gap this project's tool fills).
>       Use headings/subheadings, keep each section short and scannable, not a wall of
>       text. This is placeholder/draft content — flag it clearly with a comment so it's
>       easy to find and revise later.
>
>    b. ANIMATED VIDEO
>       Add a video embed slot (standard YouTube iframe embed component) with a clearly
>       marked placeholder video ID/URL and a visible TODO comment: "Replace with a real
>       educational video on stored procedures/DB debugging — do not ship placeholder ID."
>       Do not fabricate a real-looking YouTube video ID/URL — use an obvious placeholder
>       like YOUR_VIDEO_ID_HERE so it's unmistakable and doesn't get missed.
>
>    c. REFERENCES
>       Draft a references list structure (Books / Websites / Research Papers /
>       Educational Resources / Videos, matching the course's required categories) with
>       2-3 placeholder entries per category in the correct citation format, each marked
>       as a placeholder needing a real source.
>
> 3. Style consistent with the existing design system, theme-aware (use existing
>    ThemeContext/CSS variables — don't hardcode colors).
>
> 4. Layout should be clean and scannable — feeds into the System Design & UI/UX grading
>    criterion.
>
> Don't touch interpreter/debugger logic, flowchart generation, Help tab, or the quiz
> page — this phase is scoped to the new Learn page only.
>
> After finishing: update HANDOFF.md to move Learn tab to "Done (placeholder content —
> needs real video + references before submission)", and log this phase in the AI prompt
> log (create PROMPT_LOG.md now if it still doesn't exist, and backfill entries for prior
> phases as best you can from HANDOFF.md's history).

**What shipped:** `frontend/src/pages/LearnPage.jsx` (new) — three always-visible panel
sections (Concept Explanation, Animated Video, References). Concept explanation covers
all four required points with h3 subheadings and a procedure-vs-function comparison
table, flagged with both a file-level code comment and a visible `DRAFT` badge. Video
section embeds a real YouTube iframe pointed at the literal placeholder
`YOUR_VIDEO_ID_HERE`, marked with a code `TODO` (verbatim text from the prompt) and a
visible coral "PLACEHOLDER" badge. References section covers all five required
categories (Books/Websites/Research Papers/Educational Resources/Videos), 2-3 entries
each in real citation format, every entry individually badge-marked as a placeholder.
"Learn" added as the rightmost main nav tab with its own permanent amber-outlined
`.top-nav-item-emphasize` styling (solid-fill when active) so it reads as visually
distinct from its neighbors, per the "must be prominent" requirement. Fully theme-aware.
Live-verified via headless-Chrome screenshots in both dark and light mode, plus a
phone-width (400px) check.

**Known issue surfaced, not fixed (out of scope for this phase):** at ~400px viewport
width the top nav (`'.top-nav`, no `flex-wrap`) overflows horizontally instead of
wrapping — confirmed via `git show HEAD:frontend/src/App.css` that this predates the
Learn tab entirely (adding an 8th nav item made an already-tight row overflow more
visibly, but did not introduce the underlying issue). Left alone since fixing shared
header responsiveness wasn't part of either this phase's or the Help phase's scope; see
`HANDOFF.md` §6.

---

## 7. Download Feature — Multi-Format Report Export

**Date:** 2026-09-13 · **Not yet committed** (see `HANDOFF.md` §6)

**Prompt (verbatim):**

> PHASE: Download Feature — Multi-Format Report Export
>
> Context: Read CLAUDE.md and HANDOFF.md first for full project context before starting.
> Download currently only produces JSON. This phase replaces/extends it to meet the actual
> graded spec: full report content, exportable as PDF, Document, and Text.
>
> 1. Determine current Download implementation (frontend button + whatever backend endpoint
>    it calls) and what data it currently has access to — likely the DebugStep trace, given
>    that schema is the central data contract per CLAUDE.md.
>
> 2. Report content must include, pulled from the actual debug session:
>    a. User Inputs — the SQL the user wrote/pasted, and any parameters (note: currently
>       always {} per the Help tab's documented limitation — include this honestly, don't
>       fabricate parameter values)
>    b. Processing Steps — the step-by-step execution trace (each DebugStep: line, action,
>       variable state, etc.)
>    c. Intermediate Results — variable/cursor state at each step, where applicable
>    d. Final Output — the end result of execution (return value, final state, or error if
>       the procedure failed)
>    e. Graphs/Tables/Figures — include the flowchart (export the Mermaid diagram as an
>       embedded image/SVG) and any variable-state table, where applicable
>
> 3. Implement three export formats:
>    - PDF: use a Python library on the FastAPI backend (reportlab or weasyprint — pick
>      whichever is simpler to integrate with the existing project structure; weasyprint if
>      HTML-to-PDF is easier here) to generate a formatted PDF with headings per section
>      above.
>    - Document: generate a .docx using python-docx, same structure/sections.
>    - Text: generate a plain .txt with the same content, formatted with clear section
>      headers (no markup, just readable plaintext).
>
> 4. Frontend: replace/extend the current Download button with a format picker (e.g. a
>    small dropdown or three buttons: "Download PDF" / "Download Document" / "Download Text"),
>    theme-aware, styled consistently with the existing design system.
>
> 5. Backend: add endpoint(s) to generate and return each format (e.g. GET/POST
>    /debug/report?format=pdf|docx|txt), reusing the session's DebugStep data rather than
>    requiring the user to re-run anything.
>
> 6. Test each format actually opens correctly and contains real data from an actual debug
>    run (not placeholder/lorem ipsum) — verify with at least one of the 10 built-in sample
>    procedures.
>
> 7. Verify via npm run lint / npm run build (frontend) and confirm the backend endpoint(s)
>    respond correctly, similar to prior phases' verification approach.
>
> Don't touch interpreter/debugger logic, flowchart generation, Help tab, or Learn tab —
> this phase is scoped to the Download feature only.
>
> After finishing: update HANDOFF.md to move Download from "Not started" to "Done", note
> which PDF library was used and why, and log this phase in PROMPT_LOG.md.

**What shipped:** `backend/app/report.py` (new) — one format-agnostic intermediate
representation (`ReportSection`/`ReportBlock`) built once from a `DebugStep` trace, then
rendered three ways: **reportlab** for PDF (chosen over weasyprint specifically because
weasyprint needs the native GTK/Pango/Cairo libraries installed to do HTML-to-PDF, which
aren't guaranteed present and are painful to install reliably on this project's Windows
dev environment, whereas reportlab is pure Python and pip-installs cleanly anywhere —
directly answering the prompt's "whichever is simpler to integrate" criterion),
**python-docx** for DOCX, and stdlib-only for plain text. New endpoint `POST
/debug/report` in `main.py`, deliberately stateless: it takes the exact
`code`/`params`/`steps` the frontend already has from its last `/debug` call and only
formats them, never re-parses/re-interprets (verified by a test that monkeypatches
`interpreter.run` to explode if the endpoint ever calls it). The flowchart image is
rasterized **client-side** (`frontend/src/svgToPng.js`, new, via an offscreen `<canvas>`)
from the Mermaid SVG the Debugger page has already rendered — not attempted server-side,
since Mermaid's SVG relies on `<foreignObject>` HTML labels no lightweight Python
SVG-to-raster path handles reliably. The old single "⭳ Export Run" JSON button in
`DebuggerPage.jsx` is fully replaced (not kept alongside) by a "⭳ Download Report"
trigger opening a small anchored dropdown with three options, dismissible by outside
click/Escape/picking an option — matching this app's existing modal-dismiss convention.
Theme-aware, no hard-coded colors (`App.css`'s new `.report-download*` rules).

23 new backend tests (`test_report.py`, `test_report_endpoint.py`), all built on real
interpreter-produced `DebugStep` traces rather than hand-written fixtures — full suite:
199 passing (176 before). Beyond the test suite: hit the live backend directly with two
different real samples (`SafeAverageWithHandlers` — cursors, both handler types actually
firing — and `ComputeTax` — an OUT param) and rendered the resulting PDFs to images to
eyeball real layout/content; opened the DOCX output with python-docx to confirm real
tables/an embedded image; and, since neither puppeteer-core, playwright, nor
chromium-cli were available in this environment, drove the **actual running app**
end-to-end with a small dependency-free driver script (Node 24's native
`fetch`/`WebSocket` talking raw Chrome DevTools Protocol) — loaded `/debugger`, ran a
sample, opened the dropdown, and clicked all three downloads for real: zero console
errors, all three requests returned 200 with the correct content-type. Test-run entries
this created in the real history DB were deleted afterward via the app's own history
endpoint.

---

## 8. SQL Anti-Pattern Advisor (Innovation Feature)

**Date:** 2026-09-14 · **Not yet committed** (see `HANDOFF.md` §6)

**Prompt (verbatim):**

> PHASE: SQL Anti-Pattern Advisor (Innovation Feature)
>
> Context: Read CLAUDE.md and HANDOFF.md first for full project context before starting.
> This is one of the four "Innovation" features (5 marks) — the app should analyze the
> user's SQL and surface common anti-patterns/bad practices, similar in spirit to a
> linter.
>
> 1. IMPORTANT — before designing detection logic: inspect the existing parser/AST (the
>    tokenizer → parser → AST pipeline) to see what's already available to analyze
>    (statement types, cursor declarations, loop structures, etc.) rather than writing a
>    second parallel parser. Reuse the existing AST wherever possible.
>
> 2. Implement detection for a reasonable, defensible set of anti-patterns given what the
>    AST already exposes. Candidates (pick the ones actually detectable from the current
>    AST — don't force ones that would need new parsing work):
>    - SELECT * usage instead of explicit column lists
>    - Cursor used where a set-based operation (single SELECT/UPDATE) would work instead
>    - Nested cursors/loops (potential O(n²) row-by-row processing)
>    - Missing exception/error handling around risky operations
>    - Hard-coded literal values that should likely be parameters
>    - Cursor opened but not explicitly closed (resource leak risk)
>    - Dynamic SQL string concatenation (SQL injection risk pattern)
>    Confirm the final list against what's actually detectable and list it explicitly in
>    your implementation summary — don't claim to detect a pattern you didn't actually
>    implement.
>
> 3. Design as a static analysis pass that runs on the parsed AST (not the interpreter/
>    execution trace) — so it can flag issues even before running the procedure, ideally
>    triggered automatically after parsing (e.g. on the same action as clicking Run/Debug,
>    or on a live "Analyze" button — pick whichever fits the existing UI flow better and
>    say which you chose).
>
> 4. Output format: a results panel (e.g. sidebar or below the editor) listing each
>    detected issue with:
>    - The anti-pattern name/category
>    - The specific line/location in the user's SQL
>    - A one- or two-sentence plain-language explanation of why it's a problem
>    - A suggested fix or alternative approach
>    Use severity styling (e.g. warning vs. suggestion) consistent with the existing
>    amber/teal/coral accent system.
>
> 5. If a "no issues found" case occurs, show a clear positive confirmation rather than an
>    empty panel.
>
> 6. Style theme-aware (existing ThemeContext/CSS variables), consistent with the rest of
>    the app.
>
> 7. Verify with at least 2-3 of the 10 built-in sample procedures that intentionally
>    contain some of these patterns — if none currently do, note that in your summary
>    (don't fabricate a sample procedure without flagging it as new).
>
> Don't touch interpreter/debugger logic, flowchart generation, Help/Learn tabs, or
> Download — this phase is scoped to the Anti-Pattern Advisor only.
>
> After finishing: update HANDOFF.md to move SQL Anti-Pattern Advisor from "Not started"
> to "Done", list exactly which anti-patterns were implemented, and log this phase in
> PROMPT_LOG.md.

**What shipped:** `backend/app/advisor.py` (new) — `analyze(ast)`, a static pass that
only reads the AST `app.parser.parse()` already produces (no second parser). Wired into
the existing `POST /debug` handler (not a new endpoint): right after a successful parse,
`main.py` now also computes `issues = analyze_anti_patterns(ast)` and returns it
alongside `ast`/`steps`, so the check runs automatically the moment someone clicks Debug,
at no extra network round trip — the trigger choice the prompt asked to be explicit
about.

**Six anti-patterns implemented** (confirmed against what the AST actually exposes,
exactly as the prompt required): `select-star` (SELECT * in a cursor query),
`cursor-could-be-set-based` (a cursor loop that only accumulates a running total/count),
`nested-loops` (WHILE nested inside WHILE), `missing-error-handling` (two asymmetric
sub-checks mirroring `interpreter.py`'s own documented NOT_FOUND/DIVISION_BY_ZERO
asymmetry — division-without-a-handler is a warning since it genuinely aborts the run;
an unguarded cursor FETCH is only a suggestion since NOT_FOUND is always non-fatal here,
and a `cursor%FOUND` loop guard is correctly recognized as already-safe, not flagged),
`magic-number` (a non-trivial numeric literal repeated more than once), and
`cursor-not-closed` (OPEN with no matching CLOSE). **One candidate explicitly NOT
implemented**, exactly as the prompt permitted: dynamic SQL string concatenation / SQL
injection risk — this grammar has no EXECUTE/EXEC-IMMEDIATE construct and no way to
build/run a SQL string from concatenated variables at all, so there's nothing of that
shape to detect (documented in `advisor.py`'s own module docstring rather than silently
dropped).

**Output**: a new full-width panel in `DebuggerPage.jsx` (`.panel-advisor`, between Ask
AI and Control Flow) — each finding is a card with a coral **Warning** or amber
**Suggestion** severity badge (this app's existing two-tier accent language), a title, a
line number, a plain-language explanation, and a suggested fix; a clean run shows a teal
"✓ No anti-patterns detected" positive confirmation rather than an empty panel, per the
prompt's requirement #5. Theme-aware, no hard-coded colors.

**Verification**: 22 new `test_advisor.py` unit tests plus 2 new `/debug`-endpoint tests,
all against real tokenizer/parser-produced ASTs — full suite: 223 passing (199 before).
Ran all 10 real built-in samples through the live backend: 8 are clean, and
`ProductPriceTotal`/`SafeAverageWithHandlers` both genuinely trigger
`cursor-could-be-set-based` — the only one of the six patterns any pre-existing sample
happens to contain. Rather than silently forcing or skipping coverage for the other five,
this was **disclosed honestly** (per the prompt's explicit instruction) and a new,
clearly-flagged-as-new sample was added to `samples.js` — `AntiPatternShowcase`, commented
"Added specifically for the SQL Anti-Pattern Advisor phase" — deliberately containing all
six patterns in one procedure that still runs to completion successfully. Live-verified
via the same raw-CDP driver approach as the Download phase (loaded the sample, ran Debug,
confirmed all 7 findings render correctly with zero console errors, in both dark and
light theme). Test-run entries this created in the real history DB were deleted
afterward, matching the established cleanup habit from the Download-feature session.

**Also found and corrected this session** (not part of the original prompt, but material
enough to note here): `HANDOFF.md` had been repeating a stale claim across three sessions
that Day/Night Mode + Developed By and, later, Help Tab + Learn Tab were all uncommitted.
`git log` showed the first was committed in `a80392c` from the very session that wrote
that claim, and the latter two were committed together in `49bcd98` sometime after the
Download-feature session (most likely by the user, outside a Claude Code session, since
no corresponding prompt exists in this log). `HANDOFF.md` §1/§3/§4/§5/§6/§7 were rewritten
this session to match `git log`/`git status` instead of repeating the previous session's
notes.

---

## 9. Side-by-Side Run Comparison (Innovation Feature)

**Date:** 2026-09-14 · **Not yet committed** (see `HANDOFF.md` §6)

**Prompt (verbatim):**

> Goal: let the user run two procedures (or the same procedure edited differently) and
> see both execution traces side-by-side, with divergence points visually highlighted.
>
> 1. IMPORTANT — before building: inspect the existing DebugStep schema and the /debug
>    endpoint (used by the Anti-Pattern Advisor phase too) to confirm you're reusing the
>    same data contract for both runs, not inventing a second one.
>
> 2. UI/UX:
>    - Add a "Compare" mode/tab (or a toggle on the existing Debugger page) that presents
>      two independent SQL editor panes side-by-side (left/right), each with its own
>      Run/Debug control, reusing the existing Monaco editor component.
>    - Each side runs independently against the existing /debug endpoint — don't build a
>      new backend endpoint for this if the existing one already returns everything needed
>      (steps, ast, issues); if a small backend addition is needed to support two concurrent
>      sessions cleanly, keep it minimal and say what you added and why.
>    - Display both step-traces side-by-side, synchronized by step index where possible
>      (e.g. stepping forward advances both columns together, with a shared step counter/
>      Next-Step control) — if the two traces have different lengths, handle the shorter one
>      reaching its end gracefully (freeze/gray out rather than error).
>
> 3. Divergence highlighting:
>    - Compare the two traces step-by-step and visually flag (e.g. amber/coral highlight)
>      the first step where they diverge — different line executed, different variable
>      value, or one erroring while the other doesn't.
>    - Show a brief summary at the point of divergence: what differed (e.g. "Left took
>      branch X, right took branch Y" or "Variable `total` differs: 15 vs 20").
>
> 4. Handle the case where both runs are identical (no divergence) — clear positive
>    confirmation, not a blank/confusing state.
>
> 5. Style theme-aware (existing ThemeContext/CSS variables), consistent with the rest of
>    the app. Two side-by-side panes need careful layout — check it doesn't break at the
>    ~400px width where the nav already has a known pre-existing overflow bug (don't fix
>    that bug, just don't make it worse).
>
> 6. Verify with two real cases: (a) two of the 10 built-in samples that behave differently,
>    confirming divergence is detected and shown correctly, (b) the same sample run against
>    itself unchanged, confirming the "no divergence" state works.
>
> Don't touch interpreter/debugger logic, the Anti-Pattern Advisor, flowchart generation,
> Help/Learn tabs, or Download — this phase is scoped to the Comparison feature only.
>
> After finishing: update HANDOFF.md to move Side-by-Side Run Comparison from "Not started"
> to "Done", remove Live Parameter Tuning from any remaining "Not started" lists (mark as
> "Dropped — out of scope"), and log this phase in PROMPT_LOG.md.

**What shipped:** No backend changes at all. Inspecting `backend/app/main.py`'s `POST
/debug` confirmed it already returns everything needed (`ast`, `steps`, `issues`) and is
fully stateless per request (a fresh `demo_db` connection each call, nothing shared
server-side) — so two independent calls, one per Compare pane, need nothing extra from
FastAPI. `frontend/src/pages/ComparePage.jsx` (new, route `/compare`, new "Compare" nav
tab in `Layout.jsx`) presents two independent panes ("RUN A"/"RUN B"), each with a sample
picker, its own Monaco editor, and its own Debug button/error — exactly the "each side
runs independently" structure the prompt asked for. Both default to the same first sample
so simply clicking both Debug buttons demonstrates the no-divergence case immediately.

Once both sides have a completed trace, one shared "SYNCHRONIZED STEPPING" control
(Previous/Next/Reset/scrubber, reusing the main Debugger page's own `.step-navigator`/
`.step-scrubber` styling) drives a single `sharedStepIndex` both panes read from. A side
whose trace is shorter freezes on its last real step, grayed with an explicit "finished
after N steps" note, once the shared index runs past it — the prompt's "handle the
shorter one reaching its end gracefully" requirement.

**Divergence detection** (`frontend/src/compareTraces.js`, new — pure functions, no
execution of its own): walks both `DebugStep` traces by shared index and reports the
*first* respect in which a pair of steps differs, checked in this order: which source
line ran, whether one side hit an error the other didn't (or a different error
condition), which `IfStatement` branch was taken, then any variable name the two traces
happen to share whose value differs. If every shared step matches but the traces end at
different lengths, that itself is reported as a distinct divergence ("Left run finished
after N steps; right kept executing beyond that point") rather than silently ignored.
Returns `null` when the traces are identical as far as compared.

**Output**: a persistent divergence banner — teal "✓ No divergence detected" when `null`,
or a coral-accented card naming the step number, the divergence kind, and a
plain-language summary (e.g. `Variable total differs: 15 (left) vs 20 (right).`), with a
"Jump to this step" button. Below it, both panes' current-step view (line + statement
text, error banner if any, full variable table) render side by side; the exact diverged
step gets a coral outline on both panes, and for a variable-kind divergence the one
differing row gets its own coral highlight — reusing the existing amber/teal/coral accent
language, no new colors introduced.

**Verification**: `npm run lint` (only the same 2 pre-existing warnings) and `npm run
build` both clean; `cd backend && pytest -q` still 223/223 (untouched by this phase).
Live-verified via the same raw-CDP driver approach as the two prior phases: (a)
`CalculateTotal` vs `GradeClassifier` (two real, differently-behaving samples) correctly
reports a `branch` divergence at step 4 with the right summary text, and "Jump to this
step" correctly outlines both panes there; (b) `CalculateTotal` run against itself
unchanged correctly shows the "no divergence" confirmation across its full 8-step trace.
Both scenarios re-checked in light theme, plus a genuine 400px-wide check confirming
`.compare-grid` collapses to one column and this page's own content adds no horizontal
scroll (the only overflow present at that width is the pre-existing top-nav bug, not
worsened beyond the same one-extra-word growth the Learn-tab phase already established as
acceptable precedent). Zero console errors throughout. Test-run history rows created
during verification (ids 119-127 — 119 turned out to be a leftover row from the *previous*
session's own sign-off pass that had escaped that session's cleanup) were all deleted via
`DELETE /history/{id}` afterward.

**Live Parameter Tuning dropped**, per this prompt's explicit instruction — `HANDOFF.md`
§4/§5 updated to mark it "Dropped — out of scope" rather than "not started"; it was never
begun, so no code needed removing.

---

## 10. Breakpoints + Run-to-Breakpoint (Tier 1 addition)

**Date:** 2026-09-14 · **Not yet committed** (see `HANDOFF.md` §3/§6)

**Prompt (verbatim):**

> PHASE: Breakpoints + Run-to-Breakpoint
>
> Context: Read CLAUDE.md and HANDOFF.md first for full project context before starting.
> This begins the reassessed "Tier 1" push (Breakpoints, Step controls, Call Stack, CALL
> support) to strengthen the project beyond the original mandatory/innovation scope, given
> extra time available. Confirm the full backend test suite passes (223+) before starting,
> and again after — do not proceed to any future phase if the count drops.
>
> Goal: let the user click a line number in the Monaco editor to toggle a breakpoint, then
> run execution up to (and stopping at) that line, rather than only stepping one line at a
> time or running to completion.
>
> 1. IMPORTANT — before implementing: inspect the existing step-execution engine (the
>    interpreter's step-trace generation) to understand how "step" state is currently
>    produced and exposed to the frontend. Breakpoints should be implemented as a frontend-
>    driven feature that uses the EXISTING step trace (stop advancing the already-generated
>    trace at the breakpointed line) rather than modifying the interpreter's execution
>    semantics — this keeps risk low and avoids touching core interpreter logic.
>
> 2. Frontend:
>    - Add clickable breakpoint gutter markers in the Monaco editor (Monaco supports glyph
>      margin decorations — use that rather than building custom line-number UI).
>    - Toggling a breakpoint on a line stores it in component state (a set of line numbers).
>    - Add a "Run to Breakpoint" control alongside existing Run/Debug/Step controls — when
>      pressed, auto-advance through the existing step trace until reaching a step whose
>      line matches a breakpoint (or the trace ends, whichever first), then stop and display
>      that step as normal.
>    - If no breakpoints are set, "Run to Breakpoint" should behave the same as running to
>      completion (or be disabled with a tooltip explaining why — pick whichever fits better
>      and say which you chose).
>    - Clear visual indication of active breakpoints (red dot in gutter) and which step is
>      currently paused at a breakpoint vs. a normal step.
>
> 3. Do NOT modify the backend /debug endpoint, interpreter, or step-trace generation —
>    breakpoints are purely a frontend consumption-layer feature on top of the existing
>    trace. If you find this is genuinely impossible without backend changes, stop and
>    report why rather than proceeding with backend modifications.
>
> 4. Style theme-aware (existing ThemeContext/CSS variables), consistent with existing
>    controls (Step Forward/Back, Reset, etc.).
>
> 5. Verify: set a breakpoint mid-procedure on 2 of the 10 built-in samples, confirm
>    "Run to Breakpoint" stops exactly there; confirm toggling breakpoints off and re-running
>    works; confirm existing Step Forward/Back/Reset controls still work unchanged; confirm
>    backend test suite still shows 223+ passing (untouched, since backend wasn't touched).
>
> Don't touch interpreter/debugger core logic, the Anti-Pattern Advisor, Side-by-Side
> Comparison, Download, Help/Learn tabs, or flowchart generation — this phase is scoped to
> Breakpoints only.
>
> After finishing: update HANDOFF.md to add Breakpoints as "Done" under the new Tier 1
> additions section, and log this phase in PROMPT_LOG.md.

**What shipped:** Confirmed the required baseline first — `pytest -q` at 223 passed
before touching anything, and 223 passed again at the end, so nothing regressed and no
future phase needs to be held back. No backend files touched at all this phase (it
genuinely was possible without them, so nothing needed to be reported as blocked): a
breakpoint is a `Set<lineNumber>` in `DebuggerPage.jsx` state, and "Run to Breakpoint" is
a forward search over the *already-computed* `steps` array for the next step whose `line`
is in that set, landing on the last step (i.e. running to completion) when none match —
the chosen behavior for the no-breakpoints case, kept enabled rather than disabled since
the same code path naturally does the right thing either way.

**UI**: Monaco's built-in glyph margin (`glyphMargin: true`, no custom gutter UI) shows a
coral dot on breakpointed lines; clicking either the glyph margin or the line-number
column itself (`editor.onMouseDown`, `MouseTargetType.GUTTER_GLYPH_MARGIN` /
`GUTTER_LINE_NUMBERS`) toggles the breakpoint on that line. A "⏵ Run to Breakpoint"
button sits between Next and Reset in the existing step-navigator row, plus a hint line
under the editor showing the current breakpoint count. When execution is actually paused
on a breakpointed line, the current-line decoration gets a coral tint
(`debug-current-line-breakpoint`, overriding the normal amber-ish tint) and a
"⏸ Paused at breakpoint" badge appears next to the step counter — both conditioned purely
on `breakpoints.has(currentStep.line)`, so ordinary navigation that happens to land on the
same line looks unchanged. Breakpoints deliberately survive `resetRunState` (new sample
loads, fresh Debug runs) since they're an editor-level concept, not tied to one run —
matching real debugger behavior; the accepted simplification is that they track a raw
line **number**, not a Monaco decoration ID, so heavy edits above a breakpoint can leave
it on now-different code (exactly what the phase's own "a set of line numbers" spec asked
for, not full edit-tracking).

**Verification**: `npm run lint`/`npm run build` clean (same 2 pre-existing warnings).
Live-verified via a raw-CDP driver that dispatches **real mouse clicks**
(`Input.dispatchMouseEvent` at the actual on-screen coordinates of the target line's
gutter cell, found via `getBoundingClientRect()`) rather than calling into component
internals — so this exercised the genuine `onMouseDown` handler: (a) `CalculateTotal`,
breakpoint on line 8, "Run to Breakpoint" correctly stopped at Step 7 of 8 with the coral
tint/badge and the step log confirming line 8; (b) toggled that breakpoint back off,
Reset, "Run to Breakpoint" again correctly ran to Step 8 of 8 (no-breakpoints/
run-to-completion case); (c) confirmed Previous/Next/Reset behave exactly as before
(Step 1 → 2 → 1); (d) `GradeClassifier`, breakpoint on line 9 inside a nested IF's ELSE,
correctly stopped there too. All checked again in light theme. Zero console errors
throughout. Test-run history rows created during verification (ids 128-130) were deleted
afterward via `DELETE /history/{id}`.

**Scope discipline**: `git status --short` after finishing showed only
`frontend/src/pages/DebuggerPage.jsx` and `frontend/src/App.css` changed — no interpreter,
`/debug` endpoint, Anti-Pattern Advisor, Side-by-Side Comparison, Download, Help/Learn, or
flowchart-generation files touched, exactly as scoped.

**Also found this session**: `git log`/`git status` showed the entire backlog the
previous session's HANDOFF.md still listed as uncommitted (Developed-By content, Download,
Anti-Pattern Advisor, Side-by-Side Comparison) had since been committed in one commit,
`56a629a`, outside a Claude Code session. `HANDOFF.md` §1/§3/§6/§7 updated to match —
first session in a while where the working tree was genuinely clean at the start.

---

## 11. Continue + Restart (Tier 1 nav-controls cleanup)

**Date:** 2026-09-14 · **Not yet committed** (see `HANDOFF.md` §3/§6)

**Prompt (verbatim):**

> Goal: round out the navigation controls now that Breakpoints exist. Currently there's
> Previous/Next/Reset and Run to Breakpoint. Add:
>
> 1. "Continue" — from the current step, advance forward to either the next breakpoint
>    (reuse the exact same logic as Run to Breakpoint) or the end of the trace if none
>    remain ahead of the current position. This is effectively "Run to Breakpoint, but from
>    wherever you currently are" rather than always restarting from step 0 — check whether
>    the existing Run to Breakpoint already does this or always starts from the beginning,
>    and fix it to search forward from currentStepIndex if it doesn't already.
>
> 2. "Restart" — reset execution back to step 0 of the CURRENT trace (i.e., re-run the same
>    already-submitted SQL from the start) without needing to re-click Debug or re-fetch
>    from the backend. This is distinct from the existing "Reset" if Reset currently clears
>    the editor/trace entirely — check what Reset currently does and either repurpose it or
>    add Restart alongside it with clearly distinct labels/behavior so they're not
>    redundant or confusing.
>
> 3. Clarify and finalize the full control set's labels/order so it reads sensibly to a
>    first-time user: e.g. Previous | Next | Continue | Run to Breakpoint | Restart | Reset.
>    Merge/rename anything redundant discovered in steps 1-2 rather than just appending more
>    buttons.
>
> 4. Theme-aware styling consistent with existing controls.
>
> 5. Verify: from a paused breakpoint mid-trace, Continue advances to the next breakpoint
>    (or end) correctly; Restart returns to step 0 of the same procedure without re-fetching;
>    all existing controls (Previous/Next/breakpoint toggling) still work; backend test
>    suite unchanged at 223+.
>
> Don't touch interpreter/debugger core logic, backend endpoints, the Anti-Pattern Advisor,
> Side-by-Side Comparison, Download, Help/Learn tabs, or flowchart generation — this phase
> is scoped to navigation controls only.
>
> After finishing: update HANDOFF.md to add Step Over/Continue/Restart as "Done" under Tier
> 1, and log this phase in PROMPT_LOG.md.

**What shipped:** Confirmed the required baseline first — `pytest -q` at 223 passed
before starting and 223 after, no backend files touched at all this phase.

**Central finding — both requested controls already existed under a less accurate name,
so this was a rename-in-place, not two new buttons:**

1. **"Continue"**: inspected `runToBreakpoint`'s search loop
   (`for (let i = currentStepIndex + 1; ...)`) and confirmed it already searched forward
   from the *current* position, never restarting from step 0 — it was always "Continue"
   in standard debugger terms, just mislabeled as a fresh "run." No logic change was
   needed: renamed `runToBreakpoint` → `continueExecution`, button label "⏵ Run to
   Breakpoint" → "⏵ Continue", tooltip reworded to describe resuming rather than running
   through from scratch.
2. **"Restart"**: inspected `resetSteps` and confirmed it only ever called
   `setCurrentStepIndex(0)` (plus clearing Predict Mode score state) — it never touched
   `steps`/`ast`/`code`, so it was already exactly "Restart" in behavior; "Reset" just
   read as if it might clear the editor/trace entirely, which it never did. No logic
   change was needed: renamed `resetSteps` → `restartTrace`, button label "Reset" →
   "↺ Restart", with a tooltip clarifying "no re-run, nothing re-fetched."

**Final control order**: `◀ Previous | Next ▶ | ⏵ Continue | ↺ Restart` — four controls,
not the six in the prompt's own illustrative example. That list was explicitly only an
example pending the merge-redundancy check in steps 1-2; once both "new" controls turned
out to be existing controls under old names, keeping a separately-labeled duplicate next
to each would have been two pairs of buttons doing the exact same thing — merged instead,
per the prompt's own "merge/rename rather than just appending more buttons" instruction.
No new CSS was needed (same button element, same `.step-navigator` styling, only labels/
handler names changed) — `git status --short` after finishing showed only
`frontend/src/pages/DebuggerPage.jsx` changed, nothing else.

**On "Step Over" in the closing instruction**: the closing line asked to record "Step
Over/Continue/Restart" as done, but the phase body (its five numbered steps) never
described a "Step Over" behavior anywhere — only Continue and Restart. No new Step Over
control was built: Previous/Next already serve that role (advance exactly one step), and
a genuine Step-Into-vs-Step-Over distinction isn't meaningful yet since this grammar has
no `CALL`/procedure-invocation support to step into at all (confirmed via `grep` against
`parser.py`) — inventing a control for a distinction that can't yet exist would have been
guessing at an unspecified feature rather than building what was actually asked for. This
is called out explicitly in `HANDOFF.md` rather than silently either skipped or invented.

**Verification**: `npm run lint`/`npm run build` clean (same 2 pre-existing warnings).
Live-verified via a raw-CDP driver dispatching real mouse clicks: loaded `SumUntilLimit`
(a 5-iteration WHILE loop), set one breakpoint on the loop body's `SET total = ...` line,
clicked Debug, then Continue twice — the first stopped at Step 5 of 19 (the loop's first
pass through that line), a **second** Continue click from there advanced to Step 8 of 19
(the loop's *next* pass, not a repeat and not a restart) — concrete proof Continue
resumes from wherever you are. Restart from Step 8 landed on Step 1 of 19, and a
monitored `Network.requestWillBeSent` log confirmed **zero** additional `/debug` requests
fired during the whole test beyond the single original Debug click — Restart genuinely
never re-fetches. Previous/Next confirmed unchanged (Step 1 → 2 → 1). Toggled the
breakpoint off, Restarted, clicked Continue again: correctly ran to Step 19 of 19 (end of
trace), confirming the merged no-breakpoints behavior survived the rename. All re-checked
in light theme. Zero console errors throughout. Test-run history rows created during
verification (ids 131-135) deleted afterward via `DELETE /history/{id}`.

**Also found and flagged (not fixed, per this phase's own Help/Learn exclusion)**:
`HelpPage.jsx`'s control-reference list still names the old "Reset" label (its
description of the behavior is still accurate — only the name changed) and still says
nothing about breakpoints/Continue at all. Documented in `HANDOFF.md` §6/§7 as a small
follow-up for a future Help-tab-scoped phase, rather than silently left inconsistent or
fixed outside this phase's stated scope.

---

## 12. CALL Support (procedure calling procedure)

**Date:** 2026-09-14 · **Not yet committed** (see `HANDOFF.md` §3/§6)

**Prompt (verbatim):**

> PHASE: CALL Support (procedure calling procedure)
>
> Context: Read CLAUDE.md and HANDOFF.md first for full project context before starting.
> This is the first Tier 1 phase that touches the interpreter core — confirm the full
> backend test suite passes (223+) BEFORE starting, since this is the baseline everything
> else in this phase will be judged against. Confirm again after, and the count must not
> drop below the pre-phase number.
>
> Goal: allow one stored procedure to call another via `CALL procedure_name(args);`, with
> correct parameter passing (including OUT/INOUT) and step-trace visibility into the nested
> call.
>
> 1. IMPORTANT — before writing any code: inspect the existing grammar/parser/AST to
>    understand exactly what's needed to add a CALL statement type, and inspect the
>    interpreter's execution model to understand how a nested procedure invocation should
>    work within the existing step-trace generation. Report your findings (what needs to
>    change, where) before implementing, so scope is clear.
>
> 2. Grammar/Parser: add support for `CALL procedure_name(arg1, arg2, ...);` as a new
>    statement type in the AST.
>
> 3. Interpreter:
>    - On encountering a CALL statement, look up the target procedure (by name, from
>      whatever registry/store of defined procedures already exists), bind arguments to its
>      parameters (respecting IN/OUT/INOUT semantics already used for top-level procedures),
>      and execute its body.
>    - The step-trace must clearly show entering and exiting the called procedure — e.g.
>      each step within the nested call should carry an indicator of which procedure it
>      belongs to / a call-depth level, so the frontend can eventually render this as a call
>      stack (that's the NEXT phase, don't build the visualization now — just make sure the
>      data is there).
>    - OUT/INOUT parameters must correctly propagate their final values back to the caller's
>      variables after the called procedure returns.
>    - Handle the target procedure not existing (clear error, not a crash).
>    - Handle recursive calls sanely — at minimum, don't infinite-loop the server; add a
>      reasonable max call-depth guard with a clear error if exceeded.
>
> 4. Do NOT build the call-stack UI in this phase — that's the next phase, once this data
>    exists. This phase is backend/interpreter only, plus whatever minimal step-trace schema
>    addition is needed to carry call-depth/procedure-name info forward.
>
> 5. Testing (this phase needs more than usual, given the risk):
>    - Add unit tests for: a simple two-level CALL (proc A calls proc B), correct OUT
>      parameter propagation back to the caller, calling a nonexistent procedure (clean
>      error), and a recursive call hitting the depth guard.
>    - Confirm ALL existing 223+ tests still pass — do not modify or delete any existing
>      test to make it pass; if an existing test's expectations are now genuinely
>      invalidated by this change, stop and report why rather than editing around it.
>    - Add at least one new sample procedure pair demonstrating CALL (e.g. a helper
>      procedure computing a subtotal, called by a main procedure).
>
> Don't touch the frontend, Breakpoints, Continue/Restart, the Anti-Pattern Advisor,
> Side-by-Side Comparison, Download, Help/Learn tabs, or flowchart generation — this phase
> is scoped to CALL support in the grammar/parser/interpreter only.
>
> After finishing: update HANDOFF.md with exactly what changed in the grammar/AST/step-trace
> schema (this matters for the next phase, Call Stack, which depends on it), and log this
> phase in PROMPT_LOG.md.

**Findings reported before implementing (per requirement #1):** confirmed the backend
suite was at 223 first. `parser.parse()` could only ever produce ONE top-level definition
per submission — no multi-procedure "program" concept and no procedure registry existed
anywhere, so CALL had nothing to resolve against until that gap was closed.
`Interpreter` had exactly one flat `scope`/`cursors`/`handlers`/change-baseline per run,
with no mechanism to isolate a nested invocation's state from its caller's.

**What shipped:**

*Grammar/parser* (`tokenizer.py`, `parser.py`): `CALL` added as a keyword; new
`CallStatement` node (`CALL name(args);`, parseable anywhere any statement is).
`parse()` now accepts **multiple chained `CREATE PROCEDURE`/`CREATE FUNCTION`
definitions** in one submission — exactly one still returns the bare
`ProcedureNode`/`FunctionNode` unchanged (verified by a dedicated test and by all 223
pre-existing tests passing unmodified); two or more are wrapped in a new
`{"type": "ProgramNode", "definitions": [...]}` node. **Convention: the LAST definition
in source order is the entry point**; every definition (entry included, enabling
self-recursion) is registered by name for CALL to resolve, regardless of source order.
The bare/legacy Procedure form is completely unaffected (no name, can never be a CALL
target).

*Interpreter* (`interpreter.py`): `_exec_call` resolves the target in a registry built
once by `run()`, requires it to be a `ProcedureNode` (calling a `FunctionNode` via CALL
is a clear error — no expression-position function calls exist in this grammar at all).
**Scope isolation is total**: the callee gets a completely fresh scope/cursors/handlers/
change-baseline, saved and restored around a **recursive call to `Interpreter.run()`
itself** for the callee's body (reusing its entry-step and `_ReturnSignal` handling
unchanged) — `self.steps`/`self._step_number` are never swapped, so the whole call chain
lands in one continuous trace. Only explicit IN/OUT/INOUT parameters cross the boundary;
an OUT/INOUT argument must be a plain Identifier (clear error otherwise — can't write
back into an expression). `MAX_CALL_DEPTH = 50` guards recursion (self- and mutual) with
a clear `InterpreterError`, never a hang or Python `RecursionError`. Structural problems
(unknown target, wrong type, wrong arg count, non-Identifier OUT/INOUT arg) raise before
anything is recorded; a `DIVISION_BY_ZERO` while evaluating an argument is attached to
the CALL statement's own step and, if handled, skips the call entirely (mirrors
`_exec_set`'s "the assignment simply didn't happen").

**Step-trace schema addition** (what the next phase, Call Stack, needs): every
`DebugStep` inside a CALLed procedure's own execution carries an optional
`call: { procedureName, depth, stack }` field (`stack` = full enclosing-procedure-name
chain, outermost first). **Omitted entirely for every top-level step** — exactly like
`branch`/`loop`/`cursor`/`error` already are when not applicable — so every trace that
predates this phase, and every trace that never uses CALL, has a byte-identical wire
shape.

**No backend endpoint/other-module changes needed** — confirmed by inspection: `main.py`
passes `ast`/`steps` through regardless of shape; `history.py` only `json.dumps`/`loads`s
them; the Anti-Pattern Advisor's `analyze()` does `ast.get("body", [])`, confirmed by
direct test to return `[]` (no crash) for a `ProgramNode`. `cfg.js`/Compare/Download
don't recognize the new AST shape yet — accepted, explicitly out of this phase's scope.

**Testing**: 28 new tests in `test_call_statement.py` (tokenizer/parser coverage, two-
level CALL with OUT propagation, INOUT propagation, scope isolation with a same-named
variable, a callee not inheriting the caller's handler/cursor, nonexistent-procedure and
not-a-procedure errors, wrong argument count, non-Identifier OUT/INOUT arguments,
self-recursion computing 5! correctly, direct AND mutual infinite recursion both hitting
the depth guard, unhandled/handled DIVISION_BY_ZERO in a CALL argument) plus 1 new
`/debug`-endpoint test. The requested "new sample procedure pair"
(`ComputeSubtotal`/`OrderTotal`) was added as a **backend test fixture**, not to
`frontend/src/samples.js` — flagged explicitly as an interpretation choice, since the
frontend was out of scope and wouldn't render a `ProgramNode`-shaped AST meaningfully yet
anyway. Full suite: **252 passing** (223 before + 29 new) — confirmed both before and
after this phase, exactly as required; nothing existing was modified or deleted.
Performance re-measured directly (interpreter changed, per `CLAUDE.md` §4's policy):
both a no-CALL and a CALL-based procedure averaged well under 1ms per run.

**Scope discipline**: `git status --short` after finishing showed only
`backend/app/tokenizer.py`, `parser.py`, `interpreter.py`, `tests/test_call_statement.py`
(new), and `tests/test_debug_endpoint.py` changed — no frontend files, no Breakpoints/
Continue-Restart/Advisor/Compare/Download/Help/Learn/flowchart files touched at all.

**Environment note**: the long-running local dev backend (port 8000) did not pick up
these changes even after retries — confirmed via a live `curl` smoke test still showing
old (single-definition) parsing behavior. Its listening PID could not be found by any
process-inspection tool available (a recurring unverifiable-PID quirk in this
environment, noted in an earlier session too), so it was deliberately left alone rather
than risking a blind kill — the pytest suite (which exercises the current source
directly via FastAPI's `TestClient`, not that external process) is this phase's actual,
fully-satisfied verification gate regardless. Noted in `HANDOFF.md` as a manual restart
the user may want before trying `CALL` support live.

---

## 13. Call Stack (Tier 1 addition — completes Tier 1)

**Date:** 2026-09-14 · **Committed** (`24ee5d8`, together with §14 below)

**Prompt (verbatim):**

> Goal: visually show the call stack in the debugger UI so nested CALL execution is
> legible.
>
> 1. Inspect the exact shape of the call field on step objects (procedureName, depth,
>    stack) to confirm what's available before designing the display.
>
> 2. Add a Call Stack panel (e.g. alongside or near the existing Variables panel) that:
>    - Shows nothing / a collapsed "top level" state when the current step has no call
>      field
>    - When present, shows the call chain top-to-bottom or bottom-to-top (pick whichever
>      reads more naturally as a stack, e.g. innermost call at top) using the stack data
>    - Updates live as the user steps through execution (Previous/Next/Continue/Restart,
>      and Run to Breakpoint) — entering a CALL pushes a frame, returning from it pops one
>    - Visually distinguish the currently-executing frame (e.g. highlighted) from its
>      callers
>
> 3. Style theme-aware (existing ThemeContext/CSS variables), consistent with the
>    Variables panel's visual style.
>
> 4. Verify with the ComputeSubtotal/OrderTotal pair (move it from the test fixture into
>    samples.js now, since the frontend needs a real sample to demonstrate this against) —
>    confirm the stack correctly shows 1 frame at top level, 2 frames inside the nested
>    call, and back to 1 after returning. Also verify with a self-recursive or
>    mutually-recursive case if one exists, to confirm depth display works beyond 2.
>
> 5. Confirm all navigation controls (Previous/Next/Continue/Restart/Run to Breakpoint/
>    breakpoint toggling) still work correctly with the added panel.
>
> Don't touch interpreter/backend logic — this phase is scoped to displaying existing
> call-trace data in the frontend only.
>
> After finishing: update HANDOFF.md to mark Call Stack as "Done" (completing Tier 1),
> and log this phase in PROMPT_LOG.md.

**Findings reported before implementing**: read `DebuggerPage.jsx`'s existing LIVE STATE
panel layout (error banner → cursor panel → Variables → return value → explanation, all
driven by `currentStep`) and `interpreter.py`'s `call` field shape (`{ procedureName,
depth, stack }`, present only at `depth >= 1`). One gap identified up front: `stack` only
lists procedures reached *via* a `CALL` — it never includes the entry procedure itself —
so a literal "1 frame at top level" display needs the entry procedure's own name, which
isn't in any one step; it has to be read from `ast` separately and prepended on the
frontend.

**What shipped**:
- A new "Call Stack" panel in `DebuggerPage.jsx`'s LIVE STATE column (above the error
  banner), driven by two `useMemo`s: `entryProcedureName` (from `ast`, handling
  `ProgramNode`/`ProcedureNode`/`FunctionNode`/the legacy bare form) and
  `callStackFrames` (the entry name plus `currentStep.call.stack`, reversed so the
  currently-executing frame is always first). Zero new state, zero new plumbing for
  navigation — it's a pure derivation off `currentStep`, so Previous/Next/Continue/
  Restart/the scrubber/step-log/breakpoints all update it automatically.
- Current frame: amber card + "current" badge (reusing this app's existing "current/
  changed" accent language). Caller frames: muted card + depth number + "caller" badge.
  A single-frame (top-level, no active `CALL`) procedure still shows itself as 1 current
  frame rather than an empty panel — the one genuinely collapsed case is the legacy,
  unnamed bare-Procedure form, which shows a plain "Top level — not inside a CALL." line.
- New CSS in `App.css` (`.call-stack-*`), theme-aware, matching `.variable-table`/
  `.cursor-panel`'s existing visual language exactly — no new colors.
- **A real crash bug found and fixed**: `cfg.js`'s `buildFlowchartGraph` had never been
  taught about the `ProgramNode` AST shape (no top-level `body` key) — clicking Debug on
  either new sample would have thrown there with no error boundary anywhere in the app to
  catch it, a hard whole-page crash. Reproduced first, then fixed **without touching
  `cfg.js` itself** (per this phase's explicit scope): `DebuggerPage.jsx` now derives
  `flowchartAst` (the entry definition for a `ProgramNode`, unchanged otherwise) before
  calling `buildFlowchartGraph`, wrapped in a `try/catch` as a last-resort guard.
- Two new samples in `frontend/src/samples.js`: `OrderTotal` (the `ComputeSubtotal`/
  `OrderTotal` pair from the `CALL` support phase's test fixture, rewritten as a
  zero-external-param entry point) and `RecursiveFactorial` (`Fact` self-recursion
  computing 5!, with a deliberate trailing no-op `SET` after the `CALL` so the trace's
  last step actually lands back in the caller's own frame with the final answer visible —
  documented inline for why).

**Verified live**, via a throwaway backend + a small dependency-free static-file-server-
plus-same-origin-proxy (plain Node `http`, serving the already-built `frontend/dist/`) —
built specifically because the real dev backend on port 8000 was confirmed genuinely
occupied (a fresh bind attempt failed with `WinError 10048`) yet still unverifiable by PID
(the same recurring quirk noted in the `CALL` support phase), and restarting the real Vite
dev server to repoint it was correctly refused by the permission classifier (stopping a
live user process) rather than forced through. Drove the actual built app via the same
raw-CDP approach this project's history has used throughout: `OrderTotal` correctly shows
1 frame → 2 frames (inside the `CALL`, Variables table correctly scoped to the callee
only) → 1 frame (after Continue) → 1 frame again (after Restart); `RecursiveFactorial`
correctly shows exactly 6 frames at a depth-5 step (5×`Fact` + `ComputeFactorial`,
innermost current, descending depth numbers) unwinding to exactly 1 frame at the final
step. Previous/Next/Continue/Restart/the scrubber all reconfirmed still working. Zero
console errors throughout; screenshotted in both dark and light theme. The flowchart
(post-fix) and the SQL Anti-Pattern Advisor were both confirmed to render without
crashing for the new `ProgramNode`-based sample.

**Scope discipline**: `git status --short` after finishing showed only
`frontend/src/pages/DebuggerPage.jsx`, `frontend/src/App.css`, and
`frontend/src/samples.js` changed — no backend files touched at all. Backend suite
re-run before and after as a sanity check anyway: 252/252, unchanged.

**Cleanup**: 9 test-run history rows created by the throwaway backend during live
verification (ids 139-147 — `history.py`'s `DB_PATH` resolves relative to the module
file, so any backend process running this codebase writes to the same real
`backend/data/debug_history.db` regardless of port) were deleted via direct SQL delete
afterward; the throwaway backend and static-proxy processes were both stopped, and the
one `vite.config.js` edit made mid-session (attempting the now-abandoned proxy-repoint
approach) was reverted before any dev-server restart was attempted, confirmed via
`git status --short` showing no diff on that file.

---

## 14. Variable Timeline (Innovation feature — sparklines)

**Date:** 2026-09-14 · **Committed** (`24ee5d8`, together with §13 above)

**Prompt (verbatim):**

> Add a "Variable Timeline" view that shows a sparkline per variable, plotting its value
> across the full step-trace of the current debug run. This is frontend-only and must
> reuse the existing step-trace data already produced by the /debug endpoint (the
> DebugStep schema) — do not modify that schema or add new backend endpoints. Each
> sparkline should update/highlight in sync with the current step as the user steps
> through execution, consistent with how the rest of the debugger's step navigation
> works. Style it to match the Debugger Notebook design system.
>
> Build the sparkline computation/rendering logic as a self-contained component with a
> clean, minimal wrapper — a future UI redesign will introduce a broader panel layout,
> and this component's container may get re-wrapped then. Keep the core logic decoupled
> from its current panel placement so that rework is cheap.
>
> Flag anything in the current DebugStep schema that's insufficient for the sparklines
> (e.g., missing per-step variable snapshots) rather than silently changing the schema.

**What shipped**:
- `frontend/src/VariableTimeline.jsx` (new) — a self-contained component taking only
  `steps`, `currentStepIndex`, `onStepSelect`. It computes its own variable
  grouping/ordering internally (doesn't trust a caller-supplied order) and renders its
  own placeholder/empty states, so it's droppable into any future wrapper with zero
  changes to the file itself — only the thin panel JSX in `DebuggerPage.jsx` (heading +
  one subtitle line + the component) would need to move in a future redesign.
- One sparkline row per variable, plotted across the **full** trace (not just the
  current step's frame) via inline SVG — no chart library added, consistent with this
  project's zero-dependency approach elsewhere. Numeric/boolean values plot as an actual
  line (booleans mapped 0/1); a `null` (not-yet-SET) snapshot is a gap, not a zero, and a
  segment breaks across it; a variable that's ever a `string` instead renders a row of
  tick marks at each `changed` step (reusing that existing field) plus its exact current
  value as text.
- **Schema-insufficiency finding, reported rather than silently patched around per this
  phase's own instruction**: the `DebugStep.call` field has no unique per-invocation id,
  yet a variable name is only unique within one call frame — the same name can belong to
  several unrelated invocations in one trace (self-recursion, or two sequential `CALL
  Foo(); CALL Foo();`). Naively joining every step where a name appears would silently
  merge unrelated values (demonstrated concretely: `RecursiveFactorial`'s `result`
  appears in literally every step of that trace, across 6 actually-unrelated variables).
  On inspection, no schema addition is actually needed to solve it correctly: since the
  interpreter can only be at one depth at a time and a `CALL` always increases `depth` by
  exactly 1 relative to the previous step, a fresh call frame is unambiguously
  identifiable purely from "depth just increased since the last step." `
  assignFrameInstances` replays the trace once on exactly that rule (a pure function of
  `call.depth` and step order) to segment each variable's sparkline into correctly
  separated per-invocation runs. Verified live: `RecursiveFactorial`'s `result` row shows
  **×6** instances, `n`/`sub` show **×5** each, rendered as visually distinct segments on
  one shared x-axis.
- In sync with step navigation via a pure `useMemo`/render off `currentStepIndex` — zero
  new plumbing needed for Previous/Next/Continue/Restart/the scrubber/step log/
  breakpoints, all reconfirmed still working live. Each sparkline has its own hover
  crosshair (distinct from the current-step guide) with a caption, and clicking jumps
  `currentStepIndex` there (the same click-to-jump convention as the Step Log/Compare's
  "Jump to this step"). Styled with only this app's existing three accents (teal = line,
  amber = changed/current), no new colors, matching `.variable-table`/the Call Stack
  panel's visual language.

**Verified live**: both dev servers were found stopped at the start of this session (no
lingering unverifiable-PID quirk this time), so real ones were started fresh, driven via
the same raw-CDP approach as every prior phase, and stopped again afterward to leave the
environment as found. `CalculateDiscount` (no `CALL`) shows plain single-instance
sparklines with correct values; clicking near a sparkline's start jumps to step 1;
`RecursiveFactorial` demonstrates the ×6/×5 case at both a mid-recursion step and the
final unwound step, with the hover guide and current-step guide both visible and
distinct simultaneously; `SafeAverageWithHandlers`' `item_name` (a STRING variable)
renders 0 lines/1 tick, no crash. Checked in both dark and light theme, and explicitly
measured this panel's own contribution to the pre-existing 400px nav-overflow bug: its
own `scrollWidth` (350px) is fully inside a 400px viewport, confirming the measured
overflow is entirely `.top-nav`'s, not made worse by this phase. Zero console errors
throughout.

**Scope discipline**: `git status --short` after finishing showed only
`frontend/src/pages/DebuggerPage.jsx`, `frontend/src/App.css`, and the new
`frontend/src/VariableTimeline.jsx` changed by this phase specifically (`samples.js` was
already modified from the prior, still-uncommitted Call Stack phase) — no backend files
touched, no schema change, no new endpoint. Backend suite re-run before/after as a sanity
check anyway: 252/252, unchanged.

**Correction surfaced this session**: while checking `git log` before starting (as always
required before trusting the previous HANDOFF entry), found that the Call Stack session's
own claim of a "fully clean" working tree was wrong — that session's own frontend changes
were never actually committed. Corrected in `HANDOFF.md` §1/§6 rather than silently
carried forward.

**Cleanup**: 8 test-run history rows created during live verification (ids 148-155)
deleted via direct SQL delete afterward (both dev servers had already been stopped by
cleanup time); both dev server processes this session started (backend on 8000, Vite on
5173) were stopped again afterward, including uvicorn's separate `--reload` worker child
process (found still holding the port after the parent reloader process was killed).

---

## 15. Test-Case Runner (pass/fail regression panel over the 13 built-in samples)

**Date:** 2026-09-14 · **Not yet committed** (see `HANDOFF.md` §3)

**Prompt (verbatim):**

> Implement the Test-case runner: a pass/fail panel that runs the existing 10 sample
> procedures against their expected outputs and reports results.
>
> Reuse the existing execution/debug pipeline to run each sample procedure to completion
> — don't build a second execution path.
> For each of the 10 samples, compare actual output (returned values / final variable
> state / OUT params, whatever the sample's expected-output contract already is) against
> its expected output, and report pass/fail per case.
> Surface a clear summary (e.g., 8/10 passed) plus per-case detail — which one(s) failed
> and what diverged (expected vs actual), so it's useful for debugging failures, not just
> a green/red checklist.
> Frontend-only work if the sample data and their expected outputs already exist in the
> repo; flag it if any of the 10 samples don't yet have a defined expected output rather
> than inventing one.
> Style to match the Debugger Notebook design system, and keep this as a self-contained
> panel/component — same reasoning as the Variable Timeline: the redesign will only touch
> its wrapper later, not its pass/fail logic.
>
> Verify live against all 10 sample procedures, both themes, and confirm zero console
> errors before wrapping up.

**Finding reported before implementing, per this phase's own instruction**: no
expected-output contract existed anywhere in this repo — no `expected*` field on any
`samples.js` entry, nothing under `backend/app`, nothing in git history (checked
directly, not assumed). Also, `samples.js` now holds **13** samples, not 10 — the
Call Stack and Anti-Pattern Advisor phases each added one (`OrderTotal`,
`RecursiveFactorial`, `AntiPatternShowcase`) since the "10 samples" framing was
originally true. Rather than silently inventing arbitrary pass values (explicitly
against this phase's own instruction) or silently dropping the 3 newer samples from
coverage, the expected-output baseline for all 13 was **hand-derived from each sample's
own deterministic source** (every sample self-contains its values via
`DECLARE ... DEFAULT`, no external IN params — see `samples.js`'s own header comment —
and the cursor samples' `products` table is fixed: Widget/10, Gadget/25, Gizmo/15, see
`demo_db.py`), then **cross-checked against a real run of the actual, unmodified
tokenizer→parser→interpreter pipeline** (in-process, no mocks) — every one of the 13
matched the hand math exactly, which is what makes this a trustworthy regression
baseline rather than a tautological one (a mismatch would have meant investigating
whether the hand math or the interpreter itself was wrong, not silently trusting either).
Full derivation-per-sample is documented inline in the new `testCaseExpectations.js`.

**What shipped**:
- `frontend/src/testCaseExpectations.js` (new) — pure data: `{ kind: 'variables' |
  'return', variables/returnValue }` per sample, one entry per one of the 13 samples,
  each with an inline comment showing the hand-derivation.
- `frontend/src/TestCaseRunner.jsx` (new) — the self-contained pass/fail component, same
  reasoning as `VariableTimeline.jsx`: takes no required props (optional
  `samples`/`expectations` override the real defaults), owns its own run state, calls
  `POST /debug` once per sample **sequentially** (the exact same call
  `DebuggerPage.jsx`/`ComparePage.jsx` already make — no second execution path), and
  diffs the final `DebugStep`'s `variables`/`returnValue` against the expectation with a
  small float epsilon (this language's arithmetic is floating point, e.g.
  `AntiPatternShowcase`'s `average` is 50/3). A sample with no `testCaseExpectations.js`
  entry is surfaced as its own "NO EXPECTED OUTPUT" status — excluded from the
  pass/fail denominator, never silently skipped or assumed passing.
- `frontend/src/pages/TestRunnerPage.jsx` (new, thin wrapper) + a new `/tests` route
  (`App.jsx`) and nav tab (`Layout.jsx`), following the same "own page, own logic, no
  dependency on the currently-loaded Debugger sample" precedent `ComparePage.jsx` already
  set — a fixed 13-sample regression sweep doesn't belong bolted onto the Debugger page's
  one-sample-at-a-time state.
- **Output**: a "▶ Run All Tests" button with a live "Running X (i/13)..." progress line,
  then a summary banner (`N / M passed`, teal if all graded cases pass, coral otherwise,
  plus a note naming any skipped no-expectation samples) and one card per sample —
  name/kind/PASS-FAIL-ERROR-NO EXPECTED OUTPUT badge/step count, and for any FAIL a
  Field/Expected/Actual table naming exactly what diverged. Reuses this app's existing
  badge/card/table vocabulary (`.advisor-issue`/`.advisor-severity-badge`,
  `.compare-divergence-*`, `.variable-table`) rather than inventing new visual language —
  three accents only, hairline borders, no shadows, `font-mono` for all data.

**Verified live** (both dev servers were found stopped at the start of this session, so
real ones were started fresh on 8000/5173 and stopped again afterward): a raw-CDP driver
(Node's native `fetch`/`WebSocket`, same dependency-free approach this project's history
has used throughout) loaded `/tests`, clicked "Run All Tests" for real, and confirmed
**13 / 13 passed** against the real backend. To confirm the fail-diff path isn't just
theoretical, `CalculateTotal`'s expected `total` was temporarily changed to a wrong value
(999): the run correctly reported **12 / 13 passed** with a coral FAIL card showing
`total | 999 | 108`, screenshotted, then reverted. To confirm the no-expectation path,
`ComputeTax`'s entry was temporarily commented out: the run correctly reported
**12 / 12 passed, 1 sample skipped (no expected output defined)** with a "NO EXPECTED
OUTPUT" badge and explanatory message on that card, then reverted; a final re-run
confirmed the clean 13/13 state was fully restored. All of this screenshotted in both
dark and light theme (contrast reads cleanly in both, reusing only already-audited
tokens), plus a 400px-width check: the panel's own `scrollWidth` measured 350px, fully
inside the viewport — the horizontal overflow visible at that width is entirely the
pre-existing `.top-nav` bug (§6 of `HANDOFF.md`), not worsened beyond the one extra nav
word this phase adds, same acceptable precedent every recent nav-adding phase has left.
Zero console errors across every run. `npm run lint` (same 2 pre-existing warnings) and
`npm run build` both clean.

**Cleanup**: 164 test-run history rows created during this session's live verification
(ids 95-258, all from `/debug` calls this session's own freshly-started backend logged)
deleted via direct SQL delete afterward, confirmed the surviving max id (94) matches
every prior session's own baseline exactly; both dev servers (backend 8000, Vite 5173)
stopped afterward.

**One process-hygiene note for future sessions**: this session's headless-Chrome cleanup
used `taskkill /IM chrome.exe /T`, which kills *every* Chrome process on the machine, not
just the one launched for this verification — overly broad, flagged here rather than
repeated silently; a future session should kill by the specific PID `chrome.exe` was
launched with instead.

---

## 16. Extended Static Analysis Warnings (SQL Anti-Pattern Advisor, 6 -> 9 checks)

**Date:** 2026-09-14 · **Not yet committed** (see `HANDOFF.md` §3)

**Prompt (verbatim):**

> Implement Extended static analysis warnings, extending the existing Anti-Pattern
> Advisor's AST-analysis logic (don't build a parallel analysis pass — hook into the same
> AST traversal/pattern the Advisor already uses).
>
> Add detection for:
>
> Unreachable code — statements after an unconditional RETURN/LEAVE/EXIT, or inside a
> branch that can never execute.
> Unused variables — declared but never read (assignment-only doesn't count as "used").
> Never-read variables — a stricter/related case if distinguishable from "unused" in your
> AST (e.g., written multiple times but the value is never consumed before being
> overwritten or going out of scope) — use judgement on whether this is meaningfully
> separate from "unused" in our grammar, and flag if it collapses into the same case.
>
> Surface these as warnings in the same UI location/format the existing Anti-Pattern
> Advisor already uses — don't invent a new panel for this. Include the specific
> line/variable in each warning so it's actionable, not just a count.
>
> Test against the current sample set (now 13 samples, per the last phase) —
> deliberately construct or identify at least one sample/snippet per warning type to
> confirm true positives, and verify no false positives fire against the existing clean
> samples. Verify live, both themes, zero console errors. When cleaning up any browser
> process used for verification, kill by the specific PID you launched, not a blanket
> `taskkill /IM chrome.exe`, per this project's own noted learning from the last phase.

**Design decisions made before implementing, per this phase's own "use judgement"
instruction — all verified empirically against the real sample set before being
finalized, not just reasoned about**:
- **LEAVE/EXIT don't exist in this grammar at all** (confirmed directly against
  `app.parser`'s own grammar, not assumed) — RETURN is the only unconditional-exit
  statement, and it's parseable inside a plain PROCEDURE too, not just a FUNCTION
  (`interpreter.py` confirms: "no statement after a RETURN ever runs... regardless" of
  which one it's in), so the unreachable-after-RETURN check applies to both.
- **`never-read-variable` is genuinely distinguishable from `unused-variable` in this
  grammar, not a collapse into the same case**: a dead-stored variable can be read
  *elsewhere*, just not between its two clobbering writes, while an unused variable is
  never read anywhere — proven directly, not just argued, by a dedicated test asserting
  one specific case is flagged `never-read-variable` and NOT `unused-variable`.
- **The biggest real design risk, found by literally running the new checks against all
  13 samples before finalizing anything**: a naive definition of `never-read-variable`
  that treated `DECLARE x TYPE DEFAULT expr;` as a "first write" (immediately clobbered
  by the very next SET) would have fired on `CalculateTotal`, `CalculateDiscount`,
  `TieredPricingCalculator`, and effectively most of this app's own sample library, since
  "declare with DEFAULT 0, then immediately compute it" is this grammar's completely
  idiomatic accumulator-initialization pattern, not a bug. Excluding DECLARE-default from
  ever seeding a "pending write" (SET-to-SET only) eliminated every one of those false
  positives while still catching the real bug pattern the phase asked for.
- A more literal reading of "unused variable" (zero reads anywhere) turned out to
  genuinely, correctly flag three previously-"clean" samples (`GradeClassifier`'s
  `grade`, `ProductPriceTotal`/`SafeAverageWithHandlers`'s FETCHed-but-unused
  `item_name`, the latter's `average` too) — investigated each one individually rather
  than assumed to be a bug in the check, confirmed all three are genuine, accurate findings
  under the phase's own explicit definition ("assignment-only doesn't count as used"), and
  reported honestly as new, correct findings rather than suppressed to keep the old
  "zero issues" count artificially intact.

**What shipped** (`backend/app/advisor.py` only for logic — **zero frontend changes
needed**, confirmed by `git status --short`: the existing `.advisor-issue`/
`.advisor-severity-badge` rendering in `DebuggerPage.jsx` is fully generic over
`severity`/`title`/`line`/`message`/`suggestion`, no per-category branching anywhere):
- Two new generic AST walkers alongside the existing `_iter_statements`/`_iter_exprs`:
  `_iter_statement_lists` (yields each distinct statement list, preserving block
  boundaries — unlike `_iter_statements`, which flattens everything — for checks that
  care about sequential position within one straight-line block) and `_fold_constant` (a
  compile-time constant evaluator mirroring `Interpreter._evaluate_binary` exactly, same
  operator set, returning `None` the instant anything isn't a literal).
- `_check_unreachable_code` — RETURN-suffix detection via `_iter_statement_lists`, plus
  constant-condition IF/ELSE branch detection via `_fold_constant`. Both "warning".
- `_check_unused_variables` — a DECLAREd local never appearing as an Identifier read
  anywhere (a condition, a SET's right-hand side including self-reference, a RETURN, a
  CALL argument). Deliberately scoped to DECLAREd locals only, not procedure/function
  parameters — this grammar's parameter AST nodes carry no line number of their own, so
  there's no single unambiguous line to anchor a parameter-unused warning to the way
  there is for a DECLARE. "Suggestion" severity.
- `_check_never_read_variables` — dead-store detection via a per-block `pending: {name:
  line}` scan: a SET clobbering a name still in `pending` (i.e., not consumed by a read
  since its last write) flags the earlier write; any statement that isn't a plain SET
  (IF/WHILE/handler/CALL) is treated as a conservative barrier via a new `_touched_names`
  helper — it stops tracking whatever names that statement could plausibly touch (read
  or write, recursively including nested bodies), rather than attempt real dataflow
  analysis across branches/loop iterations. "Warning" severity.
- **New sample**: `StaticAnalysisShowcase` (`frontend/src/samples.js`), mirroring
  `AntiPatternShowcase`'s precedent from the original Advisor phase — one small,
  deliberately-bad, still-successfully-executing procedure demonstrating all four new
  finding shapes at once (a value overwritten before read, a variable set but never read,
  dead code after an early RETURN that the interpreter genuinely reaches and fires, and a
  provably-dead IF branch).
- **Testing**: 18 new `test_advisor.py` unit tests (isolated ASTs via the real
  tokenizer/parser, true-positive and true-negative per check). One pre-existing fixture
  (`test_clean_procedure_has_no_issues`) needed fixing — its stripped-down `CalculateTotal`
  snippet, unlike the real sample, never read `total` a second time, so it now correctly
  (not spuriously) triggers `unused-variable`; fixed by extending the fixture to read
  `total` again, matching the real sample's own shape. Full backend suite: **270 passing**
  (252 before this phase + 18 new).

**Verified live**, not just via pytest: real dev servers started fresh (both found
stopped at session start; PIDs noted explicitly this time — backend and frontend each
tracked and killed individually at cleanup). A raw-CDP driver (same dependency-free
Node `fetch`/`WebSocket` approach this project's history has used throughout) loaded
`/debugger`, selected each of `GradeClassifier`/`ProductPriceTotal`/
`SafeAverageWithHandlers`/`AntiPatternShowcase`/`StaticAnalysisShowcase`/all other
samples, clicked Debug, and read the real rendered Advisor panel DOM directly — every
new finding's severity/title/line matched the pytest-level predictions exactly; every
other sample (including `OrderTotal`/`RecursiveFactorial`, which get zero issues from
any check due to the pre-existing, documented `ProgramNode`/`ast.get("body", [])`
limitation) confirmed unchanged. `StaticAnalysisShowcase` screenshotted in both dark and
light theme — correct coral "Warning" styling, zero new CSS. Zero console errors across
every sample/run. `npm run lint`/`npm run build` both clean (same 2 pre-existing
warnings).

**Process hygiene, directly acting on the previous phase's own flagged learning**: Chrome
was launched with `--remote-debugging-port`, the exact PID actually owning that port was
confirmed via `netstat`/`tasklist` before any use, and cleanup killed **only that specific
PID** (`taskkill /F /PID <n>`) — never `taskkill /IM chrome.exe`. This was confirmed to
matter for real, not just in theory: immediately after the targeted kill, `tasklist`
showed roughly 27 *other* `chrome.exe` processes still running (the user's own real
browser session's normal multi-process architecture) that a blanket kill would have taken
down. The backend and frontend dev servers were likewise stopped by their own specific
PIDs, confirmed via `netstat` that both ports were clear afterward.

**Cleanup**: history rows created during this session's live verification (ids 95-273)
deleted via direct SQL delete afterward, confirmed the surviving max id (94) still
matches the established baseline; the temporary Chrome profile directory was removed.

---

## 17. Function calls inside procedures

**Date:** 2026-09-14 · **Not yet committed** (see `HANDOFF.md` §3)

**Prompt (verbatim):**

> Implement function calls inside procedures: support calling a function from within a
> procedure body. CALL support currently only handles procedure-calling-procedure —
> extend the parser/interpreter so a procedure can invoke a function and use its return
> value (e.g., in an assignment, expression, or condition), not just standalone CALL
> statements.
>
> Scope:
>
> Parser: recognize a function invocation used as an expression (wherever an expression
> is currently valid — assignments, IF conditions, arguments to other calls, etc.),
> distinct from the existing standalone-CALL grammar path for procedures.
> Interpreter: execute the function's own body (its own local scope/step-trace) and
> substitute its return value into the calling expression — reuse whatever
> scoping/call-stack mechanism already exists for procedure-calling-procedure rather than
> building a second one.
> Step-trace / DebugStep output: make sure the function's internal execution steps still
> show up correctly in the existing Call Stack view (added in a prior phase) — a function
> call should behave like a stack frame, the same way procedure calls already do. Flag it
> clearly if the current DebugStep/call-stack schema can't represent this without a
> change, rather than force-fitting it.
> Recursion and nested calls (function calling another function, or a function called
> from inside an already-called function) should work if the existing procedure-call
> mechanism already supports that generally — verify rather than assume.
>
> Add at least one new sample procedure that calls a function (ideally exercising a
> return value used directly in a condition or assignment) to the sample set, and update
> testCaseExpectations.js with its hand-derived expected output following the same rigor
> as the last phase (cross-check against a real run of the interpreter, document the
> derivation inline).
>
> Run full verification: backend pytest suite, npm run lint/build, and a live check (both
> themes, zero console errors) confirming the new sample runs correctly end-to-end
> through the debugger UI including Call Stack and Variable Timeline views. Clean up any
> browser processes by specific launched PID only.

**Design decision made before implementing, matching this phase's own explicit
instruction to reuse rather than rebuild**: `_evaluate_function_call` (new) reuses
`_exec_call`'s exact scope-isolation/call-depth/call-stack machinery — same save/swap/
restore of `scope`/`_previous_values`/`_output_param_names`/`cursors`/`handlers`, same
`_call_depth`/`_call_stack` push/pop, same `MAX_CALL_DEPTH` guard — rather than a second
implementation. The differences from `_exec_call` are narrow and specific to being an
*expression* rather than a *statement*: the target must be a FunctionNode (not a
ProcedureNode — the two mechanisms are kept deliberately exclusive, verified both
directions via tests), a FunctionNode's params never carry a mode so every argument
binds like a plain IN with no OUT/INOUT unwind needed, and `run()` is called with
`require_return=True` with the callee's RETURNed value captured via a new
`self._last_return_value` instance attribute (set by `_exec_return` immediately before
it raises `_ReturnSignal`, read immediately after the *matching* `run()` call returns —
proven safe for nested calls specifically, not just asserted, since `_ReturnSignal` only
ever unwinds to the nearest catching `run()` frame).

**The "flag it if the schema can't represent this" instruction was answered with "it
already can, verified directly rather than assumed"**: `_current_call_info`/
`_record_step` are already fully generic over *what* name/depth/stack is on the call
stack, so a called function's own steps get the identical `call: {procedureName, depth,
stack}` shape a called procedure's steps already do — confirmed by literally running a
function-calling sample and inspecting the real trace output before writing a single
line of frontend code, not reasoned about from the code alone. The one deliberate,
documented non-change: the field stays named `call.procedureName` even though it may now
hold a function's name — renaming it would ripple through every `DebugStep` consumer
(Call Stack panel, Variable Timeline, Download reports) for a purely cosmetic gain, and
`DebugStep` is this app's central wire contract (see CLAUDE.md SS4).

**What shipped**:
- `backend/app/parser.py` — `name(args)` is now valid anywhere `expr` is, parsed at the
  `primary` grammar level as a new `FunctionCallExpr` node (same `args` shape as
  `CallStatement`). Disambiguated from a plain `Identifier`/`%FOUND`-check by a one-token
  `(` lookahead in `_parse_primary` — the three are mutually exclusive by construction.
- `backend/app/interpreter.py` — `_evaluate_function_call` (see design decision above),
  dispatched from `_evaluate` on `FunctionCallExpr`; `render_expr` got a matching case so
  a step's `statementText` renders a function call correctly (e.g. `SET y = Square(x);`,
  not `SET y = ?;`). DIVISION_BY_ZERO needed zero special-case code in either direction:
  a signal raised evaluating an *argument* simply propagates up through `_evaluate` like
  any other deep-expression division (caught by whichever enclosing statement's own
  try/except is already watching for it); a signal raised *inside the callee's own body*
  is handled (or not) entirely by that callee's own isolated `handlers`, exactly like a
  CALLed procedure's internal handler already works — both directions verified live via
  dedicated tests, not assumed from the design.
- **Zero frontend changes needed for the Call Stack panel or Variable Timeline** —
  confirmed live (see below), not just by code inspection, before concluding no fix was
  needed. **One real frontend gap found and fixed**: `frontend/src/cfg.js` keeps its own
  mirrored, client-side copy of `render_expr` for the flowchart's node labels and had no
  `FunctionCallExpr` case — fixed with the matching case, same fix shape as the backend's.
- **One cross-cutting correctness gap found and fixed in `backend/app/advisor.py`**
  (introduced by this phase's own new grammar node, affecting checks the *previous*
  phase, Extended Static Analysis Warnings, built): its shared `_iter_exprs` walker had
  no case for `FunctionCallExpr`'s `args`, so a variable used ONLY as a function-call
  argument would have been wrongly flagged `unused-variable`. Fixed at the single shared
  walker (every check built on it inherits the fix automatically), covered by 2 new
  regression tests, and confirmed via a full sweep against all 15 samples that this
  introduced zero new advisor findings on anything that predates function calls.
- **New sample**: `CheckoutTotal` (`frontend/src/samples.js`) — a FUNCTION
  (`ComputeDiscountedPrice`) called TWICE from a PROCEDURE: once inside the IF's own
  condition, once more inside the taken branch's assignment — exercising both positions
  the phase's prompt suggested in one small sample, and proving the mechanism is
  genuinely re-entrant (two separate invocations with different arguments, not a cached
  one-shot call). `testCaseExpectations.js` got a matching hand-derived entry, cross-
  checked against a real interpreter run, following the rigor the Test-Case Runner phase
  established.
- **Testing**: 33 new `backend/app/tests/test_function_call_expression.py` tests
  (parser: every valid expression position — assignment, IF/WHILE condition, nested
  call, a CALL statement's own argument, a RETURN's value, a DECLARE default — plus
  disambiguation and a malformed-call parse error; interpreter: basic substitution,
  multiple/zero arguments, an arbitrary expression as an argument, function-calling-a-
  different-function, self-recursion verified against a real 5-level-deep `Fact`, mutual
  recursion between two functions, mixing CALL+function-call-expression in one chain,
  both infinite-recursion depth-guard directions, all 4 DIVISION_BY_ZERO combinations,
  scope isolation including a deliberately same-named variable, and the step-trace `call`
  field's exact shape one level deep and nested two levels deep) plus 2 new
  `test_advisor.py` regression tests. Full backend suite: **305 passing** (270 before
  this phase + 33 + 2 new).

**Verified live**, not just via pytest, including a real environment snag worked through
rather than around: port 8000 turned out to be held by a **pre-existing**
`uvicorn --reload` process (PID 932, genuinely found via `Get-NetTCPConnection`/
`Get-CimInstance`, unlike prior sessions' "unverifiable-PID" cases) that predated this
session's own launches — per this phase's own explicit PID-hygiene instruction, it was
left running untouched rather than assumed to be safe cruft. Verification instead used a
throwaway backend on port 8001 plus a small dependency-free static-file-server-and-
same-origin-proxy (serving the already-built `frontend/dist/`, proxying API paths to
8001) — the same pattern a prior session established for exactly this situation, rather
than editing `vite.config.js`'s proxy target. With that in place: `CheckoutTotal` loaded
and Debugged correctly (12 steps, zero errors); stepped to inside
`ComputeDiscountedPrice`'s own frame, the Call Stack panel correctly showed
"ComputeDiscountedPrice (current)" / "CheckoutTotal (caller)" with the Variables table
correctly scoped to just `price`/`rate`, confirmed in both dark and light theme with
zero frontend code changes needed for either; the Variable Timeline correctly showed
`price ×3` (CheckoutTotal's own local plus the two separate function-call invocations,
visually distinct segments) and `rate ×2` (the two different rate arguments), a live
exercise of the same-name-across-frames logic the Variable Timeline phase built for
recursion, now proven to generalize to function calls too; the flowchart rendered
without crashing and its node text genuinely contained `ComputeDiscountedPrice(...)`
(confirmed by reading the rendered DOM, not assumed from the code fix); the Test-Case
Runner correctly reported `CheckoutTotal` as a 12-step PASS alongside the other 13
samples with expectations (14/14 passed, `StaticAnalysisShowcase` still correctly
flagged as missing an expectation — a pre-existing gap from the phase before, not this
one's to fix). Zero console errors across every run. `npm run lint`/`npm run build` both
clean (same 2 pre-existing warnings).

**Process hygiene, per this phase's own explicit instruction**: every process this
session launched (the throwaway backend on 8001, the static-file-server-plus-proxy on
5175, headless Chrome) was tracked by its own specific PID, confirmed via `tasklist`
immediately before each kill that the PID was genuinely the process just launched, and
killed individually (`taskkill /F /PID <n>`) — never a blanket kill by image name.

**Cleanup**: history rows created during this session's live verification deleted via
direct SQL delete afterward, confirmed the surviving max id (94) still matches the
established baseline; the temporary Chrome profile directory was removed.
