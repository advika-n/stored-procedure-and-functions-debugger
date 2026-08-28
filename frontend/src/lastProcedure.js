// A tiny cross-page bridge: DebuggerPage writes whatever code is
// currently in its editor here, so QuizPage's "This Procedure" option
// (see /quiz) knows whether a procedure is loaded and what its source
// is -- without standing up a global state store for one field. Every
// route in this app is a fully independent, self-contained page (no
// Context/Redux anywhere), so this is deliberately just a thin,
// synchronous read/write pair rather than a new pattern.
//
// Session-scoped (not localStorage): "currently loaded" is a
// within-session notion and shouldn't resurface in a brand new browser
// session days later.

const STORAGE_KEY = 'spdebugger:lastProcedure'

export function writeLastProcedure(code, name) {
  try {
    if (!(code ?? '').trim()) {
      sessionStorage.removeItem(STORAGE_KEY)
      return
    }
    sessionStorage.setItem(STORAGE_KEY, JSON.stringify({ code, name: name ?? null }))
  } catch {
    // sessionStorage can throw (privacy mode, storage disabled, ...) --
    // this bridge is a nice-to-have, never worth crashing the debugger.
  }
}

/** { code, name } if a non-empty procedure was last loaded in the
 * debugger this session, else null. */
export function readLastProcedure() {
  try {
    const raw = sessionStorage.getItem(STORAGE_KEY)
    if (!raw) return null
    const parsed = JSON.parse(raw)
    if (!parsed?.code?.trim()) return null
    return parsed
  } catch {
    return null
  }
}
