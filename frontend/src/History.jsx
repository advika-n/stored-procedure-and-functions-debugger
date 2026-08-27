import { useEffect, useState } from 'react'

function formatTimestamp(iso) {
  try {
    return new Date(iso).toLocaleString()
  } catch {
    return iso
  }
}

function History({ onReplay }) {
  const [runs, setRuns] = useState(null) // null = loading
  const [error, setError] = useState(null)

  function refresh() {
    // No synchronous setState here (e.g. clearing a stale error) --
    // error already starts null, and the async .then/.catch below are
    // the only state updates this makes.
    fetch('/history')
      .then((res) => {
        if (!res.ok) throw new Error(`Request failed: ${res.status}`)
        return res.json()
      })
      .then((body) => setRuns(body.runs))
      .catch((err) => setError(err.message))
  }

  useEffect(() => {
    refresh()
  }, [])

  async function handleReplay(id) {
    setError(null)
    try {
      const res = await fetch(`/history/${id}`)
      if (!res.ok) throw new Error(`Request failed: ${res.status}`)
      const run = await res.json()
      onReplay(run)
    } catch (err) {
      setError(err.message)
    }
  }

  async function handleDelete(id, event) {
    event.stopPropagation() // don't also trigger the row's replay click
    setError(null)
    try {
      const res = await fetch(`/history/${id}`, { method: 'DELETE' })
      if (!res.ok) throw new Error(`Request failed: ${res.status}`)
      setRuns((prev) => prev.filter((run) => run.id !== id))
    } catch (err) {
      setError(err.message)
    }
  }

  async function handleClearAll() {
    setError(null)
    try {
      const res = await fetch('/history', { method: 'DELETE' })
      if (!res.ok) throw new Error(`Request failed: ${res.status}`)
      setRuns([])
    } catch (err) {
      setError(err.message)
    }
  }

  return (
    <div className="history-panel">
      <div className="history-header">
        <p className="history-blurb">
          A local log of past Debug runs, persisted server-side in SQLite -- not a user account
          system, just a "recent runs" list for this tool's own use.
        </p>
        <button onClick={handleClearAll} disabled={!runs || runs.length === 0}>
          Clear all
        </button>
      </div>

      {error && <p className="status status-error">Error: {error}</p>}
      {runs === null && !error && <p className="placeholder">Loading history…</p>}
      {runs && runs.length === 0 && <p className="placeholder">No runs yet -- Debug a procedure to start one.</p>}

      {runs && runs.length > 0 && (
        <ul className="history-list">
          {runs.map((run) => (
            <li key={run.id} className="history-row" onClick={() => handleReplay(run.id)}>
              <div className="history-row-main">
                <span className="history-name">{run.procedureName}</span>
                <span className="history-timestamp">{formatTimestamp(run.timestamp)}</span>
              </div>
              <div className="history-row-side">
                <span className="history-step-count">{run.stepCount} steps</span>
                <span className={`status-badge status-badge-${run.status}`}>{run.status}</span>
                <button className="history-delete" onClick={(event) => handleDelete(run.id, event)}>
                  Delete
                </button>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

export default History
