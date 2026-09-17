import { useMemo, useState } from 'react'
import Editor from '@monaco-editor/react'
import { SAMPLES } from '../samples'
import { useTheme } from '../ThemeContext'
import { computeDivergence, formatValue } from '../compareTraces'

// Side-by-Side Run Comparison -- the second of the four Innovation
// features (see HANDOFF.md). Reuses the exact POST /debug data contract
// the SQL Console page (the merged Debugger + SQL Console -- see
// SqlConsolePage.jsx) and the Anti-Pattern Advisor already rely on
// (backend/app/main.py) -- each pane calls it independently and this
// page never re-parses/re-interprets anything itself. No backend change
// was needed: /debug is already stateless per request, so two panes
// calling it concurrently need nothing extra from the server.

const EMPTY_RUN = { steps: null, error: null, running: false }

function makePane(initialCode, initialSampleName) {
  return { code: initialCode, sampleName: initialSampleName, ...EMPTY_RUN }
}

// One side's view of the currently-selected shared step. If this side's
// trace already ended, freezes on its last real step (grayed, with a
// note) instead of erroring -- the PHASE prompt's "handle the shorter
// one reaching its end gracefully" requirement.
function ComparePane({ label, steps, sharedIndex, diverged, divergedVariableName }) {
  const isFinished = sharedIndex >= steps.length
  const step = steps[Math.min(sharedIndex, steps.length - 1)]

  return (
    <div className={diverged ? 'panel compare-step-pane compare-step-pane-diverged' : 'panel compare-step-pane'}>
      <span className="panel-tab">{label}</span>
      {isFinished && (
        <p className="compare-finished-note">
          This run finished after {steps.length} step{steps.length === 1 ? '' : 's'} — showing its final state.
        </p>
      )}
      <p className="compare-step-line">
        <span className="compare-step-line-number">Line {step.line}</span>
        <code>{step.statementText}</code>
      </p>

      {step.error && (
        <div className={`error-banner ${step.error.handler === 'unhandled' ? 'error-banner-unhandled' : 'error-banner-handled'}`}>
          <div className="error-banner-headline">
            <span className="error-banner-condition">{step.error.condition}</span>
            {step.error.message}
          </div>
          <div className="error-banner-handler">
            {step.error.handler === 'unhandled' ? 'No handler caught this — unhandled.' : `Caught by: ${step.error.handler}`}
          </div>
        </div>
      )}

      <table className="variable-table">
        <thead>
          <tr>
            <th>Variable</th>
            <th>Value</th>
            <th>Type</th>
          </tr>
        </thead>
        <tbody>
          {Object.entries(step.variables ?? {}).map(([name, entry]) => {
            const formatted = formatValue(entry)
            const isDivergedVariable = diverged && name === divergedVariableName
            return (
              <tr
                key={name}
                className={[entry.changed && 'var-row-changed', isDivergedVariable && 'compare-var-diverged']
                  .filter(Boolean)
                  .join(' ')}
              >
                <td>{name}</td>
                <td>
                  {formatted === null ? <em className="var-empty">—</em> : formatted}
                  {entry.changed && <span className="changed-badge">changed</span>}
                </td>
                <td>{entry.type}</td>
              </tr>
            )
          })}
          {Object.keys(step.variables ?? {}).length === 0 && (
            <tr>
              <td colSpan={3}>
                <em className="var-empty">No variables declared yet.</em>
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  )
}

function ComparePage() {
  const { theme } = useTheme()

  const [left, setLeft] = useState(() => makePane(SAMPLES[0].code, SAMPLES[0].name))
  const [right, setRight] = useState(() => makePane(SAMPLES[0].code, SAMPLES[0].name))
  const [sharedStepIndex, setSharedStepIndex] = useState(0)

  const hasLeftSteps = Array.isArray(left.steps) && left.steps.length > 0
  const hasRightSteps = Array.isArray(right.steps) && right.steps.length > 0
  const bothHaveSteps = hasLeftSteps && hasRightSteps
  const maxLen = bothHaveSteps ? Math.max(left.steps.length, right.steps.length) : 0

  const divergence = useMemo(
    () => (bothHaveSteps ? computeDivergence(left.steps, right.steps) : null),
    [bothHaveSteps, left.steps, right.steps],
  )

  function updatePane(setPane, patch) {
    setPane((prev) => ({ ...prev, ...patch }))
  }

  function handleSampleChange(setPane, sampleName) {
    const sample = SAMPLES.find((s) => s.name === sampleName)
    if (!sample) return
    setPane(makePane(sample.code, sample.name))
    setSharedStepIndex(0)
  }

  async function handleDebug(setPane, pane) {
    updatePane(setPane, { running: true, error: null })
    try {
      const res = await fetch('/debug', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ code: pane.code, params: {}, name: pane.sampleName }),
      })
      const body = await res.json()
      if (!res.ok) {
        const detail = body.detail
        const line = detail?.line != null ? ` (line ${detail.line})` : ''
        throw new Error(`[${detail?.stage ?? 'error'}] ${detail?.message ?? 'Unknown error'}${line}`)
      }
      updatePane(setPane, { steps: body.steps, running: false })
      setSharedStepIndex(0) // a fresh trace on either side invalidates the old shared position
    } catch (err) {
      updatePane(setPane, { steps: null, error: err.message, running: false })
    }
  }

  const goToPreviousSharedStep = () => setSharedStepIndex((i) => (i > 0 ? i - 1 : i))
  const goToNextSharedStep = () => setSharedStepIndex((i) => (bothHaveSteps && i < maxLen - 1 ? i + 1 : i))
  const resetSharedStep = () => setSharedStepIndex(0)

  const divergedHere = divergence !== null && divergence.index === sharedStepIndex

  return (
    <section className="compare-page">
      <h1>Side-by-Side Run Comparison</h1>
      <p className="page-subtitle">
        Run two procedures (or the same one edited differently) independently, then step through both traces
        together. The first point where they diverge — a different line, a different branch, a different
        variable value, or one erroring while the other doesn't — is flagged automatically.
      </p>

      <div className="compare-grid">
        {[
          { pane: left, setPane: setLeft, label: 'RUN A' },
          { pane: right, setPane: setRight, label: 'RUN B' },
        ].map(({ pane, setPane, label }) => (
          <div className="panel compare-pane" key={label}>
            <span className="panel-tab">{label}</span>
            <select
              className="compare-sample-select"
              value={pane.sampleName ?? ''}
              onChange={(event) => handleSampleChange(setPane, event.target.value)}
            >
              {!SAMPLES.some((s) => s.name === pane.sampleName) && <option value="">Custom / edited</option>}
              {SAMPLES.map((sample) => (
                <option key={sample.name} value={sample.name}>
                  {sample.name}
                </option>
              ))}
            </select>
            <div className="editor-shell">
              <Editor
                height="260px"
                defaultLanguage="sql"
                theme={theme === 'light' ? 'vs' : 'vs-dark'}
                value={pane.code}
                onChange={(value) => {
                  const newCode = value ?? ''
                  updatePane(setPane, {
                    code: newCode,
                    sampleName: newCode === SAMPLES.find((s) => s.name === pane.sampleName)?.code ? pane.sampleName : null,
                  })
                }}
                options={{ minimap: { enabled: false }, fontSize: 13, lineHeight: 19, fontFamily: "'IBM Plex Mono', monospace" }}
              />
            </div>
            <p>
              <button onClick={() => handleDebug(setPane, pane)} disabled={pane.running}>
                {pane.running ? 'Running…' : 'Debug'}
              </button>
            </p>
            {pane.error && <p className="status status-error">Error: {pane.error}</p>}
          </div>
        ))}
      </div>

      {!bothHaveSteps && (
        <div className="panel compare-controls">
          <span className="panel-tab">SYNCHRONIZED STEPPING</span>
          <p className="placeholder">Click Debug on both sides above to compare their traces here.</p>
        </div>
      )}

      {bothHaveSteps && (
        <div className="panel compare-controls">
          <span className="panel-tab">SYNCHRONIZED STEPPING</span>
          <div className="step-navigator">
            <button onClick={goToPreviousSharedStep} disabled={sharedStepIndex <= 0}>
              ◀ Previous
            </button>
            <button onClick={goToNextSharedStep} disabled={sharedStepIndex >= maxLen - 1}>
              Next ▶
            </button>
            <button onClick={resetSharedStep} disabled={sharedStepIndex === 0}>
              Reset
            </button>
            <input
              type="range"
              className="step-scrubber"
              min={0}
              max={maxLen - 1}
              value={sharedStepIndex}
              onChange={(event) => setSharedStepIndex(Number(event.target.value))}
              aria-label="Jump to shared step"
            />
            <span className="step-label">
              Step {sharedStepIndex + 1} of {maxLen}
            </span>
          </div>

          {divergence === null && (
            <p className="compare-divergence compare-divergence-none">
              ✓ No divergence detected — both runs have produced identical traces so far.
            </p>
          )}
          {divergence !== null && (
            <div className="compare-divergence compare-divergence-flagged">
              <div className="compare-divergence-headline">
                <span className="advisor-severity-badge advisor-severity-badge-warning">Diverged</span>
                <strong>Step {divergence.index + 1}</strong>
                <span className="compare-divergence-kind">({divergence.kind})</span>
              </div>
              <p>{divergence.summary}</p>
              {divergence.index !== sharedStepIndex && (
                <button type="button" onClick={() => setSharedStepIndex(divergence.index)}>
                  Jump to this step
                </button>
              )}
            </div>
          )}
        </div>
      )}

      {bothHaveSteps && (
        <div className="compare-grid">
          <ComparePane
            label="RUN A"
            steps={left.steps}
            sharedIndex={sharedStepIndex}
            diverged={divergedHere}
            divergedVariableName={divergence?.kind === 'variable' ? divergence.variableName : null}
          />
          <ComparePane
            label="RUN B"
            steps={right.steps}
            sharedIndex={sharedStepIndex}
            diverged={divergedHere}
            divergedVariableName={divergence?.kind === 'variable' ? divergence.variableName : null}
          />
        </div>
      )}
    </section>
  )
}

export default ComparePage
