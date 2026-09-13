# HANDOFF.md

**A snapshot of exactly where the project stands right now.** This file gets
overwritten/updated at the end of every session — it is not a cumulative log. For
stable project facts (architecture, schema, design tokens) see `CLAUDE.md` instead.

---

## 1. Last updated

**2026-09-13**, end of the session that built the **Learn tab** and created
`PROMPT_LOG.md` (see §2/§4/§5). Follows the session that built the Help tab, which itself
followed the session that created this file/`CLAUDE.md` and built Day/Night Mode + the
Developed By modal.

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
- **Backend endpoints**: `/health`, `/debug`, `/explain`, `/ask`, `/quiz/generate`,
  `/history` (GET/GET-one/DELETE-one/DELETE-all) — all implemented, all covered by
  `backend/app/tests/`. Full suite: **176 tests passing** as of this session.
- **Debugger page**: Monaco editor, step navigator (Prev/Next/Reset/scrubber/step log),
  live variable watch table (`changed`/`isOutput` badges), animated gutter caret +
  cause→effect connector lines to changed variables, Mermaid control-flow diagram kept in
  sync with the step trace, error banner (handled vs. unhandled), cursor panel, return-value
  panel, Ask AI free-form chat, "⭳ Export Run" (JSON only — see §6).
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
  (one real AA miss found and fixed — light-mode `--accent-teal`). Code-complete; see §3
  for what's still open on it.
- **Developed By modal** — trigger + modal, dismissible via close button/backdrop/Escape,
  theme-aware. Code-complete; content is placeholder (see §3, §6).
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

---

## 3. In progress right now

**Day/Night Mode + Developed By modal** — built together in one phase (both touch global
nav/theming). Implementation is functionally complete and has been live-verified
(puppeteer-driven screenshots + a scripted WCAG contrast audit against the real rendered
pages), but is **not finished as a deliverable** yet:

**Implemented:**
- Every hard-coded theme color in the frontend converted to a CSS custom property (spot
  checked via `grep` for `#`/`rgba(` outside `var()` — none left in app code).
- `ThemeContext.jsx` (provider + `useTheme()`), `localStorage`-persisted, applied via
  `data-theme` on `<html>`, no-FOUC inline script in `index.html`.
- Toggle (🌙/☀️) + "Developed By" trigger in a new top-right header cluster
  (`Layout.jsx`), separated from nav tabs by a hairline divider.
- Monaco (`vs-dark`/`vs`) and Mermaid (`mermaidColors.js` + `cfg.js`'s `theme` param)
  both react live to the toggle, including re-coloring an already-rendered flowchart.
- `DevelopedByModal.jsx` — full markup/styling/dismiss behavior in place.

**Still missing / open:**
- **Not committed.** `git status` right now shows 8 modified files
  (`frontend/index.html`, `App.css`, `App.jsx`, `Layout.jsx`, `cfg.js`, `index.css`,
  `pages/DebuggerPage.jsx`, `theme.css`) and 3 untracked new files
  (`DevelopedByModal.jsx`, `ThemeContext.jsx`, `mermaidColors.js`). Nothing from this
  phase is in git history yet.
- **Developed By content is all placeholder**: student photo is an inline SVG
  silhouette, name is literally `[NAME]`, register number is literally `[REGISTER
  NUMBER]` (`DevelopedByModal.jsx`). Needs the real photo file + two real strings from
  the user before this section is actually gradeable.
- Only exercised in one headless-Chrome instance during verification — not spot-checked
  in an actual second browser engine (not blocking, just unverified).

---

## 4. Not started yet

- **Download feature upgrade** — the mandatory requirement is PDF/Document/Text export
  of inputs, steps, intermediate results, output, and graphs. What exists today
  (`handleExport` in `DebuggerPage.jsx`, the "⭳ Export Run" button) only produces a
  **JSON** file of code+AST+steps, and does not include the flowchart/graph at all. This
  does not satisfy the requirement as written — treat Download as effectively
  not-started against the actual spec, not "half done."
- **Four innovation features** — confirmed absent by grep, no partial code anywhere:
  SQL Anti-Pattern Advisor, Variable Timeline/sparklines, Side-by-Side Run Comparison,
  Live Parameter Tuning.

---

## 5. Agreed build order

Finish all 5 mandatory sections first, in this order:

1. ~~Day/Night mode + Developed By~~ — code-complete, **commit + real content still
   needed** (§3) before calling this done.
2. ~~Help tab~~ — code-complete (§2), not yet committed (§6).
3. ~~Learn tab~~ — code-complete, **placeholder content** (draft concept explanation,
   placeholder video ID, placeholder references — §2), not yet committed (§6).
4. Download feature upgrade

Then: Quiz page enhancements (if any beyond the current General-Theory/This-Procedure
version — undefined, needs the user to scope), then the four innovation features.

**Text-to-Speech is already done** (§2) — it was in the original "later" queue in the
plan but has already been built; no action needed on it before moving to Download.

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
- **`PROMPT_LOG.md` now exists** (created this session, at the project root) — every
  phase from "Help Tab" onward is logged there with the literal prompt text; the three
  initial commits and the Day/Night+Developed-By phase are backfilled as reconstructed
  summaries (rebuilt from `git show` diffs and this file's own history, clearly marked as
  reconstructed since no literal prompt was recorded for them at the time). Keep
  appending to it — don't let it go stale again.
- **Day/Night + Developed By work is uncommitted** (detailed in §3) — the single biggest
  immediate risk right now: if this working tree is lost/reset before a commit, this
  entire phase's work (theming system, modal, contrast fixes) is gone.
- **Help tab work is also uncommitted** — `frontend/src/pages/HelpPage.jsx` (new),
  `Layout.jsx`/`App.jsx`/`App.css` (modified further on top of the already-uncommitted
  Day/Night changes). Same risk as the line above: nothing from this phase is in git
  history yet either.
- **Learn tab work is also uncommitted** — `frontend/src/pages/LearnPage.jsx` (new),
  `Layout.jsx`/`App.jsx`/`App.css` (modified further still, on top of both prior
  uncommitted phases), plus the new `PROMPT_LOG.md` at the root. Same risk again: three
  phases' worth of work now sit in the working tree with nothing in git history.
- **Developed By modal ships with placeholder content** (§3) — not a code bug, but will
  read as "unfinished" to a grader until real values are filled in.
- **Learn tab ships with placeholder content by design** (§2) — draft concept-explanation
  prose (unreviewed against the actual course rubric), a literal `YOUR_VIDEO_ID_HERE`
  video embed, and placeholder references in every category. All three are visibly
  flagged in the UI (a `DRAFT` badge and coral `PLACEHOLDER` badges) so this can't be
  mistaken for finished content, but it still needs a real video ID and real, verified
  references before submission.
- **Pre-existing mobile nav overflow, surfaced (not fixed) this session**: at ~400px
  viewport width the top nav (`.top-nav` in `App.css`, no `flex-wrap`) overflows
  horizontally instead of wrapping onto a second line. Confirmed via
  `git show HEAD:frontend/src/App.css` that the missing `flex-wrap` predates the Learn
  tab — adding an 8th nav item made an already-tight row overflow more visibly, but did
  not introduce the underlying issue. Left unfixed since it's shared header layout, not
  in scope for either the Help or Learn phase; worth a small dedicated fix later (e.g.
  `flex-wrap: wrap` on `.top-nav` itself, not just `.site-header-right`).
- **Download doesn't meet the stated requirement** (§4) — JSON-only export exists;
  PDF/Doc/Text + graph inclusion do not.
- **No frontend automated test suite** — `npm run lint` (oxlint) + `npm run build` are
  the only frontend correctness gates today; all frontend verification in this project's
  history has been manual/live-browser-driven (puppeteer-core scripts), not codified as
  regression tests. Not necessarily a problem for a course project, but worth knowing
  before assuming "the frontend is tested."
- **`/debug` timing was measured once**, this session (~30ms avg, well under the 2s
  budget — see `CLAUDE.md` §4) — not wired into CI/tests as an ongoing check. Re-measure
  after any interpreter/cursor/history changes.

---

## 7. Immediate next step

1. **Commit everything currently sitting uncommitted in the working tree** — Day/Night
   Mode + Developed By modal, the Help tab, and now the Learn tab (§3, §6) — this is the
   most time-sensitive item, everything else can wait, losing three phases of
   uncommitted work can't be undone.
2. Get the real student photo, name, and register number from the user and drop them
   into `DevelopedByModal.jsx` (replacing the three placeholders listed in §3/§6).
3. Get a real educational video (swap `YOUR_VIDEO_ID_HERE` in `LearnPage.jsx`) and real,
   verified references (replacing every badge-marked placeholder entry) for the Learn
   tab (§2/§6) — and have the concept-explanation draft reviewed against the actual
   course rubric.
4. Once all of the above are done, move to the **Download feature upgrade** next, per
   the agreed build order in §5.
