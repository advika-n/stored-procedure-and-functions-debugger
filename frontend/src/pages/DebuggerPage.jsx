import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import Editor from '@monaco-editor/react'
import mermaid from 'mermaid'
import { buildFlowchartGraph, computeDiagramState, renderMermaidDefinition } from '../cfg'
import { SAMPLES } from '../samples'
import { writeLastProcedure } from '../lastProcedure'
import { useTheme } from '../ThemeContext'
import { getMermaidPalette } from '../mermaidColors'
import { rasterizeSvgToPng } from '../svgToPng'
import VariableTimeline from '../VariableTimeline'

const REPORT_FORMATS = [
  { format: 'pdf', label: 'Download PDF' },
  { format: 'docx', label: 'Download Document' },
  { format: 'txt', label: 'Download Text' },
]

function formatValue(entry) {
  if (entry.value === null || entry.value === undefined) return null // caller shows a placeholder
  if (entry.type === 'string') return `"${entry.value}"`
  return String(entry.value)
}

// Predict Mode's guess check -- numeric comparison for numbers (so "50" and
// "50.0" both match 50), case-insensitive exact match for booleans, exact
// (surrounding-quote-tolerant) match for everything else.
function checkGuess(guessRaw, entry) {
  const guess = guessRaw.trim()
  if (guess === '') return false
  if (entry.type === 'number') {
    const g = Number(guess)
    return !Number.isNaN(g) && g === Number(entry.value)
  }
  if (entry.type === 'boolean') {
    return guess.toLowerCase() === String(entry.value).toLowerCase()
  }
  const unquoted = guess.replace(/^['"]|['"]$/g, '')
  return unquoted === String(entry.value)
}

function DebuggerPage() {
  const location = useLocation()
  const navigate = useNavigate()
  const { theme } = useTheme()

  const [health, setHealth] = useState(null)
  const [healthError, setHealthError] = useState(null)

  const [code, setCode] = useState(SAMPLES[0].code)
  const [selectedSampleName, setSelectedSampleName] = useState(SAMPLES[0].name)
  const [ast, setAst] = useState(null)
  const [steps, setSteps] = useState(null)
  // SQL Anti-Pattern Advisor findings for the current `ast` -- see
  // backend/app/advisor.py. null = no live Debug run yet (a history
  // replay leaves this null too: old saved runs predate this feature
  // and never had issues computed/stored for them); [] = a run
  // completed and the advisor found nothing to flag.
  const [issues, setIssues] = useState(null)
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

  // -- Breakpoints + Run-to-Breakpoint --------------------------------
  // Purely a frontend consumption-layer feature on top of the EXISTING
  // step trace -- a breakpoint is just a line number, and "Run to
  // Breakpoint" is nothing more than fast-forwarding currentStepIndex to
  // the next step whose `line` is in this set. No interpreter/backend
  // involvement at all: the trace is already fully computed by the time
  // any of this runs. Deliberately a raw Set<lineNumber> (per this
  // phase's own spec), not a Monaco decoration-ID map -- so a breakpoint
  // is tied to a line NUMBER, not to "this specific piece of code" the
  // way a real IDE's breakpoints track edits. Heavily editing the
  // procedure (adding/removing lines above a breakpoint) can leave a
  // marker sitting on now-different code, same simplification a lot of
  // lightweight in-browser editors make; acceptable here since this
  // isn't a persistent multi-file IDE. Breakpoints deliberately survive
  // resetRunState/new sample loads (not cleared there) -- they're an
  // editor-level concept, independent of any one Debug run, matching how
  // real debuggers keep breakpoints across re-runs.
  const [breakpoints, setBreakpoints] = useState(() => new Set())
  const breakpointDecorationsRef = useRef([])

  const toggleBreakpoint = useCallback((line) => {
    setBreakpoints((prev) => {
      const next = new Set(prev)
      if (next.has(line)) next.delete(line)
      else next.add(line)
      return next
    })
  }, [])

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

  // -- Text-to-speech for the current step's explanation, via the browser's
  // native speechSynthesis API (no external service, no dependency). Feature-
  // detected once so the speaker button/auto-read toggle simply don't render
  // in a browser/context without support, rather than throwing.
  const speechSupported = useMemo(
    () => typeof window !== 'undefined' && 'speechSynthesis' in window && 'SpeechSynthesisUtterance' in window,
    [],
  )
  const [isSpeaking, setIsSpeaking] = useState(false)
  const [autoReadExplanations, setAutoReadExplanations] = useState(false)

  // -- Predict Mode (labeled "Quiz Mode" internally in these variable/class
  // names -- renamed in the UI only, to stay distinct from the separate
  // /quiz page): predict a step's effect before it's revealed. Off by
  // default (see resetRunState/restartTrace for where the score resets).
  const [quizMode, setQuizMode] = useState(false)
  const [quizScore, setQuizScore] = useState({ correct: 0, total: 0 })
  const [quizGuess, setQuizGuess] = useState('') // the value-prediction text input
  const [quizFeedback, setQuizFeedback] = useState(null) // last { correct, guessDisplay, actualDisplay }

  // Lets the standalone /quiz page's "This Procedure" option know what's
  // currently in the editor, without a global state store -- see
  // lastProcedure.js. Fires on every code/selection change, same as the
  // Monaco editor itself; sessionStorage writes are cheap and local.
  useEffect(() => {
    writeLastProcedure(code, selectedSampleName)
  }, [code, selectedSampleName])

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

  // -- Call Stack panel --------------------------------------------------
  // Purely a display of data the interpreter already produces (see
  // backend/app/interpreter.py's `call` DebugStep field, added in the
  // CALL-support phase this one builds on) -- no interpreter/backend
  // changes at all. Each step optionally carries
  // `call: { procedureName, depth, stack }`, present only once execution
  // is actually inside a CALLed procedure; `stack` is the chain of
  // *called* procedure names only (outermost-called first) -- it does
  // NOT include the entry procedure itself (the one that started running
  // when Debug was clicked), since the interpreter's own call stack only
  // grows on a CALL. To show a true "1 frame at top level, 2 frames once
  // inside a nested call" picture, the entry procedure's name (read from
  // `ast`, not from any one step) is prepended here on the frontend --
  // this is a pure display convenience, not a change to the trace data.
  const entryProcedureName = useMemo(() => {
    if (!ast) return null
    if (ast.type === 'ProgramNode') {
      const definitions = ast.definitions ?? []
      return definitions.length > 0 ? definitions[definitions.length - 1].name ?? null : null
    }
    if (ast.type === 'ProcedureNode' || ast.type === 'FunctionNode') return ast.name ?? null
    return null // the bare, wrapper-less Procedure form has no name -- and thus can never be a CALL target either
  }, [ast])

  // Innermost (currently executing) frame first -- reads most naturally
  // as "what's running right now, and what called it" without having to
  // read the list bottom-up. Index 0 is always the currently-executing
  // frame, whether that's a CALLed procedure (depth > 0) or the entry
  // procedure itself sitting at the top level (depth 0).
  const callStackFrames = useMemo(() => {
    if (!currentStep) return []
    const calledStack = currentStep.call?.stack ?? []
    const frames = entryProcedureName ? [entryProcedureName, ...calledStack] : [...calledStack]
    return frames.slice().reverse()
  }, [currentStep, entryProcedureName])

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
    setIssues(null)
    setDiagramSvg(null)
    setCurrentStepIndex(0)
    explanationCacheRef.current = {}
    setExplanations({})
    setExplanationError(null)
    setAskMessages([])
    setAskInput('')
    setConnectors([])
    variableRowRefs.current = {}
    // A stale run's explanation shouldn't keep talking once that run is gone.
    if (speechSupported) window.speechSynthesis.cancel()
    setIsSpeaking(false)
    // A new trace is a fresh quiz session -- score and any pending guess
    // from the old one no longer mean anything (quizMode itself, the
    // toggle, is a standing preference and stays as the user left it).
    setQuizScore({ correct: 0, total: 0 })
    setQuizGuess('')
    setQuizFeedback(null)
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
      setIssues(body.issues ?? [])
    } catch (err) {
      setDebugError(err.message)
    } finally {
      setIsRunning(false)
    }
  }

  // -- Download Report (PDF / Document / Text) --------------------------
  // Mandatory course requirement (see CLAUDE.md §5): a full report --
  // inputs, step trace, intermediate variable state, final output, and
  // the flowchart -- exportable in three formats. Deliberately reuses
  // the *current* run's already-fetched `steps`/`code` rather than
  // re-running anything: the backend's /debug/report is stateless and
  // just formats whatever DebugStep trace this page already has (see
  // backend/app/report.py). The flowchart is rasterized to a PNG
  // client-side (see svgToPng.js) from the Mermaid SVG this page has
  // already rendered, since that SVG can't be handed to the backend
  // directly and re-rendering it server-side isn't a reliable option.
  const [isReportMenuOpen, setIsReportMenuOpen] = useState(false)
  const [isGeneratingReport, setIsGeneratingReport] = useState(false)
  const [reportError, setReportError] = useState(null)
  const reportMenuRef = useRef(null)

  // Dismiss the format picker the same three ways the Developed By modal
  // already establishes as this app's convention: outside click, Escape,
  // or (here) actually picking an option.
  useEffect(() => {
    if (!isReportMenuOpen) return undefined
    function handleOutsideClick(event) {
      if (reportMenuRef.current && !reportMenuRef.current.contains(event.target)) {
        setIsReportMenuOpen(false)
      }
    }
    function handleKeyDown(event) {
      if (event.key === 'Escape') setIsReportMenuOpen(false)
    }
    document.addEventListener('mousedown', handleOutsideClick)
    document.addEventListener('keydown', handleKeyDown)
    return () => {
      document.removeEventListener('mousedown', handleOutsideClick)
      document.removeEventListener('keydown', handleKeyDown)
    }
  }, [isReportMenuOpen])

  async function handleDownloadReport(format) {
    if (!hasSteps) return
    setIsReportMenuOpen(false)
    setIsGeneratingReport(true)
    setReportError(null)

    try {
      // Only PDF/Document can embed an image at all -- skip the
      // rasterization entirely for a Text download.
      const flowchartImage =
        (format === 'pdf' || format === 'docx') && diagramSvg ? await rasterizeSvgToPng(diagramSvg) : null

      const res = await fetch('/debug/report', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          format,
          code,
          params: {},
          name: selectedSampleName,
          steps,
          flowchartImage,
        }),
      })

      if (!res.ok) {
        const body = await res.json().catch(() => null)
        const detail = typeof body?.detail === 'string' ? body.detail : null
        throw new Error(detail ?? `Request failed: ${res.status}`)
      }

      const blob = await res.blob()
      const disposition = res.headers.get('Content-Disposition') ?? ''
      const filenameMatch = disposition.match(/filename="?([^"]+)"?/)
      const filename = filenameMatch ? filenameMatch[1] : `debug-report.${format}`

      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = filename
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      URL.revokeObjectURL(url)
    } catch (err) {
      setReportError(err.message)
    } finally {
      setIsGeneratingReport(false)
    }
  }

  const goToNextStep = useCallback(() => {
    setCurrentStepIndex((i) => (hasSteps && i < steps.length - 1 ? i + 1 : i))
  }, [hasSteps, steps])

  // "Continue" -- fast-forwards through the EXISTING step trace (no
  // re-execution) to the next step whose line is a breakpoint, searching
  // strictly after the current position so pressing it again while
  // already paused on one breakpoint advances to the next rather than
  // staying put. This control used to be labeled "Run to Breakpoint" --
  // renamed here (this phase's own nav-controls cleanup) once it became
  // clear it already searched forward from `currentStepIndex` rather
  // than restarting from step 0, i.e. it was always "Continue" in
  // standard debugger terms (VS Code/gdb: resume from wherever you
  // paused), not a from-scratch run. Adding a second, separately-labeled
  // "Continue" button next to it would have been an exact behavioral
  // duplicate, so this was a rename in place rather than a new control.
  // Deliberate design choice for the no-breakpoints case (kept from the
  // original phase): runs to the END of the trace instead of being
  // disabled -- the loop below simply never matches, so `targetIndex`
  // falls through to the last step, i.e. identical to "run to
  // completion." Works the same way whether or not any breakpoints are
  // defined, rather than needing a separate mode.
  const continueExecution = useCallback(() => {
    if (!hasSteps) return
    let targetIndex = steps.length - 1
    for (let i = currentStepIndex + 1; i < steps.length; i += 1) {
      if (breakpoints.has(steps[i].line)) {
        targetIndex = i
        break
      }
    }
    setCurrentStepIndex(targetIndex)
  }, [hasSteps, steps, currentStepIndex, breakpoints])

  const goToPreviousStep = useCallback(() => {
    setCurrentStepIndex((i) => (i > 0 ? i - 1 : i))
  }, [])

  // "Restart" -- jumps back to step 0 of the CURRENT trace. This control
  // used to be labeled "Reset", which read as if it might clear the
  // editor/trace entirely; it never did that (resetRunState, a separate
  // function, is what actually clears `steps`/`ast`/`code` on a new
  // sample/Debug run) -- this only ever rewound `currentStepIndex`,
  // which is exactly what "Restart" means here: re-run the same
  // already-submitted SQL from the start with NO re-fetch from the
  // backend, since `steps` is untouched. Renamed in place (this phase's
  // nav-controls cleanup) rather than adding a second, separately-labeled
  // "Restart" button that would have done the identical thing.
  const restartTrace = useCallback(() => {
    setCurrentStepIndex(0)
    // Replaying the same trace from the top is a fresh quiz attempt too.
    setQuizScore({ correct: 0, total: 0 })
    setQuizGuess('')
    setQuizFeedback(null)
  }, [])

  // Predict Mode: what (if anything) to predict before the step AFTER the
  // current one is revealed. A changed variable (the first one, if a
  // step changes several -- kept to one prediction so this stays quick)
  // takes priority over a branch decision; a step with neither (a plain
  // sequential statement) just means nothing to predict here.
  const upcomingQuiz = useMemo(() => {
    if (!quizMode || !hasSteps || isLastStep) return null
    const upcoming = steps[currentStepIndex + 1]
    const changedEntry = Object.entries(upcoming.variables ?? {}).find(([, entry]) => entry.changed)
    if (changedEntry) {
      const [variableName, entry] = changedEntry
      return { type: 'value', variableName, entry }
    }
    if (upcoming.nodeType === 'IfStatement') {
      return { type: 'branch', actualPath: upcoming.branch?.path ?? 'none' }
    }
    // Deliberately NOT extended to CaseStatement: this quiz's own UI is
    // a fixed pair of Then/Else buttons (submitBranchGuess below), which
    // has nowhere to put CASE's open-ended "which of N WHENs" choice --
    // a real N-way prediction widget is a separate feature, not a
    // natural extension of this one, so a CASE step simply offers no
    // branch-prediction prompt (its own 'changed variable' prediction,
    // if any, on the step AFTER it still works normally either way).
    return null
  }, [quizMode, hasSteps, isLastStep, steps, currentStepIndex])

  const recordQuizResult = useCallback((correct, guessDisplay, actualDisplay) => {
    setQuizScore((s) => ({ correct: s.correct + (correct ? 1 : 0), total: s.total + 1 }))
    setQuizFeedback({ correct, guessDisplay, actualDisplay })
  }, [])

  const submitValueGuess = useCallback(
    (event) => {
      event.preventDefault()
      if (!upcomingQuiz || upcomingQuiz.type !== 'value') return
      const correct = checkGuess(quizGuess, upcomingQuiz.entry)
      recordQuizResult(correct, quizGuess.trim(), formatValue(upcomingQuiz.entry) ?? '—')
      setQuizGuess('')
      goToNextStep()
    },
    [upcomingQuiz, quizGuess, recordQuizResult, goToNextStep],
  )

  const submitBranchGuess = useCallback(
    (choice) => {
      if (!upcomingQuiz || upcomingQuiz.type !== 'branch') return
      // No ELSE block ('none' -- condition was false, nothing to enter)
      // still counts as "Else" for scoring: the THEN branch wasn't taken.
      const correct = choice === 'then' ? upcomingQuiz.actualPath === 'then' : upcomingQuiz.actualPath !== 'then'
      recordQuizResult(correct, choice === 'then' ? 'Then' : 'Else', upcomingQuiz.actualPath === 'then' ? 'Then' : 'Else')
      goToNextStep()
    },
    [upcomingQuiz, recordQuizResult, goToNextStep],
  )

  // The gate every "advance" action (Next button, ArrowRight) goes
  // through in Predict Mode: a pending prediction must be answered via the
  // quiz panel, not skipped past. Previous/the scrubber/step-log clicks
  // are deliberate free navigation rather than "advancing", so they're
  // left alone -- jumping around freely still works exactly as before.
  const handleAdvance = useCallback(() => {
    if (upcomingQuiz) return
    goToNextStep()
  }, [upcomingQuiz, goToNextStep])

  // Left/right arrow step navigation, but only while the editor itself
  // isn't the thing capturing keystrokes (so normal editing still works).
  useEffect(() => {
    function handleKeyDown(event) {
      if (editorRef.current?.hasTextFocus()) return
      if (event.key === 'ArrowRight') handleAdvance()
      else if (event.key === 'ArrowLeft') goToPreviousStep()
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [handleAdvance, goToPreviousStep])

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

    // Breakpoints: clicking either the glyph margin (where the red dot
    // lives) or the line-number column itself toggles a breakpoint on
    // that line -- Monaco's own MouseTargetType tells the two gutter
    // strips apart from a click anywhere else in the editor.
    // `toggleBreakpoint` is stable (empty-deps useCallback around a
    // functional setState) so this closure never goes stale even though
    // handleEditorMount itself only runs once, at mount.
    editor.onMouseDown((event) => {
      const targetType = event.target.type
      const isGutterClick =
        targetType === monacoInstance.editor.MouseTargetType.GUTTER_GLYPH_MARGIN ||
        targetType === monacoInstance.editor.MouseTargetType.GUTTER_LINE_NUMBERS
      if (!isGutterClick) return
      const line = event.target.position?.lineNumber
      if (line) toggleBreakpoint(line)
    })
  }

  // Keeps the glyph-margin red dots in sync with `breakpoints`. Clamped
  // to the current model's actual line count so a breakpoint left over
  // from a longer procedure never throws when a shorter one is loaded --
  // it just has no glyph to show until a line that far down exists again.
  useEffect(() => {
    const editor = editorRef.current
    const monacoInstance = monacoRef.current
    if (!editor || !monacoInstance) return

    const lineCount = editor.getModel()?.getLineCount() ?? 0
    const decorations = Array.from(breakpoints)
      .filter((line) => line >= 1 && line <= lineCount)
      .map((line) => ({
        range: new monacoInstance.Range(line, 1, line, 1),
        options: {
          isWholeLine: false,
          glyphMarginClassName: 'breakpoint-glyph',
          glyphMarginHoverMessage: { value: 'Breakpoint -- click the glyph margin or line number to remove' },
        },
      }))
    breakpointDecorationsRef.current = editor.deltaDecorations(breakpointDecorationsRef.current, decorations)
  }, [breakpoints, isEditorReady, code])

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
    // A distinct (coral, not amber) current-line tint when execution is
    // actually paused ON a breakpointed line -- lets "stopped here
    // because of a breakpoint" read differently at a glance from
    // ordinary step-by-step navigation landing on the same line.
    const isPausedAtBreakpoint = breakpoints.has(line)
    decorationsRef.current = editor.deltaDecorations(decorationsRef.current, [
      {
        range: new monacoInstance.Range(line, 1, line, 1),
        options: {
          isWholeLine: true,
          className: isPausedAtBreakpoint ? 'debug-current-line debug-current-line-breakpoint' : 'debug-current-line',
        },
      },
    ])
    editor.revealLineInCenter(line, monacoInstance.editor.ScrollType.Smooth)
    updateCaretAndConnectors()
  }, [currentStepIndex, currentStep, isEditorReady, updateCaretAndConnectors, breakpoints])

  // Re-applies mermaid's global config whenever Day/Night Mode changes
  // (or on first mount) -- 'base' + explicit themeVariables (rather than
  // the light 'neutral' theme this used before the restyle) so default,
  // unclassed flowchart nodes match the active theme out of the box;
  // classDef overrides in cfg.js still win for current/visited/terminal
  // nodes specifically. Declared before the mermaidDefinition memo/render
  // effect below so, within the same commit, the new palette is already
  // applied by the time mermaid.render() runs for a theme-driven redraw.
  useEffect(() => {
    const palette = getMermaidPalette(theme)
    mermaid.initialize({
      startOnLoad: false,
      theme: 'base',
      securityLevel: 'strict',
      themeVariables: {
        background: palette.background,
        primaryColor: palette.primaryColor,
        primaryBorderColor: palette.primaryBorderColor,
        primaryTextColor: palette.textPrimary,
        lineColor: palette.lineColor,
        fontFamily: "'IBM Plex Mono', monospace",
      },
    })
  }, [theme])

  // The graph's shape comes purely from the AST and is rebuilt only when
  // a new procedure is parsed -- not on every step.
  //
  // cfg.js's buildFlowchartGraph only understands a single
  // FunctionNode/ProcedureNode/bare-Procedure body (see its own module
  // docstring) -- it isn't taught about the CALL-support phase's
  // `ProgramNode` wrapper (out of THIS phase's scope too: "don't touch
  // flowchart generation"). Left completely unhandled, a ProgramNode's
  // missing top-level `body` would throw inside buildFlowchartGraph the
  // moment a CALL-based sample (e.g. OrderTotal/RecursiveFactorial,
  // added this phase) is debugged, crashing the whole page (no error
  // boundary exists anywhere in this app -- see App.jsx). The minimal,
  // crash-preventing fix that still touches none of cfg.js's own
  // graph-building/rendering logic: hand it the entry definition's own
  // ProcedureNode/FunctionNode (the last one -- see parser.py's
  // last-definition-is-entry convention) instead of the ProgramNode
  // wrapper, so the flowchart shows the entry procedure's own control
  // flow (a `CALL Foo(...)` line renders as a plain rect, labeled via
  // cfg.js's existing default case since it doesn't recognize
  // `CallStatement` specifically -- a cosmetic gap, not a crash).
  const flowchartAst = useMemo(() => {
    if (!ast) return null
    if (ast.type === 'ProgramNode') {
      const definitions = ast.definitions ?? []
      return definitions.length > 0 ? definitions[definitions.length - 1] : null
    }
    return ast
  }, [ast])

  const flowchartGraph = useMemo(() => {
    if (!flowchartAst) return null
    try {
      return buildFlowchartGraph(flowchartAst)
    } catch {
      return null // last-resort guard -- see the comment above; never expected to actually hit this
    }
  }, [flowchartAst])

  // Styling (current node, taken/untaken branches) is recomputed as the
  // user moves currentStepIndex over the already-computed step trace.
  const diagramState = useMemo(() => {
    if (!flowchartGraph || !hasSteps) return null
    return computeDiagramState(flowchartGraph, steps, currentStepIndex)
  }, [flowchartGraph, hasSteps, steps, currentStepIndex])

  // Depends on `theme` too (not just the graph/state) -- flipping Day/
  // Night Mode needs to regenerate the mermaid *source* (its classDef
  // colors are baked in as literal hex, see cfg.js), which in turn
  // reruns the render effect below since it depends on this value.
  const mermaidDefinition = useMemo(() => {
    if (!flowchartGraph || !diagramState) return null
    return renderMermaidDefinition(flowchartGraph, diagramState, theme)
  }, [flowchartGraph, diagramState, theme])

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
  // Primitive (not the object reference) so effects below only re-fire when
  // the text actually changes -- currentExplanation is looked up fresh from
  // state on every render even when it resolves to the same entry.
  const currentExplanationText = currentExplanation?.explanation ?? null

  // Speak `text` aloud, replacing whatever (if anything) is already
  // speaking -- speechSynthesis queues by default, and we never want two
  // explanations overlapping.
  const speak = useCallback(
    (text) => {
      if (!speechSupported || !text) return
      window.speechSynthesis.cancel()
      const utterance = new window.SpeechSynthesisUtterance(text)
      utterance.onstart = () => setIsSpeaking(true)
      utterance.onend = () => setIsSpeaking(false)
      utterance.onerror = () => setIsSpeaking(false)
      window.speechSynthesis.speak(utterance)
    },
    [speechSupported],
  )

  const stopSpeaking = useCallback(() => {
    if (!speechSupported) return
    window.speechSynthesis.cancel()
    setIsSpeaking(false)
  }, [speechSupported])

  const handleToggleSpeak = useCallback(() => {
    if (isSpeaking) stopSpeaking()
    else if (currentExplanationText) speak(currentExplanationText)
  }, [isSpeaking, currentExplanationText, speak, stopSpeaking])

  // Auto-cancel any in-progress speech the moment the user navigates to a
  // different step -- Prev/Next, the scrubber, and the step-log all funnel
  // through setCurrentStepIndex, so this one effect covers all of them.
  // Declared before the auto-read effect below so, within the same commit,
  // any leftover speech is cancelled before a new step's explanation (if
  // already cached) starts speaking.
  useEffect(() => {
    stopSpeaking()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentStepIndex])

  // "Auto-read explanations" -- off by default (see toggle below). Fires
  // once per step, only after that step's explanation has actually arrived
  // (immediately for a cache hit, or once the /explain fetch resolves).
  useEffect(() => {
    if (!autoReadExplanations || !currentExplanationText) return
    speak(currentExplanationText)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentStep?.stepNumber, currentExplanationText, autoReadExplanations])

  // Stop any speech in flight if the page itself unmounts mid-utterance.
  useEffect(() => {
    return () => {
      if (speechSupported) window.speechSynthesis.cancel()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

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
        <div className="report-download" ref={reportMenuRef}>
          {reportError && <span className="status status-error report-download-error">Error: {reportError}</span>}
          <button
            type="button"
            className="btn-export"
            onClick={() => setIsReportMenuOpen((prev) => !prev)}
            disabled={!hasSteps || isGeneratingReport}
            aria-haspopup="true"
            aria-expanded={isReportMenuOpen}
            title="Download a full report of this run -- inputs, steps, results, and the flowchart -- as PDF, Document, or Text"
          >
            {isGeneratingReport ? 'Preparing…' : '⭳ Download Report'}{' '}
            <span className="report-download-caret" aria-hidden="true">
              {isReportMenuOpen ? '▴' : '▾'}
            </span>
          </button>
          {isReportMenuOpen && (
            <div className="report-download-menu" role="menu">
              {REPORT_FORMATS.map(({ format, label }) => (
                <button
                  key={format}
                  type="button"
                  role="menuitem"
                  onClick={() => handleDownloadReport(format)}
                >
                  {label}
                </button>
              ))}
            </div>
          )}
        </div>
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
              theme={theme === 'light' ? 'vs' : 'vs-dark'}
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
              options={{
                minimap: { enabled: false },
                fontSize: 14,
                lineHeight: 20,
                fontFamily: "'IBM Plex Mono', monospace",
                glyphMargin: true,
              }}
            />
          </div>
          <p className="breakpoint-hint">
            Click a line number (or the glyph margin beside it) to toggle a breakpoint.
            {breakpoints.size > 0 && ` ${breakpoints.size} breakpoint${breakpoints.size === 1 ? '' : 's'} set.`}
          </p>

          <div className="step-navigator">
            <button onClick={goToPreviousStep} disabled={isFirstStep}>
              ◀ Previous
            </button>
            <button onClick={handleAdvance} disabled={isLastStep || Boolean(upcomingQuiz)} title={upcomingQuiz ? 'Answer the prediction below to continue' : undefined}>
              Next ▶
            </button>
            <button
              onClick={continueExecution}
              disabled={!hasSteps || isLastStep}
              title={
                breakpoints.size > 0
                  ? 'Resume execution from here to the next breakpoint'
                  : 'No breakpoints set -- resumes execution from here to the end of the trace'
              }
            >
              ⏵ Continue
            </button>
            <button onClick={restartTrace} disabled={!hasSteps} title="Jump back to step 1 of this same trace -- no re-run, nothing re-fetched">
              ↺ Restart
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
            {hasSteps && currentStep && breakpoints.has(currentStep.line) && (
              <span className="breakpoint-paused-badge">⏸ Paused at breakpoint</span>
            )}
            {speechSupported && (
              <label className="auto-read-toggle">
                <input
                  type="checkbox"
                  checked={autoReadExplanations}
                  onChange={(event) => setAutoReadExplanations(event.target.checked)}
                />
                Auto-read explanations
              </label>
            )}
            <label className="auto-read-toggle">
              <input
                type="checkbox"
                checked={quizMode}
                onChange={(event) => setQuizMode(event.target.checked)}
              />
              Predict Mode
            </label>
            {quizMode && (
              <span className="quiz-score">
                {quizScore.correct}/{quizScore.total} correct
                {quizFeedback && (
                  <span className={quizFeedback.correct ? 'quiz-feedback quiz-feedback-correct' : 'quiz-feedback quiz-feedback-incorrect'}>
                    {quizFeedback.correct ? '✓' : '✗'}{' '}
                    {quizFeedback.correct ? 'correct' : `was ${quizFeedback.actualDisplay} (guessed ${quizFeedback.guessDisplay})`}
                  </span>
                )}
              </span>
            )}
          </div>

          {upcomingQuiz?.type === 'value' && (
            <form className="quiz-panel" onSubmit={submitValueGuess}>
              <span className="quiz-prompt-text">
                Predict the new value of <strong>{upcomingQuiz.variableName}</strong>
              </span>
              <input
                type="text"
                className="quiz-input"
                value={quizGuess}
                onChange={(event) => setQuizGuess(event.target.value)}
                placeholder="Your guess…"
                autoFocus
              />
              <button type="submit" disabled={!quizGuess.trim()}>
                Submit
              </button>
            </form>
          )}
          {upcomingQuiz?.type === 'branch' && (
            <div className="quiz-panel">
              <span className="quiz-prompt-text">Predict which branch will be taken:</span>
              <button type="button" onClick={() => submitBranchGuess('then')}>
                Then
              </button>
              <button type="button" onClick={() => submitBranchGuess('else')}>
                Else
              </button>
            </div>
          )}

          <p>
            <button onClick={handleDebug} disabled={isRunning}>
              {isRunning ? 'Running…' : 'Debug'}
            </button>
          </p>

          {debugError && <p className="status status-error">Error: {debugError}</p>}
        </div>

        <aside className="panel panel-state">
          <span className="panel-tab">LIVE STATE</span>

          <div className="call-stack-panel">
            <h2>Call Stack</h2>
            {!hasSteps && <p className="placeholder">Run Debug to see the call stack here.</p>}
            {hasSteps && callStackFrames.length === 0 && (
              <p className="call-stack-top-level">Top level — not inside a CALL.</p>
            )}
            {hasSteps && callStackFrames.length > 0 && (
              <ol className="call-stack-list">
                {callStackFrames.map((name, index) => (
                  <li
                    key={`${index}-${name}`}
                    className={index === 0 ? 'call-stack-frame call-stack-frame-current' : 'call-stack-frame'}
                  >
                    <span className="call-stack-depth">{callStackFrames.length - 1 - index}</span>
                    <span className="call-stack-name">{name}</span>
                    {index === 0 ? (
                      <span className="call-stack-current-badge">current</span>
                    ) : (
                      <span className="call-stack-caller-badge">caller</span>
                    )}
                  </li>
                ))}
              </ol>
            )}
          </div>

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
            <div className="explanation-panel-header">
              <span className="panel-tab panel-tab-nested">EXPLANATION</span>
              {speechSupported && hasSteps && currentExplanationText && (
                <button
                  type="button"
                  className={isSpeaking ? 'speak-button speak-button-active' : 'speak-button'}
                  onClick={handleToggleSpeak}
                  aria-label={isSpeaking ? 'Stop reading explanation aloud' : 'Read explanation aloud'}
                  title={isSpeaking ? 'Stop reading aloud' : 'Read this explanation aloud'}
                >
                  {isSpeaking ? '⏹' : '🔊'}
                </button>
              )}
            </div>
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

      <div className="panel panel-advisor">
        <span className="panel-tab">SQL ANTI-PATTERN ADVISOR</span>
        <p className="page-subtitle">
          A static check of the parsed procedure's structure -- runs automatically every time you click
          Debug, before (and independent of) whether it actually executes cleanly.
        </p>
        {issues === null && <p className="placeholder">Run Debug to see anti-pattern analysis here.</p>}
        {issues !== null && issues.length === 0 && (
          <p className="advisor-clean">✓ No anti-patterns detected — this procedure's structure looks clean.</p>
        )}
        {issues !== null && issues.length > 0 && (
          <ul className="advisor-issue-list">
            {issues.map((issue, index) => (
              <li key={`${issue.category}-${issue.line}-${index}`} className={`advisor-issue advisor-issue-${issue.severity}`}>
                <div className="advisor-issue-header">
                  <span className={`advisor-severity-badge advisor-severity-badge-${issue.severity}`}>
                    {issue.severity === 'warning' ? 'Warning' : 'Suggestion'}
                  </span>
                  <strong className="advisor-issue-title">{issue.title}</strong>
                  {issue.line != null && <span className="advisor-issue-line">Line {issue.line}</span>}
                </div>
                <p className="advisor-issue-message">{issue.message}</p>
                <p className="advisor-issue-suggestion">
                  <strong>Suggested fix:</strong> {issue.suggestion}
                </p>
              </li>
            ))}
          </ul>
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

      <div className="panel panel-timeline">
        <span className="panel-tab">VARIABLE TIMELINE</span>
        <p className="page-subtitle">
          Every variable's value across the <em>whole</em> run so far, not just the current step -- click a
          sparkline (or hover, then click) to jump straight to that step.
        </p>
        <VariableTimeline steps={steps} currentStepIndex={currentStepIndex} onStepSelect={setCurrentStepIndex} />
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
