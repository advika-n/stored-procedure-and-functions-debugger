# HANDOFF.md

**A snapshot of exactly where the project stands right now.** This file gets
overwritten/updated at the end of every session — it is not a cumulative log. For
stable project facts (architecture, schema, design tokens) see `CLAUDE.md` instead.

---

## 1. Last updated

**2026-09-13**, end of the session that created this file and `CLAUDE.md`, immediately
following the session that built Day/Night Mode + the Developed By modal.

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

- **Help tab** — full user manual. No file, no route, no nav entry exists.
- **Learn tab** — concept explanation + video + references, top-right nav. No file, no
  route, no nav entry exists. (The existing `/theory` page is *not* this — six
  write-ups, no video, no references section, not positioned top-right. It may be
  reusable source material, but the Learn tab itself is unbuilt.)
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
2. Help tab
3. Learn tab
4. Download feature upgrade

Then: Quiz page enhancements (if any beyond the current General-Theory/This-Procedure
version — undefined, needs the user to scope), then the four innovation features.

**Text-to-Speech is already done** (§2) — it was in the original "later" queue in the
plan but has already been built; no action needed on it before moving to Help/Learn/
Download.

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
- **No AI prompt log exists.** Checked for `PROMPT_LOG.md`, a `docs/` folder, or any
  equivalent under version control — none found anywhere in the repo. This is listed as
  a required deliverable in the working conventions but isn't being kept. Needs a file
  created and then actually maintained going forward.
- **Day/Night + Developed By work is uncommitted** (detailed in §3) — the single biggest
  immediate risk right now: if this working tree is lost/reset before a commit, this
  entire phase's work (theming system, modal, contrast fixes) is gone.
- **Developed By modal ships with placeholder content** (§3) — not a code bug, but will
  read as "unfinished" to a grader until real values are filled in.
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

1. **Commit the Day/Night Mode + Developed By modal work** currently sitting uncommitted
   in the working tree (§3) — this is the most time-sensitive item, everything else can
   wait, losing this can't be undone.
2. Get the real student photo, name, and register number from the user and drop them
   into `DevelopedByModal.jsx` (replacing the three placeholders listed in §3/§6).
3. Once both of the above are done, Day/Night + Developed By is genuinely finished —
   move to the **Help tab** next, per the agreed build order in §5.
