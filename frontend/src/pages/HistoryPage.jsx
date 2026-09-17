import { useNavigate } from 'react-router-dom'
import History from '../History'

// The persisted, cross-session run log (backed by SQLite -- distinct
// from the within-run step log at the bottom of the debugger page,
// which only covers the *current* trace and isn't saved anywhere).
// Replaying a run navigates to /sql-console (the merged Debugger/SQL
// Console page, see SqlConsolePage.jsx) and hands the run over via
// router state; SqlConsolePage reads it back out on mount.
function HistoryPage() {
  const navigate = useNavigate()

  function handleReplay(run) {
    navigate('/sql-console', { state: { replayRun: run } })
  }

  return (
    <section className="history-page">
      <h1>History</h1>
      <History onReplay={handleReplay} />
    </section>
  )
}

export default HistoryPage
