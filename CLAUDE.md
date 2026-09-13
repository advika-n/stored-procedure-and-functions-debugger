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
- **Core pipeline**: `backend/app/tokenizer.py` → `backend/app/parser.py` (hand-rolled
  recursive-descent — chosen deliberately over a parser-generator for documentation
  clarity/control, matching this project's Documentation grading criterion) → AST (plain
  dicts, JSON-serializable) → `backend/app/interpreter.py` (tree-walking) → a
  `DebugStep` trace (see §4).
- **Execution is simulated, not hooked into a real DB engine.** The interpreter
  evaluates procedural-SQL constructs (DECLARE/SET/IF/WHILE/cursors/handlers) itself; the
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
| `explainer.py` | Gemini client wiring + per-step explanation (`/explain`) + free-form Q&A (`/ask`) + template fallback |
| `quiz.py` | Gemini-backed 5-question MCQ quiz generation (`/quiz/generate`), reuses `explainer.py`'s client |
| `demo_db.py` | Ephemeral cursor demo dataset |
| `history.py` | Persistent run history (SQLite) |
| `main.py` | FastAPI app + all routes |
| `tests/` | pytest suite, one `test_*.py` per module above plus `test_*_endpoint.py` per route |

### Endpoints (`backend/app/main.py`)
`GET /health` · `POST /debug` · `POST /explain` · `POST /ask` · `POST /quiz/generate` ·
`GET /history` · `GET /history/{id}` · `DELETE /history/{id}` · `DELETE /history`

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
| `lastProcedure.js` | sessionStorage bridge: lets `/quiz`'s "This Procedure" option see the Debugger's current code without a global store |
| `samples.js` | Built-in sample procedures/functions shown in the Debugger's library panel |
| `pages/DebuggerPage.jsx` | The main debugger UI — editor, step navigator, variables, flowchart, Predict Mode, Ask AI, TTS |
| `pages/QuizPage.jsx` | Standalone `/quiz` page (distinct from Predict Mode — see below) |
| `pages/HistoryPage.jsx`, `History.jsx` | `/history` page |
| `pages/HomePage.jsx`, `pages/AboutPage.jsx` | Landing + About |
| `Theory.jsx`, `theoryContent.jsx`, `theoryTopics.js` | `/theory` page — concept write-ups with runnable examples (six topics). **Not** the same as the still-missing "Learn tab" mandatory section — see §5. |

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
    branch?:   { condition, result, path },        // IfStatement steps only
    loop?:     { condition, result, iteration },    // WhileStatement steps only
    cursor?:   { name, rowIndex, currentRow, hasMore },
    error?:    { condition, message, handler },
    returnValue?: { value, type }                   // FunctionNode final RETURN only
  }
  ```
  (`variables` entry shape is built by `_snapshot_variables()`, ~line 798 of the same file.)

- **Gemini explainer accuracy depends on complete context.** `explainer.py`'s
  `_build_prompt()` (~line 82) explicitly forwards a step's `error` and `cursor` fields
  into the prompt, with an `"IMPORTANT --"` steering line when an error/handler fired —
  this is what makes NOT_FOUND/DIVISION_BY_ZERO steps get explained as "this failed and
  was caught" rather than a generic "a statement ran". If any future change trims what
  gets sent to `/explain` (e.g. stripping `error`/`cursor` before the request), Gemini's
  explanations on those steps will silently degrade to wrong/generic text — there is no
  automated check that would fail if this regresses, so review this by hand.

- **Non-functional requirement: `/debug` must stay under 2s.** Measured directly against
  a live local server (all 10 built-in `samples.js` procedures, via a Python timing
  script against `POST http://127.0.0.1:8000/debug`): **22.5–76.2ms per call, ~30ms
  average** — comfortably under budget today. This has *not* been re-verified since;
  re-time it (same approach: loop the sample list, hit `/debug`, measure wall time) if
  the interpreter, cursor handling, or history-write path changes meaningfully, and note
  the new numbers here as the deliverable.

---

## 5. Mandatory course-graded website sections

These five are graded requirements. **Status of each (done/in-progress/not-started) is
tracked in `HANDOFF.md`, not here** — this section only defines what's required:

1. **Learn tab** — concept explanation + video + references, positioned top-right in nav.
   Not the same as the existing `/theory` page (six write-ups, no video, no references
   section, not top-right) — that page may be reusable content, but the Learn tab itself
   doesn't exist yet.
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
- **AI prompt log**: stated as a required deliverable, but **no dedicated log file
  currently exists in this repo** (checked: no `PROMPT_LOG.md`, no `docs/` folder, no
  equivalent anywhere under version control). This is a real gap, not just undocumented —
  see `HANDOFF.md`'s known-issues list. If/when one is created, update this section with
  its actual path.
- **Testing**: backend has a thorough pytest suite (`backend/app/tests/`, one file per
  module/endpoint) — run via `cd backend && .venv/Scripts/python.exe -m pytest -q` (or
  activate the venv first). Frontend has no test suite, only `npm run lint` (oxlint) and
  `npm run build` as the correctness gate — treat both as required before considering a
  frontend phase done.
- **Live-verification habit**: this project's sessions have consistently driven the
  actual running app (via a headless-Chrome puppeteer-core script from the scratchpad,
  not just unit tests) to confirm UI changes really work, and measured things (contrast
  ratios, endpoint timing) rather than assuming — continue that standard.

---

## 7. Instruction to future Claude Code sessions

**Always read `HANDOFF.md` immediately after this file**, before making any changes, to
get the actual current status of every section above, in-progress work, and known
bugs/TODOs. This file (`CLAUDE.md`) intentionally does not track that — it will go stale
if status gets written here instead of there.
