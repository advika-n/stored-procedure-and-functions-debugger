import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import Editor from '@monaco-editor/react'
import mermaid from 'mermaid'
import { buildFlowchartGraph, computeDiagramState, renderMermaidDefinition } from './cfg'
import { SAMPLES } from './samples'
import Theory from './Theory'
import History from './History'
import './App.css'

mermaid.initialize({ startOnLoad: false, theme: 'neutral', securityLevel: 'strict' })

function formatValue(entry) {
  if (entry.value === null || entry.value === undefined) return null // caller shows a placeholder
  if (entry.type === 'string') return `"${entry.value}"`
  return String(entry.value)
}

function App() {
  const [view, setView] = useState('debugger') // 'debugger' | 'theory' | 'history'

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
  // just replays that saved state -- no re-execution.
  function loadHistoryRun(run) {
    setCode(run.code)
    lastLoadedCodeRef.current = run.code
    setSelectedSampleName(null) // may or may not match a current sample exactly
    resetRunState()
    setAst(run.ast)
    setSteps(run.steps)
    setView('debugger')
  }

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

  function handleEditorMount(editor, monacoInstance) {
    editorRef.current = editor
    monacoRef.current = monacoInstance
    setIsEditorReady(true)
  }

  // Move the current-line highlight whenever the step changes.
  useEffect(() => {
    const editor = editorRef.current
    const monacoInstance = monacoRef.current
    if (!editor || !monacoInstance) return

    if (!currentStep) {
      decorationsRef.current = editor.deltaDecorations(decorationsRef.current, [])
      return
    }

    const line = currentStep.line
    decorationsRef.current = editor.deltaDecorations(decorationsRef.current, [
      {
        range: new monacoInstance.Range(line, 1, line, 1),
        options: {
          isWholeLine: true,
          className: 'debug-current-line',
          linesDecorationsClassName: 'debug-current-line-margin',
        },
      },
    ])
    editor.revealLineInCenter(line, monacoInstance.editor.ScrollType.Smooth)
  }, [currentStepIndex, currentStep, isEditorReady])

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
    <section id="center">
      <h1>Stored Procedure and Functions Debugger</h1>

      <nav className="top-nav">
        <button
          className={view === 'debugger' ? 'top-nav-item top-nav-item-active' : 'top-nav-item'}
          onClick={() => setView('debugger')}
        >
          Debugger
        </button>
        <button
          className={view === 'theory' ? 'top-nav-item top-nav-item-active' : 'top-nav-item'}
          onClick={() => setView('theory')}
        >
          Theory
        </button>
        <button
          className={view === 'history' ? 'top-nav-item top-nav-item-active' : 'top-nav-item'}
          onClick={() => setView('history')}
        >
          History
        </button>
      </nav>

      {view === 'theory' && <Theory />}
      {view === 'history' && <History onReplay={loadHistoryRun} />}

      {view === 'debugger' && (
        <>
          <p>Backend health check (GET /health):</p>
          {healthError && <p className="status status-error">Error: {healthError}</p>}
          {!healthError && !health && <p className="status">Checking...</p>}
          {health && <p className="status status-ok">{JSON.stringify(health)}</p>}

          <h2>Sample Procedures</h2>
          <div className="sample-picker">
            <button className="sample-card sample-card-new" onClick={startNewCustomProcedure}>
              <strong>+ New / Custom</strong>
              <span className="sample-description">Clear the editor and write your own procedure from scratch.</span>
            </button>
            {SAMPLES.map((sample) => (
              <button
                key={sample.name}
                className={sample.name === selectedSampleName ? 'sample-card sample-card-active' : 'sample-card'}
                onClick={() => loadSample(sample)}
              >
                <strong>{sample.name}</strong>
                <span className="sample-description">{sample.description}</span>
              </button>
            ))}
          </div>

          <h2>Procedure</h2>

          <div className="debugger-layout">
            <div className="debugger-column-main">
              <div className="step-navigator">
                <button onClick={goToPreviousStep} disabled={isFirstStep}>
                  ◀ Previous Step
                </button>
                <button onClick={goToNextStep} disabled={isLastStep}>
                  Next Step ▶
                </button>
                <button onClick={resetSteps} disabled={!hasSteps}>
                  Reset
                </button>
                <span className="step-label">
                  {hasSteps ? `Step ${currentStepIndex + 1} of ${steps.length}` : 'No steps yet'}
                </span>
              </div>

              <div className="explanation-panel">
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
                    {currentExplanation.explanation}
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
                  </p>
                )}
              </div>

              <Editor
                height="320px"
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
                options={{ minimap: { enabled: false }, fontSize: 14 }}
              />

              <p>
                <button onClick={handleDebug} disabled={isRunning}>
                  {isRunning ? 'Running…' : 'Debug'}
                </button>
              </p>

              {debugError && <p className="status status-error">Error: {debugError}</p>}
            </div>

            <div className="debugger-column-side">
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
                            className={currentStep.cursor.hasMore ? 'cursor-badge cursor-badge-more' : 'cursor-badge cursor-badge-exhausted'}
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
                          <tr key={name} className={entry.changed ? 'var-row-changed' : undefined}>
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

              <h2>Ask AI</h2>
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
            </div>
          </div>

          <h2>Control Flow</h2>
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
        </>
      )}
    </section>
  )
}

export default App
