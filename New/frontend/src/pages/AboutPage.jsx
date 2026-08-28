function AboutPage() {
  return (
    <section className="about-page">
      <h1>About</h1>

      <div className="panel">
        <span className="panel-tab">PROJECT</span>
        <p>
          A course project debugger for a small procedural-SQL subset -- a real tokenizer, recursive-descent
          parser, and tree-walking interpreter, not a set of canned demos. Every step trace, flowchart, and
          AI explanation is generated fresh from whatever procedure is in the editor, built-in sample or
          hand-written.
        </p>
      </div>

      <div className="panel">
        <span className="panel-tab">TECH STACK</span>
        <ul className="about-list">
          <li>
            <strong>Backend</strong> -- Python, FastAPI, a hand-written tokenizer/parser/interpreter, SQLite
            (via stdlib <code>sqlite3</code>, no ORM) for both persisted run history and cursor query
            execution.
          </li>
          <li>
            <strong>AI</strong> -- Google Gemini (<code>gemini-flash-lite-latest</code>) for per-step
            explanations and free-form Q&amp;A, with an automatic deterministic-template fallback whenever
            the API is unavailable or unconfigured.
          </li>
          <li>
            <strong>Frontend</strong> -- React + Vite, Monaco Editor for the code view, Mermaid.js for the
            control-flow diagram, React Router for navigation.
          </li>
        </ul>
      </div>

      <div className="panel">
        <span className="panel-tab">SUPPORTED GRAMMAR</span>
        <ul className="about-list">
          <li>
            <strong>Procedures</strong> -- two forms, both first-class: a bare statement body with no
            wrapper at all (the original, permanent form -- every History entry saved before{' '}
            <code>CREATE PROCEDURE</code> support existed is stored this way), or the full{' '}
            <code>CREATE PROCEDURE name(params) BEGIN ... END</code> wrapper. Params are{' '}
            <code>[IN | OUT | INOUT] name TYPE</code> (mode defaults to <code>IN</code>); <code>OUT</code>/
            <code>INOUT</code> values are flagged <code>isOutput</code> in the variable table so the final
            value is identifiable as this procedure's output.
          </li>
          <li>
            <strong>Functions</strong> -- <code>CREATE FUNCTION name(params) RETURNS type BEGIN ...
            END</code>, params are plain <code>name TYPE</code> (no mode). <code>RETURN expr;</code> is a
            statement like any other -- valid inside <code>IF</code>/<code>WHILE</code> too -- and stops
            the function immediately, no statement after it ever runs. A body that never executes a{' '}
            <code>RETURN</code> is a clear error, never a silent <code>null</code>.
          </li>
          <li>
            <strong>Variables</strong> -- <code>DECLARE name TYPE [DEFAULT expr];</code>,{' '}
            <code>SET name = expr;</code>
          </li>
          <li>
            <strong>Control flow</strong> -- <code>IF ... THEN ... [ELSE ...] END IF;</code>,{' '}
            <code>WHILE ... DO ... END WHILE;</code>
          </li>
          <li>
            <strong>Expressions</strong> -- <code>+ - * /</code>, comparisons <code>&gt; &lt; = !=</code>,
            string/number literals, parentheses -- no <code>&gt;=</code>/<code>&lt;=</code>.
          </li>
          <li>
            <strong>Cursors</strong> (MySQL-style) -- <code>DECLARE cur CURSOR FOR SELECT ...;</code>,{' '}
            <code>OPEN</code>/<code>FETCH ... INTO ...</code>/<code>CLOSE</code>, plus{' '}
            <code>cur%FOUND</code> / <code>cur%NOTFOUND</code>. The embedded query is captured as raw text
            and run against a small, fixed, auto-seeded demo table (<code>products(name, price)</code>, 3
            rows) every debug run gets for free -- there's no schema-editing feature.
          </li>
          <li>
            <strong>Exception handling</strong> -- <code>DECLARE CONTINUE HANDLER FOR condition
            statement;</code>, exactly two conditions: <strong>NOT_FOUND</strong> and{' '}
            <strong>DIVISION_BY_ZERO</strong>. Only <code>CONTINUE</code> handlers (no <code>EXIT</code>), a
            single statement per handler (no <code>BEGIN...END</code> bodies). <code>NOT_FOUND</code> is
            always non-fatal; <code>DIVISION_BY_ZERO</code> only becomes non-fatal once a handler is
            actually registered for it.
          </li>
        </ul>
        <p className="about-note">
          Not supported at all: <code>CALL</code>, <code>CASE</code>, <code>LOOP</code>/<code>LEAVE</code>,
          cursor parameters, transactions, table statements (<code>UPDATE</code>/<code>INSERT</code>/...),
          and anything not listed above. See the in-app Theory tab for runnable examples of each supported
          piece. Every sample in the library now uses the full <code>CREATE PROCEDURE</code> wrapper, for
          consistency with what the Theory tab teaches -- the bare form is still fully supported, it's just
          the backward-compatibility path rather than what a new sample demonstrates.
        </p>
      </div>

      <div className="panel">
        <span className="panel-tab">SCOPE CHOICES</span>
        <ul className="about-list">
          <li>Single-user, local run history -- no login/accounts, by design.</li>
          <li>Only successful debug runs are saved to History; failed attempts are not silently logged.</li>
          <li>Cursor data lives in one fixed demo table, not a user-editable schema.</li>
        </ul>
      </div>
    </section>
  )
}

export default AboutPage
