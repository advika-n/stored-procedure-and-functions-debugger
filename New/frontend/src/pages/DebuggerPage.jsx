import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import Editor from '@monaco-editor/react'
import mermaid from 'mermaid'
import { buildFlowchartGraph, computeDiagramState, renderMermaidDefinition } from '../cfg'
import { SAMPLES } from '../samples'

// 'base' + explicit themeVariables (rather than the light 'neutral'
// theme this used before the restyle) so default, unclassed flowchart
// nodes match the "Debugger Notebook" dark palette out of the box;
// classDef overrides in cfg.js still win for current/visited/terminal
// nodes specifically.
mermaid.initialize({
  startOnLoad: false,
  theme: 'base',
  securityLevel: 'strict',
  themeVariables: {
    background: '#161d2e',
    primaryColor: '#1d2538',
    primaryBorderColor: '#2a3348',
    primaryTextColor: '#edeff4',
    lineColor: '#2a3348',
    fontFamily: "'IBM Plex Mono', monospace",
  },
})

function formatValue(entry) {
  if (entry.value === null || entry.value === undefined) return null // caller shows a placeholder
  if (entry.type === 'string') return `"${entry.value}"`
  return String(entry.value)
}

function DebuggerPage() {
  const location = useLocation()
  const navigate = useNavigate()

  const [health, setHealth] = useState(null)
  const [healthError, setHealthError] = useState(null)

  const [code, setCode] = useState(SAMPLES[0].code)
  const [selectedSampleName, setSelectedSampleName] = useState(SAMPLES[0].name)
  const [ast, setAst] = useState(null)
  const [steps, setSteps] = useState(null)
  const [debugError, setDebugError] = useState(null)
  const [isRunning, setIsRunning] = useState(false)
  const [currentStepIndex, setCurrentStepIndex] = useState(0)

  // Tracks the code text as of the last programmatic load (sample or
  // history replay), so the Editor's onChange can tell "this is the
  // load itself re-announcing the same content" apart from "the user
  // actually typed something" -- without depending on whether Monaco
  // fires onChange for an externally-set `value` prop at all.
  const lastLoadedCodeRef = useRef(SAMPLES[0].code)

  const editorRef = useRef(null)
  const monacoRef = useRef(null)
  const decorationsRef = useRef([])
  const [isEditorReady, setIsEditorReady] = useState(false)

  // -- "Debugger Notebook" gutter caret + cause->effect connector line --
  const editorShellRef = useRef(null)
  const caretRef = useRef(null)
  const gridRef = useRef(null)
  const variableRowRefs = useRef({})
  const [connectors, setConnectors] = useState([])
  const prefersReducedMotion = useMemo(
    () => typeof window !== 'undefined' && window.matchMedia('(prefers-reduced-motion: reduce)').matches,
    [],
  )

  const [diagramSvg, setDiagramSvg] = useState(null)
  const [diagramRenderError, setDiagramRenderError] = useState(null)
  const diagramRenderCounter = useRef(0)

  // stepNumber -> { explanation, source, cached } -- a synchronous ref guards
  // against double-fetching the same step (e.g. React re-running the effect),
  // while the state copy is what actually drives rendering.
  const explanationCacheRef = useRef({})
  const [explanations, setExplanations] = useState({})
  const [explanationLoading, setExplanationLoading] = useState(false)
  const [explanationError, setExplanationError] = useState(null)

  // "Ask AI" -- a separate, user-initiated chat about the CURRENT step,
  // distinct from the automatic per-step explanation above. Each entry:
  // { id, question, answer, error, loading }. Not cached (each question
  // is answered fresh, per spec) and reset whenever the run itself resets
  // (new sample, new Debug run, history replay) since a question only
  // makes sense against the code/step it was asked about.
  const [askMessages, setAskMessages] = useState([])
  const [askInput, setAskInput] = useState('')
  const [isAskExpanded, setIsAskExpanded] = useState(false)
  const askIdRef = useRef(0)
  const askMessagesEndRef = useRef(null)

  useEffect(() => {
    fetch('/health')
      .then((res) => {
        if (!res.ok) throw new Error(`Request failed: ${res.status}`)
        return res.json()
      })
      .then(setHealth)
      .catch((err) => setHealthError(err.message))
  }, [])

  const hasSteps = Array.isArray(steps) && steps.length > 0
  const currentStep = hasSteps ? steps[currentStepIndex] : null
  const isFirstStep = currentStepIndex <= 0
  const isLastStep = !hasSteps || currentStepIndex >= steps.length - 1

  // Variable names in first-declared order, computed once per trace so the
  // watch table's row order never jumps around as new variables appear.
  const variableOrder = useMemo(() => {
    const order = []
    const seen = new Set()
    for (const step of steps ?? []) {
      for (const name of Object.keys(step.variables ?? {})) {
        if (!seen.has(name)) {
          seen.add(name)
          order.push(name)
        }
      }
    }
    return order
  }, [steps])

  // Shared by "load a new sample" and "about to run Debug" -- any time the
  // code changes out from under the current trace, that trace (and its
  // cached explanations) is stale and must be cleared.
  function resetRunState() {
    setDebugError(null)
    setSteps(null)
    setAst(null)
    setDiagramSvg(null)
    setCurrentStepIndex(0)
    explanationCacheRef.current = {}
    setExplanations({})
    setExplanationError(null)
    setAskMessages([])
    setAskInput('')
    setConnectors([])
    variableRowRefs.current = {}
  }

  function loadSample(sample) {
    setCode(sample.code)
    lastLoadedCodeRef.current = sample.code
    setSelectedSampleName(sample.name)
    resetRunState()
  }

  // The explicit path from "browsing samples" to "writing my own
  // procedure": clears the editor to empty, drops the sample selection
  // (so no sample card stays highlighted), and clears any stale trace --
  // same reset a sample load does. The interpreter, flowchart builder,
  // and Ask AI are all driven entirely by the freshly parsed AST/steps
  // from the next Debug run, so a hand-written procedure runs through
  // the exact same path a sample does, with nothing sample-specific
  // cached anywhere.
  function startNewCustomProcedure() {
    setCode('')
    lastLoadedCodeRef.current = ''
    setSelectedSampleName(null)
    resetRunState()
    editorRef.current?.focus()
  }

  // Reload a saved history entry: since its step trace and AST were
  // already computed by the interpreter when it was first run, this
  // just replays that saved state -- no re-execution. Routing to this
  // page is handled by HistoryPage (navigate('/debugger', { state }));
  // this only rehydrates the state once it arrives.
  const loadHistoryRun = useCallback((run) => {
    setCode(run.code)
    lastLoadedCodeRef.current = run.code
    setSelectedSampleName(null) // may or may not match a current sample exactly
    resetRunState()
    setAst(run.ast)
    setSteps(run.steps)
  }, [])

  useEffect(() => {
    const replayRun = location.state?.replayRun
    if (replayRun) {
      loadHistoryRun(replayRun)
      // Clear the router state so a later refresh/back-navigation to
      // /debugger doesn't silently replay this run again.
      navigate('.', { replace: true, state: null })
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [location.state])

  async function handleDebug() {
    setIsRunning(true)
    resetRunState()

    try {
      const res = await fetch('/debug', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ code, params: {}, name: selectedSampleName }),
      })
      const body = await res.json()

      if (!res.ok) {
        // Backend error shape: { detail: { stage, message, line } }
        const detail = body.detail
        const line = detail?.line != null ? ` (line ${detail.line})` : ''
        throw new Error(`[${detail?.stage ?? 'error'}] ${detail?.message ?? 'Unknown error'}${line}`)
      }

      setSteps(body.steps)
      setAst(body.ast)
    } catch (err) {
      setDebugError(err.message)
    } finally {
      setIsRunning(false)
    }
  }

  // Client-side only -- bundles the current run's code + AST + step
  // trace into a downloadable JSON file. No backend involved.
  function handleExport() {
    if (!hasSteps) return
    const payload = {
      exportedAt: new Date().toISOString(),
      procedureName: selectedSampleName ?? 'Custom procedure',
      code,
      ast,
      steps,
    }
    const blob = new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `debug-run-${Date.now()}.json`
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    URL.revokeObjectURL(url)
  }

  const goToNextStep = useCallback(() => {
    setCurrentStepIndex((i) => (hasSteps && i < steps.length - 1 ? i + 1 : i))
  }, [hasSteps, steps])

  const goToPreviousStep = useCallback(() => {
    setCurrentStepIndex((i) => (i > 0 ? i - 1 : i))
  }, [])

  const resetSteps = useCallback(() => {
    setCurrentStepIndex(0)
  }, [])

  // Left/right arrow step navigation, but only while the editor itself
  // isn't the thing capturing keystrokes (so normal editing still works).
  useEffect(() => {
    function handleKeyDown(event) {
      if (editorRef.current?.hasTextFocus()) return
      if (event.key === 'ArrowRight') goToNextStep()
      else if (event.key === 'ArrowLeft') goToPreviousStep()
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [goToNextStep, goToPreviousStep])

  // Recomputes the gutter caret's pixel position and the amber
  // cause->effect connector line(s) from it to any variable row that
  // just changed. Called on every step change, and continuously during
  // Monaco's own scroll animation (see handleEditorMount) so the caret
  // stays glued to its line while revealLineInCenter smooth-scrolls --
  // that continuous re-tracking is what makes it read as "the needle
  // advancing" rather than a instant jump.
  const updateCaretAndConnectors = useCallback(() => {
    const editor = editorRef.current
    const caret = caretRef.current
    if (!editor || !caret || !currentStep) return

    const top = editor.getTopForLineNumber(currentStep.line) - editor.getScrollTop()
    caret.style.top = `${top}px`

    if (prefersReducedMotion) {
      setConnectors([])
      return
    }

    const gridEl = gridRef.current
    if (!gridEl) return
    const gridRect = gridEl.getBoundingClientRect()
    const caretRect = caret.getBoundingClientRect()

    const changedNames = Object.entries(currentStep.variables ?? {})
      .filter(([, entry]) => entry.changed)
      .map(([name]) => name)

    const lines = []
    for (const name of changedNames) {
      const rowEl = variableRowRefs.current[name]
      if (!rowEl) continue
      const rowRect = rowEl.getBoundingClientRect()
      lines.push({
        key: `${currentStep.stepNumber}-${name}`,
        x1: caretRect.right - gridRect.left,
        y1: caretRect.top + caretRect.height / 2 - gridRect.top,
        x2: rowRect.left - gridRect.left,
        y2: rowRect.top + rowRect.height / 2 - gridRect.top,
      })
    }
    setConnectors(lines)
  }, [currentStep, prefersReducedMotion])

  // Always-current ref so the onDidScrollChange/onDidLayoutChange
  // listeners (registered once, at mount) call the latest closure
  // instead of a stale one from whenever the editor first mounted.
  const updateCaretAndConnectorsRef = useRef(() => {})
  useEffect(() => {
    updateCaretAndConnectorsRef.current = updateCaretAndConnectors
  }, [updateCaretAndConnectors])

  function handleEditorMount(editor, monacoInstance) {
    editorRef.current = editor
    monacoRef.current = monacoInstance
    setIsEditorReady(true)
    editor.onDidScrollChange(() => updateCaretAndConnectorsRef.current())
    editor.onDidLayoutChange(() => updateCaretAndConnectorsRef.current())
  }

  // Move the current-line highlight (and the caret overlay + connector
  // lines) whenever the step changes.
  useEffect(() => {
    const editor = editorRef.current
    const monacoInstance = monacoRef.current
    if (!editor || !monacoInstance) return

    if (!currentStep) {
      decorationsRef.current = editor.deltaDecorations(decorationsRef.current, [])
      setConnectors([])
      return
    }

    const line = currentStep.line
    decorationsRef.current = editor.deltaDecorations(decorationsRef.current, [
      {
        range: new monacoInstance.Range(line, 1, line, 1),
        options: { isWholeLine: true, className: 'debug-current-line' },
      },
    ])
    editor.revealLineInCenter(line, monacoInstance.editor.ScrollType.Smooth)
    updateCaretAndConnectors()
  }, [currentStepIndex, currentStep, isEditorReady, updateCaretAndConnectors])

  // The graph's shape comes purely from the AST and is rebuilt only when
  // a new procedure is parsed -- not on every step.
  const flowchartGraph = useMemo(() => (ast ? buildFlowchartGraph(ast) : null), [ast])

  // Styling (current node, taken/untaken branches) is recomputed as the
  // user moves currentStepIndex over the already-computed step trace.
  const diagramState = useMemo(() => {
    if (!flowchartGraph || !hasSteps) return null
    return computeDiagramState(flowchartGraph, steps, currentStepIndex)
  }, [flowchartGraph, hasSteps, steps, currentStepIndex])

  const mermaidDefinition = useMemo(() => {
    if (!flowchartGraph || !diagramState) return null
    return renderMermaidDefinition(flowchartGraph, diagramState)
  }, [flowchartGraph, diagramState])

  useEffect(() => {
    // Nothing to render yet (no successful Debug run) -- handleDebug
    // already cleared diagramSvg when it started this run.
    if (!mermaidDefinition) return

    let cancelled = false
    diagramRenderCounter.current += 1
    const renderId = `flowchart-${diagramRenderCounter.current}`

    mermaid
      .render(renderId, mermaidDefinition)
      .then(({ svg }) => {
        if (!cancelled) {
          setDiagramSvg(svg)
          setDiagramRenderError(null)
        }
      })
      .catch((err) => {
        if (!cancelled) setDiagramRenderError(err.message)
      })

    return () => {
      cancelled = true
    }
  }, [mermaidDefinition])

  // Fetch a plain-English explanation for the current step, unless it's
  // already cached from an earlier visit to this exact step.
  useEffect(() => {
    if (!hasSteps) return
    const step = steps[currentStepIndex]
    const key = step.stepNumber

    if (explanationCacheRef.current[key]) return // already fetched (or in flight)

    explanationCacheRef.current[key] = 'pending' // claim it before the await so we never double-fetch
    let cancelled = false
    setExplanationLoading(true)
    setExplanationError(null)

    const previousVariables = currentStepIndex > 0 ? steps[currentStepIndex - 1].variables : null

    fetch('/explain', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ step, previousVariables }),
    })
      .then((res) => {
        if (!res.ok) throw new Error(`Request failed: ${res.status}`)
        return res.json()
      })
      .then((body) => {
        if (cancelled) return
        explanationCacheRef.current[key] = body
        setExplanations((prev) => ({ ...prev, [key]: body }))
      })
      .catch((err) => {
        if (cancelled) return
        delete explanationCacheRef.current[key] // allow retrying on a later visit
        setExplanationError(err.message)
      })
      .finally(() => {
        if (!cancelled) setExplanationLoading(false)
      })

    return () => {
      cancelled = true
    }
  }, [hasSteps, currentStepIndex, steps])

  const currentExplanation = hasSteps ? explanations[steps[currentStepIndex].stepNumber] : null

  // Keep the chat scrolled to the most recent message as new ones arrive.
  useEffect(() => {
    askMessagesEndRef.current?.scrollIntoView({ block: 'nearest' })
  }, [askMessages])

  async function handleAsk(event) {
    event.preventDefault()
    const question = askInput.trim()
    if (!question || !currentStep) return

    const id = ++askIdRef.current
    setAskInput('')
    setAskMessages((prev) => [...prev, { id, question, answer: null, error: null, loading: true }])

    try {
      const res = await fetch('/ask', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ code, step: currentStep, question }),
      })
      const body = await res.json()
      if (!res.ok) {
        throw new Error(typeof body.detail === 'string' ? body.detail : `Request failed: ${res.status}`)
      }
      setAskMessages((prev) => prev.map((m) => (m.id === id ? { ...m, answer: body.answer, loading: false } : m)))
    } catch (err) {
      setAskMessages((prev) => prev.map((m) => (m.id === id ? { ...m, error: err.message, loading: false } : m)))
    }
  }

  const isAskBusy = askMessages.some((m) => m.loading)

  return (
    <section className="debugger-page">
      <div className="debugger-topbar">
        <div className="debugger-topbar-status">
          {healthError && <span className="status status-error">backend: {healthError}</span>}
          {!healthError && !health && <span className="status">backend: checking…</span>}
          {health && <span className="status status-ok">backend: ok</span>}
        </div>
        <button className="btn-export" onClick={handleExport} disabled={!hasSteps} title="Download this run's code and step trace as JSON">
          ⭳ Export Run
        </button>
      </div>

      <div className="debugger-grid" ref={gridRef}>
        <aside className="panel panel-samples">
          <span className="panel-tab">PROCEDURE LIBRARY</span>
          <button className="new-custom-button" onClick={startNewCustomProcedure}>
            + New / Custom Procedure
          </button>
          <div className="sample-list">
            {SAMPLES.map((sample) => (
              <button
                key={sample.name}
                className={sample.name === selectedSampleName ? 'sample-card sample-card-active' : 'sample-card'}
                onClick={() => loadSample(sample)}
              >
                <div className="sample-card-header">
                  <strong>{sample.name}</strong>
                  <span className={`sample-kind-tag sample-kind-tag-${sample.kind.toLowerCase()}`}>{sample.kind}</span>
                </div>
                <span className="sample-description">{sample.description}</span>
              </button>
            ))}
          </div>
        </aside>

        <div className="panel panel-editor">
          <span className="panel-tab">EDITOR</span>
          <div className="editor-shell" ref={editorShellRef}>
            <div className="editor-caret" ref={caretRef} aria-hidden="true">
              ▸
            </div>
            <Editor
              height="360px"
              defaultLanguage="sql"
              theme="vs-dark"
              value={code}
              onChange={(value) => {
                const newCode = value ?? ''
                setCode(newCode)
                // Only a genuine edit (not the load itself re-announcing
                // the same content) breaks the "this is exactly that
                // named sample" association.
                if (newCode !== lastLoadedCodeRef.current) {
                  setSelectedSampleName(null)
                }
              }}
              onMount={handleEditorMount}
              options={{ minimap: { enabled: false }, fontSize: 14, lineHeight: 20, fontFamily: "'IBM Plex Mono', monospace" }}
            />
          </div>

          <div className="step-navigator">
            <button onClick={goToPreviousStep} disabled={isFirstStep}>
              ◀ Previous
            </button>
            <button onClick={goToNextStep} disabled={isLastStep}>
              Next ▶
            </button>
            <button onClick={resetSteps} disabled={!hasSteps}>
              Reset
            </button>
            <input
              type="range"
              className="step-scrubber"
              min={0}
              max={hasSteps ? steps.length - 1 : 0}
              value={currentStepIndex}
              disabled={!hasSteps}
              onChange={(event) => setCurrentStepIndex(Number(event.target.value))}
              aria-label="Jump to step"
            />
            <span className="step-label">
              {hasSteps ? `Step ${currentStepIndex + 1} of ${steps.length}` : 'No steps yet'}
            </span>
          </div>

          <p>
            <button onClick={handleDebug} disabled={isRunning}>
              {isRunning ? 'Running…' : 'Debug'}
            </button>
          </p>

          {debugError && <p className="status status-error">Error: {debugError}</p>}
        </div>

        <aside className="panel panel-state">
          <span className="panel-tab">LIVE STATE</span>

          {hasSteps && currentStep?.error && (
            <div
              className={`error-banner ${
                currentStep.error.handler === 'unhandled' ? 'error-banner-unhandled' : 'error-banner-handled'
              }`}
            >
              <div className="error-banner-headline">
                <span className="error-banner-condition">{currentStep.error.condition}</span>
                {currentStep.error.message}
              </div>
              <div className="error-banner-handler">
                {currentStep.error.handler === 'unhandled'
                  ? 'No handler caught this — unhandled.'
                  : `Caught by: ${currentStep.error.handler}`}
              </div>
            </div>
          )}

          {hasSteps && currentStep?.cursor && (
            <div className="cursor-panel">
              <h2>Cursors</h2>
              <table className="cursor-table">
                <thead>
                  <tr>
                    <th>Cursor</th>
                    <th>Row</th>
                    <th>Current row</th>
                  </tr>
                </thead>
                <tbody>
                  <tr>
                    <td className="cursor-name">{currentStep.cursor.name}</td>
                    <td>
                      {currentStep.cursor.rowIndex}
                      <span
                        className={
                          currentStep.cursor.hasMore ? 'cursor-badge cursor-badge-more' : 'cursor-badge cursor-badge-exhausted'
                        }
                      >
                        {currentStep.cursor.hasMore ? 'more rows' : 'no more rows'}
                      </span>
                    </td>
                    <td>
                      {currentStep.cursor.currentRow ? (
                        Object.entries(currentStep.cursor.currentRow)
                          .map(([column, value]) => `${column}: ${value}`)
                          .join(', ')
                      ) : (
                        <em className="var-empty">—</em>
                      )}
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          )}

          <h2>Variables</h2>
          {!hasSteps && (
            <p className="placeholder">
              {debugError ? 'Fix the error above and run Debug again.' : 'Run Debug to see variable state here.'}
            </p>
          )}
          {hasSteps && currentStep && (
            <table className="variable-table">
              <thead>
                <tr>
                  <th>Variable</th>
                  <th>Value</th>
                  <th>Type</th>
                </tr>
              </thead>
              <tbody>
                {variableOrder
                  .filter((name) => name in currentStep.variables)
                  .map((name) => {
                    const entry = currentStep.variables[name]
                    const formatted = formatValue(entry)
                    return (
                      <tr
                        key={name}
                        ref={(el) => {
                          variableRowRefs.current[name] = el
                        }}
                        className={entry.changed ? 'var-row-changed' : undefined}
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
              </tbody>
            </table>
          )}

          {hasSteps && currentStep?.returnValue && (
            <div className="return-value-panel">
              <span className="panel-tab panel-tab-nested panel-tab-success">RETURN VALUE</span>
              <p className="return-value-text">
                <span className="return-value-badge">final result</span>
                {formatValue(currentStep.returnValue) === null ? (
                  <em className="var-empty">—</em>
                ) : (
                  formatValue(currentStep.returnValue)
                )}
                <span className="return-value-type">{currentStep.returnValue.type}</span>
              </p>
            </div>
          )}

          <div className="explanation-panel">
            <span className="panel-tab panel-tab-nested">EXPLANATION</span>
            {!hasSteps && (
              <p className="placeholder">Run Debug to see a plain-English explanation of each step.</p>
            )}
            {hasSteps && !currentExplanation && explanationLoading && (
              <p className="placeholder">Explaining…</p>
            )}
            {hasSteps && !currentExplanation && explanationError && (
              <p className="status status-error">Couldn't explain this step: {explanationError}</p>
            )}
            {hasSteps && currentExplanation && (
              <p className="explanation-text">
                <span
                  className={`explanation-source-badge explanation-source-badge-${currentExplanation.source}`}
                  title={
                    currentExplanation.source === 'gemini'
                      ? 'Generated by Gemini'
                      : 'Generated by a local template (Gemini unavailable or not configured)'
                  }
                >
                  {currentExplanation.source === 'gemini' ? 'Gemini' : 'template'}
                </span>
                {currentExplanation.explanation}
              </p>
            )}
          </div>
        </aside>

        {connectors.length > 0 && (
          <svg className="connector-overlay" aria-hidden="true">
            {connectors.map((c) => (
              <line key={c.key} x1={c.x1} y1={c.y1} x2={c.x2} y2={c.y2} className="connector-line" />
            ))}
          </svg>
        )}
      </div>

      <div className="panel panel-askai">
        <button
          className="ask-ai-toggle"
          onClick={() => setIsAskExpanded((prev) => !prev)}
          aria-expanded={isAskExpanded}
        >
          <span className="panel-tab panel-tab-inline">ASK AI</span>
          <span className="ask-ai-toggle-caret">{isAskExpanded ? '▾' : '▸'}</span>
          {!isAskExpanded && askMessages.length > 0 && (
            <span className="ask-ai-toggle-count">{askMessages.length}</span>
          )}
        </button>

        {isAskExpanded && (
          <div className="ask-panel">
            {!hasSteps && (
              <p className="placeholder">Run Debug, then step to a point in execution to ask about it.</p>
            )}
            {hasSteps && (
              <>
                <p className="ask-blurb">
                  Ask a free-form question about the current step (line {currentStep?.line}) -- e.g. "why did it
                  take this branch" or "what would happen if x was 0".
                </p>
                {askMessages.length > 0 && (
                  <ul className="ask-messages">
                    {askMessages.map((m) => (
                      <li key={m.id} className="ask-message">
                        <p className="ask-question">{m.question}</p>
                        {m.loading && <p className="ask-answer ask-loading">Thinking…</p>}
                        {!m.loading && m.answer && <p className="ask-answer">{m.answer}</p>}
                        {!m.loading && m.error && (
                          <p className="ask-answer ask-error">Couldn't get an answer: {m.error}</p>
                        )}
                      </li>
                    ))}
                    <li ref={askMessagesEndRef} />
                  </ul>
                )}
                <form className="ask-form" onSubmit={handleAsk}>
                  <input
                    type="text"
                    className="ask-input"
                    placeholder="Ask about this step…"
                    value={askInput}
                    onChange={(event) => setAskInput(event.target.value)}
                    disabled={isAskBusy}
                  />
                  <button type="submit" disabled={isAskBusy || !askInput.trim()}>
                    {isAskBusy ? 'Asking…' : 'Ask'}
                  </button>
                </form>
              </>
            )}
          </div>
        )}
      </div>

      <div className="panel panel-flowchart">
        <span className="panel-tab">CONTROL FLOW</span>
        <div className="diagram-panel">
          {!flowchartGraph && (
            <p className="placeholder">
              {debugError ? 'Fix the error above and run Debug again.' : 'Run Debug to see the control-flow diagram here.'}
            </p>
          )}
          {diagramRenderError && <p className="status status-error">Diagram error: {diagramRenderError}</p>}
          {flowchartGraph && diagramSvg && (
            // eslint-disable-next-line react/no-danger -- mermaid's own SVG output, not user input
            <div className="diagram-svg" dangerouslySetInnerHTML={{ __html: diagramSvg }} />
          )}
        </div>
      </div>

      <div className="panel panel-steplog">
        <span className="panel-tab">STEP LOG — THIS RUN</span>
        <p className="page-subtitle">
          Every step in the <em>current</em> trace only — nothing here is saved. For past sessions across
          reloads, see the <strong>History</strong> page in the top nav.
        </p>
        {!hasSteps && <p className="placeholder">Run Debug to populate the step log.</p>}
        {hasSteps && (
          <ol className="step-log-list">
            {steps.map((step, index) => (
              <li key={step.stepNumber}>
                <button
                  className={index === currentStepIndex ? 'step-log-entry step-log-entry-active' : 'step-log-entry'}
                  onClick={() => setCurrentStepIndex(index)}
                >
                  <span className="step-log-index">{index + 1}</span>
                  <span className="step-log-line">L{step.line}</span>
                  <span className="step-log-text">{step.statementText}</span>
                  {step.error && (
                    <span className={`step-log-flag ${step.error.handler === 'unhandled' ? 'step-log-flag-coral' : 'step-log-flag-amber'}`}>
                      {step.error.condition}
                    </span>
                  )}
                </button>
              </li>
            ))}
          </ol>
        )}
      </div>
    </section>
  )
}

export default DebuggerPage
