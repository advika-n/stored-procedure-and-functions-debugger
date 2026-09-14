# CLAUDE.md

Persistent context for this repo — read this first, then **read `HANDOFF.md` immediately
after** for current status before making any changes (see §7).

This file describes what the project *is* and how it's built; it should rarely change and
should stay short — high-level orientation, not implementation documentation. Detailed
per-feature design rationale lives in `docs/features.md`; the `DebugStep` wire-contract
field breakdown and performance-timing history live in `docs/schema.md`. Day-to-day
status, in-progress work, and known bugs belong in `HANDOFF.md`, not here.

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
- **Frontend**: React 19 + Vite, Monaco Editor, Mermaid.js (flowcharts), React Router.
- **AI**: Google Gemini (`gemini-flash-lite-latest`), with a deterministic template
  fallback. Client wiring lives once in `explainer.py`, reused by `quiz.py`.
- **Core pipeline**: `tokenizer.py` → `parser.py` (hand-rolled recursive-descent) → AST
  (plain dicts) → `interpreter.py` (tree-walking) → a `DebugStep` trace — the central
  wire contract every frontend feature reads; full shape in `docs/schema.md`.
- **Execution is simulated, not a real DB engine** — the interpreter evaluates
  DECLARE/SET/IF/WHILE/CASE/LOOP/cursors/handlers itself; only cursor `SELECT` queries
  hit real SQLite, against a small fixed auto-seeded dataset (`demo_db.py`:
  `products(name, price)`, 3 rows) — no schema-authoring feature.
- **SQLite has two unrelated jobs**: `history.py` (on-disk, persists the 50 most recent
  successful `/debug` runs) vs. `demo_db.py` (ephemeral `:memory:` per request, cursor
  queries only).

**Shipped features** (full rationale in `docs/features.md`): Breakpoints +
Continue/Restart · SQL Anti-Pattern Advisor (`advisor.py`, nine AST checks, rides on
`/debug` as `issues`) · Side-by-Side Run Comparison (`/compare`) · Report export
(`/debug/report`, PDF/DOCX/TXT) · `CALL` support (procedure-calling-procedure) ·
Function calls in expressions (`FunctionCallExpr`, reuses `CALL`'s scope isolation) ·
CASE statement (reuses IF's `branch` field) · LOOP / LEAVE (optionally labeled, reuses
WHILE's iteration guard + `loop` field).

### Backend file map (`backend/app/`)
`tokenizer.py` text→tokens · `parser.py` tokens→AST · `interpreter.py` AST→`DebugStep`s
· `advisor.py` static Advisor (`analyze(ast)`) · `explainer.py` Gemini client + `/explain`
+ `/ask` · `quiz.py` MCQ quiz gen · `demo_db.py` ephemeral cursor dataset · `history.py`
persistent run history · `report.py` PDF/DOCX/TXT export · `main.py` FastAPI routes ·
`tests/` one `test_*.py` per module/route.

### Endpoints
`GET /health` · `POST /debug` · `POST /debug/report` · `POST /explain` · `POST /ask` ·
`POST /quiz/generate` · `GET|DELETE /history[/{id}]`

### Frontend file map (`frontend/src/`)
`App.jsx` routes · `Layout.jsx` header/nav · `ThemeContext.jsx` Day/Night (§3) ·
`theme.css`/`App.css` styling · `mermaidColors.js` JS-mirrored theme hex (Mermaid can't
read CSS vars) · `cfg.js` AST→Mermaid flowchart · `svgToPng.js` flowchart rasterization
for Download · `compareTraces.js` pure trace diff · `samples.js` sample library ·
`pages/DebuggerPage.jsx` main UI · `pages/ComparePage.jsx`, `QuizPage.jsx`,
`TestRunnerPage.jsx`, `HistoryPage.jsx`, `HelpPage.jsx`, `LearnPage.jsx` — one per route
· `Theory.jsx`/`theoryContent.jsx` `/theory` (distinct from Learn: no video/references).

### Known repo cruft
`New/` at the project root is a stray, fully-duplicated snapshot of an earlier
backend+frontend state (~54 files, tracked in git). Not referenced by any build/run
script, not part of the live app. Leave it alone unless explicitly asked to remove it.

---

## 3. Design system — "Debugger Notebook"

Dark navy palette is the default/Night theme. Fonts: **IBM Plex Mono** (code/data) +
**Space Grotesk** (display) + IBM Plex Sans (body). Exactly three semantic accents
(amber/teal/coral), hairline borders instead of shadows, flat surfaces, an animated
gutter caret (`▸`, `.editor-caret` in `App.css`) that glides to the current line as you
step.

**Day/Night Mode** is CSS-custom-property-driven, not per-component overrides. Every
token is defined twice in `frontend/src/theme.css`: once on bare `:root` (dark/Night,
default) and once under `:root[data-theme="light"]`. `ThemeContext.jsx`
(`ThemeProvider`/`useTheme()`) tracks which is active, persists to `localStorage`
(`spdebugger:theme`), applies via a `data-theme` attribute on `<html>`.
`frontend/index.html` has a tiny inline script that applies the stored value before
first paint to avoid a flash of the wrong theme.

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
the original bright hue as a translucent wash — verified with the actual WCAG contrast
formula against real composited backgrounds, not assumed (see comments in `theme.css`
above the light block).

**Monaco and Mermaid do not read CSS custom properties** — Monaco needs its `theme` prop
switched explicitly (`vs-dark` / `vs`), and Mermaid's `classDef`/`linkStyle` mini-grammar
**rejects `var(...)` outright** (confirmed by hitting the parse error directly — don't
attempt to pass a CSS variable into a Mermaid color string again). `mermaidColors.js`
hand-mirrors the same dark/light hex values in JS for this reason; keep it in sync with
`theme.css` by hand when either changes.

---

## 4. Key technical facts to preserve

- **`DebugStep` is the central contract** every frontend feature reads (step navigator,
  variables, flowchart, explanations, Ask AI, Predict Mode, History, Export). Changing a
  field ripples across the whole frontend. Full shape: **see `docs/schema.md`**.
- **Gemini explainer needs complete context** — `explainer.py`'s `_build_prompt()`
  forwards a step's `error`/`cursor` fields so failed/handled steps get explained
  correctly, not generically. Trimming what's sent to `/explain` silently degrades this
  with no automated check — review by hand.
- **`/debug` must stay under 2s** — comfortably met (~30ms live; every
  interpreter-touching phase since re-measures in-process, stays well under 1ms). Re-time
  and log **in `docs/schema.md`** if the interpreter/cursor/history-write path changes.

---

## 5. Mandatory course-graded website sections

These five are graded requirements. **Status of each (done/in-progress/not-started) is
tracked in `HANDOFF.md`, not here** — this section only defines what's required:

1. **Learn tab** — concept explanation + video + references, positioned top-right in nav.
   Not the same as the existing `/theory` page (write-ups, no video, no references
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
  prompt text, in chronological order. Keep appending to it at the end of each phase;
  don't let it go stale.
- **Testing**: backend has a thorough pytest suite (`backend/app/tests/`, one file per
  module/endpoint) — run via `cd backend && .venv/Scripts/python.exe -m pytest -q` (or
  activate the venv first). Frontend has no test suite, only `npm run lint` (oxlint) and
  `npm run build` as the correctness gate — treat both as required before considering a
  frontend phase done.
- **Live-verification habit**: this project's sessions have consistently driven the
  actual running app (headless Chrome from the scratchpad — via puppeteer-core when
  available, or a small dependency-free raw-CDP driver script over Node's native
  `fetch`/`WebSocket` when it isn't) to confirm UI changes really work, and measured
  things (contrast ratios, endpoint timing) rather than assuming — continue that
  standard.

---

## 7. Instruction to future Claude Code sessions

**Always read `HANDOFF.md` immediately after this file**, before making any changes, to
get the actual current status of every section above, in-progress work, and known
bugs/TODOs. This file (`CLAUDE.md`) intentionally does not track that — it will go stale
if status gets written here instead of there. When adding a new shipped feature, add a
one-line summary + bullet under §2's "Shipped features" list here, and put the full
design rationale in `docs/features.md` — don't let the detailed narrative creep back into
this file.
