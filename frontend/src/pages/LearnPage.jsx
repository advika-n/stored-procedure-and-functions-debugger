// Learn tab -- mandatory, graded course requirement (concept explanation +
// video + references). Also absorbs the former standalone Theory tab as a
// "Deep Dive" panel, per professor's instruction to merge the two: Theory's
// per-construct write-ups (Variables/Control Flow/Cursors/Exception
// Handling/Putting It Together) now live here, between Concept Explanation
// and References. Theory's own "Stored Procedures & Functions" topic was
// dropped entirely -- it duplicated this page's Concept Explanation section.
// Four always-visible sections rather than an accordion (unlike the Help
// page): this is graded content meant to be read in order, not a reference
// to jump around in -- except Deep Dive, which is itself a tab-switcher
// (reusing the old Theory page's nav/content pattern) since its topics are
// independent of each other and not meant to be read strictly in sequence.

import { useState } from 'react'
import { THEORY_TOPICS } from '../theoryTopics'

function LearnPage() {
  const [activeTopicId, setActiveTopicId] = useState(THEORY_TOPICS[0].id)
  const activeTopic = THEORY_TOPICS.find((topic) => topic.id === activeTopicId) ?? THEORY_TOPICS[0]
  const ActiveContent = activeTopic.Content

  return (
    <section className="learn-page">
      <h1>Learn</h1>
      <p className="page-subtitle">
        The assigned topic, explained end to end: what stored procedures and functions are, why
        databases have them, and why the debugger in this project exists in the first place.
      </p>

      {/* ---------------------------------------------------------------- */}
      {/* a. ANIMATED VIDEO                                                 */}
      {/* ---------------------------------------------------------------- */}
      <div className="panel learn-panel">
        <span className="panel-tab">VIDEO</span>

        <p className="learn-video-caption">
          "Advanced SQL Tutorial | Stored Procedures + Use Cases" by Alex The Analyst — walks through
          creating and using stored procedures with practical examples.
        </p>

        <div className="learn-video-wrap">
          <iframe
            className="learn-video-iframe"
            src="https://www.youtube.com/embed/NrBJmtD0kEw"
            title="Advanced SQL Tutorial | Stored Procedures + Use Cases — Alex The Analyst"
            allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
            allowFullScreen
          />
        </div>
      </div>

      {/* ---------------------------------------------------------------- */}
      {/* b. CONCEPT EXPLANATION                                            */}
      {/* ---------------------------------------------------------------- */}
      <div className="panel learn-panel">
        <span className="panel-tab">CONCEPT EXPLANATION</span>

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
      {/* c. DEEP DIVE -- former standalone Theory tab, merged in here.     */}
      {/* ---------------------------------------------------------------- */}
      <div className="panel learn-panel">
        <span className="panel-tab">DEEP DIVE</span>

        <div className="theory-layout">
          <nav className="theory-nav">
            {THEORY_TOPICS.map((topic) => (
              <button
                key={topic.id}
                className={topic.id === activeTopicId ? 'theory-nav-item theory-nav-item-active' : 'theory-nav-item'}
                onClick={() => setActiveTopicId(topic.id)}
              >
                {topic.title}
              </button>
            ))}
          </nav>
          <article className="theory-content">
            <h2>{activeTopic.title}</h2>
            <ActiveContent />
          </article>
        </div>
      </div>

      {/* ---------------------------------------------------------------- */}
      {/* d. REFERENCES -- verified real sources per required category.    */}
      {/* ---------------------------------------------------------------- */}
      <div className="panel learn-panel">
        <span className="panel-tab">REFERENCES</span>

        <div className="learn-ref-category">
          <h3>Books</h3>
          <ul className="learn-ref-list">
            <li>
              Elmasri, R., &amp; Navathe, S. B. (2016). <em>Fundamentals of Database Systems</em> (7th
              ed.). Pearson. Ch. 13 covers stored procedures and PL/SQL-style procedural constructs.
            </li>
            <li>
              Silberschatz, A., Korth, H. F., &amp; Sudarshan, S. (2020). <em>Database System
              Concepts</em> (7th ed.). McGraw-Hill. Ch. 5, "Advanced SQL," covers procedural SQL,
              functions, and procedures.
            </li>
          </ul>
        </div>

        <div className="learn-ref-category">
          <h3>Websites</h3>
          <ul className="learn-ref-list">
            <li>
              MySQL 8.0 Reference Manual — <em>Stored Objects</em>.{' '}
              <span className="learn-ref-url">https://dev.mysql.com/doc/refman/8.0/en/stored-objects.html</span>
            </li>
            <li>
              PostgreSQL Documentation — <em>PL/pgSQL — SQL Procedural Language</em>.{' '}
              <span className="learn-ref-url">https://www.postgresql.org/docs/current/plpgsql.html</span>
            </li>
            <li>
              Oracle® Database PL/SQL Language Reference, 19c.{' '}
              <span className="learn-ref-url">https://docs.oracle.com/en/database/oracle/oracle-database/19/lnpls</span>
            </li>
          </ul>
        </div>

        <div className="learn-ref-category">
          <h3>Educational Resources</h3>
          <ul className="learn-ref-list">
            <li>
              <em>SQL Stored Procedures</em>. GeeksforGeeks.{' '}
              <span className="learn-ref-url">https://www.geeksforgeeks.org/sql/what-is-stored-procedures-in-sql/</span>
            </li>
            <li>
              Kumar, P. S. <em>Introduction to Database Systems</em>. NPTEL/Swayam, IIT Madras.{' '}
              <span className="learn-ref-url">https://onlinecourses.nptel.ac.in/noc22_cs57/preview</span>
            </li>
            <li>
              Shukla, D. (2024). <em>Stored Procedure in SQL</em>. Analytics Vidhya.{' '}
              <span className="learn-ref-url">https://www.analyticsvidhya.com/blog/2024/06/stored-procedure-in-sql/</span>
            </li>
          </ul>
        </div>

        <div className="learn-ref-category">
          <h3>Videos</h3>
          <ul className="learn-ref-list">
            <li>
              Alex The Analyst. (2021, March 16). <em>Advanced SQL Tutorial | Stored Procedures + Use
              Cases</em> [Video]. YouTube.{' '}
              <span className="learn-ref-url">https://www.youtube.com/watch?v=NrBJmtD0kEw</span>
            </li>
          </ul>
        </div>
      </div>
    </section>
  )
}

export default LearnPage
