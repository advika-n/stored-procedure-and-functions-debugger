# HANDOFF.md

**A snapshot of exactly where the project stands right now.** Fully rewritten at the end
of every session, not appended to — it's a status board, not a diary. Session-by-session
history lives in `git log` and `PROMPT_LOG.md`; stable project facts live in `CLAUDE.md`
(`docs/features.md`/`docs/schema.md` for design detail).

**Last updated**: 2026-09-14, end of the user-created tables (CREATE TABLE / INSERT /
UPDATE / DELETE) session.

---

## Feature status

**Mandatory (5/5 done)**: Day/Night Mode · Developed By (photo still a placeholder SVG,
text is real) · Help tab · Learn tab (**placeholder content** — draft concept text,
`YOUR_VIDEO_ID_HERE`, placeholder references, all badge-flagged — needs real material
before submission) · Download (PDF/DOCX/Text export).

**Innovation (3/4 done, 1 dropped)**: SQL Anti-Pattern Advisor · Side-by-Side Run
Comparison · Variable Timeline · Live Parameter Tuning — **dropped**, don't pick back up
without a fresh scoping prompt.

**Tier 1 (4/4 done)**: Breakpoints + Continue/Restart · `CALL` support · Call Stack
panel.

**Extras beyond original scope (all done)**: Text-to-Speech · Test-Case Runner ·
Extended Static Analysis Warnings (advisor: 6→9 checks) · Function calls in expressions
· CASE statement · LOOP/LEAVE · **User-created tables: CREATE TABLE / INSERT / UPDATE /
DELETE** (this session — see below; advisor now 9→10 checks).

---

## Uncommitted right now

This session's user-created tables support: `backend/app/{tokenizer,parser,interpreter,
advisor,explainer}.py`, new `test_table_crud.py`, regression additions to
`test_advisor.py`/`test_explainer.py`, a forced test-expectation update in
`test_parser.py` (a bare leading `CREATE TABLE ...;` used to be the go-to example of a
malformed `CREATE` and now correctly parses instead — see that test file's own comment),
`frontend/src/{cfg.js,samples.js,testCaseExpectations.js,TestCaseRunner.jsx,App.css,
pages/DebuggerPage.jsx}`, `README.md`, `CLAUDE.md`, `HANDOFF.md`, `PROMPT_LOG.md`,
`docs/features.md`, `docs/schema.md`. Backend suite: 440 passing (391 before this
session). `npm run lint`/`build` clean. In-process sweep across all 18 samples (Python
pipeline + Node `cfg.js`, both themes) clean. Verified live end-to-end against a real
running backend/frontend + headless Chrome (raw-CDP driver, zero console errors, both
themes) — new sample `ManageInventory`'s Tables panel, flowchart, Advisor, and Variable
Timeline all confirmed correct step by step; see `PROMPT_LOG.md`'s latest entry for
detail if needed.

---

## Immediate next steps

1. Commit this session's work (see above) — clean, isolated layer, nothing left over
   from prior sessions.
2. Get a real student photo (Developed By) and a real video + references (Learn tab) —
   the only two pieces of placeholder content left before submission.
3. SQL Anti-Pattern Advisor still doesn't analyze a `ProgramNode` AST at all (a
   `CALL`-based multi-procedure source always shows "no issues" — `ast.get("body", [])`
   degrades to `[]`); Download/Compare have never been exercised against one either. Only
   worth fixing if `CALL`-based procedures need to be fully first-class everywhere, not
   just the main Debugger. (Pre-existing, unrelated to this session's own work — verified
   this session's `cfg.js` flowchart-building sweep needed the SAME entry-definition
   extraction `DebuggerPage.jsx` already does for `ProgramNode`, confirming this gap is
   real and still unfixed, not something newly introduced.)
4. This session's CRUD is entirely simulated in `Interpreter.tables` — a user-created
   table is never real SQLite and is never queryable from a cursor's embedded SELECT
   (which still only ever sees the fixed `products` demo table). If a future phase wants
   the two to interoperate (e.g. a cursor querying a table the same procedure just
   CREATEd), that's a real, separate piece of design work, not a natural extension of
   what exists today — flagging now rather than letting it go unnoticed.

---

## Live gotchas

- **`backend/data/debug_history.db` needs manual cleanup after any live-verification
  session** — it auto-rotates at 50 rows but real `/debug` calls during manual testing
  still show up; delete test-run rows afterward (direct SQL is fine if no backend is
  left running) so the user's real history stays clean. (Done this session — 5 test rows
  from live-verifying `ManageInventory` were deleted afterward.)
- **A stray, non-listening process can hold a port's `Bound` reservation on Windows**
  without actually accepting connections (`Get-NetTCPConnection` shows `Bound`, not
  `Listen`; `curl` gets connection refused) — this session hit exactly that on port 8000
  (a leftover system-Python process, not one this session started). Per "leave
  pre-existing processes alone," the fix was NOT to kill it: ran the throwaway backend on
  8010 instead and temporarily pointed `frontend/vite.config.js`'s proxy targets at 8010
  for the live-verification session only, then reverted that file back to 8000 exactly
  (confirmed via `git diff` showing no net change) once done. Vite itself only bound
  `[::1]` (IPv6), not `127.0.0.1` — curl/fetch calls during verification needed
  `http://[::1]:5173`, not `http://127.0.0.1:5173`.
- **Chrome's DevTools HTTP endpoint requires `PUT`, not `GET`, for `/json/new`** in
  current Chrome versions (`GET` returns a plain-text "Using unsafe HTTP verb" body, not
  JSON) — the raw-CDP driver script needs `{ method: 'PUT' }` on that one call.
- **Check port usage before binding anything** for live verification — a naive
  `startsWith('/debug')` API-route check in a throwaway proxy script will also swallow
  the frontend's own `/debugger` route; match exact-or-slash-prefixed instead.
- Mobile nav overflows horizontally at ~400px width (pre-existing, `.top-nav` has no
  `flex-wrap`) — cosmetic, not blocking, don't need to re-verify it isn't worse unless
  you touch the nav.
