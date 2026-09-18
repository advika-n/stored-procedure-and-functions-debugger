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

**Date:** 2026-09-14 · **Committed** (`e322915`, together with §16/§17 below)

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

**Date:** 2026-09-14 · **Committed** (`e322915`, together with §15 above/§17 below)

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

**Date:** 2026-09-14 · **Committed** (`e322915`, together with §15/§16 above)

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

---

## 18. CASE statement support

**Date:** 2026-09-14 · **Not yet committed** (see `HANDOFF.md` §3)

**Prompt (verbatim):**

> Implement CASE statement support — both the grammar and the interpreter.
>
> Scope:
>
> Parser: support both common CASE forms — simple CASE (CASE expr WHEN val1 THEN ...
> WHEN val2 THEN ... ELSE ... END CASE) and searched CASE (CASE WHEN cond1 THEN ... WHEN
> cond2 THEN ... ELSE ... END CASE), consistent with however this grammar already names/
> handles IF/WHILE. Match existing statement-block conventions (whatever terminates
> IF/WHILE bodies today) rather than inventing a new pattern.
> Interpreter: evaluate the CASE expression/conditions in order, execute the first
> matching branch's statements, fall through to ELSE if present, and no-op if no branch
> matches and there's no ELSE — confirm what this grammar's convention is for missing
> ELSE (some SQL dialects error, some no-op) and follow whatever pattern IF already uses
> for a missing ELSE, don't invent a new one.
> Step-trace: make sure CASE branch selection is visible/traceable in the existing
> DebugStep step-by-step view, the same way IF branch-taken is currently shown — reuse
> that mechanism rather than building a new one.
> Nesting: CASE nested inside IF/WHILE/another CASE should work if the existing
> block-execution mechanism supports it generally — verify, don't assume.
> Cross-cutting checks: same category of gap as last phase — check whether cfg.js's
> flowchart renderer and advisor.py's AST walker (unreachable-code, unused-variable,
> never-read-variable) already handle a new statement/expression node type or need an
> explicit CASE case added, the way FunctionCallExpr did last time. Don't assume they're
> generic over new node types — verify directly.
>
> Add at least one new sample procedure exercising both CASE forms (simple and
> searched), with hand-derived expected output cross-checked against a real interpreter
> run, documented inline in testCaseExpectations.js per existing convention.
>
> Full verification: backend pytest suite, lint/build, live check both themes with zero
> console errors, Call Stack / Variable Timeline / Advisor / Test-Case Runner all
> confirmed working against the new sample. Kill any browser/server processes you launch
> by specific PID only — never touch a pre-existing process you didn't start (checked
> port usage before binding, per last phase's snag).

**Design decision made before implementing, matching this phase's own explicit
instruction to reuse rather than build parallel mechanisms**: both CASE forms are ONE
AST node type (`CaseStatement`), not two, since a simple CASE is just syntactic sugar
over a searched CASE (compare each WHEN value against the same operand, instead of
evaluating each WHEN as its own independent condition) — one node type means
`_exec_case`/`_parse_case`/every cross-cutting consumer only ever needs one code path.
`_parse_case` tells the two forms apart with a single-token lookahead right after CASE (a
WHEN next means searched); every WHEN/ELSE body is parsed via `_parse_block` — the exact
same block-parsing helper `if_stmt`/`while_stmt` already use, terminators `{WHEN, ELSE,
END}`/`{END}` mirroring `if_stmt`'s own `then_body`/`else_body` terminators exactly, per
this phase's own "match existing statement-block conventions" instruction.

**Missing-ELSE convention confirmed by reading `_exec_if` first, not invented**: a silent
no-op (the CaseStatement's own DebugStep still recorded, no InterpreterError) — exactly
IF's own established behavior, not a fresh design decision. DIVISION_BY_ZERO while
evaluating the operand or any WHEN expression also mirrors `_exec_if` exactly
("condition couldn't be evaluated -- don't guess a branch"), generalized to a whole
sequence: evaluation stops the moment a signal is raised, no later WHEN is even checked,
and it falls through to ELSE/none — including the somewhat non-obvious detail (found by
re-reading `_exec_if`'s actual code, not just its comment) that ELSE still runs even
though the error is what caused the fallthrough, confirmed by a dedicated test.

**Step-trace: reuses IfStatement's own `branch` field verbatim, per this phase's own
"reuse that mechanism" instruction — no new DebugStep field needed at all.** `path` is
`"when-<N>"` (0-based matched WHEN index) instead of IF's fixed `"then"`, or `"else"`/
`"none"` (identical to IF). `condition` is the operand's rendered text for simple CASE,
or the literal string `"CASE"` for searched CASE.

**Cross-cutting checks were verified directly, not assumed generic — and found real gaps
in MORE places than the previous phase's `FunctionCallExpr` fix needed, per this phase's
own explicit warning that this was "the same category of gap... verify directly"**:
- `frontend/src/cfg.js`'s flowchart builder (`emitBlock`) had a hardcoded
  IfStatement/WhileStatement/ReturnNode dispatch with **zero** CaseStatement
  understanding — confirmed by reading the function directly before writing any fix. A
  CASE would have rendered as a generic rect with literal "CaseStatement" text, and
  **every WHEN/ELSE body would have been silently dropped from the diagram entirely**
  (no recursion into them at all -- not a cosmetic label gap like `FunctionCallExpr`'s
  was, a structural one). Fixed with a real design: a diamond node per CASE, one labeled
  edge per WHEN (`"when 1"`, `"when 2"`, ... -- open-ended, unlike IF's fixed pair, so the
  old fixed `edgeLabel` lookup object was replaced with `edgeLabelFor`/
  `isConditionalEdgeKind` functions) plus one for ELSE (synthesized when absent, mirroring
  IF's own "no ELSE" tail), and `computeDiagramState`'s taken-edge highlighting
  generalized from a hardcoded `'then'`/`'else'` check to "whatever `branch.path` says,
  unless it's `'none'`" — verified live: a "CASE tier" diamond with 4 labeled edges,
  correct one highlighted teal, in both themes.
- `backend/app/advisor.py` needed CASE support in **five** places, not the single
  `_iter_exprs` fix `FunctionCallExpr` needed: the three shared walkers
  (`_iter_statements`, `_statement_exprs`, `_iter_statement_lists`) PLUS two separate
  hand-rolled recursive walkers that don't use the shared ones at all
  (`_check_nested_loops`'s own `walk`, and `_find_unguarded_fetch`) — found by reading
  each one individually rather than assuming the shared-walker fix would cover
  everything. Without these two extra fixes, a FETCH inside a CASE branch would have
  been invisible to `missing-error-handling`, and a WHILE nested inside a CASE nested
  inside another WHILE would not have been detected as nested — both confirmed as real
  gaps with a failing test written first. One new detection also added (not just
  plumbing): a searched CASE's WHEN with a compile-time-constant condition is now flagged
  the same way IF's constant-condition check already works, deliberately scoped to
  searched CASE only (folding simple CASE's operand-equality would need `_fold_constant`
  to handle STRING literals too, a separate piece of work, documented as out of scope
  rather than silently skipped).
- `backend/app/explainer.py`'s deterministic template fallback dispatches by `nodeType`
  with **no case for CaseStatement** before this phase — would have degraded to the
  generic "Executed line N: ..." fallback. Added a proper CASE branch. The Gemini-backed
  prompt-building (`_build_prompt`/`_build_ask_prompt`) needed **no fix** — already fully
  generic, confirmed by reading it directly, and confirmed live (the real configured
  Gemini key produced a correct, coherent explanation for an actual CASE step with zero
  backend changes for that path).
- `backend/app/report.py` and `frontend/src/compareTraces.js` were both checked and
  confirmed already fully generic over `branch.path` — no fix needed, verified by
  reading both rather than assumed safe by analogy.
- `frontend/src/pages/DebuggerPage.jsx`'s Predict Mode branch-guessing quiz checks
  `nodeType === 'IfStatement'` specifically (its UI is a fixed Then/Else button pair,
  nowhere to put CASE's open-ended N-way choice) — a CASE step correctly, gracefully
  offers no branch-prediction prompt rather than crashing; documented with a code
  comment at the exact check site as a deliberate scope decision, not silently left
  unexplained.

**What shipped**: `backend/app/tokenizer.py` (CASE/WHEN keywords -- THEN/ELSE/END
reused as-is), `backend/app/parser.py` (`_parse_case`, the `CaseStatement` node shape),
`backend/app/interpreter.py` (`_exec_case`, `render_statement_header`'s CaseStatement
case), `backend/app/advisor.py` (5 fixes above), `backend/app/explainer.py` (template
fallback case), `frontend/src/cfg.js` (flowchart support above),
`frontend/src/pages/DebuggerPage.jsx` (Predict Mode scope-decision comment). New sample:
`ClassifyOrder` (`frontend/src/samples.js`) exercising both CASE forms in one procedure
— a simple CASE picks a discount rate off a tier code, then a searched CASE classifies
the discounted total into a size label. Two genuine Advisor findings on this sample
(`magic-number` on tier's own `DEFAULT 2` colliding with `WHEN 2`; `unused-variable` on
`sizeLabel`, the same "final classification result" pattern `GradeClassifier`'s `grade`
already demonstrates) were investigated and left in rather than dodged, matching this
project's "investigate and disclose, don't hide" precedent. `testCaseExpectations.js`
got a matching hand-derived, cross-checked entry.

**Testing**: 25 new `backend/app/tests/test_case_statement.py` tests (tokenizer; parser
— both forms, structural errors, nesting inside IF/WHILE/another CASE; interpreter —
first-match-wins both forms, ELSE, no-ELSE no-op, short-circuit evaluation proven via a
later WHEN calling an undefined function that's never reached, three-level nesting
including CASE-inside-CASE, RETURN inside a WHEN body, a function call as operand and as
a WHEN value, all 3 DIVISION_BY_ZERO combinations, the exact `branch` shape for both
forms, and a CASE inside a CALLed procedure carrying the correct `call` field) plus 13
new `test_advisor.py` regression tests. Full backend suite: **343 passing** (305 before
this phase + 25 + 13 new).

**Verified live**, not just via pytest, including a real cross-check tool built for this
phase specifically: an in-process script (not just spot-checking individual samples)
loaded ALL 16 samples' actual source from `samples.js`/`testCaseExpectations.js` at once
(via a small Node dump script bridging ES modules to a Python verification script) and
ran each through the real tokenizer/parser/interpreter/advisor pipeline, confirming
zero regressions on every pre-CASE sample's own expected final state AND its own Advisor
findings, not just the new sample. Live in the browser: `ClassifyOrder` loaded and
Debugged (12 steps, zero errors, exactly the 2 predicted Advisor findings); the
flowchart's two CASE diamonds ("CASE tier" and bare "CASE") both showed correctly
labeled multi-way edges with the taken one highlighted teal, confirmed in both dark and
light theme; the Call Stack panel showed a correct single "ClassifyOrder current" frame
(no regression for a plain procedure); the Test-Case Runner reported 15/15 passed (14
prior + `ClassifyOrder`), 1 skipped (`StaticAnalysisShowcase`, a pre-existing gap); a
regression spot-check against `GradeClassifier` (an unrelated IF-based sample) confirmed
unchanged behavior. Zero console errors across every run. `npm run lint`/`npm run build`
both clean (same 2 pre-existing warnings).

**Process hygiene, per this phase's own explicit instruction (a direct callback to the
previous phase's own snag)**: port availability was confirmed via
`Get-NetTCPConnection`/`netstat` *before* binding anything this time — port 8000
confirmed still held by the same pre-existing PID 932 from last session (left
untouched, again), ports 8001/5176/9336 confirmed free before use. Every process this
session launched (throwaway backend, static-proxy server, headless Chrome) was tracked
by its own specific PID and killed individually at cleanup, confirmed via `tasklist`
immediately before each kill that the PID was genuinely the process just launched.

**Cleanup**: history rows created during this session's live verification deleted via
direct SQL delete afterward, confirmed the surviving max id (94) still matches the
established baseline; the temporary Chrome profile directory was removed.

## 19. LOOP/LEAVE support

**Date:** 2026-09-14 · **Not yet committed** (see `HANDOFF.md`)

**Prompt (verbatim):**

> read claude.md and handoff.md for context
>
> This is the SQL Stored Procedure & Function Debugger project. The tree should be clean. Start this phase fresh.
>
> Implement **LOOP/LEAVE support** — grammar and interpreter.
>
> Scope:
> - **Parser**: support a labeled or unlabeled `LOOP ... END LOOP` block (confirm which this grammar's spec/docs call for — check existing docs/tests before assuming labels are required) plus `LEAVE` to break out of it. Reuse `_parse_block` for the loop body, same as IF/WHILE/CASE.
> - **Interpreter**: execute the loop body repeatedly until a `LEAVE` is hit; if labels are supported, `LEAVE <label>` should break the correctly-labeled enclosing loop when loops are nested, not just the innermost one. Guard against infinite loops the same way `WHILE` already does, if it already has a safeguard — check and reuse it rather than inventing a new one.
> - **Step-trace**: make LOOP iterations and the LEAVE exit visible in the existing DebugStep view, consistent with how WHILE iteration is currently shown — reuse that mechanism.
> - **Nesting**: LOOP nested inside IF/WHILE/CASE/another LOOP should work if the existing block mechanism supports it generally — verify.
> - **Cross-cutting checks — do this for every one of these, don't assume generic handling**:
>   - `cfg.js` flowchart renderer — does it need an explicit LOOP/LEAVE case?
>   - `advisor.py`'s AST walkers (unreachable-code, unused-variable, never-read-variable, constant-condition) — do any need a LOOP/LEAVE case? In particular, code after an unconditional LEAVE inside a loop body is a real unreachable-code case worth checking.
>   - `explainer.py`'s template fallback — does it have a case for LOOP/LEAVE steps?
>   - Predict Mode — does LOOP/LEAVE fit its existing branch-guessing UI, or does it need the same kind of documented scope-exclusion CASE got?
>
> Add at least one new sample procedure exercising LOOP+LEAVE (ideally with nesting, if labels are supported) with hand-derived expected output cross-checked against a real interpreter run, documented inline in `testCaseExpectations.js`.
>
> Full verification: backend pytest suite, lint/build, an in-process script running all samples through the real pipeline at once (per last phase's approach) to confirm zero regressions, and a live check both themes with zero console errors — Call Stack, Variable Timeline, Advisor, Test-Case Runner all confirmed against the new sample. Check port usage before binding anything, leave any pre-existing process alone, and kill only what you launched by exact PID.

**Design decisions made before implementing**: labels were checked against this grammar's
own existing docs first, not assumed — neither `README.md` nor `Theory.jsx`'s
`ControlFlowTopic` (which already described "a bare LOOP... until an explicit
LEAVE/EXIT" as a concept worth knowing) required them, so labels were built as an
*optional* MySQL-style feature (`label: LOOP ... END LOOP label;`), added specifically
because the phase's own nested-LEAVE-by-label requirement needs them. `LoopStatement`/
`LeaveStatement` are two new AST node types, not a variant of `WhileStatement` — LOOP has
no condition of its own at all, unlike WHILE, so forcing it through the same node shape
would have meant a meaningless `condition` field. `':'` became a real punctuation token
for the first time (previously unneeded) since it's the label terminator;
`_parse_statement` tells a labeled LOOP apart from every other statement with a
one-token `IDENT ':'` lookahead (unambiguous — no other statement in this grammar starts
with a bare IDENTIFIER).

**Interpreter**: `_exec_loop` reuses `WhileStatement`'s own `MAX_LOOP_ITERATIONS` guard
verbatim, per the phase's own explicit "reuse... rather than inventing a new one"
instruction, and reuses its `loop: {condition, result, iteration}` DebugStep field too —
`condition` is the literal `"LOOP"`/`"LOOP <label>"` string (LOOP has no real boolean to
show), `result` is always `True` (a LOOP never "fails" a check; its only exits are an
executed LEAVE or the iteration cap raising instead of ever recording a false one).
`_exec_leave` validates its target BEFORE recording anything (matching every other
statement's "structural problems raise before the step" convention): an unlabeled
`LEAVE;` needs a non-empty `Interpreter._loop_stack`; a labeled one needs that exact
label somewhere on it. Once validated, its own step is recorded and an internal
`_LeaveSignal(label)` unwinds — `_exec_loop` either catches it (unlabeled, or its own
label matches) and stops, or re-raises it unchanged to keep unwinding outward. This is
the concrete mechanism that makes `LEAVE <label>` from two loop levels deep correctly
jump straight past the innermost loop entirely, not just stop at its boundary — verified
live and in a dedicated test (the new `FindPairSum` sample's own labeled `LEAVE outer;`
fired from inside `inner:`'s own body).

`self._loop_stack` is isolated per CALL/function-call frame exactly like
`cursors`/`handlers` already are — saved and replaced with a fresh empty list around a
callee's own execution, restored afterward. LOOP/LEAVE nesting is a purely lexical,
single-procedure concept, so without this a callee could otherwise "LEAVE" a label still
sitting on the caller's own stack purely because the caller happens to be paused inside a
CALL right now — confirmed as a real, previously-possible bug by a dedicated test that
fails without the isolation, not just reasoned about abstractly (and a second test
confirms the reverse: a callee reusing the exact same label name as its caller resolves
completely independently, no collision either direction).

**Cross-cutting checks verified directly, in the same places the CASE-statement phase
found gaps, not assumed fixed by analogy**:
- `frontend/src/cfg.js`'s `emitBlock` threads a new `loopStack` accumulator (an array of
  `{label, exits}` contexts, innermost last) through every recursive call it already
  makes — a LEAVE resolves against it exactly like `Interpreter._loop_stack` does
  (unlabeled → innermost; labeled → search outward for a match) and contributes its own
  exit edge (`kind: 'leave'`, labeled "leave" for readability, deliberately never
  taken/not-taken-colored since a LEAVE node has only one outgoing edge to disambiguate
  from) into whatever follows its *target* LOOP specifically, not necessarily the
  nearest one. Verified against the real rendered SVG, not just the graph object:
  `FindPairSum`'s unlabeled `LEAVE;` edge correctly landed on the statement right after
  the inner LOOP (inside the outer loop's own body), while both labeled `LEAVE outer;`
  edges (one at the top of the outer loop, one from inside the inner loop) correctly
  landed on the diagram's End node — the intended "escape both loop levels at once"
  shape, not just "didn't crash."
- `backend/app/advisor.py` needed the three shared walkers fixed again PLUS both
  hand-rolled ones (`_check_nested_loops`'s own `walk`, `_find_unguarded_fetch`) — same
  two as the CASE phase's own list, confirming this is a real, recurring pattern in this
  codebase's design, not a one-off. `_check_nested_loops` was generalized from
  WHILE-only to "any loop nested inside any loop" the moment a second loop construct
  existed. **One new detection, explicitly requested by the phase**: code positionally
  after an unconditional LEAVE, in the same statement list, is now flagged by
  `unreachable-code` — refactored alongside RETURN's own existing sub-case (both share
  the "unconditionally exits this block" property) rather than duplicated as a parallel
  check. **One deliberate non-extension, documented rather than silently left out**:
  `cursor-could-be-set-based` stays WHILE-only — a LOOP-based cursor loop's real
  idiomatic guard is retrospective (`FETCH ...; IF cur%NOTFOUND THEN LEAVE; END IF;`),
  not the predictive `%FOUND` this check already understands; recognizing that idiom is
  real, separate work, and was proven as a genuine, accepted false positive by a
  dedicated test, not just asserted.
- `backend/app/explainer.py`'s deterministic template fallback had no
  LoopStatement/LeaveStatement cases — added both. The Gemini-backed
  `_build_prompt`/`_build_ask_prompt` paths needed **no fix**, confirmed by reading them
  directly: both already forward `step.get('loop')` generically for any nodeType.
- `frontend/src/pages/DebuggerPage.jsx`'s Predict Mode branch-guessing quiz checks
  `nodeType === 'IfStatement'` specifically — a LOOP/LEAVE step correctly, gracefully
  offers no branch-prediction prompt, documented with a comment extending CASE's own
  existing one.
- `backend/app/report.py` and `frontend/src/compareTraces.js` were both checked and
  confirmed already fully generic over `loop`'s shape — no fix needed.

**`README.md` and `Theory.jsx`'s `ControlFlowTopic` were both updated** — both
previously, accurately, said LOOP/LEAVE (and, stale from even earlier phases, CALL/CASE)
weren't supported; fixed while directly touching the exact stale claim this phase's own
diff made false. Theory also got a new runnable labeled-LOOP-with-LEAVE code example.

**New sample**: `FindPairSum` (`frontend/src/samples.js`) — a labeled LOOP nested inside
another labeled LOOP, brute-force searching for the first pair `(i, j)`, each 1..5,
summing to a target. Demonstrates both LEAVE forms: an unlabeled `LEAVE;` (breaks only
the innermost loop, fired when the inner search comes up empty) and a labeled `LEAVE
outer;` fired from inside the inner loop (breaks straight out of both loops at once).
Hand-traced (`i=1`: no `j` in 1..5 sums to 7, unlabeled LEAVE fires, `i` advances to 2;
`i=2`: `j=5` hits `2+5=7`, `LEAVE outer;` fires immediately) and cross-checked against a
real interpreter run — `target=7, i=2, j=5, foundI=2, foundJ=5`, 58 steps.
`testCaseExpectations.js` got a matching entry. Four genuine, investigated-and-left-in
Advisor findings (`unused-variable` ×2 on `foundI`/`foundJ`, `magic-number` on the
repeated search bound `5`, `nested-loops`) match this project's "investigate and
disclose" precedent.

**Testing**: 31 new `backend/app/tests/test_loop_statement.py` tests (tokenizer; parser
— labeled/unlabeled forms, mismatched/stray end-labels as `ParserError`, nesting LOOP
inside IF/WHILE/CASE and vice versa, LOOP inside LOOP; interpreter — basic unlabeled
LEAVE, the `loop`/`branch`-field shapes, unlabeled-only-breaks-innermost, the flagship
labeled-LEAVE-crosses-two-loop-levels case, same label reused across independent
sibling loops, LEAVE-outside-any-loop and LEAVE-with-no-matching-label as
`InterpreterError`s, the `MAX_LOOP_ITERATIONS` guard reused via `monkeypatch`, RETURN
inside a LOOP stopping the whole function rather than just the loop, both loop-stack-
isolation-across-CALL directions) plus 16 new `test_advisor.py`/3 new
`test_explainer.py` regression tests. Full backend suite: **390 passing** (343 before
this phase + 31 + 16 + 3 new; two **pre-existing** test fixtures had to be renamed —
`test_call_statement.py`/`test_function_call_expression.py` each used a
procedure/function literally named `Loop`, which now collides case-insensitively with
the new `LOOP` keyword; renamed to `Recur`, an expected breaking change from reserving a
new keyword, not a regression).

**Verified beyond pytest, at every layer**: (1) an in-process Python sweep script ran
all 17 real samples (via a Node script that imports `samples.js` directly) through the
actual tokenizer→parser→interpreter→advisor pipeline at once — zero pipeline
exceptions, every sample with a `testCaseExpectations.js` entry matched exactly; (2) a
second Node sweep fed every sample's real AST+trace through the actual `cfg.js` —
`buildFlowchartGraph`/`computeDiagramState`/`renderMermaidDefinition` — stepping through
EVERY step of EVERY sample in BOTH themes: zero crashes, `FindPairSum` correctly
produced 2 LOOP nodes and 3 leave edges; (3) live in an actual headless Chrome (raw-CDP
driver, no puppeteer-core/playwright available in this environment — hit and fixed a
real snag: the throwaway static-file-server's naive `startsWith('/debug')` API-route
check also swallowed the frontend's own `/debugger` route, 404ing the whole SPA before
it could mount — fixed to an exact-or-slash-prefixed match) against a throwaway
backend+static-proxy: loaded `FindPairSum`, clicked Debug (Step 1 of 58, Advisor showing
the predicted `foundI`-never-read finding), clicked Continue (jumped straight to Step 58
of 58), final variables matched the hand-derivation exactly, Call Stack correctly showed
a single top-level `FindPairSum current` frame, Variable Timeline rendered all 5
variables with no crash, and the REAL rendered Mermaid SVG showed `outer: LOOP`/`inner:
LOOP`/`LEAVE;`/`LEAVE outer;` node text and `loop`/`leave` edge labels correctly, current
node correctly landing on the final `LEAVE outer;` step. Toggled to light theme: Advisor
panel re-rendered correctly, zero new console errors. Navigated to `/tests`: **16/16
passed** (1 skipped, `StaticAnalysisShowcase`, a pre-existing gap), `FindPairSum` shown
as `PASS · 58 steps`. **Zero console errors across the entire session.** `npm run
lint`/`npm run build` both clean (same 2 pre-existing warnings).

**Process hygiene**: port availability confirmed via `Get-NetTCPConnection` before
starting anything — port 8000 (the long-lingering PID every prior session's notes
mentioned) was confirmed genuinely gone this time, not assumed from a stale note; 8001/
5176/9336 confirmed free first. Every process launched (throwaway backend, static-proxy
server, headless Chrome) was tracked by its own specific PID and killed individually at
cleanup, confirmed via `Get-Process`/`Get-CimInstance` (~26 other `chrome.exe`
processes — the user's own real browser session — confirmed still running afterward,
untouched).

**Cleanup**: `backend/data/debug_history.db` had grown to 351 rows by the time live
verification finished (the table auto-rotates at 50 most-recent rows, so most of this
session's own churn had already self-evicted); deleted every row with `id > 94` via
direct SQL, confirmed the surviving max id (94) and row count (12) match the
established baseline.

**Mid-session addendum**: the user interjected to split `CLAUDE.md` (which had grown to
~3973 words, mostly per-feature narrative accumulated phase over phase) into a lean
orientation doc plus two new reference files — `docs/features.md` (per-feature design
rationale, one section per feature) and `docs/schema.md` (the `DebugStep` field
breakdown + performance-timing history table) — and to rewrite `HANDOFF.md` as a true
snapshot (status lines + uncommitted work + next steps + live gotchas only, no
session-by-session history or verification narrative, since `git log`/this file already
carry that). `CLAUDE.md` went from 3973 words to ~1220 (file maps/endpoints kept for
navigability, everything narrative moved out); `HANDOFF.md` went to ~440 words. Both new
docs files, and this restructuring itself, are part of this session's own uncommitted
work.

## 20. User-created tables: CREATE TABLE / INSERT / UPDATE / DELETE

**Date:** 2026-09-14 · **Not yet committed** (see `HANDOFF.md`)

**Prompt (verbatim):**

> Read CLAUDE.md and HANDOFF.md for context
>
> This is the SQL Stored Procedure & Function Debugger project. The tree should be clean. This is the final backend/interpreter phase before the redesign — it's deliberately the biggest one, since it changes the scope of the project (currently only a fixed products demo table exists).
>
> Implement user-created tables + CRUD (INSERT/UPDATE/DELETE).
>
> Scope:
>
> Parser: CREATE TABLE name (col type [constraints], ...), INSERT INTO name (...) VALUES (...), UPDATE name SET ... [WHERE ...], DELETE FROM name [WHERE ...]. Check README.md/Theory.jsx first for exactly which column types and constraints this grammar already commits to elsewhere (don't invent new ones) — match the existing products table's type system if one is documented.
> Interpreter: maintain in-memory table state per debug session (scoped correctly — check whether products is currently global/shared across calls or reset per run, and follow that same convention for user tables rather than inventing new semantics). WHERE clause evaluation should reuse whatever expression-evaluation path conditions/IF already use, not a new one.
> Step-trace: table mutations (a row inserted/updated/deleted) need to be visible in DebugStep the same way variable mutations already are — check whether this needs a new field or can reuse an existing pattern, and flag if a schema change is genuinely required rather than force-fitting.
> Cross-cutting checks — same discipline as every prior phase, and expect more surface area than usual since this touches data, not just control flow:
> cfg.js flowchart — CREATE TABLE/INSERT/UPDATE/DELETE as flowchart nodes.
> advisor.py — do any existing checks (unreachable-code, unused-variable, never-read-variable, constant-condition) need a case for these new statement types? Consider whether a new check (e.g., INSERT/UPDATE with no WHERE on UPDATE/DELETE — a classic footgun) is worth adding, and note it as a suggestion rather than assuming scope.
> explainer.py template fallback cases.
> Predict Mode — does this fit, or is it another documented scope-exclusion like CASE/LOOP got?
> Variable Timeline — table state isn't a scalar variable; confirm it correctly excludes tables rather than crashing or rendering garbage for them.
>
> Add at least one new sample procedure exercising CREATE TABLE + INSERT + UPDATE + DELETE together, with hand-derived expected output (final table state, not just variables) cross-checked against a real interpreter run, documented inline in testCaseExpectations.js.
>
> Full verification: backend pytest suite, lint/build, the in-process sweep across all samples (Python pipeline + Node cfg.js, per last phase), and live check both themes with zero console errors — Call Stack, Variable Timeline, Advisor, Test-Case Runner, flowchart all confirmed against the new sample. Check port usage before binding, leave pre-existing processes alone, kill only what you launch by exact PID.

**Design decisions made before implementing**: README.md/`app.parser`'s own docstring
confirmed this grammar has never validated a `DECLARE`/parameter's `TYPE` against a
fixed set at all (it's a bare, unchecked identifier throughout) — so a column's `TYPE`
gets the exact same "advisory, unenforced" treatment, rather than inventing a new type
system just for tables. `products` (`demo_db.py`) was checked directly, not assumed: its
underlying SQLite connection is a fresh `:memory:` DB every run (reset per run) but is
NEVER saved/swapped around a `CALL`/function-call frame (global for the whole call
chain) — `Interpreter.tables` follows that exact convention. WHERE evaluation reuses
`_evaluate` verbatim via a new `_evaluate_with_row` helper (temporarily layers a row's
columns on top of `self.scope`, restored in a `finally`) rather than a second
expression-evaluator, per the phase's own explicit instruction. Constraints were scoped
to `NOT NULL`/`PRIMARY KEY` only (not `UNIQUE`/`FOREIGN KEY`/`CHECK`, and no `AND`/`OR` in
WHERE) — enough to demonstrate real constraint enforcement without inventing grammar the
task never asked for.

**Parser**: `_is_definition_start` replaces a bare `_check("KEYWORD", "CREATE")` at the
top-level `parse()` dispatch, since a leading `CREATE` is no longer unambiguously "start
of a CREATE PROCEDURE/FUNCTION definition chain" now that `CREATE TABLE` exists as an
ordinary statement — only `CREATE PROCEDURE`/`CREATE FUNCTION` specifically still routes
there; a bare `CREATE TABLE` falls through to the ordinary statement grammar. A stray
`CREATE TABLE` immediately after an already-started definition chain is still a clear
`ParserError` (not silently dropped) — caught by keeping the *continuation* check inside
that loop unconditional, exactly as it always was. This forced one test-expectation
update (`test_parser.py`'s "CREATE with neither FUNCTION nor PROCEDURE" example used a
bare `CREATE TABLE ...;`, which is now genuinely valid syntax — rewritten to demonstrate
both the new valid case and the real remaining error case). Four new statement types,
plus a new `NullLiteral` expression (most useful as an explicit INSERT value).

**Interpreter**: `_exec_insert`/`_exec_update`/`_exec_delete` all funnel constraint
checking through one shared `_validate_row_constraints` (INSERT's brand-new row and
UPDATE's prospective new row both go through it, UPDATE passing `ignore_row` so a
PRIMARY KEY column rewritten to its own existing value isn't flagged as a duplicate of
itself). UPDATE evaluates every matched row's SET expressions against that row's
ORIGINAL values (standard SQL semantics — `SET a = b, b = a;` swaps rather than
cascading), and constraint-checks every planned change BEFORE writing any of them, so a
violation partway through leaves the table completely unmodified. DELETE removes rows by
`id()` identity, never structural equality, so two rows with identical values don't
cause a WHERE match on one to silently remove the other too.

**Step-trace**: a genuine new `table` DebugStep field, added only after checking (and
ruling out) every existing one first — see `docs/schema.md`/`docs/features.md` for the
reasoning. Carries a FULL current row snapshot on every touched step (not a diff),
mirroring `variables`' own always-current convention.

**Cross-cutting**: `cfg.js` needed `renderStatementHeader`/`renderExpr` cases only — no
`emitBlock` change, since none of the four statement types branch or loop, so they fall
straight into the existing plain-rect-node path. `advisor.py` needed `_statement_exprs`
cases (feeding every shared check — magic-number, unused-variable, never-read-variable,
missing-error-handling — for free) plus one genuinely new check, `missing-where-clause`
(an UPDATE/DELETE with no WHERE touches every row — flagged as a real, separate
suggestion-worthy check, per the phase's own "note it as a suggestion rather than
assuming scope" instruction, added as a full "warning"-severity check since it's a real
footgun, not just a style nit). `explainer.py` got template-fallback cases plus `table`
forwarded from both `_build_prompt` and `_build_ask_prompt`. Predict Mode: verified
(not assumed) that none of the four statement types change a scope variable or carry a
boolean branch, so they correctly, silently offer no prediction prompt — documented as
the same kind of deliberate scope exclusion CASE/LOOP/LEAVE already are. Variable
Timeline: verified live against the new sample (see below) that it needed zero changes —
built purely from `variables`, a table's rows live in the separate `table` field, so a
table-only procedure correctly renders its "This run never declared any variables" empty
state.

New sample **`ManageInventory`**: `CREATE TABLE inventory (id NUMBER PRIMARY KEY, item
TEXT NOT NULL, qty NUMBER, price NUMBER)`, 3 `INSERT`s, two independent `UPDATE`s
(restock qty<10, then discount price>12), one `DELETE ... WHERE id = 2` — hand-derived
final state (`{id:1,item:'Widget',qty:13,price:10}`, `{id:3,item:'Gizmo',qty:15,
price:13}`) cross-checked against a real interpreter run before being written into
`testCaseExpectations.js`, which gained an additive, optional `tables: {name: [row,
...]}` field (checked by a new `TestCaseRunner.jsx` helper, `findFinalTableState`,
against the LAST step whose own `table.name` matches — not just whatever the very last
step overall happens to be).

**Verification**: backend suite 391 → **440 passing** (49 new tests: `test_table_crud.py`
plus advisor/explainer regressions). `npm run lint`/`npm run build` clean (same 2
pre-existing warnings). In-process sweep of all 18 samples (Python tokenize→parse→run,
real `demo_db` connection) — zero failures, 0.155–0.927ms each. A second Node sweep
(`cfg.js`'s `buildFlowchartGraph`/`computeDiagramState`/`renderMermaidDefinition` against
every sample's real backend-produced AST/steps, both themes, every step index) — zero
failures; confirmed `ManageInventory` produces exactly the 4 new node kinds
(`CreateTableStatement`/`InsertStatement`/`UpdateStatement`/`DeleteStatement`) as plain
rect nodes.

**Live verification** hit a real, worth-recording snag: port 8000 showed `Bound` (not
`Listen`) under a leftover, non-listening system-Python process this session didn't
start — `curl` got connection refused. Per "leave pre-existing processes alone," did NOT
kill it: ran the throwaway backend on 8010 instead, temporarily repointed
`vite.config.js`'s proxy targets at 8010, and reverted that file byte-for-byte (`git
diff` confirmed empty) once verification finished. A raw-CDP driver (`fetch`+`WebSocket`,
no puppeteer-core/playwright available) drove headless Chrome: loaded `ManageInventory`,
clicked Debug, stepped through all 8 steps — the Tables panel's summary
(name/operation/rows-affected) and full row grid matched the hand-derivation EXACTLY at
every single step (CREATE: 0 rows; 3×INSERT building up Widget/Gadget/Gizmo; first
UPDATE: Widget→13, Gadget→5, Gizmo untouched, 2 rows affected; second UPDATE: Gadget
price→23, Gizmo price→13, Widget untouched, 2 rows affected; DELETE: exactly Widget(13,
10)/Gizmo(15,13) left, 1 row affected). Flowchart SVG rendered (`#flowchart-1`), Advisor
panel showed the expected magic-number findings, Variable Timeline showed its correct
empty state, and toggling Day/Night produced zero new console errors in either theme.
**Zero console errors across the entire session.**

**Cleanup**: 5 test rows this session's own live verification wrote to
`backend/data/debug_history.db` were deleted by id afterward, restored to the
established baseline (max id 94, 12 rows). Every process this session launched
(throwaway backend on 8010, Vite on 5173, headless Chrome with `--remote-debugging-port
9333`) was tracked and killed individually by its own exact PID; the pre-existing,
non-listening process holding port 8000 was left completely untouched, as instructed.

## 21. Testing infrastructure: golden traces, Hypothesis, hand-written grammar edge cases

**Date:** 2026-09-14 · **Not yet committed** (see `HANDOFF.md`)

**Prompt (verbatim):**

> This is the SQL Stored Procedure & Function Debugger project. Before starting, commit the current tree if there's uncommitted work, then work on a clean tree. This phase is testing infrastructure, not a feature — nothing here should change parser/interpreter/frontend behavior. If you find a real bug while writing these tests, stop, flag it clearly, and don't silently fix it as a side effect — report it separately from the testing work.
>
> Four things, in this order:
>
> 1. Golden-output regression harness (do this first — cheapest, highest immediate value)
> Formalize the in-process sweep pattern already used in recent phases (Python pipeline + Node cfg.js) into a proper automated regression check: run every sample in samples.js through /debug, save the current step-trace output as a versioned "golden" fixture per sample, and add a test that fails loudly with a diff if any future change alters a sample's trace output. Wire it so it runs as part of the existing pytest suite, not a separate manual script. This is the safety net every future phase should run against.
>
> 2. Property-based testing with Hypothesis (Python)
> Add Hypothesis-based tests targeting the parser/interpreter. Start with two invariants: (a) the interpreter never crashes with an uncaught exception on malformed input — it should always return a structured error, never a stack trace to the user; (b) step-trace length is always ≥ 1 for any successfully parsed procedure. Build this by mutating tokens/values in the existing 17+ sample procedures (swap keywords, corrupt literals, drop semicolons, unbalanced BEGIN/END) rather than generating SQL from scratch — much higher signal-to-effort ratio for this grammar. Report (don't fix) any crash Hypothesis finds; let me decide whether it's worth a follow-up phase.
>
> 3. Grammar edge cases by hand
> Add explicit test cases for: nested cursors, deeply nested loops (check against the existing MAX_LOOP_ITERATIONS/MAX_CALL_DEPTH guards), empty procedure bodies, comments inside SQL string literals, missing semicolons, mismatched BEGIN/END, and a large-loop-count timing check against the 2s NFR (measure for real, like the /debug endpoint timing was measured before — don't assume).

**Tree check**: `git status` was already clean (previous session's "Implemented
User-created tables" was already committed as HEAD) — no commit was needed before
starting.

**1. Golden-trace harness.** `backend/app/tests/_frontend_samples.py` (new, not itself a
test module) loads the real `SAMPLES` array out of `frontend/src/samples.js` via a
precise regex extraction — deliberately not a full JS parse (no Node dependency at
pytest time), safe specifically because `code:` is a stable one-per-entry anchor and
this grammar's own tokenizer never produces a literal backtick, so the first backtick
after `` code: ` `` is always that entry's own closing one regardless of backticks
elsewhere in the same entry's `description` (verified: two real descriptions,
`ProductPriceTotal`'s and `ComputeTax`'s, genuinely contain backticks, and both still
extracted correctly). `test_golden_traces.py` posts each of the 18 real samples to the
REAL `/debug` endpoint (`TestClient`, not a bare interpreter call) and diffs the
resulting `steps` against a checked-in fixture at `backend/app/tests/golden/<name>.json`
— a missing fixture is a hard failure by design (never silently auto-created, so a new
future sample can't slip in without a reviewed baseline), and `UPDATE_GOLDENS=1` is the
one explicit, opt-in path to write/regenerate one. A second test
(`test_every_sample_has_exactly_one_golden_fixture`) catches the inverse staleness case
(a fixture left behind for a renamed/removed sample). Verified the harness actually
catches real divergences, not just trivially passing, by deliberately corrupting a
fixture value (`CalculateTotal`'s final `total`) and confirming a specific, step-numbered
failure message naming the exact expected/actual JSON — then restored it via
`UPDATE_GOLDENS=1`. All 18 fixtures generated fresh against this project's current,
unmodified pipeline (this phase changes no parser/interpreter/frontend behavior, so
"current" and "correct" are the same baseline here).

**2. Property-based testing (Hypothesis).** Added `hypothesis==6.168.0` to
`requirements.txt` (pinned, matching this project's exact-pin convention) and
`.hypothesis/` to `backend/.gitignore`. `test_property_based.py` mutates the same 18 real
samples (not from-scratch SQL generation, per the prompt's own explicit "much higher
signal-to-effort ratio" instruction) via seven pure, index-parameterized operators —
drop a semicolon, swap a keyword, corrupt a numeric literal, unbalance a BEGIN/END,
delete/duplicate a character, or truncate the source — each degrading gracefully to "no
change" when there's nothing of the relevant shape to mutate, composed via one
`@st.composite` strategy. Two invariants, `@given`+`@settings(max_examples=1000,
deadline=None)` each (deadline disabled since a mutated WHILE/LOOP can legitimately spin
up to the real `MAX_LOOP_ITERATIONS`): (a) tokenize→parse→run either succeeds or raises
one of exactly the three structured error types `app/main.py`'s own `/debug` handler
already catches (`TokenizerError`/`ParserError`/`InterpreterError`) -- anything else is
flagged as a crash; (b) a successful run's step count is >= 1, with one EXPLICIT,
hand-verified carve-out for a bare empty-body procedure (see finding #2 below and
`test_grammar_edge_cases.py`), so the invariant isn't spuriously falsified by
already-understood behavior on the very first truncated example.

**Found a real, previously-unknown bug** (reported per the prompt's own explicit
instruction, not fixed): an exploratory 20,000-iteration direct fuzz run (outside the
checked-in `@given` budget, just to hunt harder before finalizing) surfaced one genuine
crash out of 20,000 mutations — a `swap_keyword` mutation on `RecursiveFactorial` (`SET`
-> `RETURN` inside the recursive branch) eventually propagated an unset `None` OUT
parameter two call-levels up into an UNMUTATED `SET result = n * sub;`, raising Python's
raw `TypeError: unsupported operand type(s) for *: 'NoneType' and 'int'`. Reduced BY
HAND to a minimal, entirely un-mutated 2-line repro with no CALL/recursion/mutation
needed at all (`DECLARE x NUMBER; SET x = x * 2;` — a DECLAREd variable with no DEFAULT
starts at `None`, and `Interpreter._evaluate_binary`'s `+ - * /` never guard against
that), then confirmed directly against the REAL `/debug` endpoint: a raw **500 Internal
Server Error**, not this app's own `{"stage", "message", "line"}` structured error
contract every other failure mode holds. Tracked as a minimal, `xfail(strict=True)`
regression in the new `test_known_bugs.py` (so a future fix flips it loudly, not
silently) rather than fixed here, and the general Hypothesis test narrowly excludes only
this EXACT message shape (a regex on `"unsupported operand type(s) for [+-*/]: ...
NoneType"`, not "every TypeError") so the broad fuzz test keeps doing its real job of
surfacing genuinely NEW crashes instead of permanently re-reporting this one already-
known root cause on every run. Full write-up in this phase's own report to the user and
`HANDOFF.md`'s new "Bugs found this session, NOT fixed" section.

**3. Hand-written grammar edge cases.** `test_grammar_edge_cases.py` (22 tests), every
number/behavior confirmed by actually running it first, not assumed:
- **Nested cursors**: an inner cursor's full OPEN/FETCH-loop/CLOSE cycle nested inside
  each pass of an outer cursor's own loop (genuinely both open at once at points during
  the run, not just declared in the same procedure) -- hand-derived against the fixed
  `products` table (outer_total=50, inner_total=120 -- the inner WHERE price>10 subset
  summed fresh on all 3 outer passes) and cross-checked against a real run; plus a
  dedicated test confirming CLOSE-then-reOPEN genuinely resets FETCH position rather than
  resuming.
- **Deeply nested loops vs. the REAL guards** (not monkeypatched-small ones, unlike
  `test_loop_statement.py`'s own guard tests): 50 levels of individually-labeled nested
  LOOPs with one `LEAVE lvl0;` fired from the innermost, confirming the unwind-until-
  caught mechanism scales past the 2-3 levels every other LOOP/LEAVE test uses; the real
  `MAX_LOOP_ITERATIONS` (10,000, via a genuinely infinite `WHILE 1 = 1 DO` -- this grammar
  has no `>=`) and the real `MAX_CALL_DEPTH` (50, via unbounded self-recursion) both
  confirmed to raise a clean `InterpreterError`, never a Python `RecursionError`.
- **Empty procedure bodies** -- a second real, hand-verified finding (not a crash,
  flagged separately, not fixed): a bare/wrapper-less procedure with a genuinely empty
  body (blank or whitespace-only source) parses and runs successfully with a
  **zero-length** step trace, unlike a wrapped `CREATE PROCEDURE ... BEGIN END`'s empty
  body, which still gets its own synthetic entry step (length 1) -- confirmed directly
  against the real endpoint (`POST /debug` with `code: ""` returns `200 {"steps": []}`)
  before being written down, and is exactly the carve-out invariant (b) above needed.
  An empty FUNCTION body still correctly raises "completed without executing a RETURN".
- **Comments inside SQL string literals** -- this grammar has no comment syntax at all,
  so these confirm comment-LOOKING text inside an ordinary STRING literal is never
  mistaken for a real one: both as a plain DECLARE value, and (the more interesting case)
  inside a cursor's embedded SELECT's own WHERE clause, round-tripped through
  `_render_raw_query` and handed to a REAL SQLite connection (which DOES understand `--`
  as a genuine comment outside of a string) -- confirmed the FETCH still finds the
  correct real row rather than SQLite silently truncating the query at the embedded `--`.
- **Missing semicolons** / **mismatched BEGIN/END**: parametrized tests across DECLARE/
  SET/IF/WHILE/CREATE TABLE/INSERT and missing-END/missing-BEGIN/END-WHILE-for-an-IF/
  END-IF-for-a-WHILE/mismatched-LOOP-label -- all confirmed to raise a clean `ParserError`
  (never a crash) before being asserted.
- **Large-loop-count timing, measured for real** (not assumed): a 9,999-iteration WHILE
  loop (one under the real `MAX_LOOP_ITERATIONS` cap) through the REAL `/debug` endpoint
  -- HTTP + JSON serialization + `history.save_run` included, not just the bare
  interpreter call -- produces a 20,001-step trace (1 entry + 1 DECLARE + 10,000
  condition-checks + 9,999 SET-body-runs, confirmed by direct count, not guessed) and
  measured at **~617ms** wall-clock, logged in `docs/schema.md`'s own performance table
  per this project's "re-time and log" convention; the checked-in test asserts a looser
  1.8s ceiling (not the exact number) so ordinary machine variance doesn't make it
  flaky, while still meaningfully guarding the real 2s NFR at a scale (300-1000x) no
  hand-written sample reaches on its own.

**Verification**: backend suite 440 -> **483 passing + 1 xfailed** (+44 new tests across
the four new test files: 19 golden-trace + 2 property-based + 1 known-bug + 22 grammar-
edge-case). Full suite runtime ~18-19s (was ~10s before this session -- the added
Hypothesis budget, 2000 total examples across both invariants, accounts for essentially
all of the increase; still fast enough to run on every phase going forward). No parser/
interpreter/frontend source file was touched this session, confirmed by `git status`
listing only test files, `requirements.txt`, `.gitignore`, and docs (`CLAUDE.md`/
`HANDOFF.md`/`docs/schema.md`/`PROMPT_LOG.md`) -- exactly this phase's own "nothing here
should change parser/interpreter/frontend behavior" scope, honored literally, not just in
spirit. `backend/data/debug_history.db` picked up a handful of stray rows from this
session's own ad-hoc, outside-pytest hand-verification scripts (which aren't covered by
`conftest.py`'s per-test DB isolation, since that only applies inside a pytest session)
-- cleaned up back to the established baseline (max id 94, 12 rows) afterward. No live
browser verification was needed or performed this session (no frontend changes at all).

---

## 22. Bug-fix phase: the two bugs the testing-infrastructure session found and did not fix

**Date:** 2026-09-17 · **Not yet committed** (see `HANDOFF.md`)

**Prompt (verbatim):**

> This is the SQL Stored Procedure & Function Debugger project. The tree should be clean. This is a bug-fix phase, not a feature phase — the golden-output regression harness, Hypothesis tests, and grammar edge-case tests from the last phase are your safety net; run the full suite before and after, and the golden traces for all 18 existing samples must not change unless you can explain exactly why.
>
> Fix two bugs found and documented in `test_known_bugs.py` / `HANDOFF.md`:
>
> **1. `None`-arithmetic crash (the real bug — fix properly)**
> `DECLARE x NUMBER; SET x = x * 2;` (or any `+ - * /` where an operand is `None`) crashes with a raw, unstructured 500 instead of this app's structured error contract. In `Interpreter._evaluate_binary`, guard against `None` operands on `+ - * /` and raise the same structured error type/shape every other runtime error already uses (check an existing case like DIVISION_BY_ZERO for the exact convention — error code, message format, whatever step-trace field carries it — and match it exactly, don't invent a new error shape). Decide and document what the error should say in a way a first-time user would understand (e.g. "variable used before being assigned a value") rather than a generic type error.
> - Un-xfail `test_known_bugs.py`'s test for this once fixed — it should now pass for real, not just stop failing.
> - Add regression tests: the exact repro above, plus each of `+ - *` on a `None` operand individually, and confirm `/` still correctly reports DIVISION_BY_ZERO before this fix would even trigger (i.e. don't let the new guard mask a different existing error).
>
> **2. Empty-body zero-length trace inconsistency**
> A bare (wrapper-less) empty procedure body (`POST /debug` with `code: ""`) returns `{"steps": []}`, while a wrapped `CREATE PROCEDURE ... BEGIN END`'s empty body gets a synthetic entry step. Make the bare case consistent with the wrapped case — same synthetic entry-step behavior — rather than picking a new third behavior. Check whether the frontend ever actually hits this path (search for any place assuming `steps[0]` exists) and note what you find, but fix the backend regardless since it's a real inconsistency in the contract.
> - Add a regression test covering both the bare-empty and wrapped-empty cases producing the same shape.
>
> Full verification: full backend suite passes (golden traces, property-based, grammar edge cases, existing unit/endpoint tests) with the two bug fixes and their new regression tests, zero unrelated files touched, lint/build clean if any frontend file needed a change for #2. Update `HANDOFF.md`'s "Bugs found this session, NOT fixed" section to move these two into "fixed this session" with a one-line note each.

**Tree check**: `git status` was already clean (previous session's testing-infrastructure
work was already committed as `774dd05`) — no commit was needed before starting.
Baseline run confirmed first: 483 passing + 1 xfailed.

**1. `None`-arithmetic crash — fixed.** Traced the exact convention DIVISION_BY_ZERO
already uses (`app/main.py`'s `/debug` handler: `except InterpreterError as exc: raise
_error_response("interpret", str(exc), exc.line)`, giving the client a 400 with
`{"stage": "interpret", "message", "line"}` — nothing in `interpreter.py` catches
`InterpreterError` internally before it reaches that handler, so simply raising one from
`_evaluate_binary` slots straight into the existing contract with zero new plumbing).
Added a `None`-operand guard to `+ - * /` only (confirmed comparisons don't need one —
`None == 2` is simply `False` in Python, never a `TypeError`), placed *before* the `/`
branch's own `right == 0` check so a genuinely-zero (not `None`) divisor still raises the
pre-existing DIVISION_BY_ZERO error untouched — verified with a dedicated regression test
(`test_division_by_zero_still_wins_over_the_none_guard_when_both_apply`) that the new
guard cannot mask it. Message written for a first-time user, not a Python type-error
echo: `"Cannot use '*': a variable used in this expression has no value yet -- it was
declared but never assigned (or is an OUT parameter never SET on this code path)"`.
`test_known_bugs.py`'s original regression test had its `xfail` removed and now asserts
the fix positively (`result["status"] == "known_error"`, not just "not a crash"); added
four more regression tests to `test_interpreter.py` (each of `+ - * /` individually via
`@pytest.mark.parametrize`, the division-by-zero-still-wins case above, and a real
`TestClient` hit against the actual `/debug` endpoint confirming 400 with the expected
`stage`/`message`, not a raw 500) — matching the original bug report's own verification
method, not just the interpreter in isolation.

**2. Empty-body zero-length trace inconsistency — fixed.** Root cause: a bare/legacy
`Procedure` AST node (`{"type": "Procedure", "body": [...]}`) has no `"line"` key and no
CREATE-header line to give an entry step to at all (unlike `ProcedureNode`/
`FunctionNode`, which get one from `render_definition_header` in `Interpreter.run`) — so
when its body was ALSO completely empty, nothing ever got recorded, and `self.steps`
stayed `[]`. Fixed narrowly: `Interpreter.run` now checks specifically for `entry_node is
None and not body` (the bare form AND a genuinely empty body — a bare body with even one
statement is completely untouched by this change) and records one synthetic placeholder
step (`nodeType: "Procedure"`, line `1` since there's no real source line to point at,
statement text `"(empty procedure body)"`), giving it the same "always >= 1 step" shape a
wrapped empty body already had. Checked the frontend per the prompt's own instruction
before touching anything there: `DebuggerPage.jsx` already gates every steps-dependent
render behind `hasSteps = Array.isArray(steps) && steps.length > 0` (falling back to a
plain "No steps yet" label otherwise) — confirmed this was never a live crash risk, so no
frontend file needed changing. Rewrote `test_grammar_edge_cases.py`'s now-outdated
"produces zero steps" test to assert the new "produces exactly one synthetic step"
behavior instead, and added a new `test_bare_and_wrapped_empty_bodies_now_produce_the_
same_shape` regression test asserting both forms produce the same step count for an
empty body.

**Test-suite cleanup for consistency.** Since both of `test_property_based.py`'s
documented invariant carve-outs (the None-arithmetic-crash exclusion in invariant (a),
the bare-empty-body zero-step exception in invariant (b)) were exactly the two bugs just
fixed, removed both special-case exclusions from that file rather than leaving now-dead
carve-out logic in a test suite that's supposed to be the project's regression safety
net — both invariants now hold completely unconditionally, and the module docstring was
rewritten to describe this as history (what used to be excluded, and why it no longer
needs to be) rather than silently deleting the context. `test_known_bugs.py` itself was
kept (per this project's own convention for tracking a bug found while testing something
else) but its docstring rewritten to record both bugs as FIXED, pointing at where their
now-permanent regression coverage lives.

**Verification**: full backend suite 483 passing + 1 xfailed -> **491 passing, 0
xfailed** (net +7 across the fix's regression coverage: the un-xfailed test stays 1, plus
4 new tests in `test_interpreter.py`, plus 1 new test in `test_grammar_edge_cases.py`,
plus the removed carve-out logic collapsing two property-based test *names* into
differently-named ones with no count change there). Golden-trace harness re-run in
isolation and confirmed **byte-for-byte unchanged, all 19 tests still passing** — neither
fix's trigger condition (arithmetic on a `None` operand; a genuinely empty procedure
body) occurs in any of the 18 built-in samples, so this is a real, verified "no
unintended behavior change" result, not an assumption. `git status --short` confirmed
only `backend/app/interpreter.py` plus four test files touched — zero frontend files, so
no lint/build step was needed for this session (the prompt's own "if any frontend file
needed a change for #2" conditional never triggered, confirmed above). `HANDOFF.md`
rewritten: both bugs moved from "NOT fixed" into a new "Bugs fixed this session" section,
each with a one-line note on what changed and where its regression tests live; the
"Immediate next steps" list had the now-resolved "decide whether to fix bug #1" item
removed.

## 23. Persistent user database + standalone SQL Console

**Date:** 2026-09-17 · **Not yet committed** (see `HANDOFF.md`)

**Prompt (verbatim):**

> Add a real, persistent SQLite database that user data lives in (replacing
> the current hardcoded demo `products` table), plus a standalone SQL
> console page for running arbitrary SQL outside of any procedure.
>
> Backend:
> - Set up a separate SQLite database file (distinct from whatever SQLite
>   file/table already backs app persistence — don't mix app tables with
>   user data tables) that persists across requests, not per-request/in-memory.
> - New endpoint: POST /sql/execute, takes { sql: string }, executes it
>   as-is against that database using the SQLite driver directly (not
>   through this project's own parser/interpreter — this is raw passthrough).
> - Response: for SELECT, return column names + rows. For
>   INSERT/UPDATE/DELETE/CREATE/DROP/ALTER, return rows-affected (or
>   success) and a brief description of what ran. Return SQL errors from
>   SQLite as a clean error message, not a stack trace.
> - Seed the new database with the existing `products(name, price)` table
>   and its 3 rows on first run, so the ProductPriceTotal and
>   SafeAverageWithHandlers cursor samples keep working unchanged.
> - Update the cursor-handling code path (OPEN/FETCH) to query this same
>   persistent database instead of the old fixed in-memory demo table --
>   cursors and the SQL console should now share one source of truth.
>
> Frontend:
> - New page/route: SQL Console. Monaco editor for input (reuse existing
>   Monaco setup/theme), an Execute button, and a results area: a table
>   for SELECT results, a short status line for writes, an error panel
>   styled consistently with existing error displays elsewhere in the app.
> - Add it to nav. Theme-aware (day/night mode), matches existing
>   "Debugger Notebook" visual system (dark navy, IBM Plex Mono/Space
>   Grotesk, amber/teal/coral accents).
> - Keep it a separate page from the procedure debugger — this is not a
>   step-through trace, just run-and-see-result.
>
> Verify: existing backend test suite still fully passing (no regressions
> to cursor behavior), new tests for /sql/execute covering SELECT, INSERT,
> UPDATE, DELETE, CREATE TABLE, and a deliberate SQL error. Live-check the
> console page in both themes and confirm ProductPriceTotal/
> SafeAverageWithHandlers samples still run correctly against the new
> persistent DB. Confirm /debug and /sql/execute both comfortably clear
> the 2s NFR.

**New backend module: `app/user_db.py`.** `get_connection()` opens
`backend/data/user_data.db` (a real on-disk file, sibling to but never mixed with
`history.py`'s `debug_history.db`), seeding `products(name, price)` — the exact same 3
rows as the old `demo_db.py` — the first time the table doesn't already exist
(`_ensure_seed_data`, checked via `sqlite_master` rather than an unconditional `CREATE
TABLE IF NOT EXISTS` + insert, so re-seeding never clobbers a user's own edits/deletes
through the console; a `DROP TABLE products` does legitimately re-trigger seeding on the
next open, which reads as correct "bootstrap" behavior rather than a bug). A short-lived
connection is opened per call, same convention `history.py` already uses (sqlite3
connections aren't safe to share across FastAPI's sync-handler threads).

`app/demo_db.py` was deliberately left alone rather than deleted: several existing tests
(`test_grammar_edge_cases.py`, `test_property_based.py`) call
`demo_db.create_demo_connection()` directly to get a cheap, deterministic, disk-free
seeded connection for interpreter-level unit tests, decoupled from `app.main`'s actual
request path — that's still a legitimate use. Its docstring was rewritten to say plainly
that it's no longer wired into `/debug` and point at `user_db.py` instead.

**New backend module: `app/sql_console.py`.** `execute_sql(sql)` backs the new endpoint:
opens `user_db.get_connection()`, runs the statement through `cursor.execute()` (NOT
`app.tokenizer`/`app.parser`/`app.interpreter` — genuinely raw passthrough), and branches
the response shape on `cursor.description is not None` (SQLite's own signal for "this
statement produces rows") rather than trying to keyword-sniff SELECT vs. everything else
— covers PRAGMA and any other row-producing statement for free, and can never
misclassify in a way that breaks execution (only the human-readable `description` string
depends on keyword-sniffing, via `_first_keyword`, which skips leading `--`/`/* */`
comments). A `sqlite3.Error` (bad table, syntax error, running two statements in one
`execute()` call, ...) is caught and re-raised as `SqlExecutionError(str(exc))` — SQLite's
own error text is already a clean one-liner ("no such table: foo", "near \"SELEKT\":
syntax error"), so no message-rewriting was needed; `main.py` surfaces it as a 400.

**`app/main.py` changes.** Swapped `demo_db.create_demo_connection()` for
`user_db.get_connection()` in the `/debug` handler (one line — `interpreter.run()` already
accepted any `sqlite3.Connection` via its `db_connection` param, so no interpreter change
was needed for this half of the prompt). Added `POST /sql/execute`
(`SqlExecuteRequest{sql: str}` -> `execute_sql`, `SqlExecutionError` -> 400).

**Test isolation.** `conftest.py` gained an autouse `_isolated_user_db` fixture,
monkeypatching `user_db.DB_PATH` to a per-test `tmp_path` file — exact same shape as the
pre-existing `_isolated_history_db` fixture, for the same reason (the suite must never
touch the real `backend/data/user_data.db` a developer might be using locally, now that
both `/debug` cursor runs and `/sql/execute` have real on-disk side effects).

**New tests.** `test_user_db.py` (seeding on first open, persistence across separate
`get_connection()` calls, no re-seed after a user DELETEs rows, re-seed after a DROP).
`test_sql_console.py` (unit tests directly on `execute_sql` — SELECT with/without rows,
CREATE TABLE, INSERT/UPDATE/DELETE rows-affected counts, writes persisting across calls,
a SQL syntax error, a missing-table error, empty SQL, and multiple statements in one
call). `test_sql_endpoint.py` (the same SELECT/INSERT/UPDATE/DELETE/CREATE TABLE/error
coverage through the real `TestClient`-driven `POST /sql/execute`, plus one round-trip
test proving the console and a cursor's OPEN/FETCH share one source of truth: INSERT a
row via `/sql/execute`, then run a cursor-based procedure through `/debug` that sums
exactly that row). Also fixed one now-stale comment in `test_debug_endpoint.py` that
still referenced `app/demo_db.py` for the endpoint's own seeding.

**Frontend: `pages/SqlConsolePage.jsx`, route `/sql-console`.** A Monaco editor (reusing
the Debugger's exact options/fontFamily and `theme === 'light' ? 'vs' : 'vs-dark'`
pattern) plus an Execute button (also bound to Ctrl/Cmd+Enter via
`editor.addCommand`), and a results panel that renders one of three states: a
`.cursor-table` for SELECT rows (reusing the Debugger's own cursor/table styling
wholesale rather than a new table component), a `.status.status-ok` line for a write's
`description`, or a `.error-banner.error-banner-unhandled` for a `SqlExecutionError` —
the exact same coral error styling every other error display in the app already uses.
Added to `App.jsx`'s routes and `Layout.jsx`'s nav (between Compare and Quiz). A few
console-specific CSS rules (`.sql-console-actions`, `.sql-console-hint`,
`.sql-console-table-scroll`) added to `App.css` right before the existing SQL
Anti-Pattern Advisor section, matching that section's own "reuse first, add only what's
missing" comment style.

**`vite.config.js`.** Added a `/sql` proxy entry with the same `bypassNavigations` guard
every other entry already needs — `/sql` (the API prefix for `/sql/execute`) is a
path-prefix match for the page's own `/sql-console` route, the identical collision
`/debug`/`/debugger` already has.

**Verification.** Backend suite: 491 passing -> **522 passing, 0 xfailed**, zero
regressions (ran the full suite, not just the new files). `npm run lint` clean (same two
pre-existing warnings as before, unrelated to this change) and `npm run build` clean.
Live-checked via a small dependency-free raw-CDP driver script (headless Chrome, no
puppeteer available) against an already-running dev backend+frontend (found both already
up and already serving the current code — used them directly rather than starting
redundant instances against the same `backend/data/*.db` files): SQL Console in dark
mode (default SELECT * FROM products renders its 3-row table correctly), a deliberate
`SELEKT * FROM products` syntax error renders the coral error banner correctly, toggled
to light mode and re-ran the same SELECT (Monaco and every panel re-themed correctly),
then navigated to the Debugger and ran both `ProductPriceTotal` (17 steps) and
`SafeAverageWithHandlers` (19 steps) to completion against the new persistent database.
Timing: `POST /sql/execute` ~13ms, `POST /debug` (cursor sample) ~24ms live via curl,
both comfortably under the 2s NFR. Cleaned up the 4 history rows this verification
session's browser-driven sample runs added to the real, already-running backend's
`debug_history.db` (`DELETE /history/{id}` for ids 446-449), confirmed `/history`'s top
entry is back to the pre-session state; confirmed the real `user_data.db` still has
exactly the one seeded `products` table (all CREATE/INSERT/UPDATE/DELETE test coverage
ran through pytest's isolated `tmp_path` DB instead, never against the real file).
`HANDOFF.md` rewritten with this session's status; `CLAUDE.md` §2 updated (new shipped-
feature bullet, backend/frontend file maps, endpoint list, the "SQLite has two unrelated
jobs" bullet rewritten to three); `docs/features.md` gained a new "Persistent user
database + SQL Console" section.

## 24. Merge Debugger + SQL Console pages; SQL passthrough statements inside procedures

**Date:** 2026-09-17 · **Not yet committed** (see `HANDOFF.md`)

**Prompt (verbatim):**

> Merge the Debugger page and the SQL Console page into a single page/tab,
> labeled "SQL Console" in the nav (remove the separate "Debugger" and old
> "SQL Console" nav entries and routes).
>
> Detection logic on Run/Execute (single button, one Monaco editor):
> 1. Attempt to parse the input using the existing procedure/function
>    parser (same entry point /debug already uses — CREATE PROCEDURE/
>    FUNCTION wrapper or bare body).
> 2. If it parses successfully as a procedure/function: call /debug as
>    normal, render the existing full debugger UI beneath the editor
>    (step trace, breakpoints, call stack, control-flow flowchart, Ask AI,
>    anti-pattern advisor — everything currently on the Debugger page,
>    unchanged).
> 3. If it does NOT parse as a procedure, check whether it looks like
>    plain SQL (starts with CREATE, INSERT, UPDATE, DELETE, SELECT, DROP,
>    or ALTER, no BEGIN/END or DECLARE wrapper): call /sql/execute instead,
>    render the existing SQL Console results panel (table for SELECT,
>    status line for writes, error banner) in place of the debugger UI.
> 4. If it matches neither cleanly, show one clear error rather than
>    silently picking a path — don't guess.
>
> Then, per the existing Phase 2 scope (still needed, now inside this
> merged page): extend the procedure/function grammar so CREATE TABLE,
> INSERT, UPDATE, DELETE, and standalone SELECT are valid *inside* a
> procedure body too (raw-passthrough statement, same approach as the
> cursor's embedded SELECT — capture as text, execute directly against
> the persistent DB from Phase 1, no SQL parsing of your own). Add a new
> DebugStep type/shape for these statements (SQL keyword, rows affected,
> resulting table snapshot) and render it in the step panel. Update the
> DebugStep schema note in HANDOFF.md per existing convention (this is a
> central-contract change).
>
> Sample selector, Compare page links, and any other place that referenced
> the old Debugger route need updating to the merged route.
>
> Keep both underlying capabilities intact and independently testable —
> this is a UI/routing consolidation plus the grammar extension, not a
> rewrite of either execution path.
>
> Verify: full backend suite passing, new tests for the raw-SQL-in-
> procedure statement types (parsing + execution) and the new DebugStep
> shape, one new sample procedure combining CREATE TABLE + INSERT + UPDATE
> + a cursor SELECT to demonstrate the merged flow end-to-end. Frontend:
> lint/build clean, live-check both detection paths (a plain CREATE TABLE
> input, and a full procedure input) in both themes, confirm Compare page
> and sample selector still work after the route merge.

**Blocking ambiguity, resolved with the user before writing code.** CREATE TABLE/INSERT/
UPDATE/DELETE already existed as a simulated, in-memory-only feature from an earlier
phase (`Interpreter.tables`, its own `table` DebugStep field, its own Tables UI panel,
`ManageInventory` sample, its own tests/golden traces) — a different, already-shipped,
graded piece of work from what this prompt describes. The new spec wants the same five
keywords to be raw passthrough against the real persistent DB (`app.user_db`), which is
exactly what would close the interoperability gap the previous session's `HANDOFF.md`
flagged (a cursor's SELECT couldn't see a procedure's own CREATE TABLEd data) — but the
same keywords can't parse two different ways at once. Asked the user via `AskUserQuestion`
how the two should coexist: replace the simulated feature entirely (closes the actual
gap, matches "raw passthrough for all five" most literally, but retires already-graded
work), keep both side by side under a disambiguating marker (zero risk to existing work,
real added parser complexity, two ways to do the same thing), or only add the genuinely-
missing standalone SELECT (simplest, lowest-risk, but doesn't close the gap or match the
prompt's wording). User chose **replace** (recommended option). This decision shaped
everything that followed.

**Frontend merge.** `DebuggerPage.jsx` (~1550 lines, extensive existing functionality:
breakpoints, call stack, cursor/table panels, flowchart, explanations, Ask AI, Predict
Mode, report export) was edited in place — new `mode`/`sqlResult`/`sqlError` state, a
`looksLikePlainSql` heuristic helper, `handleDebug` rewritten into `handleRun`
implementing the three-way detection flow described above, the step-navigator/breakpoint-
hint/Predict-Mode/Live-State-panel-contents/Ask-AI-panel/Advisor-panel all wrapped in
`{mode !== 'sql' && (...)}` (falling back to a one-line "not applicable" placeholder in
the Live State column, and simply not rendering the other three panels, when
`mode === 'sql'`), and a new `{mode === 'sql' && (...)}` block rendering the exact SQL
Console results view (reusing `.cursor-table`/`.status.status-ok`/`.error-banner`
wholesale) in their place. The Run button (renamed from "Debug") and its Ctrl/Cmd+Enter
binding are the only pieces always visible regardless of `mode`. The file was then
renamed to `SqlConsolePage.jsx` (`mv`, after first deleting the OLD standalone
`SqlConsolePage.jsx` from the previous session — its results-panel JSX had already been
folded into the renamed file, not lost), component renamed to match, `App.jsx`'s
`/debugger` route replaced with `<Navigate to="/sql-console" replace />` (so an old
bookmark/link still works), `Layout.jsx`'s nav collapsed to one "SQL Console" entry,
`HistoryPage.jsx`/`HomePage.jsx` updated to target `/sql-console` directly instead of
`/debugger`. Internal CSS class names and the component's former identity
(`debugger-page`, `debugger-grid`, `panel-editor`, ...) were deliberately left unchanged
-- documented as a conscious choice, not an oversight, in the file's own new header
comment.

**A consequence of the grammar extension that changes what the detection heuristic
actually catches in practice, discovered and confirmed live rather than just reasoned
about**: since CREATE TABLE/INSERT/UPDATE/DELETE/SELECT are now ALSO valid bare-procedure-
body statements (see below), input starting with one of those five almost always parses
successfully at step 1 and lands in the full debugger UI (with its new `sql` step panel)
-- it essentially never reaches the plain-SQL heuristic/flat-results-panel path at all.
Verified directly: a bare `CREATE TABLE ...;` and a bare `SELECT ...;` both render the
debugger UI (1-step trace, `sql` panel showing the result); only a `DROP TABLE ...;`
(not part of the procedure grammar) renders the flat SQL Console panel. Documented this
prominently in code comments, `docs/features.md`, and `HANDOFF.md` rather than silently
shipping a heuristic that rarely fires without explaining why.

**Backend grammar/interpreter.** Replaced `CreateTableStatement`/`InsertStatement`/
`UpdateStatement`/`DeleteStatement` (4 node types, structured column-def/VALUES/SET/WHERE
expression parsing, `Interpreter.tables` Python-dict simulation, NOT NULL/PRIMARY KEY
enforcement written in this interpreter) with one new node type, `SqlStatement`
(`{type, keyword, sql, line}`), covering all four PLUS the genuinely new fifth case,
standalone SELECT. `app/parser.py`'s `_parse_sql_passthrough` captures tokens verbatim
from the leading keyword to the next top-level `;` and reassembles them via the exact
same `_render_raw_query` helper a cursor's embedded query already used -- deliberately
"no SQL parsing of our own," matching that precedent exactly rather than inventing a new
capture mechanism. `app/interpreter.py`'s `_exec_sql_statement` hands `node["sql"]`
straight to a NEW shared function, `app/sql_console.py`'s `execute_sql_on_connection`
(the previous session's `execute_sql` was refactored into a thin wrapper around this),
called against `self._db` -- the SAME connection a cursor's OPEN already uses, which is
the entire mechanism that makes the new interoperability demo possible. A
`sqlite3.Error`/`SqlExecutionError` becomes an ordinary `InterpreterError` at the
statement's line (same treatment a cursor query against a nonexistent table already got).
Added `extract_table_name(keyword, sql)` (a small per-keyword regex, not a real parse) to
`sql_console.py`, used by the new `sql.tableName`/`sql.snapshot` DebugStep fields (a
follow-up read-only `SELECT *` on the affected table) and reused by `app/advisor.py`'s
rewritten `_check_missing_where_clause`.

**Three real, deliberate capability losses versus the retired feature**, each tested and
documented rather than left as an implicit surprise: (1) no variable interpolation -- a
DECLAREd variable's name inside a passthrough statement means a literal SQL identifier
("no such column"), never a value substitution, since there's no expression parsing left
for VALUES/SET/WHERE to hook into; (2) no server-side NOT NULL/PRIMARY KEY enforcement --
real SQLite's own behavior is authoritative now, including its well-known quirk that a
non-INTEGER PRIMARY KEY column doesn't reject NULL by itself (verified directly, not
assumed); (3) a missing `;` no longer fails to PARSE (the old structured grammar caught it
immediately) -- it silently merges with the next statement and fails to INTERPRET instead
as a real SQLite syntax error. An existing `test_grammar_edge_cases.py` parametrized case
asserting the old behavior was removed and replaced with a new test asserting the new one,
with a comment explaining why.

**Ripple-through updates**, each checked for actual usages rather than assumed unaffected:
`app/advisor.py` (`_statement_exprs` lost its three retired cases entirely -- no
expression tree inside raw `sql` text, same scope boundary a cursor's own query already
had; `_check_select_star` gained a second case for standalone-SELECT `SqlStatement`).
`app/explainer.py` (four template-fallback cases and two prompt-builders collapsed to one
case plus a shared `_describe_sql_step` helper). `frontend/src/cfg.js` (four flowchart-
rendering cases collapsed to one, `renderColumnDef` helper deleted as now-unused).
`frontend/src/TestCaseRunner.jsx`'s `findFinalTableState` (reads `sql.tableName`/
`sql.kind`/`sql.snapshot`, zipping the new list-of-lists row shape back into the
column-keyed dicts `testCaseExpectations.js`'s existing format already used, so that
file's own expectation entries needed no reshaping, just a new one for the new sample).

**New sample, `InventoryValueReport`** (`frontend/src/samples.js`): CREATE TABLE + 3
INSERTs + 1 UPDATE (raw SQL) followed by a cursor that reads back those exact rows and
sums `qty * price` -- hand-traced (Widget 4->14, Gadget 2->12, Gizmo unchanged at 6;
14*10 + 12*25 + 6*15 = 530) and cross-checked against a real interpreter run. Uses
`CREATE TABLE IF NOT EXISTS`/`INSERT OR REPLACE INTO` specifically so it stays safely
re-runnable against the real, persistent database (a plain `CREATE TABLE`/`INSERT` would
fail with a real SQLite error on a second click, since the previous run's data is still
there for real now -- not simulated, not reset per-request). `ManageInventory` (the
previous session's demo of the now-retired simulated feature) migrated to the same
`IF NOT EXISTS`/`OR REPLACE` pattern for the same re-runnability reason; its actual data
and final row state (`Widget(13, 10)`, `Gizmo(15, 13)`) are unchanged, since its original
SQL was already valid, standard SQL the retired simulation's own semantics happened to
already match.

**Tests.** Deleted `test_table_crud.py` (tested the retired feature's structured grammar
and Python-simulation semantics, no longer applicable), replaced with
`test_sql_passthrough_statement.py`: parser tests (all five keywords produce the shared
node type, valid inside IF/WHILE, the missing-semicolon behavior change), interpreter
tests against a real `user_db.get_connection()` (write/rows step shapes, the cursor-sees-
raw-INSERT interop test, a clean-SQLite-error-becomes-InterpreterError test, the
no-interpolation and no-constraint-enforcement documentation tests, the `<=`
round-trip-caveat test), and two real-`/debug`-endpoint end-to-end tests. Updated
`test_advisor.py` (rewrote the now-false "magic-number sees inside INSERT" test into one
asserting the new, narrower boundary; added standalone-SELECT select-star coverage),
`test_explainer.py` (all `table`-field fixtures rebuilt as `sql`-field fixtures),
`test_report_endpoint.py` (asserts `SqlStatement`/raw SQL text instead of the retired
per-statement node-type names), `test_parser.py` (one updated assertion). Regenerated
golden fixtures (`UPDATE_GOLDENS=1 pytest`): `ManageInventory.json` changed (new
statement shape and `IF NOT EXISTS`/`OR REPLACE` text), new `InventoryValueReport.json`
added -- both diffs reviewed by hand before accepting. Backend suite: 505 passing (up
from 491), zero regressions.

**`HelpPage.jsx` (graded user manual) and `AboutPage.jsx` (grammar reference) rewritten**
in every section describing the Debugger page, the "Debug" button, cursor data source, or
supported grammar, to accurately describe the merged page, the "Run" button, the real
persistent database, and the new SQL passthrough statements. `AboutPage.jsx` also had a
genuinely pre-existing (not caused by this session) false claim corrected in passing,
since it was directly touched anyway: "table statements not supported at all" -- they
were, even before this session, via the now-retired simulation; `CALL`/`CASE`/`LOOP`/
`LEAVE` were also incorrectly listed there as unsupported. Did not attempt a full audit/
rewrite of `AboutPage.jsx`'s entire grammar reference beyond what this session's own
changes made newly or still inaccurate -- out of scope.

**Verification.** `npm run lint`/`npm run build` clean. Live-checked via the scratchpad's
raw-CDP driver against an already-running dev backend+frontend (found both already
serving current code, used directly): nav shows exactly one "SQL Console" entry (no
"Debugger"); navigating to `/debugger` redirects to `/sql-console`; a full procedure
(`CalculateTotal`, then a hand-written one combining CREATE TABLE/INSERT/UPDATE/cursor)
renders the debugger UI correctly in both dark and light mode, including the new `sql`
step panel (screenshotted mid-trace on the CREATE TABLE step, showing the table/keyword/
rows-affected/empty-snapshot correctly); a bare `CREATE TABLE`/`SELECT` input ALSO
correctly renders the debugger UI (confirming the "consequence" noted above is real, not
just reasoned about) with correct SQL step content; a `DROP TABLE` input correctly renders
the flat SQL Console results panel; input matching neither shows the combined clear error
naming both why it didn't parse and that it doesn't look like SQL; the Compare page still
runs two procedures side by side and reports "no divergence" correctly; the sample
selector still loads a sample's code into the editor correctly. Timing: `/debug` ~26-33ms,
`/sql/execute` ~13-25ms, both comfortably under the 2s NFR (up from sub-millisecond
pre-this-session for the interpreter path specifically, now doing real SQLite file I/O
per write instead of a pure Python dict mutation -- still 2-3 orders of magnitude under
budget, logged as a new `docs/schema.md` performance-table row per that file's own
convention). Cleaned up real history rows AND real stray tables (`inventory`, `stock`)
this session's own verification and an ad-hoc in-process benchmarking script (run outside
pytest, so not covered by `conftest.py`'s isolation) left in the real, already-running dev
backend's databases -- confirmed both back to baseline afterward, and noted the "measure
through pytest, not a bespoke script" lesson in `HANDOFF.md`'s gotchas.

`docs/schema.md` updated (the `sql` field's full shape, a note that it replaces `table`,
a new performance-table row + a corrected "no measurable overhead" claim). `docs/
features.md` gained a new "Merged Debugger/SQL Console page + SQL passthrough statements"
section (and a superseded-by note on the previous session's own section). `CLAUDE.md` §2
updated (shipped-features bullet rewritten, backend/frontend file maps, the "execution is
simulated" and "SQLite backs three things" bullets both corrected). `HANDOFF.md` rewritten
with this session's status, including a note in "Immediate next steps" flagging that
several frontend files were already showing as modified/uncommitted at this session's own
start, from unrelated prior work this session did not touch (except `AboutPage.jsx`,
noted explicitly) -- worth reviewing separately before committing.

---

## 25. Full functional audit (no new features)

**Date:** 2026-09-17

**Prompt (verbatim):**

> Run a full functional audit of the current app and report a clear pass/fail list --
> do not make speculative fixes; if you find a genuine bug, note it and fix only that
> specific thing, then re-verify. The goal is a complete, trustworthy status list, not
> new features.
>
> [full checklist covering: procedure debugging via the merged page's debug path
> (DECLARE/SET arithmetic, IF/ELSE, WHILE, LOOP/LEAVE incl. labeled nested LEAVE, CASE
> status unknown, cursor lifecycle, NOT_FOUND/DIVISION_BY_ZERO handlers, SELECT...INTO
> status unknown, CALL + call stack, IN/OUT/INOUT syntax verification, breakpoints/
> continue/restart); plain SQL via the direct-execute path (CREATE TABLE, INSERT,
> multi-statement-block behavior unconfirmed, UPDATE, DELETE, SELECT, a deliberate
> syntax error); merge routing correctness; cross-cutting persistence (a table/row
> created via direct SQL visible to a cursor afterward, including after a DROP+reseed
> cycle); mandatory course sections (Learn tab, Help tab staleness, Developed By,
> Download in all 3 formats, Day/Night on the merged page); innovation features not
> regressed (Advisor, Compare, Quiz/Predict Mode, TTS); non-functional (re-time /debug
> and /sql/execute, report the current test count vs, the last known baseline) --
> output as a PASS/FAIL/PARTIAL list grouped by section, plus "bugs found and fixed"
> and "needs a decision from the student" sections.]

**What I did.** Exercised every item live -- via the existing 505-test backend suite where
coverage already existed, and directly against the already-running dev backend/frontend
(confirmed up via `curl` before touching anything) everywhere it didn't: raw `curl`/`python`
one-liners against `/debug` and `/sql/execute` for CASE, nested labeled LOOP/LEAVE, cursor+
NOT_FOUND, DIVISION_BY_ZERO, CALL+call-stack, IN/OUT/INOUT syntax, multi-statement SQL
blocks, a deliberate syntax error, cross-cutting persistence (including a DROP+reseed
cycle), the Anti-Pattern Advisor, and all three report formats (validated PDF magic bytes,
DOCX zip structure, TXT content -- not just a 200 status); grep/read-based inspection of
`SqlConsolePage.jsx`'s actual routing logic, `HelpPage.jsx`, `DevelopedByModal.jsx`,
`LearnPage.jsx`, `ComparePage.jsx`, `QuizPage.jsx` for the frontend-only items; a live
`/quiz/generate` call for Quiz. Two real findings: (1) `SELECT ... INTO` genuinely doesn't
exist in the grammar (only `FETCH cursor INTO var` does) -- reported as an absence, not
built in this pass, per the prompt's own instruction; (2) `>=`/`<=`/`<>` are completely
absent from the documented comparison grammar (`parser.py`'s own
`comparison := term (('>' | '<' | '=' | '!=') term)*`), not merely a raw-SQL round-trip
caveat as a previous session's docs implied -- confirmed by testing `CASE WHEN score >= 90`
and getting a genuine `ParserError`. Both became this session's next prompt's scope. Also
discovered (not a bug, a correction to stale HANDOFF status) that the Developed By photo
and Learn tab video/references, both previously flagged as placeholders, are now real --
from unrelated prior work already on disk at session start.

**One real mistake, caught and fixed within the same pass:** an Advisor test used
`DELETE FROM products` with no WHERE clause against the REAL, live seeded `products`
table -- it executed for real and emptied it. Caught immediately via a follow-up SELECT,
reseeded the exact original 3 rows (`Widget/10, Gadget/25, Gizmo/15`) per `user_db.py`'s
own seed data, confirmed restored. All other live-verification side effects (11 history
rows total across the session) were also cleaned up, confirmed back to the pre-audit
baseline (`/history` top id 445).

**Result:** a full PASS/FAIL/PARTIAL list delivered to the user (not reproduced here --
see the conversation itself); 505/505 backend tests passing (no regression from the prior
session's count), `npm run lint`/`npm run build` both clean.

---

## 26. Comparison operators (`>=`/`<=`/`<>`) + `SELECT ... INTO`

**Date:** 2026-09-17–18 · **Not yet committed** (see `HANDOFF.md`)

**Prompt (verbatim):**

> Two focused grammar/interpreter fixes, verified independently, no unrelated changes.
>
> FIX 1 — comparison operators:
> Extend the procedural comparison rule (currently comparison := term (('>' | '<' | '=' |
> '!=') term)*) to also accept >=, <=, and <>. Applies everywhere procedural conditions
> are evaluated — IF, WHILE, CASE. Watch tokenizer ordering: >= must be lexed before a
> bare >, same for <= before <, so this touches the tokenizer as well as the parser rule.
>
> FIX 2 — SELECT...INTO:
> Add SELECT col1, col2, ... INTO var1, var2, ... FROM table WHERE condition; as a
> procedure-body statement, distinct from the existing cursor mechanism (DECLARE CURSOR/
> OPEN/FETCH/CLOSE, which stays unchanged). Parser: capture the SQL after INTO as raw
> text (same raw-passthrough approach used elsewhere) plus the INTO variable list.
> Interpreter: run it against the persistent database, expect exactly one row, assign
> columns to the INTO variables in order. Zero rows: raise the same NOT_FOUND condition
> cursor FETCH already raises, so an existing DECLARE CONTINUE HANDLER FOR NOT_FOUND
> catches it — don't add a new error path. More than one row: raise a clear distinct
> error. Add a DebugStep entry showing the query and resulting assignments (reuse the
> existing raw-SQL step shape if one already exists for CRUD-in-procedures).
>
> Add one test sample per fix: a condition using >=/<=/<> together, and a single-row
> lookup with both the found and NOT_FOUND cases covered.
>
> Verify: full backend suite passing (505 baseline), new unit tests for both fixes
> covering found/not-found/multi-row and all three new operators, live-check both in the
> merged SQL Console page. Report the new total test count.

**What I did.** **Fix 1**: `app/tokenizer.py`'s `_TOKEN_SPEC` gained `GTE`(`>=`)/`LTE`(`<=`)
patterns ordered before the bare `OPERATOR` pattern; `NEQ` widened to `!=|<>`.
`app/parser.py`'s `COMPARISON_OPERATORS` gained the three values -- since IF/WHILE/CASE all
share `_parse_comparison`/`_evaluate_binary`, one change covered all three constructs.
`app/interpreter.py`'s `_evaluate_binary` gained `>=`/`<=`/`<>` branches. Caught and fixed a
real bug this surfaced: `app/explainer.py`'s deterministic template fallback had its own
condition-phrasing regex (`(>|<|!=|=)`) that would have mis-split `score >= 90` into
`score > = 90` -- reordered the alternation, added the new operators to
`_COMPARISON_PHRASES`. **Fix 2**: new `SelectIntoStatement` AST node
(`app/parser.py`'s `_parse_select_into`, dispatched via a new `_select_has_into` lookahead
that tells it apart from a bare-SELECT `SqlStatement`), new `_exec_select_into` in
`app/interpreter.py` reusing `execute_sql_on_connection` and the exact same
`_condition_error_info("NOT_FOUND", ...)`/`_run_handler_if_triggered` machinery an
exhausted cursor FETCH already uses for its own zero-row case -- no new error path. A
column-count mismatch and a multi-row result are both distinct, immediately-fatal
`InterpreterError`s, never routed through a handler. New `sql.into` DebugStep field
(`docs/schema.md` updated). `app/advisor.py`'s `_touched_names` now tracks
`SelectIntoStatement.targets` as writes (same as `FetchCursorNode`, needed for the
dead-store check's correctness). `app/explainer.py` and `SqlConsolePage.jsx` (a new
"Assigned: var = value" / "No row matched ... left unchanged" line in the existing SQL
step panel) both gained cases recognizing `sql.into`. Two new samples,
`OperatorShowcase` and `LookupOnePlayer`, added to `samples.js` + `testCaseExpectations.js`
per the prompt's own instruction (one per fix; `LookupOnePlayer` covers both found and
NOT_FOUND in a single run, per the prompt's explicit ask).

**Tests.** One existing test rewritten (it had documented the round-trip bug Fix 1 fixed
as a side effect). Two new files: `test_comparison_operators.py` (25 tests) and
`test_select_into.py` (20 tests, including two real `/debug`-endpoint end-to-end cases --
caught along the way that `found`/`notfound` are reserved KEYWORDs in this grammar, so an
OUT param literally named `found` fails to parse; renamed to `was_found`). Two new golden
fixtures generated (`UPDATE_GOLDENS=1`), the other 19 confirmed byte-for-byte unchanged.
Backend suite: **552 passing** (up from the 505 baseline the prompt named), zero
regressions.

**Verification.** `npm run lint`/`npm run build` clean. Neither dev server was already
running this session (unlike most prior sessions) -- started both fresh, live-checked via
the scratchpad's `cdp.js` driver: hand-typed raw source using all three new operators
directly (not just the sample) parsed, ran, and stepped to a hand-verified final value
(`r = 111`); `LookupOnePlayer`'s step log showed both SELECT INTO steps, the NOT_FOUND one
tagged inline; the new SQL step panel correctly showed "Assigned: foundScore = 95" for the
found case and the "left unchanged" message plus the pre-existing NOT_FOUND error banner
for the miss, confirmed in both themes (screenshots in the scratchpad). Cleaned up 8 real
history rows and a real `players` table this session's own live verification created on
the real `user_data.db`, confirmed back to baseline afterward.

`docs/features.md` gained a new "Comparison operators + SELECT...INTO" section (and fixed
a now-stale round-trip-caveat claim in its "Backend grammar extension" section from two
sessions ago). `docs/schema.md`'s `sql` field documentation extended for `into`.
`CLAUDE.md` §2's shipped-features bullet extended. `HANDOFF.md` rewritten with this
session's status, including this audit's finding that the Developed By/Learn tab
placeholder gaps a much earlier HANDOFF had flagged are actually already resolved.

---

## 27. Compact Procedure Library + layout density pass (frontend-only)

**Date:** 2026-09-18 · **Not yet committed**

**Prompt (verbatim):**

> PHASE: Compact Procedure Library + layout density pass
>
> Context: Current SQL Console / Debugger layout has a wide left "Procedure Library"
> column where each item is a tall card (badge + bold name + 3-4 line description).
> This makes the left column much taller than the editor column, which pushes
> everything below the editor (flowchart, etc.) far down the page with a large gap.
> Reference screenshot (attached) shows a denser layout style to move toward:
> top bar with step counter + playback icon controls, a slim left "OBJECTS" list
> (name + small type/scope badge only, no description text), and a right panel
> using compact NAME/TYPE/VALUE table rows for Variables. Do NOT copy its exact
> colors -- keep our existing "Debugger Notebook" system (dark navy background,
> IBM Plex Mono for code/labels, Space Grotesk for headings, amber/teal/coral
> accents). Keep the top nav bar exactly as-is -- do not touch it.
>
> Scope (frontend-only, no backend/interpreter changes expected): compact the
> sample list to one-line badge+name rows (~40-48px, ~220-260px column), re-check
> the grid layout so the editor column's height drives row height instead of the
> list, and (only if quick/non-breaking) group Run + step counter/playback into
> one control bar and restyle Variables to NAME/TYPE/VALUE. No hover-flyout
> sidebar, no backend/interpreter/nav changes.

**What I did.** `frontend/src/pages/SqlConsolePage.jsx`: each `.sample-card` dropped its
`sample.description` paragraph and the stacked `sample-card-header` wrapper -- now one
flex row (`sample-kind-tag` badge + `sample-card-name`), with the dropped description text
still reachable via the button's own `title` attribute (hover/assistive tech only). Pulled
the `.step-navigator` block up next to the Run button into a new shared `.control-bar`
wrapper (same conditionals, same handlers -- purely moved, not rewritten), and moved the
"Runs as a procedure/function..." hint out to its own paragraph below the bar. Reordered
the Variables table's columns from Variable/Value/Type to Name/Type/Value per the
reference. `App.css`: `.sample-card`/`.new-custom-button` restyled as compact single-line
rows (`min-height: 40px`, tighter padding, `text-overflow: ellipsis` on the name so a long
camelCase identifier truncates instead of wrapping/overflowing); removed the now-dead
`.sample-card-header`/`.sample-card strong`/`.sample-description` rules. `.debugger-grid`'s
first column narrowed 240px -> 220px. New `.control-bar`/`.btn-run` rules for the grouped
strip. **The real layout fix**: compacting the row height alone wasn't enough -- with 21
samples at 40px each the list still summed to ~1000px+, taller than the editor column, so
the grid row height (and everything rendered after the grid closes, e.g. the flowchart)
was still being dragged down. Gave `.panel-samples` a `max-height: 560px` (roughly the
editor column's own height) with the inner `.sample-list` scrolling internally
(`overflow-y: auto`) above that -- verified via a Puppeteer measurement script that the
grid height now tracks the editor column, not the list. The `max-height` cap is lifted
back to `none` under the existing `max-width: 1000px` breakpoint where the grid already
collapses to one stacked column (a capped, internally-scrolling list reads oddly stacked
above the editor at that width). No backend, interpreter, or top-nav changes.

**Verification.** `npm run lint`/`npm run build` both clean (pre-existing oxlint warnings
unrelated to this change, unchanged). Backend suite re-run to confirm this really was
frontend-only: **552 passing**, same count as before this phase, zero regressions. Both
dev servers were already running this session; live-checked via a Puppeteer script
(reusing an existing scratchpad's `node_modules`/local Chrome) against `/sql-console`:
measured the sample column's width (220px) and first row height (40px) before any run,
confirmed zero rows contain description-length text, ran `OperatorShowcase`, and confirmed
the control bar contains both the Run button and `.step-navigator`, the Variables table's
headers read `Name`/`Type`/`Value` in that order, and the grid's height tracks the editor
column rather than the sample list. Screenshotted both Day and Night mode at 1500px and
Night mode at the known 400px nav-overflow-prone width -- the pre-existing `.top-nav`
overflow at that width (documented in `HANDOFF.md`, untouched by this phase) is still the
only issue there; the stacked single-column layout, uncapped/full sample names, and
compact control bar all render correctly at that width.

---

## 28. Hover-flyout sample rail + trim Live State + wider editor (frontend-only)

**Date:** 2026-09-18 · **Not yet committed**

**Prompt (verbatim):**

> PHASE: Hover-flyout sample rail + trim Live State + wider editor
>
> Context: SqlConsolePage.jsx + App.css. Left "Procedure Library" is a static
> 220px list (badge + name, ~40px rows, truncated, max-height 560px scroll).
> Right "Live State" column is wider than its content needs. Reference: VS
> Code-style collapsed icon rail that flies out on hover. Keep top nav bar,
> "Debugger Notebook" palette/fonts, and all backend/logic untouched — layout only.
>
> 1. Left column → rail + flyout:
>    - Collapsed (default): ~56-64px rail, badge/glyph per row, no name text.
>    - Hover: absolute-positioned overlay expands to ~240-260px (does not
>      reflow grid/editor), full names at normal spacing, wrap don't truncate.
>      Keep existing scroll/max-height, active highlight, "+ New/Custom", and
>      the `title` tooltip (as collapsed-state fallback).
>    - ~150-200ms collapse delay on mouse leave. Items clickable while collapsed
>      — needs a per-item distinguishing mark beyond the badge (e.g. initials)
>      since multiple PROCEDUREs look identical at rest; use your judgment.
>    - Mobile breakpoint: keep prior phase's simple list if the rail doesn't fit.
>
> 2. Right column: cut width ~15-20%, tighten Variables table + Call Stack
>    padding to match. Same data, no wrap/clip issues.
>
> 3. Editor: reflow grid so it claims the width freed by 1 & 2. Flyout overlays
>    on hover, does not shift this base width.
>
> Verify: lint/build clean; Puppeteer screenshots of collapsed + expanded rail
> (confirm no editor shift) + full layout, Day/Night; recheck 400px + mobile
> breakpoints; backend suite unchanged; update HANDOFF.md/PROMPT_LOG.md.

**What I did.** Split the single always-visible compact list from phase #27 into two
DOM copies of the same `SAMPLES` map in `SqlConsolePage.jsx`: `.sample-rail` (always
in-flow, defines the grid's actual 60px first column — each row a `.rail-item` button
showing only a colored initials chip from a new `getSampleInitials(name)` helper, which
pulls capital letters out of a PascalCase name for a short, usually-unique pair like "OS"
for OperatorShowcase) and `.sample-flyout` (always `position: absolute`, full badge +
name rows via a new `renderWrappableName(name)` helper that inserts a `<wbr/>` before
each internal capital letter so a wrapped name breaks at a word boundary instead of an
arbitrary character). The flyout is opened/closed purely via CSS: `.panel-samples:hover
.sample-flyout` / `:focus-within` toggle `opacity`/`visibility`/`pointer-events`, with a
`transition-delay: 200ms` on the closing direction only (no JS timers) giving the
"forgiveness" window the prompt asked for; opening has no delay. Because the flyout is
*always* `position: absolute` (never toggled between static/absolute), opening it can
never reflow the grid — confirmed by measuring `.panel-editor`'s `left` before/after
hover in Puppeteer (bit-for-bit identical). Two real bugs caught during live-checking,
not by inspection: (1) an absolutely-positioned child's `top:0; left:0` resolves against
its containing block's *padding* box, not border box — the flyout needed
`top: -1.5rem; left: -0.4rem` (matching `.panel-samples`'s own padding) to actually cover
the rail's border/tab area instead of leaving a visible sliver of it above the flyout,
which was rendering as an ugly overlap with the flyout's own "PROCEDURE LIBRARY" tab.
(2) `overflow-wrap: break-word` alone chopped a name at an arbitrary character
(`CalculateTota` / `l`) — fixed by the `<wbr/>`-insertion approach above, giving
`Calculate` / `Total` instead. `.debugger-grid`'s columns changed from
`220px minmax(0,1.6fr) minmax(280px,1fr)` to `60px minmax(0,2fr) minmax(230px,0.8fr)`;
`.panel-state` (Live State) and `.panel-samples` both gained tighter horizontal padding
overrides. Mobile (`max-width: 1000px`): `.sample-rail` becomes `display: none` and
`.sample-flyout` has its absolute positioning/opacity/transition all stripped back to
plain static/always-visible/no-transition — i.e. it reverts to exactly phase #27's plain
compact list, since a hover flyout has no equivalent on a touch device.

**A real debugging detour, worth recording.** Puppeteer screenshots intermittently
showed a "ghost" double-exposure of the flyout's full-name rows over the collapsed rail
in `fullPage: true` captures, specifically on a page that had already fired the hover
transition earlier in its lifetime (and more reliably after several rapid interactions —
theme toggle + sample click + Run — in quick succession before the capture).
`getComputedStyle` queried at the literal moment of each screenshot consistently reported
the CORRECT hidden state (`opacity: 0`, `pointer-events: none`) even when the saved PNG
showed the ghost — ruling out an actual CSS/state bug immediately. Isolated further: a
`fullPage: false` (viewport-only) screenshot taken at the exact same moment, with the
exact same interaction history, was always clean; a `fullPage: true` screenshot on a
*fresh* page/tab with no prior hover history was always clean; a `fullPage: true`
screenshot on a page WITH hover history, after a short settle delay plus a forced
reflow (`element.getBoundingClientRect()`) and a scroll nudge, also came back clean.
Conclusion: a stale-compositor-tile race specific to Puppeteer/CDP's full-page capture
stitching path after a CSS opacity transition, not a product bug — no real user
interaction ever triggers that specific capture mechanism. Documented in `HANDOFF.md`'s
Live gotchas for future sessions rather than chased further or "fixed" in app CSS.

**Verification.** `npm run lint`/`npm run build` clean (same two pre-existing warnings
as recent sessions). Backend suite re-run specifically to confirm frontend-only: **552
passing**, unchanged. Both dev servers were already running. Live-checked via Puppeteer
(reused an existing scratchpad's `node_modules` + local Chrome): measured the rail
(60px), the editor's width increase and Live State's ~16% reduction at a 1500px
viewport, confirmed zero reflow of the editor while the flyout is open, confirmed
collapsed/hovered opacity+pointer-events values, confirmed the Variables table headers
(Name/Type/Value, unchanged from #27) and control bar (unchanged from #27) still render
correctly, and confirmed the mobile fallback (rail hidden, flyout static and always
visible, all 21 full-name rows unclipped) at 400px. Screenshotted collapsed rail,
expanded rail (hover), and full page layout in both Day and Night mode.

`HANDOFF.md` rewritten with this session's status (its own convention: fully rewritten,
not appended to).

---

## 29. Sidebar row overflow, YouTube video centering, remove Variable Timeline (frontend-only)

**Date:** 2026-09-18 · **Not yet committed**

**Prompt (verbatim):**

> PHASE: Sidebar row overflow, YouTube video centering, remove Variable Timeline
>
> 1. Sample list rows (SqlConsolePage.jsx/App.css): rows with 3-line names
>    overflow their card boundary. Fix so row height auto-grows to fit wrapped
>    text (no fixed/min-height clipping), consistent spacing/padding preserved
>    for 1/2/3-line names alike.
>
> 2. Learn page video embed: currently left-aligned, center it (embed +
>    caption/attribution block) within its container.
>
> 3. Remove "Variable Timeline" feature entirely: the card/panel, its section
>    in the Debugger page, and any nav/toggle entry point to it. Check
>    overview.md-equivalent docs (HANDOFF.md) for wherever it's listed as an
>    innovation feature and mark it dropped, matching how Live Parameter Tuning
>    was already handled. Leave sparkline-adjacent Variables table (from the
>    density-pass phase) untouched — that's separate.
>
> Verify: lint/build clean; Puppeteer check of sidebar at long names, Learn
> page centering, and Debugger page layout without the removed card, Day/Night;
> backend suite unchanged; update HANDOFF.md/PROMPT_LOG.md.

**What I did.** Three independent fixes, all in `frontend/src/` (`App.css`,
`SqlConsolePage.jsx`, plus deleting `VariableTimeline.jsx` outright).

**1. Sample-row overflow — root-caused with a Puppeteer probe, not patched by guessing.**
Measured every flyout row's `getBoundingClientRect()` height against its
`.sample-card-name`'s actual content height before touching any CSS: **every** row,
1-line names included, was locked at exactly `.sample-card`'s `min-height: 40px`
regardless of how much text it actually held. Root cause: `.sample-list` (the flex column
these rows sit in) is shorter than its combined row content once ~21 samples are listed,
and `.sample-card`'s default `flex-shrink: 1` was squeezing *every* row down to its
`min-height` floor trying to make them all fit — a floor that happens to match 1-line
content exactly (so those rows looked fine) but clips a 2- or 3-line wrapped name (e.g.
`StaticAnalysisShowcase`, whose name needed 51px of content height but was being forced
into a 40px box). Fixed with `flex-shrink: 0` on `.sample-card` (and defensively on
`.rail-item`, the rail's own rows, which share the identical flex-column-in-a-capped-
height-container pattern even though initials never currently wrap). Re-measured
post-fix: the 3-line row now reports `cardHeight: 67.375px`, `overflows: false` — grown to
fit, not clipped — while 1-/2-line rows stayed exactly as tall as their own content (40px
/ ~50px), confirming the fix didn't over-grow rows that were already correct.
Screenshotted the previously-overflowing row scrolled into view to confirm visually too.

**2. Learn page video centering.** `.learn-video-wrap` (the 720px-capped 16:9 iframe
container) had `width: 100%; max-width: 720px` but no horizontal auto margins, so on any
panel wider than 720px (every real viewport) it sat flush against the panel's left edge.
`.learn-video-caption` (the attribution text directly above the embed) had the same
problem. Added `margin: 0 auto` to `.learn-video-wrap`, and `max-width: 720px; margin: 0
auto 1rem; text-align: center` to `.learn-video-caption` — both now center as one visual
unit rather than the video centering while its own caption stayed pinned left above it (a
mismatch the prompt's "embed + caption/attribution block" wording specifically called
out). Verified in Puppeteer by measuring both elements' left/right gap to the panel's own
edge: 316px/316px on both sides at a 1500px viewport, in both Day and Night theme — not
just eyeballed.

**3. Variable Timeline removed entirely**, per the prompt's explicit instruction:
- `frontend/src/VariableTimeline.jsx` deleted outright (the whole sparkline component).
- Its panel (`<div className="panel panel-timeline">…<VariableTimeline .../></div>`,
  sitting between Control Flow and Step Log on the Debugger page) and its import both
  removed from `SqlConsolePage.jsx`.
- Its entire CSS block in `App.css` (`.var-timeline` through `.var-timeline-hover-caption
  code`, ~130 lines, everything under the "Variable Timeline" section comment) removed.
- Three lingering prose references that would otherwise now describe a nonexistent
  feature: a code comment in `backend/app/interpreter.py` ("...the Call Stack panel, the
  Variable Timeline, Download reports...") trimmed to drop the dangling mention; a
  comment in `frontend/src/TestCaseRunner.jsx` ("same reasoning as VariableTimeline.jsx")
  reworded to stand on its own. Deliberately left `docs/features.md`'s own historical
  phase narrative alone — it's a record of what a past phase actually designed and
  reasoned through at the time (including a "Variable Timeline: needed zero changes"
  verification note specific to that phase), the same treatment every other past-tense
  design decision in that file already gets; rewriting it to erase a feature that phase
  genuinely shipped would falsify the history, not just clean it up.
- `HANDOFF.md`'s Innovation line changed from "3/4 done, 1 dropped" to "2/4 done, 2
  dropped," explicitly distinguishing Variable Timeline (shipped, then dropped/removed
  this session) from Live Parameter Tuning (dropped, never started) rather than treating
  both the same way.
- Confirmed via Puppeteer against the live page: `document.querySelector('.panel-timeline')`
  returns null, and the page's `.panel-tab` sequence reads straight from `"CONTROL FLOW"`
  to `"STEP LOG — THIS RUN"` with no gap where `"VARIABLE TIMELINE"` used to sit —
  screenshotted the resulting Debugger page layout in both Day and Night mode to confirm
  no leftover empty space or broken flow.

Left the sparkline-adjacent Variables table (Name/Type/Value columns, from the #27
density-pass phase) completely untouched, per the prompt's explicit instruction — it's a
different, unrelated panel that happens to sit near where Variable Timeline used to.

**Verification.** `npm run lint` (same two pre-existing warnings as every recent session,
unrelated: a `SqlConsolePage.jsx` exhaustive-deps warning and a `ThemeContext.jsx`
fast-refresh warning) and `npm run build` both clean. Backend suite re-run specifically to
confirm frontend-only: **552 passing**, unchanged. Both dev servers were already running.
Live-checked via Puppeteer (reused an existing scratchpad's `node_modules` + local
Chrome): the sample-row fix (measured + screenshotted), the Learn-page centering
measurement (both themes), and the Debugger page's panel sequence + full-page screenshot
with the Variable Timeline card gone (both themes). None of this session's own
verification scripts clicked Run or otherwise called `/debug`, so no
`debug_history.db`/`user_data.db` cleanup was needed afterward (confirmed by checking
`GET /history` afterward — the only recent rows are pre-existing `OperatorShowcase` runs
from the prior #28 session, not new ones).

`HANDOFF.md` rewritten with this session's status (its own convention: fully rewritten,
not appended to).

---

## 30. Fix Download Report generation (all formats — PDF/Document/Text)

**Date:** 2026-09-18 · **Not yet committed**

**Prompt (verbatim):**

> PHASE: Fix Download Report generation (all formats — PDF/Document/Text)
>
> Context: Report generator (wherever /debug download builds PDF/docx/txt) has
> 3 bugs, confirmed via LookupOnePlayer sample, but NOT sample-specific — check
> report-building code path, not sample data:
>
> 1. Intermediate Results table — remove entirely from all three formats. Too
> granular, not useful; drop the section and its heading.
>
> 2. "ERROR" mislabeling — steps caught by a CONTINUE/handler (e.g. NOT_FOUND
> caught normally) are shown as "ERROR [...] ... caught by X handler" in the
> Processing Steps Details column. This reads as a failure when it's expected,
> handled behavior. Distinguish handled vs. unhandled: caught steps should
> read something like "Handled: NOT_FOUND (caught by handler)" without the
> ERROR label; reserve "ERROR" for genuinely unhandled/fatal errors that
> halted execution. Apply the same distinction everywhere this status renders
> in the report (and check the in-app step view for the same mislabeling —
> fix there too if present).
>
> 3. Control-flow diagram missing — "Graphs, Tables & Figures" page shows only
> a heading + caption ("Control-flow diagram, as rendered in the Debugger.")
> with no actual diagram image, in every sample tested. Root-cause why the
> Mermaid flowchart isn't being rendered/embedded (e.g. server-side Mermaid
> render step failing silently, image not attached to the PDF/docx builder,
> or txt correctly skipping images but PDF/docx incorrectly matching). Fix
> so the real diagram is embedded as an image in PDF and Document formats;
> for Text format, either omit this section cleanly (no dangling caption) or
> substitute a simple text-based step-flow summary — your call.
>
> "Steps by statement type" table: keep as-is, seems useful and correct.
>
> Verify: regenerate reports for 3-4 varied samples (include one with a handler/
> caught-error case, one with CALL, one plain) across all 3 formats; confirm no
> Intermediate Results section, no false ERROR labels on handled steps, and a
> real diagram image present in PDF/Document output. lint/build clean; backend
> suite unchanged unless report logic is backend-side (note count either way).
> Update HANDOFF.md/PROMPT_LOG.md.

**What I did.** All three bugs lived in `backend/app/report.py`'s shared, format-agnostic
`build_report()`/`_step_details()` — confirmed by reading the module before touching
anything: one `build_report()` call produces one intermediate representation that all
three renderers (`render_text`/`render_docx`/`render_pdf`) share, so a fix there applies
to all three formats at once, exactly as the prompt expected.

**1. Intermediate Results removed.** Deleted the whole section (one row per variable per
step) from `build_report()` — `sections` now has four entries instead of five (`User
Inputs`, `Processing Steps`, `Final Output`, `Graphs, Tables & Figures`), left a comment
in its place explaining what used to be there and why it's gone.

**2. "ERROR" mislabeling — root-caused, not just reworded.** Before changing any text,
traced *why* `error.handler == "unhandled"` doesn't actually mean "this halted
execution" in this data: `/debug` only ever returns a `steps` list for a run that
completed — a genuinely fatal `InterpreterError` aborts with a 400 *before* producing any
steps, and `/debug/report` only ever receives a prior `/debug` response's own `steps`, so
this endpoint structurally can never see a step from a run that actually halted.
Cross-checked against `interpreter.py`'s own design and its existing test
(`test_not_found_without_a_handler_is_unhandled_but_still_non_fatal`): NOT_FOUND is
unconditionally non-fatal, handler declared or not. Conclusion: a per-step `error` in
this endpoint's data is **always** non-fatal, so "ERROR" should never appear on it at
all, in either branch. Fixed `_step_details()`: caught-by-handler now reads `"Handled:
NOT_FOUND -- <message> (caught by NOT_FOUND handler)"`; no-handler-declared-but-still-
non-fatal reads `"Note: NOT_FOUND -- <message> (no handler declared; non-fatal, execution
continued)"`. Found and fixed the same misconception in a second place the prompt asked
to check ("apply the same distinction everywhere this status renders"): Final Output's
own separate rendering said "Execution stopped with an unhandled error" for the exact
same non-fatal case, just because it happened to be the run's last step — reworded to
"Execution completed after N step(s) ... this condition is non-fatal by design and did
not halt execution." **Checked the in-app step view per the prompt's explicit
instruction — the mislabeling isn't present there**: `SqlConsolePage.jsx`'s error banner
(`error-banner-handled`/`error-banner-unhandled` classes, "Caught by: X" / "No handler
caught this — unhandled." text) and step-log flag both already render the raw
`condition`/`message` with no literal "ERROR" anywhere; `explainer.py`'s Gemini-prompt
builder and template fallback were already correct too (`"caught by the X"` /
`"unhandled"` phrasing, no "ERROR" label). This bug was isolated to `report.py`.

**3. Control-flow diagram — the real work this session, four stacked bugs found live in
order, each hiding the next.** Started by reproducing the exact symptom through the real
UI via Puppeteer (intercepting the actual `/debug/report` POST body a real Download PDF
click sends), not guessing from reading code:

- **Bug 1, sizing**: `svgToPng.js`'s old width/height detection regex-scanned the ENTIRE
  svg string for the first `width="..."`/`height="..."` match, not just the root `<svg>`
  tag. Mermaid's actual root tag sets `width="100%"` (a percentage, no height attribute
  at all) with the real pixel size only in its `viewBox` — confirmed by dumping the live
  rendered SVG's own markup. That whole-string scan skipped the root tag (percentage
  doesn't match the regex) and landed on the first `width="0"`/`height="0"` it found
  deeper in the markup (an internal marker/defs element), silently producing a 1×1-pixel
  canvas — confirmed by decoding the actual captured PNG bytes' own IHDR chunk (width=1,
  height=1). This matches the reported symptom exactly: a caption WAS showing (meaning a
  real image, however tiny, was already being embedded), just invisible. Fixed by scoping
  the match to the root `<svg ...>` tag only and preferring its `viewBox`.
- **Bug 2, canvas tainting**: once the image was the right size, `canvas.toDataURL()`
  started throwing `SecurityError: Tainted canvases may not be exported` — reproduced
  directly in-page via Puppeteer (not just inferred from a stack trace), confirmed on
  every sample tried. Any SVG containing a `<foreignObject>` (exactly how Mermaid renders
  node/edge labels) permanently taints a canvas once drawn via `<img>` + `drawImage`, a
  hard browser restriction. Tried Mermaid's own `flowchart.htmlLabels: false` via an
  inline `%%{init: ...}%%` directive (which should avoid `<foreignObject>` entirely) —
  confirmed live it did NOT actually suppress `<foreignObject>` in this Mermaid version
  (`hasForeignObject: true` on the rendered output even with the directive applied), then
  confirmed via a web search of Mermaid's own issue tracker that this is a known,
  documented upstream limitation, not a config mistake on this app's part.
- **Bug 3, html2canvas tried and rejected**: installed `html2canvas` (sidesteps the taint
  issue by walking the live DOM instead of decoding an `<img>`) and wired it up — it ran
  without throwing, and produced a correctly-sized PNG, but sampling the resulting
  canvas's own pixel data directly (not just eyeballing a screenshot) showed 100% pure
  white, zero non-white pixels across 5.4 million of them: html2canvas silently failed to
  paint any of this SVG's content, a known gap in its nested-SVG support. Removed again
  (`npm uninstall html2canvas`) once this was confirmed — the frontend has no new
  dependency as a result of this session.
- **The fix that actually works**: rewrote `svgToPng.js` to convert every
  `<foreignObject>` label in a cloned copy of the live diagram SVG to a plain SVG
  `<text>`/`<tspan>` (`foreignObjectsToSvgText`) before rasterizing through the same
  `<img>` + `<canvas>` path bug 1 already fixed the sizing for — a `<foreignObject>`-free
  SVG carries none of bug 2's restriction. Verified this actually produces a real,
  legible image by decoding the rasterized PNG and viewing it directly (not just
  checking file size): a `CalculateTotal` trace rendered as a fully readable flowchart on
  the first attempt, but with the two longest DECLARE statement labels' text visibly
  overflowing their node boxes on both sides — a second real bug, fixed with
  `shrinkTextNodesToFit` (temporarily attaches the cloned SVG off-screen, since
  `getComputedTextLength()` needs real layout and returns 0 on a detached node, then
  shrinks any label that measures wider than the box Mermaid originally sized for it).
  Testing next against `GradeClassifier` (a branching sample, to exercise edge/condition
  labels — "then"/"else" — which `CalculateTotal` doesn't have) surfaced a THIRD bug:
  those edge labels rendered as invisible near-white text on the white report page
  (correct on screen, against the app's own dark canvas; wrong once transplanted). Fixed
  with a dark, page-safe fallback specifically for `.edgeLabel`-rooted labels (detected
  via `fo.closest('.edgeLabel')`), leaving node labels on their existing near-white
  default (correct, since they always sit on their own node's dark shape fill). Setting
  that fallback via a bare `fill="..."` **attribute** didn't actually work either —
  confirmed live it was silently overridden by the diagram's own embedded `<style>`
  block's `#flowchart-1{fill:#edeff4}` rule (an SVG presentation attribute is the
  *weakest* possible CSS origin) — fixed by setting `text.style.fill` (inline style)
  instead, which does outrank an embedded, non-`!important` stylesheet rule.
- **A fourth, separate bug, found only once the diagram was finally correct**: generating
  a real PDF for `GradeClassifier` (a taller, narrower diagram than `CalculateTotal`)
  returned a 500. The actual error, read directly from the response body rather than
  assumed: reportlab's `"Flowable ... too large ... in frame"` — `render_pdf()`'s image
  block used to scale ONLY by width, so a tall, narrow image could still come out taller
  than an entire fresh page's own frame height, which reportlab refuses to lay out at all
  (not shrink, not split) rather than error gracefully. Fixed by also computing a
  height-based scale factor and taking the `min()` of both width- and height-based
  ratios — the exact fix that made the diagram finally appear would have silently
  re-broken PDF specifically, for any sufficiently tall diagram, without this.
- **Wiring**: `SqlConsolePage.jsx` gained a `diagramContainerRef` (attached to the live
  `.diagram-svg` div) and `handleDownloadReport` now calls
  `rasterizeDiagramElementToPng(diagramContainerRef.current)` instead of the old
  `rasterizeSvgToPng(diagramSvg)` call over the raw SVG string.

**Testing added.** `test_report.py`: `test_build_report_has_no_intermediate_results_
section` (replaces the old intermediate-results test), `test_step_details_labels_a_
caught_error_as_handled_not_error`, `test_step_details_no_handler_declared_condition_is_
not_labeled_error_either`, `test_final_output_no_handler_declared_does_not_say_execution_
stopped`, `test_generate_report_pdf_scales_a_tall_narrow_image_to_fit_the_page` (a real
200×4000 Pillow PNG, reproducing the exact reportlab failure if the height-based scale
factor is ever removed). `test_report_endpoint.py`:
`test_report_endpoint_handles_a_caught_handler_trace_without_false_error_label` (the same
fix, end to end through the real `/debug` → `/debug/report` pipeline with a genuine
cursor+handler procedure, not a hand-built step dict).

**Verification.** Backend suite: **557 passing** (was 552; +5 net), 0 xfailed. `npm run
lint`/`npm run build` both clean (same two pre-existing warnings). Regenerated reports
for four varied samples end to end through the real UI (driven live via Puppeteer, not
direct API calls) — `GradeClassifier` (plain branching), `OrderTotal` (`CALL`),
`SafeAverageWithHandlers` (cursor + NOT_FOUND handler + DIVISION_BY_ZERO handler),
`ClassifyOrder` (`CASE`) — across all three formats: confirmed no "Intermediate Results"
section anywhere; `"Handled:"`/`"Note:"` wording with zero occurrences of the literal
word "ERROR" for any caught/non-fatal condition (txt: grepped directly; docx: read via
python-docx); a real diagram image in PDF (valid `%PDF-`/`%%EOF`, `/Image` XObject
markers present) and DOCX (extracted the actual `word/media/image1.png` from inside the
generated `.docx` and viewed it directly — a fully legible, correctly-colored,
correctly-sized flowchart, not just "a file exists"). Both dev servers went down mid-
session (a context reset landed between two verification steps) — restarted both
directly rather than assuming either was still up. `backend/data/debug_history.db`'s 44
test rows from this session (ids 512–555, across many Puppeteer-driven `/debug` calls)
deleted afterward via `DELETE /history/{id}`; no `user_data.db` writes this session
(every sample used was read-only against it).

`HANDOFF.md` rewritten with this session's status (its own convention: fully rewritten,
not appended to).

## 31. AI Practice — Competitive Exam Practice Generator (replaces standalone Quiz page)

**Date:** 2026-09-18 · **Not yet committed**

**Prompt (verbatim):**

> PHASE: AI Practice — Competitive Exam Practice Generator (replaces standalone Quiz page)
>
> ## Remove: standalone Quiz page
> - Remove the standalone Quiz page/tab and its nav entry entirely (route,
>   component, any Quiz-specific backend endpoint(s) used only by it)
> - Do NOT touch Predict Mode — it is a separate, inline, in-debugger feature
>   and must be left fully intact
> - Check for and clean up any now-dead references: imports, nav config,
>   route definitions, any shared Gemini quiz-generation backend code that
>   only the Quiz page used (leave it if Predict Mode or anything else
>   depends on it)
> - Update HANDOFF.md / HELP tab content if either references the Quiz page
>
> ## Add: "AI Practice" tab
>
> Add a new "AI Practice" tab to the app (nav placement: alongside Learn/Help,
> NOT inside the debugger flow — this is a standalone practice tool, not tied
> to any sample or trace). This replaces the old Quiz page in the nav.
>
> ## Backend
>
> New endpoint: POST /practice/generate
> - Request body: { difficulty: "easy" | "medium" | "hard", numQuestions: int (1-15) }
> - Use the Gemini API (same client/pattern as the existing AI explainer) to
>   generate `numQuestions` MCQ questions about stored procedures, functions,
>   cursors, exception handling, and control flow in SQL/PL-SQL, styled like
>   competitive/placement exam questions (GATE DBMS PYQ style and campus
>   placement SQL rounds), at the requested difficulty.
> - Prompt Gemini for strict JSON output: array of objects with
>   { question, options: [4 strings], correctIndex, explanation }.
> - Validate the JSON response (correct shape, correctIndex in range, exactly
>   4 options) before returning it. If Gemini fails or returns malformed JSON,
>   fall back to a hardcoded bank of pre-written questions (mirror the existing
>   template-fallback pattern used elsewhere) — split the bank by difficulty,
>   at least 5 questions per difficulty level, and sample `numQuestions` from it.
> - No persistence needed — this is stateless, generate-and-serve.
>
> ## Frontend — new page, e.g. PracticePage.jsx, route /practice
>
> ### Setup screen
> - Difficulty selector: Easy / Medium / Hard as large selectable cards (not a
>   dropdown) — use the amber/teal/coral accent trio to color-code the three
>   difficulty levels
> - Number of questions: stepper or slider, 1-15
> - "Generate Practice Set" button — loading state while Gemini responds
>   (skeleton loaders or an animated caret consistent with the gutter caret
>   motif elsewhere in the app, not a generic spinner)
>
> ### Question flow (one question at a time, not a scroll-through list)
> - Progress indicator (e.g. "Question 3 of 10")
> - Question text + 4 options as selectable cards
> - On selecting an answer:
>   - If correct: immediate green/teal success state, reveal the explanation,
>     "Next Question" button
>   - If wrong: DO NOT immediately mark it wrong. Show a "not quite — try
>     again" state, let the user pick again. Only on the SECOND wrong attempt,
>     mark it wrong (count it against the score), reveal the correct answer
>     highlighted + the explanation, then "Next Question" button
>   - Track first-attempt-correct vs. wrong-after-retry vs. wrong distinctly
>     so the score screen can show nuance, not just right/wrong
> - Smooth transitions between questions (fade/slide, not a hard reload) —
>   this page should feel noticeably more alive/interactive than the rest of
>   the site, which has been flagged as visually flat elsewhere
>
> ### Score screen (after last question)
> - Score out of total, with a breakdown: correct on first try / correct on
>   retry / incorrect
> - Per-question review list (collapsed by default, expandable) showing the
>   question, the user's answer(s), correct answer, and explanation
> - "Try Another Set" button that returns to the setup screen (keep difficulty
>   selection but let them change it)
>
> ## Design system compliance
> - Follow the existing "Debugger Notebook" system: dark navy palette,
>   IBM Plex Mono + Space Grotesk fonts, amber/teal/coral accents
> - Must be fully theme-aware (Day/Night mode toggle already exists app-wide —
>   do not hardcode colors, use the existing theme tokens/CSS variables)
> - Should work down to ~400px width (existing nav overflow bug was already
>   fixed at this breakpoint — don't reintroduce it)
>
> ## Out of scope for this phase
> - No persistence of past practice sessions/history (flag as a possible
>   future addition, don't build it)
> - No integration with Predict Mode — this is a fully separate,
>   general-purpose practice tool
>
> ## Verification
> - Add basic backend tests for /practice/generate: valid request shape,
>   fallback path when Gemini is mocked to fail, malformed-JSON handling
> - Confirm no test references the removed Quiz page break the suite; remove/
>   update any that do
> - Confirm lint/build clean
> - Live-verify via headless Chrome: full flow (setup → generate → answer with
>   one deliberate wrong-then-right retry → reach score screen) in both themes,
>   and confirm the Quiz nav entry is gone while Predict Mode still works

**What I did.** Full rationale: `docs/features.md`'s "AI Practice (replaces the standalone
Quiz page)" section. Summary:

**Removed**, entirely (not deprecated/hidden): `backend/app/quiz.py`,
`backend/app/tests/test_quiz.py`, `backend/app/tests/test_quiz_endpoint.py`, `POST
/quiz/generate` + its `QuizGenerateRequest` model in `main.py`, `frontend/src/pages/
QuizPage.jsx`, its `/quiz` route + nav entry, and `frontend/src/lastProcedure.js` (its
only consumer was the old Quiz page's "This Procedure" option — nothing else referenced
it). Confirmed Predict Mode (`SqlConsolePage.jsx`, internally still named `quiz-*` in its
own state/class names) untouched throughout — checked before and after.

**Added**: `backend/app/practice.py` (Gemini generation + hardcoded fallback bank, reusing
`app/explainer.py`'s client wiring) and `POST /practice/generate`; `frontend/src/pages/
PracticePage.jsx` (`/practice`, nav entry "AI Practice" in the same top-level nav list the
old Quiz entry sat in) implementing the full setup → one-question-at-a-time-with-retry →
score-screen flow from the prompt, plus a matching `App.css` section
(difficulty cards, stepper, generating-caret/skeleton, option states, score chips, review
accordion).

**Two real bugs found and fixed during live verification** (not caught by lint/build):
(1) a `str.format`/literal-brace collision in the shared JSON-shape prompt text (fixed via
a `__COUNT__` marker + `str.replace`); (2) a CSS specificity bug where the global
`button:disabled` rule silently beat the new single-class `.practice-option-correct/
-wrong/-tried` modifiers on every answered (disabled) option, confirmed via
`getComputedStyle` and fixed with compound selectors. Also caught and fixed a dead/missing
`vite.config.js` dev-proxy entry (`/quiz` → `/practice`, same path-prefix-collision pattern
the file already documents for `/debug`/`/history`/`/sql`) — missing it 404'd the whole
feature in dev, caught live, not statically.

**Testing added.** `backend/app/tests/test_practice.py` + `test_practice_endpoint.py` —
JSON-shape validation, fallback-bank sampling (with/without replacement), Gemini-mocked
success/retry/fallback paths, pydantic bounds validation, a real end-to-end no-key
fallback test. Backend suite: **568 passing** (was 552 before `quiz.py`'s ~30 tests were
removed and `practice.py`'s ~30 added), 0 xfailed. `npm run lint`/`npm run build` both
clean (same two pre-existing warnings).

**Verification.** Live-verified via headless Chrome (Puppeteer-core + local Chrome, fresh
`node_modules` in this session's scratchpad — none was reused from a prior session, all
had been cleaned up) against freshly started dev backend+frontend (neither was already
running): nav shows "AI Practice", no "Quiz" entry; direct-navigating the old `/quiz` URL
renders no quiz UI; Predict Mode confirmed still present/functional on the SQL Console
page; full setup → real-Gemini-generated question → a genuine wrong-then-correct retry
(and, across repeated runs, a genuine wrong-then-wrong-again final-incorrect path) → score
screen → expandable review → "Try Another Set" (difficulty kept) flow, in both Day and
Night mode; confirmed no horizontal overflow at 400px. `getComputedStyle`-verified exact
accent colors for all three answered-option states post-fix. Neither `debug_history.db`
nor `user_data.db` touched this session (`/practice/generate` has no history/user-db side
effects at all).

`HANDOFF.md` rewritten with this session's status (its own convention: fully rewritten,
not appended to).
