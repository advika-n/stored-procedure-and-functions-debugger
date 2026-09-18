import { useState } from 'react'

// AI Practice -- a standalone, general-purpose competitive-exam practice
// tool (GATE DBMS PYQ style / campus placement SQL rounds), replacing the
// old standalone /quiz page (see HANDOFF.md). Not tied to any sample or
// trace -- entirely separate from the in-debugger "Predict Mode" toggle
// on the SQL Console page (which still internally calls itself "quiz-*"
// in its own state/class names, see that file's own comment -- this page
// shares nothing with it, by design).
//
// Three phases, driven by `phase`: 'setup' (difficulty + question count)
// -> 'question' (one question at a time, with the two-attempt retry flow
// described below) -> 'score' (breakdown + per-question review).
//
// The retry flow: a first wrong answer does NOT immediately count against
// the score -- it shows a "not quite, try again" state and lets the user
// pick again. Only a SECOND wrong answer on the same question counts as
// incorrect. `attempts` accumulates the indices picked for the CURRENT
// question (reset to [] on every question change); once a question is
// settled (correct, or wrong twice), a finalized record is pushed onto
// `results`, which the score screen reads for its correct-first /
// correct-retry / incorrect breakdown and per-question review.

const DIFFICULTIES = [
  {
    key: 'easy',
    label: 'Easy',
    blurb: 'Foundational recall -- keyword purposes, basic cursor/handler mechanics, procedure vs. function.',
  },
  {
    key: 'medium',
    label: 'Medium',
    blurb: 'Connect two concepts or trace a short snippet -- campus placement written-round style.',
  },
  {
    key: 'hard',
    label: 'Hard',
    blurb: 'GATE DBMS PYQ style -- subtle edge cases, nested handlers, multi-step traces.',
  },
]

const OUTCOME_LABEL = {
  'first-try': 'Correct (first try)',
  retry: 'Correct (on retry)',
  incorrect: 'Incorrect',
}

function PracticePage() {
  const [phase, setPhase] = useState('setup') // 'setup' | 'question' | 'score'

  const [difficulty, setDifficulty] = useState('medium')
  const [numQuestions, setNumQuestions] = useState(10)
  const [generating, setGenerating] = useState(false)
  const [generateError, setGenerateError] = useState(null)

  const [questions, setQuestions] = useState([])
  const [currentIndex, setCurrentIndex] = useState(0)
  const [attempts, setAttempts] = useState([]) // indices picked so far for the CURRENT question
  const [status, setStatus] = useState('answering') // 'answering' | 'retry' | 'correct' | 'revealed'
  const [results, setResults] = useState([]) // finalized {question, options, correctIndex, explanation, selections, outcome}[]

  async function handleGenerate() {
    setGenerating(true)
    setGenerateError(null)
    try {
      const res = await fetch('/practice/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ difficulty, numQuestions }),
      })
      const body = await res.json()
      if (!res.ok) {
        throw new Error(typeof body.detail === 'string' ? body.detail : `Request failed: ${res.status}`)
      }
      setQuestions(body.questions)
      setResults([])
      setCurrentIndex(0)
      setAttempts([])
      setStatus('answering')
      setPhase('question')
    } catch (err) {
      setGenerateError(err.message)
    } finally {
      setGenerating(false)
    }
  }

  function handleSelect(optionIndex) {
    if (status === 'correct' || status === 'revealed') return // already settled -- ignore stray clicks
    const question = questions[currentIndex]
    const attemptNumber = attempts.length + 1
    const nextAttempts = [...attempts, optionIndex]
    setAttempts(nextAttempts)

    if (optionIndex === question.correctIndex) {
      const outcome = attemptNumber === 1 ? 'first-try' : 'retry'
      setStatus('correct')
      setResults((prev) => [...prev, { ...question, selections: nextAttempts, outcome }])
    } else if (attemptNumber === 1) {
      setStatus('retry') // first miss -- let them try again, doesn't count yet
    } else {
      setStatus('revealed') // second miss -- now it counts, reveal the correct answer
      setResults((prev) => [...prev, { ...question, selections: nextAttempts, outcome: 'incorrect' }])
    }
  }

  function handleNext() {
    if (currentIndex + 1 < questions.length) {
      setCurrentIndex((i) => i + 1)
      setAttempts([])
      setStatus('answering')
    } else {
      setPhase('score')
    }
  }

  function handleTryAnother() {
    // Keeps difficulty/numQuestions as-is (per the spec) -- just clears
    // the finished set and drops back to the setup screen.
    setPhase('setup')
    setQuestions([])
    setResults([])
    setCurrentIndex(0)
    setAttempts([])
    setStatus('answering')
    setGenerateError(null)
  }

  const currentQuestion = questions[currentIndex]
  const score = results.filter((r) => r.outcome !== 'incorrect').length
  const firstTryCount = results.filter((r) => r.outcome === 'first-try').length
  const retryCount = results.filter((r) => r.outcome === 'retry').length
  const incorrectCount = results.filter((r) => r.outcome === 'incorrect').length
  const progressPct = questions.length ? Math.round((results.length / questions.length) * 100) : 0

  return (
    <section className="practice-page">
      <h1>AI Practice</h1>
      <p className="page-subtitle">
        Gemini-generated, competitive-exam-style practice questions on stored procedures, functions, cursors,
        exception handling, and control flow -- GATE DBMS PYQ style and campus placement SQL rounds.
      </p>

      {phase === 'setup' && (
        <div className="panel practice-setup-panel">
          <span className="panel-tab">GENERATE PRACTICE SET</span>

          <h2 className="practice-section-heading">Difficulty</h2>
          <div className="practice-difficulty-grid" role="group" aria-label="Difficulty">
            {DIFFICULTIES.map((d) => (
              <button
                key={d.key}
                type="button"
                className={`practice-difficulty-card practice-difficulty-card-${d.key}${
                  difficulty === d.key ? ' practice-difficulty-card-selected' : ''
                }`}
                aria-pressed={difficulty === d.key}
                onClick={() => setDifficulty(d.key)}
              >
                <span className="practice-difficulty-label">{d.label}</span>
                <span className="practice-difficulty-blurb">{d.blurb}</span>
              </button>
            ))}
          </div>

          <h2 className="practice-section-heading">Number of questions</h2>
          <div className="practice-stepper">
            <button
              type="button"
              className="practice-stepper-btn"
              onClick={() => setNumQuestions((n) => Math.max(1, n - 1))}
              disabled={numQuestions <= 1}
              aria-label="Fewer questions"
            >
              &minus;
            </button>
            <span className="practice-stepper-value">{numQuestions}</span>
            <button
              type="button"
              className="practice-stepper-btn"
              onClick={() => setNumQuestions((n) => Math.min(15, n + 1))}
              disabled={numQuestions >= 15}
              aria-label="More questions"
            >
              +
            </button>
            <input
              type="range"
              className="practice-stepper-slider"
              min={1}
              max={15}
              value={numQuestions}
              onChange={(event) => setNumQuestions(Number(event.target.value))}
              aria-label="Number of questions"
            />
          </div>

          <p>
            <button type="button" className="practice-generate-btn" onClick={handleGenerate} disabled={generating}>
              {generating ? (
                <span className="practice-generating-label">
                  Generating<span className="practice-generating-caret">&#9656;&#9656;&#9656;</span>
                </span>
              ) : (
                'Generate Practice Set'
              )}
            </button>
          </p>

          {generateError && <p className="status status-error">Couldn't generate a practice set: {generateError}</p>}

          {generating && (
            <div className="practice-skeleton" aria-hidden="true">
              <div className="practice-skeleton-line practice-skeleton-line-question" />
              <div className="practice-skeleton-line" />
              <div className="practice-skeleton-line" />
              <div className="practice-skeleton-line" />
            </div>
          )}
        </div>
      )}

      {phase === 'question' && currentQuestion && (
        <div className="panel practice-question-panel" key={currentIndex}>
          <span className="panel-tab">
            QUESTION {currentIndex + 1} OF {questions.length}
          </span>
          <div className="practice-progress-track" aria-hidden="true">
            <div className="practice-progress-fill" style={{ width: `${progressPct}%` }} />
          </div>

          <p className="practice-question-text">{currentQuestion.question}</p>

          <div className="practice-options">
            {currentQuestion.options.map((option, index) => {
              const pickedFirst = attempts[0] === index
              const pickedSecond = attempts[1] === index
              const isCorrectOption = index === currentQuestion.correctIndex

              let className = 'practice-option'
              if (status === 'correct' && isCorrectOption) className += ' practice-option-correct'
              if (status === 'revealed') {
                if (isCorrectOption) className += ' practice-option-correct'
                else if (pickedSecond) className += ' practice-option-wrong'
              }
              if (status === 'retry' && pickedFirst) className += ' practice-option-tried'

              const disabled = status === 'correct' || status === 'revealed' || (status === 'retry' && pickedFirst)

              return (
                <button
                  key={index}
                  type="button"
                  className={className}
                  disabled={disabled}
                  onClick={() => handleSelect(index)}
                >
                  {option}
                </button>
              )
            })}
          </div>

          {status === 'retry' && (
            <p className="practice-feedback practice-feedback-retry">Not quite -- try again.</p>
          )}

          {status === 'correct' && (
            <div className="practice-feedback practice-feedback-correct">
              <p className="practice-feedback-headline">
                &#10003; Correct{attempts.length > 1 ? ' (on retry)' : ''}!
              </p>
              <p className="practice-explanation">{currentQuestion.explanation}</p>
            </div>
          )}

          {status === 'revealed' && (
            <div className="practice-feedback practice-feedback-wrong">
              <p className="practice-feedback-headline">&#10007; Incorrect -- the correct answer is highlighted above.</p>
              <p className="practice-explanation">{currentQuestion.explanation}</p>
            </div>
          )}

          {(status === 'correct' || status === 'revealed') && (
            <p>
              <button type="button" onClick={handleNext}>
                {currentIndex + 1 < questions.length ? 'Next Question' : 'See Results'}
              </button>
            </p>
          )}
        </div>
      )}

      {phase === 'score' && (
        <div className="panel practice-score-panel">
          <span className="panel-tab">RESULTS</span>

          <p className="practice-score-headline">
            {score} / {questions.length} correct
          </p>
          <div className="practice-score-breakdown">
            <span className="practice-score-chip practice-score-chip-teal">{firstTryCount} first-try</span>
            <span className="practice-score-chip practice-score-chip-amber">{retryCount} on retry</span>
            <span className="practice-score-chip practice-score-chip-coral">{incorrectCount} incorrect</span>
          </div>

          <ol className="practice-review-list">
            {results.map((r, index) => (
              <li key={index}>
                <details className="practice-review-item">
                  <summary className="practice-review-summary">
                    <span className="practice-review-question">
                      {index + 1}. {r.question}
                    </span>
                    <span className={`practice-review-outcome practice-review-outcome-${r.outcome}`}>
                      {OUTCOME_LABEL[r.outcome]}
                    </span>
                  </summary>
                  <div className="practice-review-body">
                    <ul className="practice-review-options">
                      {r.options.map((option, oIndex) => {
                        const isCorrectAnswer = oIndex === r.correctIndex
                        const attemptLabel = r.selections
                          .map((sel, i) => (sel === oIndex ? (i === 0 ? '1st pick' : '2nd pick') : null))
                          .filter(Boolean)
                          .join(', ')
                        let cls = 'practice-review-option'
                        if (isCorrectAnswer) cls += ' practice-review-option-correct'
                        else if (attemptLabel) cls += ' practice-review-option-incorrect'
                        return (
                          <li key={oIndex} className={cls}>
                            {option}
                            {isCorrectAnswer && <span className="practice-review-mark">correct answer</span>}
                            {attemptLabel && <span className="practice-review-mark">{attemptLabel}</span>}
                          </li>
                        )
                      })}
                    </ul>
                    <p className="practice-review-explanation">{r.explanation}</p>
                  </div>
                </details>
              </li>
            ))}
          </ol>

          <p>
            <button type="button" onClick={handleTryAnother}>
              Try Another Set
            </button>
          </p>
        </div>
      )}
    </section>
  )
}

export default PracticePage
