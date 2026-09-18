# HANDOFF.md

**A snapshot of exactly where the project stands right now.** Fully rewritten at the end
of every session, not appended to — it's a status board, not a diary. Session-by-session
history lives in `git log` and `PROMPT_LOG.md`; stable project facts live in `CLAUDE.md`
(`docs/features.md`/`docs/schema.md` for design detail).

**Last updated**: 2026-09-18, end of a frontend-only "Hover-flyout sample rail + trim Live
State + wider editor" session (`PROMPT_LOG.md` #28) — the Procedure Library column
collapsed from a 220px compact list to a 60px icon rail (kind badge + PascalCase initials
per row) that flies out to a 250px absolute-positioned overlay on hover/focus, the Live
State column narrowed ~16%, and the editor claimed the freed width. No backend/interpreter/
`DebugStep`-contract changes — backend suite re-run specifically to confirm this: still
**552 passing**, unchanged. `npm run lint`/`npm run build` both clean.

---

## Feature status

**Mandatory (5/5 done)**: Day/Night Mode · Developed By (real photo + name + register
number + Guided By) · Help tab (accurate for the merged page) · Learn tab (real embedded
video + real MySQL/Oracle reference citations) · Download (PDF/DOCX/Text export, all three
confirmed to produce valid non-empty files). All five confirmed via a full functional
audit three sessions ago — see `PROMPT_LOG.md` #25 for the pass/fail list.

**Innovation (3/4 done, 1 dropped)**: SQL Anti-Pattern Advisor · Side-by-Side Run
Comparison · Variable Timeline · Live Parameter Tuning — **dropped**, don't pick back up
without a fresh scoping prompt.

**Tier 1 (4/4 done)**: Breakpoints + Continue/Restart · `CALL` support · Call Stack
panel.

**Extras beyond original scope (all done)**: Text-to-Speech · Test-Case Runner ·
Extended Static Analysis Warnings (advisor: 6→10 checks across all phases) · Function
calls in expressions · CASE statement · LOOP/LEAVE · Persistent user database · Merged
Debugger/SQL Console page + SQL passthrough statements · Comparison operators
`>=`/`<=`/`<>` + `SELECT ... INTO` (backend grammar, full detail: `PROMPT_LOG.md` #26 /
`docs/features.md`) · Compact Procedure Library + control-bar/Variables-table density pass
(`PROMPT_LOG.md` #27) · Hover-flyout sample rail + Live State/editor rebalance (this
session — see below).

---

## This session's work — Hover-flyout sample rail + trim Live State + wider editor

Frontend-only, `SqlConsolePage.jsx` + `App.css` only. Builds directly on the prior
session's compact list (#27), replacing its always-visible 220px column with a
collapsed rail + hover flyout, and rebalances the other two columns around it. Full
prompt + rationale: `PROMPT_LOG.md` #28.

- **Collapsed rail** (`.sample-rail`, always in the document flow — this is what actually
  defines the grid's first column at 60px): each row is a small `.rail-item` showing only
  a colored initials chip (`getSampleInitials` in `SqlConsolePage.jsx` — pulls the capital
  letters out of a PascalCase sample name, e.g. `OperatorShowcase` → "OS"), since the kind
  badge alone isn't distinguishing (most samples share a kind) and there's no room for a
  name at 60px. Full name + description still reach a mouse user via `title` and a screen
  reader via `aria-label`.
- **Hover/focus flyout** (`.sample-flyout`): a second, always `position: absolute` copy of
  the same list (full badge + wrapped name, same click handlers) anchored at the rail's own
  border-box top-left corner, width 250px. Pure CSS — opacity/visibility/pointer-events
  toggle on `.panel-samples:hover`/`:focus-within` (the `:focus-within` half is a keyboard-
  accessibility bonus a pure-hover implementation wouldn't have had for free), with a
  `transition-delay` on the closing (non-hover) state giving ~200ms of "forgiveness" before
  it collapses — no JS timers needed. Because it's *always* absolutely positioned (never
  toggled in/out of flow), opening it never reflows the grid/editor — verified directly via
  a Puppeteer measurement of `.panel-editor`'s `left` before/after hover.
- **Two nonobvious fixes along the way** (see `PROMPT_LOG.md` #28 for the full mechanism):
  (1) `top:0; left:0` on an absolutely-positioned child aligns to the *padding* box of its
  containing block, not the *border* box — the flyout needed `top: -1.5rem; left: -0.4rem`
  (matching `.panel-samples`'s own padding) to actually cover the rail's border/tab instead
  of leaving a sliver of it showing above the flyout. (2) Long PascalCase names wrap via a
  `<wbr/>` inserted before each internal capital letter (`renderWrappableName`) so a wrapped
  name breaks at a word boundary (`Calculate` / `Total`) instead of an arbitrary character
  (`CalculateTota` / `l`, what bare `overflow-wrap: break-word` alone produced).
- **Column rebalance**: `.debugger-grid` changed from `220px minmax(0,1.6fr)
  minmax(280px,1fr)` to `60px minmax(0,2fr) minmax(230px,0.8fr)` — Live State narrowed
  ~16% (measured: 478px → 359px at a 1500px viewport) with tighter panel padding
  (`.panel-state`'s own horizontal padding 1.25rem → 1rem), and the editor claimed both the
  rail's freed ~160px and Live State's reduction (measured: ~766px → ~898px at the same
  viewport).
- **Mobile breakpoint** (`max-width: 1000px`, where the grid already collapses to one
  stacked column): the rail is `display: none` and the flyout's absolute positioning/
  opacity/transition are all stripped back to normal in-flow/always-visible — i.e. it
  becomes exactly the prior session's plain compact list again, since a hover flyout has
  no equivalent on a touch device with no pointer.
- **Did not touch**: the top nav bar, Call Stack/Explanation/breakpoint-gutter/Predict Mode
  behavior, the Variables table's Name/Type/Value columns (from #27, untouched), any
  backend file, the `/debug` contract.

**Verification**: `npm run lint`/`npm run build` clean (same two pre-existing warnings as
every recent session, unrelated). Backend suite re-run: **552 passing**, unchanged,
confirming frontend-only. Live-checked via Puppeteer (reused an existing scratchpad's
`node_modules` + local Chrome) against `/sql-console`: measured rail width (60px) and
column widths pre/post; confirmed `.panel-editor`'s left offset is bit-for-bit identical
hovering vs. not (no reflow); confirmed collapsed-state opacity/pointer-events are 0/none
and hovered-state are 1/auto; confirmed the mobile fallback (rail hidden, flyout static,
all 21 full-name rows visible, no clipping). Screenshotted collapsed rail, expanded rail,
and full layout in both Day and Night mode, plus the 400px mobile breakpoint — see the
next paragraph for one real finding this session's screenshot verification caught (and
ruled out as tooling, not product).

**A live-verification finding worth recording**: this session's Puppeteer screenshots
intermittently showed a "ghost" — the flyout's full-name rows faintly double-exposed over
the collapsed rail — in `fullPage: true` captures taken on a page that had already fired
the hover-flyout's CSS opacity transition earlier in that same page's lifetime, especially
after several rapid state changes (theme toggle + sample click + Run in quick succession).
Chased down methodically rather than dismissed: `getComputedStyle` queried at the exact
screenshot moment consistently reported the correct hidden state (`opacity: 0`,
`pointer-events: none`) even when the captured PNG showed the ghost, and the ghost never
once appeared in a `fullPage: false` (viewport-only) screenshot taken at the same moment,
nor in a `fullPage: true` screenshot on a *fresh* page/tab with no prior hover history.
Conclusion: a stale-compositor-tile race specific to Puppeteer/CDP's full-page capture
stitching after a CSS opacity transition has fired, not a real rendering bug — no real user
action triggers that capture path. Worked around for this session's own screenshots by
using a fresh page per `fullPage` capture and a short settle delay (forced reflow +
scroll-nudge) after rapid interactions before capturing; see Live gotchas below for future
sessions.

---

## Testing infrastructure (see `CLAUDE.md` §6 for the mechanics)

- **Golden-trace regression harness** (`backend/app/tests/test_golden_traces.py` +
  `backend/app/tests/golden/*.json`, **21 fixtures**): runs every sample through the REAL
  `/debug` endpoint and diffs the resulting step trace against a checked-in baseline.
  **Run this before considering any future tokenizer/parser/interpreter-touching phase
  done.** Untouched this session (frontend-only).
- **Property-based tests** (`backend/app/tests/test_property_based.py`, `hypothesis`):
  mutates the real samples via `demo_db.create_demo_connection()`; two invariants across
  1000 examples each.
- **Known-bugs tracker** (`backend/app/tests/test_known_bugs.py`): empty of unfixed bugs.
- **Hand-written grammar edge cases** (`backend/app/tests/test_grammar_edge_cases.py`).
- Backend suite: **552 passing, 0 xfailed** — unchanged this session (confirmed by
  re-running it specifically to verify the frontend-only claim).

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
   grid's `60px`/`2fr`/`0.8fr` column split (this session) are fixed values tuned to this
   session's own editor/content proportions — if a future phase changes what sits above the
   editor (taller Monaco, more controls) or the Live State panel's typical content width,
   re-check these rather than assuming they still balance correctly.
6. `getSampleInitials`'s PascalCase-capital-letter extraction can collide for two samples
   that happen to share their first two capitals (not currently the case among the 21
   samples, checked by eye, but worth a glance whenever a new sample is added) — a
   collision is a cosmetic ambiguity in the rail only (the flyout and `aria-label` are
   always unambiguous), not a functional bug, since rail rows still resolve to the correct
   sample on click regardless of what their initials show.

---

## Live gotchas

- **Puppeteer `fullPage: true` screenshots can show a stale "ghost" of a just-collapsed
  CSS-opacity-transitioned element** (this session's hover flyout, but likely any element
  using `opacity`/`transition-delay` for a hover/focus reveal) even when `getComputedStyle`
  confirms the correct hidden state at the same moment — see this session's own writeup
  above for how it was diagnosed. Workaround: use a fresh `browser.newPage()` per `fullPage`
  capture rather than reusing a page that already fired the transition, or fall back to
  `fullPage: false` (viewport-only, tiled manually if needed) which was never affected.
  This is a capture-tool artifact, not a product bug — don't "fix" it in app CSS.
- **`backend/data/debug_history.db` needs manual cleanup after any live-verification
  session** — it auto-rotates at 50 rows but real `/debug` calls during manual testing
  still show up; delete test-run rows afterward (`DELETE /history/{id}` while the backend
  is up). This session's `OperatorShowcase` runs (used repeatedly across screenshot
  batches) are the only `/debug` calls it made.
- **`backend/data/user_data.db` is a similarly real, persistent artifact** — any live
  verification that runs CREATE TABLE/INSERT/UPDATE/DELETE against the real backend
  leaves real rows/tables behind if not cleaned up. Prefer measuring through pytest
  (isolation for free via `conftest.py`'s autouse fixtures) over a bespoke script whenever
  one would touch this database at all.
- Both dev servers (`uvicorn` on :8000, `npm run dev` on :5173) were already running at
  the start of this session — check with `curl`/`netstat` before assuming either state.
- Puppeteer-core + a local Chrome install (`C:\Program Files\Google\Chrome\Application\
  chrome.exe`) is the live-verification approach in use — this session again reused an
  existing scratchpad's `node_modules` (via `NODE_PATH`) rather than reinstalling.
- The sample rail's collapsed rows are `.rail-item` buttons (`aria-label` = the sample
  name, since visible text is just initials); the flyout's rows are still `.sample-card`
  (unchanged from #27). The Run/step controls live inside `.control-bar` (from #27). The
  Live State panel is still `.panel-state`; the SQL step panel is still `.table-state-panel`.
- `found`/`notfound` are reserved KEYWORDs in this grammar (the `cur_name%FOUND`/
  `cur_name%NOTFOUND` cursor-attribute suffix) — a variable or OUT parameter literally
  named `found` fails to parse with a confusing "Expected IDENTIFIER (got KEYWORD)"
  error; use `was_found`/`matched`/similar instead.
- Mobile nav overflows horizontally at ~400px width (pre-existing, `.top-nav` has no
  `flex-wrap`) — cosmetic, not blocking, explicitly out of scope again this session (told
  not to touch the top nav bar).
