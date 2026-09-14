# HANDOFF.md

**A snapshot of exactly where the project stands right now.** Fully rewritten at the end
of every session, not appended to — it's a status board, not a diary. Session-by-session
history lives in `git log` and `PROMPT_LOG.md`; stable project facts live in `CLAUDE.md`
(`docs/features.md`/`docs/schema.md` for design detail).

**Last updated**: 2026-09-14, end of the LOOP/LEAVE support session.

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
· CASE statement · **LOOP/LEAVE** (this session — see below).

---

## Uncommitted right now

This session's LOOP/LEAVE support: `backend/app/{tokenizer,parser,interpreter,advisor,
explainer}.py`, new `test_loop_statement.py`, regression additions to `test_advisor.py`/
`test_explainer.py`, a forced rename in `test_call_statement.py`/
`test_function_call_expression.py` (a procedure named `Loop` now collides with the new
keyword), `frontend/src/{cfg.js,samples.js,testCaseExpectations.js,theoryContent.jsx}`,
`pages/DebuggerPage.jsx` (comment only), `README.md`, `CLAUDE.md`, `HANDOFF.md`,
`PROMPT_LOG.md`, and the new `docs/features.md`/`docs/schema.md` (this session's own
CLAUDE.md split). Backend suite: 390 passing. `npm run lint`/`build` clean. Verified live
(zero console errors, both themes) — see `PROMPT_LOG.md` §19 for detail if needed.

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
   just the main Debugger.

---

## Live gotchas

- **`backend/data/debug_history.db` needs manual cleanup after any live-verification
  session** — it auto-rotates at 50 rows but real `/debug` calls during manual testing
  still show up; delete test-run rows afterward (direct SQL is fine if no backend is
  left running) so the user's real history stays clean.
- **Check port usage before binding anything** for live verification — a naive
  `startsWith('/debug')` API-route check in a throwaway proxy script will also swallow
  the frontend's own `/debugger` route; match exact-or-slash-prefixed instead.
- Mobile nav overflows horizontally at ~400px width (pre-existing, `.top-nav` has no
  `flex-wrap`) — cosmetic, not blocking, don't need to re-verify it isn't worse unless
  you touch the nav.
