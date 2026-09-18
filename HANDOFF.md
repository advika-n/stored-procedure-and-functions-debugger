# HANDOFF.md

**A snapshot of exactly where the project stands right now.** Fully rewritten at the end
of every session, not appended to — it's a status board, not a diary. Session-by-session
history lives in `git log` and `PROMPT_LOG.md`; stable project facts live in `CLAUDE.md`
(`docs/features.md`/`docs/schema.md` for design detail).

**Last updated**: 2026-09-18, end of an "AI Practice — Competitive Exam Practice
Generator" session (`PROMPT_LOG.md` #31) — removed the standalone Quiz page entirely
(route, component, nav entry, `backend/app/quiz.py`, `POST /quiz/generate`,
`frontend/src/lastProcedure.js`) and replaced it with a new "AI Practice" tab (`/practice`)
and `backend/app/practice.py`: a general-purpose, GATE-DBMS-PYQ/placement-style MCQ
practice generator with a hardcoded fallback bank (unlike the old Quiz page, a Gemini
failure never surfaces as an error) and a two-attempt retry flow per question. Predict
Mode (in-debugger, `SqlConsolePage.jsx`) confirmed untouched throughout. Full rationale:
`docs/features.md`'s "AI Practice" section. Backend: `practice.py` new (replaced
`quiz.py`), suite **568 passing** (+16 net vs. 552, still 0 xfailed). Frontend:
`PracticePage.jsx` new (replaced `QuizPage.jsx`), `App.css`/`Layout.jsx`/`App.jsx`/
`vite.config.js`/`HelpPage.jsx` touched; `npm run lint`/`npm run build` both clean.

---

## Feature status

**Mandatory (5/5 done)**: Day/Night Mode · Developed By (real photo + name + register
number + Guided By) · Help tab (accurate for the merged page + AI Practice) · Learn tab
(real embedded video + real MySQL/Oracle reference citations) · Download (PDF/DOCX/Text
export).

**Innovation (2/4 done, 2 dropped)**: SQL Anti-Pattern Advisor · Side-by-Side Run
Comparison. **Variable Timeline — dropped** (#29; it had shipped and was removed, not
"never started"). **Live Parameter Tuning — dropped**, never started; don't pick either
back up without a fresh scoping prompt.

**Tier 1 (4/4 done)**: Breakpoints + Continue/Restart · `CALL` support · Call Stack
panel.

**Extras beyond original scope (all done)**: Text-to-Speech · Test-Case Runner ·
Extended Static Analysis Warnings (advisor: 6→10 checks across all phases) · Function
calls in expressions · CASE statement · LOOP/LEAVE · Persistent user database · Merged
Debugger/SQL Console page + SQL passthrough statements · Comparison operators
`>=`/`<=`/`<>` + `SELECT ... INTO` (backend grammar, full detail: `PROMPT_LOG.md` #26 /
`docs/features.md`) · Compact Procedure Library + control-bar/Variables-table density pass
(`PROMPT_LOG.md` #27) · Hover-flyout sample rail + Live State/editor rebalance
(`PROMPT_LOG.md` #28) · Sample-row overflow fix + centered Learn video (`PROMPT_LOG.md`
#29) · Download Report: real diagram image, no false ERROR labels, no Intermediate
Results (`PROMPT_LOG.md` #30) · **AI Practice** — replaces the standalone Quiz page with a
general-purpose, competitive-exam-style MCQ practice tool (this session — see below).

---

## This session's work — AI Practice (replaces the standalone Quiz page)

Full prompt + rationale: `PROMPT_LOG.md` #31, `docs/features.md`'s "AI Practice (replaces
the standalone Quiz page)" section.

1. **Removed the standalone Quiz page entirely** — not hidden/deprecated. Deleted:
   `backend/app/quiz.py`, `backend/app/tests/test_quiz.py`,
   `backend/app/tests/test_quiz_endpoint.py`, `POST /quiz/generate` +
   `QuizGenerateRequest` from `main.py`, `frontend/src/pages/QuizPage.jsx`, its `/quiz`
   route (`App.jsx`) and nav entry (`Layout.jsx`), and `frontend/src/lastProcedure.js`
   (its only consumer was the old Quiz page's "This Procedure" option — nothing else
   referenced it, including the `writeLastProcedure` call/effect that used to live in
   `SqlConsolePage.jsx`, also removed). **Predict Mode** (`SqlConsolePage.jsx`'s
   in-debugger toggle, internally still named `quiz-*` in its own state/class names —
   entirely separate from any of this) was checked untouched both before and after, live.

2. **Added `backend/app/practice.py`** — same Gemini client wiring as
   `app/explainer.py`/the old `quiz.py` (`_get_gemini_client`/`_GEMINI_MODEL`, reused not
   duplicated), same ask-for-JSON/strip-fence/retry-once-at-temp-0 two-strikes parsing
   pattern the old quiz generator used. The real behavior change:
   `generate_practice_questions` **always returns something** — unlike the old
   `/quiz/generate` (502 on any Gemini failure, no fallback), this one falls back to a
   hardcoded, hand-written `_FALLBACK_BANK` (split by difficulty, 8 questions each,
   covering procedures/functions/cursors/exception-handling/control-flow) sampled via
   `random.sample`/`random.choices`, same "never leave the user with a bare failure for a
   nice-to-have AI feature" principle `app/explainer.py`'s template fallback already uses
   for `/explain`. New `POST /practice/generate` (`{difficulty, numQuestions}`,
   `numQuestions` bounds-checked 1-15 via a pydantic `Field`).

3. **Added `frontend/src/pages/PracticePage.jsx`** (`/practice`, nav entry "AI Practice"
   in the same top-level nav list the old Quiz entry occupied) — a three-phase
   `setup → question → score` state machine. Setup: three large color-coded difficulty
   cards (teal=easy, amber=medium, coral=hard) + a stepper/slider for 1-15 questions +
   an animated-caret/skeleton loading state (no spinner). Question flow: the spec's
   two-attempt retry rule — a first wrong pick shows an amber "not quite, try again"
   banner and doesn't count against the score; only a second wrong pick on the same
   question is final (counts as incorrect, reveals the correct answer). Score screen:
   first-try/retry/incorrect breakdown chips + an expandable per-question review
   (`<details>`, same accessible pattern `HelpPage.jsx`'s accordion uses). Matching
   `App.css` section added (difficulty cards, stepper, generating caret/skeleton shimmer,
   option correct/wrong/tried states, score chips, review accordion) — fully
   theme-aware via existing CSS custom properties, no hardcoded colors.

4. **Two real bugs found and fixed live, neither caught by lint/build**:
   - A `str.format` / literal-`{`/`}` collision: the shared JSON-shape prompt text
     contains a real JSON example (literal braces), so calling `.format(count=...)` on it
     raised `KeyError` immediately on the first Gemini call. Fixed with a `__COUNT__`
     marker + `str.replace` instead of `str.format`.
   - A CSS specificity bug: the app's global `button:disabled { border-color: ...;
     color: ...; }` rule (a type+pseudo-class selector, specificity `(0,1,1)`) silently
     beat the new single-class `.practice-option-correct`/`-wrong`/`-tried` modifiers
     (`(0,1,0)`) on every answered (disabled) option — confirmed via `getComputedStyle`
     (an answered-correct option still showed `border-hairline`, not teal) before
     assuming the styling worked. Fixed with compound selectors
     (`.practice-option.practice-option-correct`, specificity `(0,2,0)`) rather than
     `!important` (unused elsewhere in this codebase). Re-verified via `getComputedStyle`
     for all three states (correct/wrong/tried) post-fix, in both themes.
   - Also caught (before it could ship broken): `frontend/vite.config.js`'s dev proxy
     still had a `/quiz` entry and no `/practice` one — Vite's proxy matches path
     *prefixes*, so `/practice/generate` 404'd from the dev server entirely until this
     was swapped. Same collision pattern the file already documents for
     `/debug`/`/history`/`/sql`.

**Testing added**: `backend/app/tests/test_practice.py` (JSON-shape validation,
fallback-bank sampling with/without replacement, Gemini-mocked success/retry/
double-failure-into-fallback, input validation) + `test_practice_endpoint.py` (request
shape, a real end-to-end no-key → fallback path through the actual endpoint, a
malformed-Gemini-response → fallback path, pydantic bounds validation).

**Verification**: backend suite **568 passing** (was 552), 0 xfailed. `npm run
lint`/`npm run build` both clean (same two pre-existing warnings as every recent
session). Live-verified via headless Chrome (Puppeteer-core + local Chrome, fresh
scratchpad `node_modules` — none was reused, all prior sessions' had been cleaned up)
against a freshly started dev backend+frontend (neither was already running — both had to
be started this session): nav shows "AI Practice" and no "Quiz" entry; direct-navigating
the old `/quiz` URL renders no quiz UI; Predict Mode confirmed still present/functional;
full setup → real-Gemini-generated question → a genuine wrong-then-correct retry (and,
across repeated runs, a genuine wrong-then-wrong-again final-incorrect path) → score
screen → expandable review → "Try Another Set" (difficulty kept) flow, in both Day and
Night mode; confirmed no horizontal overflow at 400px width. Screenshots taken and
inspected in both themes. Neither `debug_history.db` nor `user_data.db` touched this
session (`/practice/generate` has no history/user-db side effects).

---

## Testing infrastructure (see `CLAUDE.md` §6 for the mechanics)

- **Golden-trace regression harness** (`backend/app/tests/test_golden_traces.py` +
  `backend/app/tests/golden/*.json`, **21 fixtures**): runs every sample through the REAL
  `/debug` endpoint and diffs the resulting step trace against a checked-in baseline.
  **Run this before considering any future tokenizer/parser/interpreter-touching phase
  done.** Untouched this session (no `DebugStep`/interpreter changes — this was a
  frontend-page + standalone-endpoint swap only).
- **Property-based tests** (`backend/app/tests/test_property_based.py`, `hypothesis`):
  mutates the real samples via `demo_db.create_demo_connection()`; two invariants across
  1000 examples each.
- **Known-bugs tracker** (`backend/app/tests/test_known_bugs.py`): empty of unfixed bugs.
- **Hand-written grammar edge cases** (`backend/app/tests/test_grammar_edge_cases.py`).
- **AI Practice tests** (`backend/app/tests/test_practice.py` +
  `test_practice_endpoint.py`, new this session — replaced `test_quiz.py`/
  `test_quiz_endpoint.py`, deleted): see "This session's work" above.
- Backend suite: **568 passing, 0 xfailed** (was 552; +16 net this session — roughly
  30 quiz tests removed, ~30 practice tests added, plus overlap).

---

## Immediate next steps

1. SQL Anti-Pattern Advisor still doesn't analyze a `ProgramNode` AST at all (a
   `CALL`-based multi-procedure source always shows "no issues"); Download/Compare have
   never been exercised against one either. Pre-existing, unrelated to recent sessions.
2. The SQL Console (whether reached via the flat results view or the debugger UI's `sql`
   step panel) executes exactly one statement per Run click — running multiple
   `;`-separated statements at once fails cleanly rather than running any of them.
   Deliberate scope boundary, not a bug; worth a fresh scoping prompt if multi-statement
   support is ever wanted. Applies equally to `SELECT ... INTO` (one lookup per statement).
3. No server-side constraint enforcement (NOT NULL/PRIMARY KEY) or variable interpolation
   for SQL passthrough statements (`SqlStatement` or `SelectIntoStatement`) — a real,
   documented, deliberate capability loss versus an earlier phase's retired simulated
   feature. If a future phase wants either back, it needs its own scoping.
4. `SELECT ... INTO`'s zero-row NOT_FOUND path assigns no target variable at all (they
   keep whatever value they held before) — same convention an exhausted cursor FETCH
   already has, deliberate and tested, not a gap.
5. Both `.panel-samples`'s `max-height: 560px` (rail/flyout scroll cap, from #27) and the
   grid's `60px`/`2fr`/`0.8fr` column split (#28) are fixed values tuned to that session's
   own editor/content proportions — if a future phase changes what sits above the editor
   (taller Monaco, more controls) or the Live State panel's typical content width, re-check
   these rather than assuming they still balance correctly.
6. `getSampleInitials`'s PascalCase-capital-letter extraction can collide for two samples
   that happen to share their first two capitals (not currently the case among the 21
   samples, checked by eye, but worth a glance whenever a new sample is added) — a
   collision is a cosmetic ambiguity in the rail only, not a functional bug.
7. `.sample-card`/`.rail-item` carry `flex-shrink: 0` (#29) so a height-constrained
   `.sample-list` never squeezes a row below its own content height — if a future phase
   adds any other row-style list inside a height-capped flex column, check it for the same
   squeeze rather than assuming `min-height` alone is a safe floor.
8. The exported diagram image (`svgToPng.js`'s `foreignObjectsToSvgText`) is a close
   visual approximation of the on-screen Mermaid diagram, not a pixel-perfect one — line
   wrapping is approximated with a fixed line height rather than Mermaid's own
   font-metric-based wrapping logic, and a `CALL` node currently just labels itself
   "CallStatement". Good enough for a report figure; revisit only if a future session
   wants pixel parity specifically.
9. `svgToPng.js`'s `foreignObjectsToSvgText`/`shrinkTextNodesToFit` were built and
   verified against THIS app's specific Mermaid output shape — if a future phase changes
   Mermaid version, diagram type, or theme config, re-verify this conversion still finds
   the right text/colors rather than assuming it degrades gracefully.
10. **AI Practice has no persistence of past sessions/history** (flagged, not built —
    explicitly out of scope this phase). A future phase wanting it needs its own scoping
    (where to store results, whether per-viewer, etc.) rather than assuming it slots into
    `history.py`'s existing debug-run history, which is a different shape entirely.
11. `practice.py`'s `_FALLBACK_BANK` is static/hand-written (8 questions per difficulty) —
    a user who exhausts Gemini and generates many sets in a row at the same difficulty
    will start seeing repeats (samples with replacement once `numQuestions` exceeds the
    bank size, e.g. asking for 15 at once already does). Acceptable for a fallback path,
    not the primary path, but worth knowing if a future session wants to grow the bank.
12. The **general CSS lesson from this session's specificity bug is worth remembering for
    any future page**: a modifier class meant to override styling on a `<button
    disabled>` (or any element the app's existing global `button`/`button:disabled`
    rules already target) needs a compound selector (`.base-class.modifier-class`) to
    reliably outrank those global rules — a bare single-class modifier can silently lose.

---

## Live gotchas

- **A CSS modifier class on a `<button disabled>` can silently lose to this app's global
  `button:disabled` rule** (App.css, top of file) — that rule's specificity `(0,1,1)`
  (type selector + pseudo-class) beats a single custom class `(0,1,0)`, regardless of
  source order. Confirmed live via `getComputedStyle`, not assumed from reading the CSS.
  Fix: make the modifier a compound selector with the element's base class
  (`.base-class.modifier-class`, specificity `(0,2,0)`), not a bare `.modifier-class`.
  See AI Practice's `.practice-option-correct`/`-wrong`/`-tried` this session.
- **`str.format()` cannot be used on a prompt-instruction string that itself contains a
  literal JSON example** (real `{`/`}` characters) — Python tries to interpret every
  brace pair as a format field and raises `KeyError` on the first one it doesn't
  recognize. Use a unique marker (e.g. `__COUNT__`) + `str.replace()` instead whenever a
  template string needs one substitution but also contains literal braces elsewhere. See
  `practice.py`'s `_JSON_SHAPE_INSTRUCTIONS`/`_build_system_prompt`.
- **Vite's dev proxy (`vite.config.js`) matches config keys as path PREFIXES, not exact
  paths** — adding a new page route AND a same-named API path prefix (e.g. `/practice`
  page + `/practice/generate` endpoint) needs its own proxy entry with the
  `bypassNavigations` guard, same as the existing `/debug`/`/history`/`/sql` entries.
  Forgetting this 404s the API call from the dev server with no other symptom — easy to
  miss without live-verifying an actual fetch, not just a page load. Removing a page+
  endpoint pair (like the old Quiz page) means removing its proxy entry too, not just the
  route/component.
- **Both dev servers may not be running at the start of a new session** — this session,
  neither `uvicorn`/`npm run dev` was up; always `curl`/`netstat` before assuming either
  is already running rather than trusting a previous session's HANDOFF note. Restarting
  is `uvicorn app.main:app --port 8000` (from `backend/`, `.venv/Scripts/python.exe -m
  uvicorn ...` on Windows) and `npm run dev` (from `frontend/`) — and after any
  `vite.config.js` edit, the Vite dev server needs an actual restart (not just a file
  save) to pick up new/changed proxy entries.
- **A `<foreignObject>`-containing SVG permanently taints a `<canvas>` once drawn via
  `<img>` + `drawImage`** — `canvas.toDataURL()`/`toBlob()` then throws `SecurityError:
  Tainted canvases may not be exported`, confirmed live, regardless of the image source
  being a same-origin blob URL. This is a hard browser restriction, not fixable by
  tweaking the SVG markup or trying `flowchart.htmlLabels: false` (confirmed NOT to
  actually suppress `<foreignObject>` in Mermaid v11 — a known upstream limitation, not a
  config mistake). If you need to rasterize a Mermaid diagram (or any `<foreignObject>`-
  bearing SVG) client-side again, don't re-attempt the `<img>`+canvas route on the raw
  SVG — see `svgToPng.js`'s `foreignObjectsToSvgText` for the actual working approach
  (strip `<foreignObject>` to plain `<text>` first).
- **html2canvas does not reliably rasterize this app's Mermaid SVG output** — it runs
  without error but silently produces a 100%-blank white canvas (confirmed by sampling
  pixel data directly, not just eyeballing a screenshot). Don't reach for it again for
  this specific diagram-export use case without re-verifying against pixel data first.
- **An SVG presentation attribute (`fill="..."`, `stroke="..."`, etc.) loses to ANY
  matching rule in an embedded/external `<style>` block, even a plain non-`!important`
  one** — confirmed live: `text.setAttribute('fill', '#1a1a1a')` was silently overridden
  by Mermaid's own `#flowchart-1{fill:#edeff4}` rule. An inline `style="fill:..."`
  (`element.style.fill = ...`) does win. Relevant to any future code that builds/modifies
  SVG programmatically in this app.
- **`SVGTextElement.getComputedTextLength()`/`getBBox()` return 0 (or throw) on a
  detached DOM node** — real layout is required, so measuring text on a `cloneNode(true)`
  copy before it's ever attached anywhere silently gives wrong answers rather than an
  error. `svgToPng.js`'s `shrinkTextNodesToFit` temporarily attaches its clone
  off-screen (`position:fixed; left:-99999px; visibility:hidden`) specifically for this.
- **reportlab (PDF) refuses to lay out any `Flowable` — including an `Image` — that's
  taller than a full page's own frame height, even a fresh, otherwise-empty page** (a
  "Flowable ... too large ... in frame" exception, which fails the ENTIRE PDF build, not
  just that one element). Scale any variably-sized image by both width AND height ratios
  (`min()` of both), never width alone — see `render_pdf`'s `content_height`.
- **Puppeteer `fullPage: true` screenshots can show a stale "ghost" of a just-collapsed
  CSS-opacity-transitioned element** even when `getComputedStyle` confirms the correct
  hidden state at the same moment. Workaround: a fresh `browser.newPage()` per `fullPage`
  capture, or `fullPage: false` (this session used fixed-viewport, non-fullPage shots).
- **`backend/data/debug_history.db` needs manual cleanup after any live-verification
  session that actually clicks Run** (on a procedure/function trace) — it auto-rotates at
  50 rows but real `/debug` calls during manual testing still show up; delete test-run
  rows afterward (`DELETE /history/{id}` while the backend is up). Not needed this
  session (`/practice/generate` never calls `/debug` or writes history).
- **`backend/data/user_data.db` is a similarly real, persistent artifact** — any live
  verification that runs CREATE TABLE/INSERT/UPDATE/DELETE against the real backend
  leaves real rows/tables behind if not cleaned up. Not needed this session (AI Practice
  never touches it).
- Puppeteer-core + a local Chrome install (`C:\Program Files\Google\Chrome\Application\
  chrome.exe`) is the live-verification approach in use. Scratchpad `node_modules` from
  prior sessions are NOT persistent (all had been cleaned up by this session's start) —
  expect to `npm install puppeteer-core@latest` fresh each session rather than assuming a
  reusable install is still there; it installs in a few seconds so this isn't costly.
- `found`/`notfound` are reserved KEYWORDs in this grammar (the `cur_name%FOUND`/
  `cur_name%NOTFOUND` cursor-attribute suffix) — a variable or OUT parameter literally
  named `found` fails to parse with a confusing "Expected IDENTIFIER (got KEYWORD)"
  error; use `was_found`/`matched`/similar instead.
- Mobile nav overflows horizontally at ~400px width — actually NOT reproduced this
  session (`.top-nav` has `flex-wrap: wrap` already, confirmed via a live
  `scrollWidth`/`clientWidth` check at exactly 400px on `/practice`, `/sql-console`, and
  the nav itself); a prior HANDOFF's note calling this a live pre-existing bug may be
  stale — re-verify with an actual measurement (not eyeballing) before treating it as
  still open.
