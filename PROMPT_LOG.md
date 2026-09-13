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

**Date:** 2026-09-13 · **Not yet committed** (see `HANDOFF.md` §6)

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

**Date:** 2026-09-13 · **Not yet committed** (see `HANDOFF.md` §6)

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
