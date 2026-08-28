import { useState } from 'react'
import { readLastProcedure } from '../lastProcedure'

// A standalone conceptual quiz, distinct from the Debugger's inline
// "Predict Mode" (predicting one step's outcome mid-trace) -- this is a
// full 5-question multiple-choice quiz generated fresh by Gemini, either
// general theory or grounded in whatever procedure is currently loaded
// in the Debugger. See backend/app/quiz.py for the generation/parsing.
function QuizPage() {
  // Read once per page visit (this component remounts on every
  // navigation to /quiz, so a fresh read always reflects whatever the
  // Debugger last had loaded -- see lastProcedure.js).
  const [lastProcedure] = useState(() => readLastProcedure())
  const hasLoadedProcedure = Boolean(lastProcedure)

  const [source, setSource] = useState('theory') // 'theory' | 'procedure'
  const [generating, setGenerating] = useState(false)
  const [generateError, setGenerateError] = useState(null)

  const [phase, setPhase] = useState('setup') // 'setup' | 'taking' | 'results'
  const [questions, setQuestions] = useState(null)
  const [currentIndex, setCurrentIndex] = useState(0)
  const [answers, setAnswers] = useState([]) // [{ selectedIndex, correct }, ...] in question order

  async function handleGenerate() {
    setGenerating(true)
    setGenerateError(null)
    try {
      const res = await fetch('/quiz/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          source,
          code: source === 'procedure' ? lastProcedure?.code : undefined,
        }),
      })
      const body = await res.json()
      if (!res.ok) {
        throw new Error(typeof body.detail === 'string' ? body.detail : `Request failed: ${res.status}`)
      }
      setQuestions(body.questions)
      setAnswers([])
      setCurrentIndex(0)
      setPhase('taking')
    } catch (err) {
      setGenerateError(err.message)
    } finally {
      setGenerating(false)
    }
  }

  function handleAnswer(optionIndex) {
    const question = questions[currentIndex]
    const correct = optionIndex === question.correctIndex
    const nextAnswers = [...answers, { selectedIndex: optionIndex, correct }]
    setAnswers(nextAnswers)

    if (currentIndex + 1 < questions.length) {
      setCurrentIndex((i) => i + 1)
    } else {
      setPhase('results')
    }
  }

  const score = answers.filter((a) => a.correct).length

  return (
    <section className="quiz-page">
      <h1>Quiz</h1>

      {phase === 'setup' && (
        <div className="panel">
          <span className="panel-tab">GENERATE QUIZ</span>
          <p className="quiz-page-blurb">
            Five Gemini-generated multiple-choice questions -- either general theory covering procedures,
            functions, control flow, cursors, and exception handling, or questions specific to whatever
            procedure is currently loaded in the Debugger.
          </p>

          <div className="quiz-page-source-picker">
            <label className="quiz-page-source-option">
              <input
                type="radio"
                name="quiz-source"
                value="theory"
                checked={source === 'theory'}
                onChange={() => setSource('theory')}
              />
              General Theory
            </label>
            <label className={`quiz-page-source-option${hasLoadedProcedure ? '' : ' quiz-page-source-option-disabled'}`}>
              <input
                type="radio"
                name="quiz-source"
                value="procedure"
                checked={source === 'procedure'}
                disabled={!hasLoadedProcedure}
                onChange={() => setSource('procedure')}
              />
              This Procedure{hasLoadedProcedure && lastProcedure.name ? ` (${lastProcedure.name})` : ''}
            </label>
          </div>
          {!hasLoadedProcedure && (
            <p className="quiz-page-hint">Load a procedure in the Debugger first to enable this option.</p>
          )}

          <p>
            <button onClick={handleGenerate} disabled={generating}>
              {generating ? 'Generating…' : 'Generate Quiz'}
            </button>
          </p>

          {generateError && <p className="status status-error">Couldn't generate a quiz: {generateError}</p>}
        </div>
      )}

      {phase === 'taking' && questions && (
        <div className="panel">
          <span className="panel-tab">
            QUESTION {currentIndex + 1} OF {questions.length}
          </span>
          <p className="quiz-page-question">{questions[currentIndex].question}</p>
          <div className="quiz-page-options">
            {questions[currentIndex].options.map((option, index) => (
              <button key={index} className="quiz-page-option" onClick={() => handleAnswer(index)}>
                {option}
              </button>
            ))}
          </div>
        </div>
      )}

      {phase === 'results' && questions && (
        <div className="panel">
          <span className="panel-tab">RESULTS</span>
          <p className="quiz-page-score">
            {score} / {questions.length} correct
          </p>

          <ol className="quiz-page-review-list">
            {questions.map((question, qIndex) => {
              const answer = answers[qIndex]
              return (
                <li key={qIndex} className="quiz-page-review-item">
                  <p className="quiz-page-review-question">
                    {qIndex + 1}. {question.question}
                  </p>
                  <ul className="quiz-page-review-options">
                    {question.options.map((option, oIndex) => {
                      const isCorrectAnswer = oIndex === question.correctIndex
                      const isUserPick = oIndex === answer?.selectedIndex
                      let className = 'quiz-page-review-option'
                      if (isCorrectAnswer) className += ' quiz-page-review-option-correct'
                      else if (isUserPick) className += ' quiz-page-review-option-incorrect'
                      return (
                        <li key={oIndex} className={className}>
                          {option}
                          {isCorrectAnswer && <span className="quiz-page-review-mark">✓ correct answer</span>}
                          {isUserPick && !isCorrectAnswer && <span className="quiz-page-review-mark">✗ your answer</span>}
                        </li>
                      )
                    })}
                  </ul>
                  <p className="quiz-page-review-explanation">{question.explanation}</p>
                </li>
              )
            })}
          </ol>

          <p>
            <button onClick={handleGenerate} disabled={generating}>
              {generating ? 'Generating…' : 'Try another quiz'}
            </button>
          </p>
          {generateError && <p className="status status-error">Couldn't generate a quiz: {generateError}</p>}
        </div>
      )}
    </section>
  )
}

export default QuizPage
