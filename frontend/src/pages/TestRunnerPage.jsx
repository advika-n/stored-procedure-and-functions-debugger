// Thin page wrapper around TestCaseRunner.jsx -- per that component's
// own "self-contained panel" design (see its file header), this page
// owns only the heading/subtitle/panel chrome; all pass/fail logic
// lives in the component itself, so a future redesign only ever needs
// to touch this file, never TestCaseRunner.jsx.

import TestCaseRunner from '../TestCaseRunner'

export default function TestRunnerPage() {
  return (
    <section className="test-runner-page">
      <h1>Test-Case Runner</h1>
      <p className="page-subtitle">
        Runs every built-in sample through the same /debug pipeline the SQL Console page uses, then checks the
        final result against a hand-verified expected outcome for each -- a pass/fail regression check, not
        just a manual spot-check.
      </p>

      <div className="panel panel-test-runner">
        <span className="panel-tab">Results</span>
        <TestCaseRunner />
      </div>
    </section>
  )
}
