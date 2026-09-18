# HANDOFF.md

**A snapshot of exactly where the project stands right now.** Fully rewritten at the end
of every session, not appended to — it's a status board, not a diary. Session-by-session
history lives in `git log` and `PROMPT_LOG.md`; stable project facts live in `CLAUDE.md`
(`docs/features.md`/`docs/schema.md` for design detail).

**Last updated**: 2026-09-18, end of a "Fix Download Report generation" session
(`PROMPT_LOG.md` #30) — three real bugs in the report generator, all confirmed via
`LookupOnePlayer` but root-caused in the shared report-building code path, not sample
data: (1) removed the "Intermediate Results" section from all three formats; (2) fixed a
genuine mislabeling where a step caught by a declared CONTINUE HANDLER read as
`"ERROR [...] ... caught by X handler"`, reading as a failure when it's expected, handled
behavior — now `"Handled: ..."`; (3) root-caused and fixed the control-flow diagram never
actually appearing in PDF/Document exports (three stacked bugs in the client-side
rasterization path, see below — not a one-line fix). Backend: `backend/app/report.py`
changed, suite **557 passing** (+5 new tests, up from 552, still 0 xfailed). Frontend:
`svgToPng.js` rewritten, `SqlConsolePage.jsx` touched only for the download wiring;
`npm run lint`/`npm run build` both clean.

---

## Feature status

**Mandatory (5/5 done)**: Day/Night Mode · Developed By (real photo + name + register
number + Guided By) · Help tab (accurate for the merged page) · Learn tab (real embedded
video + real MySQL/Oracle reference citations) · Download (PDF/DOCX/Text export). The
three real bugs fixed this session (see below) mean the "all three confirmed to produce
valid non-empty files" claim from three sessions ago (`PROMPT_LOG.md` #25) was true but
incomplete — a non-empty file isn't the same as a *correct* one; this session is the first
to verify actual report *content* end to end (diagram image really embedded and legible,
no mislabeled steps) rather than just "did a download happen."

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
Results (this session — see below).

---

## This session's work — Fix Download Report generation (all formats)

Full prompt + rationale: `PROMPT_LOG.md` #30. Three independent bugs in
`backend/app/report.py` (plus, for bug 3, `frontend/src/svgToPng.js` and a small wiring
change in `SqlConsolePage.jsx`) — verified across four varied samples (a plain
branching one, a `CALL`-based one, a cursor/handler-based one, a `CASE`-based one) and
all three export formats.

1. **"Intermediate Results" section removed entirely**, from all three formats — one row
   per variable per step (the full `variables` snapshot repeated at every step) was too
   granular to be useful in a written report. `build_report()` in `report.py` no longer
   builds it; the Processing Steps section's own "Details" column and Final Output's
   "Final variable state" table already cover what a reader needs. Four sections remain
   (`User Inputs`, `Processing Steps`, `Final Output`, `Graphs, Tables & Figures`), down
   from five.

2. **"ERROR" mislabeling fixed, with a deeper finding underneath it.** `_step_details()`
   used to render any step with an `error` field as `"ERROR [condition] message (caught
   by X handler)"` — even when that condition was caught by a declared CONTINUE HANDLER,
   i.e. completely normal, expected, non-fatal control flow (a cursor running out of
   rows, a division by zero the procedure explicitly guards against). Root-caused rather
   than just reworded: traced *why* `error.handler == "unhandled"` doesn't mean "this
   halted execution" here — `/debug` only ever returns a `steps` list for a run that
   completed; a genuinely fatal `InterpreterError` aborts with a 400 *before* producing
   any steps at all, so `/debug/report` (which only ever receives a prior `/debug`
   response's own `steps`) structurally can never see a step from a run that actually
   halted. Combined with `interpreter.py`'s own design (NOT_FOUND is unconditionally
   non-fatal, handler declared or not — confirmed via
   `test_not_found_without_a_handler_is_unhandled_but_still_non_fatal`), this means a
   per-step `error` in this data is **always** non-fatal, whichever value `handler`
   carries. Fixed by dropping "ERROR" entirely from `_step_details()`: caught-by-handler
   now reads `"Handled: NOT_FOUND -- <message> (caught by NOT_FOUND handler)"`; no-handler
   -declared-but-still-non-fatal reads `"Note: NOT_FOUND -- <message> (no handler
   declared; non-fatal, execution continued)"`. The Final Output section's own separate
   rendering had the same misconception baked into different wording ("Execution stopped
   with an unhandled error") for the same last-step-happens-to-carry-an-unhandled-
   condition case — fixed to say "Execution completed after N step(s) ... this condition
   is non-fatal by design and did not halt execution" instead. **Checked the in-app step
   view for the same mislabeling per the prompt's explicit instruction — not present**:
   `SqlConsolePage.jsx`'s error banner and step-log flag already read the raw
   `condition`/`message` plus "Caught by: X" / "No handler caught this — unhandled.",
   never literally the word "ERROR"; `explainer.py`'s Gemini-prompt builder and template
   fallback were already correct too. This bug was isolated to `report.py`.

3. **Control-flow diagram now actually embeds a real, legible image** — the deepest fix
   this session, three stacked bugs found live, each hiding the next (full blow-by-blow:
   `PROMPT_LOG.md` #30, and the comment block at the top of `svgToPng.js`):
   - **Sizing bug**: the old width/height detection regex-scanned the ENTIRE svg string
     for the first `width="..."`/`height="..."` match rather than just the root `<svg>`
     tag. Mermaid's root tag sets width as a *percentage* (`width="100%"`, no height
     attribute at all) with the real size only in its `viewBox`, so the scan skipped the
     root tag and matched the first `width="0"`/`height="0"` it found deeper in the
     markup — silently rasterizing a 1×1-pixel image every time. This is exactly what
     the reported symptom was: a caption with no visible diagram, because a real (if
     invisible) image WAS being embedded.
   - **Canvas tainting**: once the sizing was fixed and the canvas was the right size,
     `canvas.toDataURL()` started throwing `SecurityError: Tainted canvases may not be
     exported` — confirmed live, on every sample. Any SVG containing a `<foreignObject>`
     (exactly how Mermaid renders node/edge labels — rich HTML text) permanently taints a
     canvas once drawn via `<img>` + `drawImage`, a hard browser restriction, not
     something fixable by tweaking the SVG markup. Mermaid's own
     `flowchart.htmlLabels: false` config (which should avoid `<foreignObject>` entirely)
     was tried and confirmed, via a live test plus a web search of Mermaid's own issue
     tracker, to NOT actually suppress it in this Mermaid version — a known upstream
     limitation.
   - **html2canvas tried and rejected**: sidesteps the taint issue (walks the live DOM
     instead of decoding an `<img>`), briefly added as a dependency, but rendered the
     whole diagram as a blank white image — confirmed by sampling the resulting canvas's
     own pixel data (100% pure white, not even borders painted). A known html2canvas gap
     in nested-SVG support. **Removed again** (`npm uninstall html2canvas`) once this was
     confirmed — no longer a dependency.
   - **The fix that actually works**: `svgToPng.js` now converts every `<foreignObject>`
     label in a *cloned* copy of the live diagram SVG to a plain SVG `<text>`/`<tspan>`
     (`foreignObjectsToSvgText`) before rasterizing through the same `<img>` + `<canvas>`
     approach the sizing fix already covers — a `<foreignObject>`-free SVG carries none of
     the tainting restriction. Two more real bugs surfaced and fixed while getting this
     approach to actually look right (not just "an image exists"):
     - Text could render slightly wider than the box Mermaid originally sized for it
       (HTML and SVG text layout use different metrics at the same nominal font-size) —
       fixed with `shrinkTextNodesToFit`, which temporarily attaches the cloned SVG
       off-screen (`getComputedTextLength()` needs real layout, unavailable on a detached
       node) and shrinks any label that measures wider than its own box.
     - Edge/condition labels ("then"/"else"/"TRUE"/"FALSE", which have no shape behind
       them) rendered as invisible near-white text once transplanted onto this export's
       white page (they're near-white *on screen* against the app's own dark canvas,
       which is correct there) — fixed with a dark, page-safe fallback color specifically
       for `.edgeLabel`-rooted labels (node labels keep the near-white default, correct
       since they always sit on their own node's dark shape fill).
     - Setting that fallback color as a bare `fill="..."` **attribute** was itself
       silently overridden by the diagram's own embedded `<style>` block (`#flowchart-1
       {fill:#edeff4}`, from `mermaidColors.js`'s theme) — an SVG presentation attribute
       is the *weakest* possible CSS origin, losing even to a plain non-`!important`
       stylesheet rule. Fixed by setting `text.style.fill` (an inline `style="fill:..."`)
       instead, which does outrank the embedded stylesheet.
   - **A fourth, separate bug found only once the diagram was finally real and correctly
     sized**: `render_pdf()`'s image block used to scale ONLY by width
     (`content_width / image_width`), so a tall, narrow image — exactly what a long,
     vertically-stacked flowchart rasterizes to — could still come out taller than an
     entire fresh page's own frame height. reportlab refuses to lay out a flowable that
     doesn't fit at all rather than shrink or split it (a "Flowable ... too large ... in
     frame" exception), which failed the **whole PDF download with a 500**, not just a
     missing image — this was caught live while verifying the fix above (`GradeClassifier`
     PDF, `IF/IF` nested branches, 8-node vertical trace). Fixed by also computing a
     height-based scale factor (`content_height / image_height`, `content_height` derived
     from the same page margins with a little headroom reserved for the caption) and
     taking the `min()` of both — the same fix that made the diagram appear at all would
     have re-broken PDF specifically, for any tall enough diagram, without this.
   - **Wiring**: `SqlConsolePage.jsx` gained `diagramContainerRef` (attached to the live
     `.diagram-svg` div) and now calls `rasterizeDiagramElementToPng(diagramContainerRef
     .current)` in `handleDownloadReport` — replacing the old `rasterizeSvgToPng
     (diagramSvg)` call over the raw SVG *string*. `VariableTimeline`-era `mermaid`/
     `diagramRenderCounter` usage elsewhere in the file is untouched.

**Verification**: regenerated reports for `GradeClassifier` (plain branching), `OrderTotal`
(`CALL`), `SafeAverageWithHandlers` (cursor + two handler types), and `ClassifyOrder`
(`CASE`) across all three formats via the real `/debug` → `/debug/report` pipeline (driven
live through the actual UI via Puppeteer, not just direct API calls) — confirmed: no
"Intermediate Results" section anywhere; `"Handled:"`/`"Note:"` wording with zero
occurrences of the literal word "ERROR" for a caught/non-fatal condition; a real, legible,
correctly-colored, correctly-sized diagram image extracted straight out of the generated
PDF (grep for `/Image` XObject markers, valid `%PDF-`/`%%EOF`) and DOCX (extracted
`word/media/image1.png` and viewed directly) files, not just "download didn't error."
`npm run lint`/`npm run build` clean (same two pre-existing warnings as every recent
session). Backend suite: **557 passing** (+5 new/changed tests in `test_report.py` +1 new
in `test_report_endpoint.py`), 0 xfailed. `backend/data/debug_history.db` test rows (44,
ids 512–555, across this session's many Puppeteer-driven `/debug` calls) deleted
afterward via `DELETE /history/{id}`; no `user_data.db` writes this session (every sample
used was read-only against it).

**A mid-session interruption, worth recording**: partway through, both dev servers had
gone down (a context reset landed mid-verification) — resumed by restarting
`uvicorn app.main:app --port 8000` and `npm run dev` directly rather than assuming either
was still up; see Live gotchas below.

---

## Testing infrastructure (see `CLAUDE.md` §6 for the mechanics)

- **Golden-trace regression harness** (`backend/app/tests/test_golden_traces.py` +
  `backend/app/tests/golden/*.json`, **21 fixtures**): runs every sample through the REAL
  `/debug` endpoint and diffs the resulting step trace against a checked-in baseline.
  **Run this before considering any future tokenizer/parser/interpreter-touching phase
  done.** Untouched this session (`report.py`/frontend rasterization only — no
  `DebugStep`/interpreter changes).
- **Property-based tests** (`backend/app/tests/test_property_based.py`, `hypothesis`):
  mutates the real samples via `demo_db.create_demo_connection()`; two invariants across
  1000 examples each.
- **Known-bugs tracker** (`backend/app/tests/test_known_bugs.py`): empty of unfixed bugs.
- **Hand-written grammar edge cases** (`backend/app/tests/test_grammar_edge_cases.py`).
- **Report tests** (`backend/app/tests/test_report.py` + `test_report_endpoint.py`): this
  session added `test_step_details_labels_a_caught_error_as_handled_not_error`,
  `test_step_details_no_handler_declared_condition_is_not_labeled_error_either`,
  `test_final_output_no_handler_declared_does_not_say_execution_stopped`,
  `test_generate_report_pdf_scales_a_tall_narrow_image_to_fit_the_page` (the reportlab
  "Flowable too large" regression, using a real 200×4000 Pillow PNG), and
  `test_report_endpoint_handles_a_caught_handler_trace_without_false_error_label` (the
  same fix, end to end through the real `/debug` → `/debug/report` pipeline, not a
  hand-built step dict); replaced `test_build_report_intermediate_results_reflects_
  variable_changes` with `test_build_report_has_no_intermediate_results_section`.
- Backend suite: **557 passing, 0 xfailed** (was 552; +5 net this session).

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
   "CallStatement" (matching what the on-screen diagram already shows via `cfg.js`'s
   `nodeMermaidText` — not something this session changed or was asked to). Good enough
   for a report figure; revisit only if a future session wants pixel parity specifically.
9. `svgToPng.js`'s `foreignObjectsToSvgText`/`shrinkTextNodesToFit` were built and
   verified against THIS app's specific Mermaid output shape (flowchart-v2, classic
   look, `htmlLabels` always effectively on) — if a future phase changes Mermaid version,
   diagram type, or theme config in a way that changes the `<foreignObject>`/`<g
   class="...">` structure this code pattern-matches on (`.edgeLabel`, `.node`, `<p>`
   children, inline `style="color:..."` spans), re-verify this conversion still finds the
   right text/colors rather than assuming it degrades gracefully — a structural mismatch
   would silently drop text rather than error.

---

## Live gotchas

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
  (`min()` of both), never width alone — see `render_pdf`'s `content_height` this session
  added.
- **Puppeteer `fullPage: true` screenshots can show a stale "ghost" of a just-collapsed
  CSS-opacity-transitioned element** (the hover-flyout sample rail from #28, but likely any
  element using `opacity`/`transition-delay` for a hover/focus reveal) even when
  `getComputedStyle` confirms the correct hidden state at the same moment — see
  `PROMPT_LOG.md` #28 for how it was diagnosed. Workaround: a fresh `browser.newPage()`
  per `fullPage` capture, or `fullPage: false`. A capture-tool artifact, not a product bug.
- **Both dev servers can go down mid-session** (this session: a context reset landed
  between two verification steps, and both `uvicorn`/`npm run dev` had exited) — always
  `curl`/`netstat` before assuming either is still up rather than trusting an earlier
  check in the same conversation; restarting is just `uvicorn app.main:app --port 8000`
  (from `backend/`, with `.venv/Scripts/python.exe -m uvicorn ...` on Windows) and
  `npm run dev` (from `frontend/`).
- **`backend/data/debug_history.db` needs manual cleanup after any live-verification
  session that actually clicks Run** — it auto-rotates at 50 rows but real `/debug` calls
  during manual testing still show up; delete test-run rows afterward (`DELETE
  /history/{id}` while the backend is up). This session's ids 512–555 (44 rows, across
  several Puppeteer-driven sample runs) were the only ones it created.
- **`backend/data/user_data.db` is a similarly real, persistent artifact** — any live
  verification that runs CREATE TABLE/INSERT/UPDATE/DELETE against the real backend
  leaves real rows/tables behind if not cleaned up. Prefer measuring through pytest
  (isolation for free via `conftest.py`'s autouse fixtures) over a bespoke script whenever
  one would touch this database at all. Untouched this session (every sample used for
  live verification was read-only against it).
- Puppeteer-core + a local Chrome install (`C:\Program Files\Google\Chrome\Application\
  chrome.exe`) is the live-verification approach in use — reuse an existing scratchpad's
  `node_modules` (via `NODE_PATH`) rather than reinstalling. Vite serves ES modules
  directly, so `await import('/src/<file>.js')` inside a `page.evaluate` works for testing
  a frontend module's exports directly, without going through the UI at all when that's
  the more direct way to isolate a bug (used heavily this session to pin down the
  rasterization bugs above).
- `found`/`notfound` are reserved KEYWORDs in this grammar (the `cur_name%FOUND`/
  `cur_name%NOTFOUND` cursor-attribute suffix) — a variable or OUT parameter literally
  named `found` fails to parse with a confusing "Expected IDENTIFIER (got KEYWORD)"
  error; use `was_found`/`matched`/similar instead.
- Mobile nav overflows horizontally at ~400px width (pre-existing, `.top-nav` has no
  `flex-wrap`) — cosmetic, not blocking, out of scope again this session.
