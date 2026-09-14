// Test-Case Runner -- runs every built-in sample procedure/function
// through the exact same execution pipeline the Debugger page already
// uses (POST /debug, unmodified) and checks the resulting final
// variable state / return value -- and, optionally, a user-created
// table's final row state (see testCaseExpectations.js's own contract
// comment) -- against a hand-verified expected outcome per sample (see
// testCaseExpectations.js for how those were derived -- NOT invented).
// Reports a pass/fail summary plus, for any failure, exactly which
// field(s) diverged and by how much.
//
// Deliberately self-contained, same reasoning as VariableTimeline.jsx:
// this component takes no required props -- it owns its own sample
// list, expectations, run state, and rendering, so a future redesign
// only ever needs to touch the thin wrapper around it (today,
// pages/TestRunnerPage.jsx), never this file's pass/fail logic itself.
// Optional `samples`/`expectations` props exist purely so this can be
// exercised against a different list without editing the component.

import { useState } from 'react'
import { SAMPLES } from './samples'
import { TEST_CASE_EXPECTATIONS } from './testCaseExpectations'

// Floating-point arithmetic (this language has no integer-only mode --
// see interpreter.py) means an exact `===` would spuriously fail a
// correct run over rounding noise (e.g. 50/3). Anything under this gap
// counts as equal; non-numeric fields still compare with `===`.
const FLOAT_EPSILON = 1e-6

function valuesMatch(actual, expected) {
  if (typeof actual === 'number' && typeof expected === 'number') {
    return Math.abs(actual - expected) < FLOAT_EPSILON
  }
  return actual === expected
}

function formatValue(value) {
  if (value === undefined) return '(missing)'
  if (value === null) return 'NULL'
  if (typeof value === 'string') return `"${value}"`
  if (typeof value === 'number') return Number.isInteger(value) ? String(value) : value.toFixed(6).replace(/0+$/, '').replace(/\.$/, '')
  return String(value)
}

// A user-created table's rows (see backend/app/interpreter.py's "User-
// created tables" section) are checked against the LAST step in the
// whole trace whose OWN `table.name` matches -- i.e. the state right
// after that table's own final CREATE/INSERT/UPDATE/DELETE -- not just
// whatever the very last step overall happens to be (which may belong
// to an entirely different table, or to no table mutation at all).
function findFinalTableState(steps, tableName) {
  for (let i = steps.length - 1; i >= 0; i -= 1) {
    if (steps[i].table?.name === tableName) return steps[i].table
  }
  return null
}

function rowsMatch(actualRows, expectedRows) {
  if (actualRows.length !== expectedRows.length) return false
  return expectedRows.every((expectedRow, index) => {
    const actualRow = actualRows[index] ?? {}
    return Object.entries(expectedRow).every(([column, expectedValue]) => valuesMatch(actualRow[column], expectedValue))
  })
}

function formatRows(rows) {
  return JSON.stringify(rows ?? null)
}

// Runs one sample through POST /debug (the same call the Debugger page
// itself makes -- see DebuggerPage.jsx's handleDebug) and diffs the
// final step against that sample's expectation. No second execution
// path: this is the only place this component talks to the backend.
async function runOneCase(sample, expectation) {
  const base = { name: sample.name, kind: sample.kind }

  let res
  let body
  try {
    res = await fetch('/debug', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ code: sample.code, params: {}, name: sample.name }),
    })
    body = await res.json()
  } catch (err) {
    return { ...base, status: 'error', message: `Network error: ${err.message}`, diffs: [] }
  }

  if (!res.ok) {
    const detail = body?.detail
    const line = detail?.line != null ? ` (line ${detail.line})` : ''
    return {
      ...base,
      status: 'error',
      message: `[${detail?.stage ?? 'error'}] ${detail?.message ?? 'Unknown error'}${line}`,
      diffs: [],
    }
  }

  const steps = body.steps ?? []
  if (steps.length === 0) {
    return { ...base, status: 'error', message: 'Run produced zero steps.', diffs: [] }
  }
  const last = steps[steps.length - 1]

  const diffs = []
  if (expectation.kind === 'return') {
    const actual = last.returnValue?.value
    if (!valuesMatch(actual, expectation.returnValue)) {
      diffs.push({ field: 'returnValue', expected: expectation.returnValue, actual })
    }
  } else {
    const actualVars = last.variables ?? {}
    for (const [name, expectedValue] of Object.entries(expectation.variables)) {
      const actualValue = actualVars[name]?.value
      if (!valuesMatch(actualValue, expectedValue)) {
        diffs.push({ field: name, expected: expectedValue, actual: actualValue })
      }
    }
  }

  // Optional, additive to either `kind` (see testCaseExpectations.js's
  // own contract comment) -- a user-created table's FINAL row state,
  // not just scalar variables/a return value.
  for (const [tableName, expectedRows] of Object.entries(expectation.tables ?? {})) {
    const finalState = findFinalTableState(steps, tableName)
    const actualRows = finalState?.rows ?? null
    if (actualRows === null || !rowsMatch(actualRows, expectedRows)) {
      diffs.push({ field: `table:${tableName}`, expected: formatRows(expectedRows), actual: formatRows(actualRows), raw: true })
    }
  }

  return { ...base, status: diffs.length === 0 ? 'pass' : 'fail', diffs, numSteps: steps.length }
}

function StatusBadge({ status }) {
  const labels = { pass: 'PASS', fail: 'FAIL', error: 'ERROR', 'no-expectation': 'NO EXPECTED OUTPUT' }
  const classes = {
    pass: 'testrunner-badge testrunner-badge-pass',
    fail: 'testrunner-badge testrunner-badge-fail',
    error: 'testrunner-badge testrunner-badge-fail',
    'no-expectation': 'testrunner-badge testrunner-badge-unknown',
  }
  return <span className={classes[status]}>{labels[status]}</span>
}

function CaseCard({ result }) {
  return (
    <li className={`testrunner-case testrunner-case-${result.status}`}>
      <div className="testrunner-case-header">
        <span className="testrunner-case-name">{result.name}</span>
        <span className="testrunner-case-kind">{result.kind}</span>
        <StatusBadge status={result.status} />
        {typeof result.numSteps === 'number' && (
          <span className="testrunner-case-steps">{result.numSteps} steps</span>
        )}
      </div>

      {result.status === 'error' && <p className="testrunner-case-message">{result.message}</p>}

      {result.status === 'no-expectation' && (
        <p className="testrunner-case-message">
          This sample has no expected output defined in testCaseExpectations.js yet -- flagged rather than
          assumed to pass or fail.
        </p>
      )}

      {result.status === 'fail' && result.diffs.length > 0 && (
        <table className="testrunner-diff-table">
          <thead>
            <tr>
              <th>Field</th>
              <th>Expected</th>
              <th>Actual</th>
            </tr>
          </thead>
          <tbody>
            {result.diffs.map((diff) => (
              <tr key={diff.field}>
                <td className="testrunner-diff-field">{diff.field}</td>
                <td className="testrunner-diff-expected">{diff.raw ? diff.expected : formatValue(diff.expected)}</td>
                <td className="testrunner-diff-actual">{diff.raw ? diff.actual : formatValue(diff.actual)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </li>
  )
}

/**
 * Self-contained pass/fail panel. Props are optional -- both default to
 * this app's real built-in sample library / expected-output baseline,
 * so `<TestCaseRunner />` with no props is the normal usage.
 */
export default function TestCaseRunner({ samples = SAMPLES, expectations = TEST_CASE_EXPECTATIONS }) {
  const [results, setResults] = useState(null) // null = never run yet
  const [running, setRunning] = useState(false)
  const [progress, setProgress] = useState(null) // { index, total, name } while running

  async function runAll() {
    setRunning(true)
    setResults(null)
    const outcomes = []
    for (let i = 0; i < samples.length; i += 1) {
      const sample = samples[i]
      setProgress({ index: i + 1, total: samples.length, name: sample.name })
      const expectation = expectations[sample.name]
      if (!expectation) {
        outcomes.push({ name: sample.name, kind: sample.kind, status: 'no-expectation', diffs: [] })
        continue
      }
      // Sequential, not Promise.all: keeps run order deterministic for
      // the live progress line, and this app's own timing note
      // (CLAUDE.md SS4, ~30ms/call) means 13 sequential calls is still
      // well under a second end to end.
      // eslint-disable-next-line no-await-in-loop
      const outcome = await runOneCase(sample, expectation)
      outcomes.push(outcome)
    }
    setResults(outcomes)
    setProgress(null)
    setRunning(false)
  }

  const passCount = results ? results.filter((r) => r.status === 'pass').length : 0
  const gradedCount = results ? results.filter((r) => r.status === 'pass' || r.status === 'fail').length : 0
  const missingCount = results ? results.filter((r) => r.status === 'no-expectation').length : 0
  const allPassed = results !== null && gradedCount > 0 && passCount === gradedCount

  return (
    <div className="testrunner">
      <div className="testrunner-controls">
        <button type="button" onClick={runAll} disabled={running}>
          {running ? 'Running...' : results === null ? '▶ Run All Tests' : '▶ Run All Tests Again'}
        </button>
        {running && progress && (
          <span className="testrunner-progress">
            Running {progress.name} ({progress.index}/{progress.total})...
          </span>
        )}
      </div>

      {results === null && !running && (
        <p className="placeholder">
          Runs all {samples.length} built-in sample procedures/functions through the real /debug pipeline and
          checks each one's final variable state (or return value), and any user-created table's final row
          state, against a known-correct expected outcome.
        </p>
      )}

      {results !== null && (
        <>
          <div className={`testrunner-summary ${allPassed ? 'testrunner-summary-pass' : 'testrunner-summary-fail'}`}>
            {gradedCount > 0 ? (
              <strong>
                {passCount} / {gradedCount} passed
              </strong>
            ) : (
              <strong>No graded cases -- every sample is missing an expected output.</strong>
            )}
            {missingCount > 0 && (
              <span className="testrunner-summary-note">
                {missingCount} sample{missingCount === 1 ? '' : 's'} skipped (no expected output defined)
              </span>
            )}
          </div>

          <ul className="testrunner-case-list">
            {results.map((result) => (
              <CaseCard key={result.name} result={result} />
            ))}
          </ul>
        </>
      )}
    </div>
  )
}
