// Side-by-Side Run Comparison -- innovation feature #2 (see
// backend/app/main.py's POST /debug, unchanged by this feature: both
// sides of ComparePage.jsx call that exact endpoint independently and
// hand its `steps` array straight to computeDivergence below). This
// module does no execution of its own -- it's a pure comparison over
// two already-computed DebugStep arrays (backend/app/interpreter.py),
// the same shape the main Debugger page already renders.

// Mirrors DebuggerPage.jsx's own formatValue -- kept as a small local
// copy (not imported from there) so this phase doesn't have to touch
// that file at all to get it, per this phase's scope.
export function formatValue(entry) {
  if (!entry || entry.value === null || entry.value === undefined) return null
  return entry.type === 'string' ? `"${entry.value}"` : String(entry.value)
}

// Compares one pair of steps at the same trace index and returns a
// divergence descriptor for the *first* respect in which they differ,
// or null if this particular pair matches closely enough that the
// comparison should keep looking further down the trace.
//
// Checked in this order, matching the PHASE prompt's own examples:
// which line ran, whether one side errored and the other didn't, which
// branch was taken, then any variable value the two traces share.
function compareStepPair(left, right) {
  if (left.line !== right.line) {
    return {
      kind: 'line',
      summary:
        `Left executed line ${left.line} ("${left.statementText}"); ` +
        `right executed line ${right.line} ("${right.statementText}").`,
    }
  }

  const leftError = left.error ?? null
  const rightError = right.error ?? null
  if (Boolean(leftError) !== Boolean(rightError) || (leftError && rightError && leftError.condition !== rightError.condition)) {
    if (leftError && rightError) {
      return {
        kind: 'error',
        summary: `Both sides hit an error here, but different conditions: ${leftError.condition} (left) vs ${rightError.condition} (right).`,
      }
    }
    const which = leftError ? 'Left' : 'Right'
    const error = leftError ?? rightError
    return {
      kind: 'error',
      summary: `${which} raised ${error.condition} here (${error.message}); the other side did not.`,
    }
  }

  const leftBranch = left.branch ?? null
  const rightBranch = right.branch ?? null
  if ((leftBranch?.path ?? null) !== (rightBranch?.path ?? null)) {
    return {
      kind: 'branch',
      summary: `Left took the "${leftBranch?.path ?? 'none'}" branch; right took the "${rightBranch?.path ?? 'none'}" branch.`,
    }
  }

  const leftVars = left.variables ?? {}
  const rightVars = right.variables ?? {}
  for (const name of Object.keys(leftVars)) {
    if (!(name in rightVars)) continue // different procedures may not share every variable name
    const leftEntry = leftVars[name]
    const rightEntry = rightVars[name]
    if (leftEntry.value !== rightEntry.value) {
      return {
        kind: 'variable',
        variableName: name,
        summary: `Variable \`${name}\` differs: ${formatValue(leftEntry) ?? '—'} (left) vs ${formatValue(rightEntry) ?? '—'} (right).`,
      }
    }
  }

  return null
}

/**
 * Walks two full DebugStep traces step-by-step (by shared index, not by
 * line number -- the two procedures need not be related at all) and
 * returns the FIRST point of divergence, or null if they're identical
 * as far as they can be compared.
 *
 * Return shape: { index, kind: 'line'|'error'|'branch'|'variable'|'length', summary, variableName? }
 * `index` is a step index valid in both traces up to a 'length' divergence,
 * where it's exactly the length of the shorter trace (the first index
 * that trace no longer has).
 */
export function computeDivergence(leftSteps, rightSteps) {
  if (!Array.isArray(leftSteps) || !Array.isArray(rightSteps) || leftSteps.length === 0 || rightSteps.length === 0) {
    return null
  }

  const sharedLength = Math.min(leftSteps.length, rightSteps.length)
  for (let index = 0; index < sharedLength; index += 1) {
    const found = compareStepPair(leftSteps[index], rightSteps[index])
    if (found) return { index, ...found }
  }

  if (leftSteps.length !== rightSteps.length) {
    const leftShorter = leftSteps.length < rightSteps.length
    const shorter = leftShorter ? 'Left' : 'Right'
    const longer = leftShorter ? 'Right' : 'Left'
    return {
      index: sharedLength,
      kind: 'length',
      summary:
        `${shorter} run finished after ${sharedLength} step${sharedLength === 1 ? '' : 's'}; ` +
        `${longer} kept executing beyond that point.`,
    }
  }

  return null // every step matched and both traces are the same length
}
