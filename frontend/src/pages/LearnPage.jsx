// Learn tab -- mandatory, graded course requirement (concept explanation +
// video + references). Three always-visible sections rather than an
// accordion (unlike the Help page): this is graded content meant to be
// read in order, not a reference to jump around in.
//
// ============================================================================
// DRAFT CONTENT NOTICE (concept explanation below)
// ----------------------------------------------------------------------------
// The prose in the CONCEPT EXPLANATION section is a first-pass draft written
// to satisfy the assignment's required coverage (what a stored
// procedure/function is, why they exist, the difference between the two,
// why debugging them is non-trivial). It has not been reviewed against the
// specific course's marking rubric or the instructor's own lecture material.
// Revise/expand before submission -- do not assume this is final.
// ============================================================================

function LearnPage() {
  return (
    <section className="learn-page">
      <h1>Learn</h1>
      <p className="page-subtitle">
        The assigned topic, explained end to end: what stored procedures and functions are, why
        databases have them, and why the debugger in this project exists in the first place.
      </p>

      {/* ---------------------------------------------------------------- */}
      {/* a. CONCEPT EXPLANATION -- draft content, see the file-level      */}
      {/* comment above before treating this as final.                     */}
      {/* ---------------------------------------------------------------- */}
      <div className="panel learn-panel">
        <span className="panel-tab">CONCEPT EXPLANATION</span>
        <span className="learn-draft-flag" title="First-pass draft -- revise before submission">
          DRAFT
        </span>

        <article className="learn-concept">
          <h2>Stored Procedures &amp; Functions in Databases, and Debugging Them</h2>

          <section className="learn-concept-section">
            <h3>What is a stored procedure or function?</h3>
            <p>
              A <strong>stored procedure</strong> or <strong>function</strong> is a named block of
              procedural SQL — variables, conditionals, loops, and ordinary SQL statements — that is
              written once and saved <em>inside the database engine itself</em>, rather than living in
              application code. Once created, it's invoked by name (<code>CALL</code> for a procedure,
              or directly in an expression for a function) instead of being re-sent as raw SQL text on
              every use.
            </p>
          </section>

          <section className="learn-concept-section">
            <h3>Why they exist</h3>
            <ul className="learn-bullets">
              <li>
                <strong>Reusability</strong> — business logic (a validation rule, a multi-step update, a
                report calculation) is written once in the database and called from every application,
                script, or other procedure that needs it, instead of being copy-pasted as inline SQL in
                each place.
              </li>
              <li>
                <strong>Performance</strong> — the database can parse and plan a stored routine once and
                reuse that plan, and a single <code>CALL</code> replaces what might otherwise be several
                separate statements sent over the network one round-trip at a time.
              </li>
              <li>
                <strong>Encapsulating logic in the database layer</strong> — keeping data-manipulation
                rules next to the data they govern means the schema's invariants can be enforced (and
                changed) in one place, independent of how many different applications read or write that
                data.
              </li>
            </ul>
          </section>

          <section className="learn-concept-section">
            <h3>Procedure vs. function</h3>
            <div className="learn-table-scroll">
              <table className="learn-compare-table">
                <thead>
                  <tr>
                    <th>Question</th>
                    <th>Procedure</th>
                    <th>Function</th>
                  </tr>
                </thead>
                <tbody>
                  <tr>
                    <td>Must it return a value?</td>
                    <td>No — output is optional, via <code>OUT</code>/<code>INOUT</code> parameters</td>
                    <td>Yes — exactly one value, via <code>RETURN</code></td>
                  </tr>
                  <tr>
                    <td>Callable inside a SQL expression (e.g. a <code>SELECT</code>)?</td>
                    <td>No</td>
                    <td>Yes</td>
                  </tr>
                  <tr>
                    <td>How it's invoked</td>
                    <td><code>CALL my_procedure(...)</code></td>
                    <td>Used inline, like <code>my_function(...)</code></td>
                  </tr>
                  <tr>
                    <td>Typical use</td>
                    <td>Side-effecting operations — inserts, updates, multi-step tasks</td>
                    <td>Pure-ish computations that produce one value from their inputs</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </section>

          <section className="learn-concept-section">
            <h3>Why debugging them is non-trivial</h3>
            <p>
              Ordinary application code (Python, Java, JavaScript, ...) has decades of mature debugger
              tooling: set a breakpoint, step line by line, inspect any variable at any point. Most
              database engines offer nothing comparable for procedural SQL. A stored procedure is
              usually a black box from the caller's side — you run <code>CALL</code>, and it either
              succeeds or throws. You don't get to pause it mid-execution, watch a variable change after
              each <code>SET</code>, see which branch an <code>IF</code> actually took, count how many
              times a <code>WHILE</code> loop ran, or inspect which row a cursor was sitting on when
              something went wrong.
            </p>
            <p>
              The common workaround — sprinkling temporary <code>SELECT</code> statements through the
              body to print variable state — is intrusive (it changes the code you're trying to debug),
              slow to iterate with (one more thing to inspect means editing and re-running the whole
              procedure again), and still doesn't show control-flow decisions directly.
            </p>
            <p>
              This is exactly the gap this project's debugger fills: rather than executing procedures
              against a real database engine, it parses the procedure into a syntax tree and walks that
              tree itself, one statement at a time, recording a full snapshot of every variable, the
              branch/loop decision, and any cursor state at each step. That gives procedural SQL the same
              step-through visibility a regular application debugger gives ordinary code, without needing
              engine-specific debugger support that, for the most part, doesn't exist.
            </p>
          </section>
        </article>
      </div>

      {/* ---------------------------------------------------------------- */}
      {/* b. ANIMATED VIDEO -- placeholder embed. See the TODO immediately  */}
      {/* below: the video ID must be replaced before this ships.          */}
      {/* ---------------------------------------------------------------- */}
      {/* TODO: Replace with a real educational video on stored
          procedures/DB debugging -- do not ship placeholder ID. */}
      <div className="panel learn-panel">
        <span className="panel-tab">ANIMATED VIDEO</span>
        <span className="learn-placeholder-badge">PLACEHOLDER — replace before submission</span>

        <p className="learn-video-caption">
          An animated/explainer video on stored procedures, functions, and debugging them belongs here.
          The embed below is wired up and working, but points at a placeholder ID — swap{' '}
          <code>YOUR_VIDEO_ID_HERE</code> for a real YouTube video ID once one is chosen.
        </p>

        <div className="learn-video-wrap">
          <iframe
            className="learn-video-iframe"
            src="https://www.youtube.com/embed/YOUR_VIDEO_ID_HERE"
            title="Stored Procedures &amp; Functions — educational video (placeholder)"
            allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
            allowFullScreen
          />
        </div>
      </div>

      {/* ---------------------------------------------------------------- */}
      {/* c. REFERENCES -- placeholder entries per required category.      */}
      {/* ---------------------------------------------------------------- */}
      <div className="panel learn-panel">
        <span className="panel-tab">REFERENCES</span>
        <p className="learn-video-caption">
          Every entry below is a structural placeholder in the correct citation format for its category
          — each is flagged and needs a real, verified source before submission.
        </p>

        <div className="learn-ref-category">
          <h3>Books</h3>
          <ul className="learn-ref-list">
            <li>
              Elmasri, R., &amp; Navathe, S. B. (2015). <em>Fundamentals of Database Systems</em> (7th
              ed.). Pearson. <span className="learn-placeholder-badge">PLACEHOLDER</span>
            </li>
            <li>
              Silberschatz, A., Korth, H. F., &amp; Sudarshan, S. (2019). <em>Database System
              Concepts</em> (7th ed.). McGraw-Hill. <span className="learn-placeholder-badge">PLACEHOLDER</span>
            </li>
            <li>
              Date, C. J. (2003). <em>An Introduction to Database Systems</em> (8th ed.).
              Addison-Wesley. <span className="learn-placeholder-badge">PLACEHOLDER</span>
            </li>
          </ul>
        </div>

        <div className="learn-ref-category">
          <h3>Websites</h3>
          <ul className="learn-ref-list">
            <li>
              MySQL 8.0 Reference Manual — <em>Stored Objects</em>.{' '}
              <span className="learn-ref-url">https://dev.mysql.com/doc/refman/8.0/en/stored-objects.html</span>{' '}
              <span className="learn-placeholder-badge">PLACEHOLDER</span>
            </li>
            <li>
              PostgreSQL Documentation — <em>PL/pgSQL — SQL Procedural Language</em>.{' '}
              <span className="learn-ref-url">https://www.postgresql.org/docs/current/plpgsql.html</span>{' '}
              <span className="learn-placeholder-badge">PLACEHOLDER</span>
            </li>
            <li>
              Oracle PL/SQL Language Reference.{' '}
              <span className="learn-ref-url">https://docs.oracle.com/en/database/oracle/oracle-database/</span>{' '}
              <span className="learn-placeholder-badge">PLACEHOLDER — needs exact version/URL</span>
            </li>
          </ul>
        </div>

        <div className="learn-ref-category">
          <h3>Research Papers</h3>
          <ul className="learn-ref-list">
            <li>
              Author, A. A. (Year). <em>Title of paper on procedural-SQL debugging or program
              slicing.</em> Journal/Conference Name, Volume(Issue), pages.{' '}
              <span className="learn-placeholder-badge">PLACEHOLDER — needs a real citation</span>
            </li>
            <li>
              Author, B. B. (Year). <em>Title of paper on database stored-procedure
              performance/testing.</em> Journal/Conference Name, Volume(Issue), pages.{' '}
              <span className="learn-placeholder-badge">PLACEHOLDER — needs a real citation</span>
            </li>
          </ul>
        </div>

        <div className="learn-ref-category">
          <h3>Educational Resources</h3>
          <ul className="learn-ref-list">
            <li>
              Course lecture notes/slides on stored procedures and functions (this course's own DBMS
              module). <span className="learn-placeholder-badge">PLACEHOLDER — cite specific unit</span>
            </li>
            <li>
              An online course module on PL/SQL or T-SQL programming (e.g. a Coursera/edX/NPTEL
              offering). <span className="learn-placeholder-badge">PLACEHOLDER — pick a specific course</span>
            </li>
            <li>
              A tutorial article on stored procedures &amp; functions (e.g. GeeksforGeeks,
              TutorialsPoint). <span className="learn-placeholder-badge">PLACEHOLDER — pick a specific article</span>
            </li>
          </ul>
        </div>

        <div className="learn-ref-category">
          <h3>Videos</h3>
          <ul className="learn-ref-list">
            <li>
              "Title of video on stored procedures," Channel Name, YouTube.{' '}
              <span className="learn-ref-url">https://www.youtube.com/watch?v=YOUR_VIDEO_ID_HERE</span>{' '}
              <span className="learn-placeholder-badge">PLACEHOLDER — same slot as the embed above</span>
            </li>
            <li>
              "Title of video on debugging database code," Channel Name, YouTube.{' '}
              <span className="learn-ref-url">https://www.youtube.com/watch?v=YOUR_VIDEO_ID_HERE</span>{' '}
              <span className="learn-placeholder-badge">PLACEHOLDER</span>
            </li>
          </ul>
        </div>
      </div>
    </section>
  )
}

export default LearnPage
