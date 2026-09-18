// Full user manual -- a mandatory, graded course requirement (see
// CLAUDE.md §5). Every control described below was read directly off
// Layout.jsx and SqlConsolePage.jsx (the merged Debugger/SQL Console
// page -- plus History.jsx/PracticePage.jsx for the "other pages" section)
// rather than invented, so this stays accurate as the actual source of
// truth. Uses <details>/<summary> for the accordion sections -- native,
// keyboard/screen-reader accessible, no extra JS state needed -- styled
// in App.css's Help page block, fully theme-aware via the existing CSS
// custom properties (no hard-coded colors here).

function HelpSection({ id, title, defaultOpen, children }) {
  return (
    <details className="help-section" id={id} {...(defaultOpen ? { open: true } : {})}>
      <summary className="help-section-summary">
        <span className="help-section-title">{title}</span>
        <span className="help-section-caret" aria-hidden="true">▸</span>
      </summary>
      <div className="help-section-body">{children}</div>
    </details>
  )
}

function HelpPage() {
  return (
    <section className="help-page">
      <h1>Help</h1>
      <p className="page-subtitle">
        A complete walkthrough of this application, control by control. Open any section below --
        everything you need to run your first debug session is here.
      </p>

      <HelpSection id="what-is-this" title="1. What this application does" defaultOpen>
        <p>
          This is a <strong>Stored Procedure &amp; Function Debugger</strong> merged with a{' '}
          <strong>SQL Console</strong> into one page. You write (or pick from a library) a small
          procedural-SQL program -- a <code>CREATE PROCEDURE</code> or <code>CREATE FUNCTION</code> -- and
          the tool <em>simulates</em> its execution one statement at a time, rather than just running it
          and showing you a final result. At every step it shows you exactly which line is executing, what
          every variable currently holds, which branch of an <code>IF</code> or loop was taken, and a
          control-flow diagram highlighting where you are inside the procedure's overall shape. A built-in
          AI (Google Gemini, with an automatic fallback when it's unavailable) explains each step in plain
          English, and you can ask it free-form questions about what's happening.
        </p>
        <p>
          The <strong>same page and the same Run button</strong> also accept plain SQL that isn't wrapped
          in a procedure -- a bare <code>SELECT</code>/<code>INSERT</code>/<code>UPDATE</code>/
          <code>DELETE</code>/<code>CREATE TABLE</code>/<code>DROP</code>/<code>ALTER</code> statement runs
          directly against this app's real, persistent database and shows its result (a row table for a
          query, a status line for a write) in place of the step-through debugger view. See section 2 for
          how the tool decides which of the two you meant.
        </p>
        <p>
          It's meant for learning how procedural SQL constructs -- <code>DECLARE</code>/<code>SET</code>,{' '}
          <code>IF</code>/<code>WHILE</code>, cursors, and exception handlers -- actually execute. Unlike
          an earlier version of this tool, table statements are no longer a pure simulation: a{' '}
          <code>CREATE TABLE</code>/<code>INSERT</code>/<code>UPDATE</code>/<code>DELETE</code> inside a
          procedure body runs as real SQL against this app's real database, so it's genuinely there for a
          cursor's <code>SELECT</code> (or the SQL Console) to read back afterward -- see section 2's note
          on this.
        </p>
      </HelpSection>

      <HelpSection id="inputs" title="2. What inputs you can give it">
        <p>The editor on the SQL Console page accepts two different kinds of input, auto-detected on Run:</p>
        <ul className="about-list">
          <li>
            <strong>A procedure or function</strong> -- <code>CREATE PROCEDURE name(params) BEGIN ... END</code>{' '}
            (optionally with <code>IN</code>/<code>OUT</code>/<code>INOUT</code> parameters), or{' '}
            <code>CREATE FUNCTION name(params) RETURNS type BEGIN ... END</code> (which must end by
            executing a <code>RETURN expr;</code>). If this parses successfully, Run shows the full
            step-through debugger view described in the rest of this page.
          </li>
          <li>
            <strong>Plain SQL</strong> -- a bare statement that doesn't parse as a procedure/function but
            looks like SQL (starts with <code>CREATE</code>/<code>INSERT</code>/<code>UPDATE</code>/
            <code>DELETE</code>/<code>SELECT</code>/<code>DROP</code>/<code>ALTER</code>, with no{' '}
            <code>BEGIN</code>/<code>END</code>/<code>DECLARE</code> wrapper). Run sends this straight to
            the database and shows its result -- a row table for a query, a status line for a write, or an
            error banner -- in place of the debugger view. If the input matches neither cleanly, Run shows
            one clear error rather than guessing.
          </li>
        </ul>
        <p>
          Inside a procedure/function body: <code>DECLARE</code>/<code>SET</code> for variables,{' '}
          <code>IF...ELSE...END IF</code>, <code>WHILE...DO...END WHILE</code>, and <code>LOOP...END
          LOOP</code>/<code>LEAVE</code> for control flow, <code>CASE</code>, cursors (
          <code>DECLARE ... CURSOR FOR SELECT ...</code>, <code>OPEN</code>/<code>FETCH...INTO</code>/
          <code>CLOSE</code>, <code>%FOUND</code>/<code>%NOTFOUND</code>), <code>DECLARE CONTINUE HANDLER
          FOR NOT_FOUND | DIVISION_BY_ZERO</code> exception handlers, <code>CALL</code> (procedure calling
          procedure), and -- raw SQL against the real database, no simulation -- standalone{' '}
          <code>CREATE TABLE</code>/<code>INSERT</code>/<code>UPDATE</code>/<code>DELETE</code>/
          <code>SELECT</code> statements. See the <strong>Learn</strong> tab's Deep Dive panel for a
          runnable example of each of these, and the <strong>About</strong> page for the full grammar
          reference.
        </p>
        <p className="help-note">
          <strong>Note on parameters:</strong> the editor does not currently have a form for typing in
          external parameter values before running. Every procedure you run must be fully self-contained --
          give any <code>IN</code> parameters or variables a starting value with{' '}
          <code>DECLARE name TYPE DEFAULT expr;</code> inside the body itself. <code>OUT</code>/
          <code>INOUT</code> parameters work fine (their final value shows up flagged{' '}
          <span className="changed-badge">changed</span> in the variable table) since they don't need an
          external input to start.
        </p>
        <p className="help-note">
          <strong>Note on the database:</strong> cursor <code>SELECT</code> queries, and every{' '}
          <code>CREATE TABLE</code>/<code>INSERT</code>/<code>UPDATE</code>/<code>DELETE</code>/
          <code>SELECT</code> statement (inside a procedure, or typed as plain SQL), all run against ONE
          real, persistent database -- seeded with a small demo table, <code>products(name, price)</code>{' '}
          (3 rows), on first use. It's real SQLite, not a simulation: a table you <code>CREATE</code> and{' '}
          <code>INSERT</code> into stays there for a cursor to <code>SELECT</code> from later in that same
          run (or a later run), and changes persist across runs. A raw SQL statement's text is sent to the
          database exactly as written -- it can't reference a procedure variable by name the way{' '}
          <code>SET</code> can; only literal values work there today.
        </p>
      </HelpSection>

      <HelpSection id="providing-input" title="3. How to provide input, step by step">
        <ol className="help-steps">
          <li>
            Go to the <strong>SQL Console</strong> tab in the top navigation.
          </li>
          <li>
            Either click a card in the <strong>Procedure Library</strong> panel on the left to load a
            ready-made sample, or click <strong>+ New / Custom Procedure</strong> to clear the editor and
            write your own -- procedure/function or plain SQL.
          </li>
          <li>
            Type or paste your SQL into the editor in the middle panel. As soon as you edit a loaded
            sample's text, it stops being treated as that sample (so nothing is silently overwritten).
          </li>
          <li>
            Make sure any values your procedure needs are supplied via <code>DECLARE ... DEFAULT</code>{' '}
            inside the body (see the note in section 2 above -- there is no separate parameter-entry form).
          </li>
          <li>
            Click the <strong>Run</strong> button under the editor (or press Ctrl/Cmd+Enter) -- it detects
            whether this is a procedure/function or plain SQL and shows the right view automatically.
          </li>
        </ol>
      </HelpSection>

      <HelpSection id="controls" title="4. What every button and control does">
        <p>Top navigation and header, present on every page:</p>
        <ul className="help-control-list">
          <li>
            <strong>Home / SQL Console / Compare / AI Practice / About</strong> (top nav), plus{' '}
            <strong>Help</strong> and <strong>🎓 Learn</strong> (top-right cluster) -- the page tabs.
            SQL Console is the main tool (the merged step-through debugger and plain-SQL runner); Compare
            runs two procedures side by side and steps through both together; Learn's Deep Dive panel has
            concept write-ups with runnable examples; AI Practice is a standalone, Gemini-generated
            competitive-exam-style question set (GATE DBMS PYQ / placement style), not tied to any
            procedure. Your saved run history is still there (see section 7) even though it has no nav tab
            of its own.
          </li>
          <li>
            <strong>🌙 / ☀️ toggle</strong> (top-right header cluster) -- switches between Night (dark) and
            Day (light) mode. Your choice is remembered on this device.
          </li>
          <li>
            <strong>Developed By</strong> (top-right header cluster) -- opens a modal with the author's
            name, register number, and guide. Close it with the ✕ button, the Escape key, or by clicking
            outside it.
          </li>
        </ul>

        <p>SQL Console page -- top bar:</p>
        <ul className="help-control-list">
          <li>
            <strong>backend: ok / checking… / [error]</strong> -- a live status badge showing whether the
            backend server is reachable.
          </li>
          <li>
            <strong>⭳ Export Run</strong> -- downloads the current run (code, parsed structure, and full
            step trace) as a JSON file. Disabled until you've run Debug at least once.
          </li>
        </ul>

        <p>SQL Console page -- Procedure Library panel (left):</p>
        <ul className="help-control-list">
          <li>
            <strong>+ New / Custom Procedure</strong> -- clears the editor to a blank slate for writing your
            own procedure or function from scratch.
          </li>
          <li>
            <strong>Sample cards</strong> -- click any card to load that ready-made procedure/function into
            the editor, replacing whatever was there.
          </li>
        </ul>

        <p>SQL Console page -- Editor panel (middle):</p>
        <ul className="help-control-list">
          <li>
            <strong>The code editor</strong> -- a full Monaco (VS Code's editor) text box for writing/editing
            SQL. A gutter arrow (▸) glides to whichever line is currently executing once you've run Debug.
          </li>
          <li>
            <strong>Breakpoints</strong> -- click a line number (or the glyph margin beside it) to toggle a
            breakpoint on that line; a red dot marks it. Click the same spot again to remove it. Breakpoints
            survive re-running Debug, so you can set them once and reuse them across runs.
          </li>
          <li>
            <strong>◀ Previous / Next ▶</strong> -- step backward/forward one statement at a time through
            the trace. You can also use the Left/Right arrow keys (as long as the editor itself isn't
            focused).
          </li>
          <li>
            <strong>⏵ Continue</strong> -- fast-forwards from the current step to the next breakpointed
            line, without re-running Debug. If no breakpoints are set, it instead runs all the way to the
            end of the trace. When you're stopped on a breakpointed line, a{' '}
            <span className="breakpoint-paused-badge">⏸ Paused at breakpoint</span> badge appears next to
            the step counter.
          </li>
          <li>
            <strong>↺ Restart</strong> -- jumps back to step 1 of the current trace without re-running
            Debug.
          </li>
          <li>
            <strong>Step scrubber</strong> (slider) -- drag to any step directly instead of stepping one at
            a time.
          </li>
          <li>
            <strong>"Step X of N"</strong> -- your current position in the trace.
          </li>
          <li>
            <strong>Auto-read explanations</strong> (checkbox, only shown if your browser supports
            text-to-speech) -- when checked, each step's explanation is read aloud automatically as you
            arrive at it.
          </li>
          <li>
            <strong>Predict Mode</strong> (checkbox) -- turns on a quiz overlay: before certain steps are
            revealed, you're asked to predict a variable's new value or which <code>IF</code> branch will be
            taken, with a running correct/total score. When a prediction is pending, Next is disabled until
            you answer it (via the prediction form that appears, or the Then/Else buttons for a branch
            guess).
          </li>
          <li>
            <strong>Run</strong> (or Ctrl/Cmd+Enter) -- the single button for both of this page's modes
            (see section 2). If the editor content parses as a procedure/function, this generates the full
            step trace from scratch, exactly like the old Debug button did, and clears any previous trace,
            explanations, and Ask AI conversation. Otherwise, if it looks like plain SQL, this runs it
            directly against the database and shows the result panel described in section 6 instead.
          </li>
        </ul>

        <p>SQL Console page -- Live State panel (right, procedure/function runs only):</p>
        <ul className="help-control-list">
          <li>
            <strong>🔊 / ⏹ speaker button</strong> (next to the Explanation panel, only shown if your browser
            supports text-to-speech) -- reads the current step's explanation aloud, or stops it if it's
            already speaking.
          </li>
        </ul>
        <p>
          (The error banner, cursor table, variable table, return value panel, and explanation text in this
          panel are all read-only displays -- see section 6 below for how to interpret them.)
        </p>

        <p>SQL Console page -- Ask AI panel (procedure/function runs only):</p>
        <ul className="help-control-list">
          <li>
            <strong>ASK AI header</strong> -- click it to expand or collapse the panel; a badge shows how
            many questions you've asked while it's collapsed.
          </li>
          <li>
            <strong>Question box + Ask</strong> -- type a free-form question about the currently displayed
            step (e.g. "why did it take this branch") and submit it to get an AI-generated answer.
          </li>
        </ul>

        <p>SQL Console page -- Step Log panel (bottom, procedure/function runs only):</p>
        <ul className="help-control-list">
          <li>
            <strong>Any row</strong> -- click a past step in the log to jump straight to it, same as
            dragging the scrubber to that position.
          </li>
        </ul>
      </HelpSection>

      <HelpSection id="processing" title="5. How processing takes place">
        <p>In plain terms, once you click Run, four things happen in order (for a procedure/function):</p>
        <ol className="help-steps">
          <li>
            <strong>Reading:</strong> your SQL text is broken down into small pieces (keywords, names,
            numbers, symbols) -- this is called tokenizing.
          </li>
          <li>
            <strong>Understanding structure:</strong> those pieces are assembled into a tree that represents
            the procedure's structure -- which statements are inside which <code>IF</code>/<code>WHILE</code>{' '}
            blocks, in what order.
          </li>
          <li>
            <strong>Execution:</strong> that structure is walked one statement at a time -- variables,
            conditions, and loops are all simulated in the tool itself, while cursor queries and any raw{' '}
            <code>CREATE TABLE</code>/<code>INSERT</code>/<code>UPDATE</code>/<code>DELETE</code>/
            <code>SELECT</code> statement run for real against this app's persistent database (see section
            2). Every single statement produces one "step," recording the line number, the statement's
            text, and the full state of every variable at that point.
          </li>
          <li>
            <strong>Delivery:</strong> the complete list of steps is sent back and drives everything you see
            on screen -- the step navigator, variable table, and flowchart. Each step's plain-English
            explanation is generated separately (by Gemini, or a template if Gemini isn't available) as you
            reach it.
          </li>
        </ol>
        <p className="help-note">
          This whole process typically takes well under a second, even for longer procedures.
        </p>
      </HelpSection>

      <HelpSection id="output" title="6. How to interpret the output">
        <ul className="help-control-list">
          <li>
            <strong>The gutter arrow and highlighted line</strong> in the editor show exactly which
            statement the current step corresponds to.
          </li>
          <li>
            <strong>Error banner</strong> (appears above the variable table when relevant) -- shows an
            error condition (e.g. <code>DIVISION_BY_ZERO</code>) that occurred at this step, and whether it
            was caught by a handler you declared or is unhandled.
          </li>
          <li>
            <strong>Cursors table</strong> -- when the current step touches a declared cursor, shows its
            name, which row it's on, whether more rows remain, and the current row's column values.
          </li>
          <li>
            <strong>SQL panel</strong> -- when the current step is a <code>CREATE TABLE</code>/
            <code>INSERT</code>/<code>UPDATE</code>/<code>DELETE</code>/<code>SELECT</code> statement, shows
            the table it touched, how many rows were affected, and either that table's full current row set
            (for a write) or the query's own result rows (for a <code>SELECT</code>).
          </li>
          <li>
            <strong>Variables table</strong> -- every declared variable, its current value and type. A row
            highlighted with a <span className="changed-badge">changed</span> badge means this exact step is
            what changed it -- an amber connector line briefly links the executing line to that row so you
            can see cause and effect.
          </li>
          <li>
            <strong>Return Value panel</strong> -- appears only on a function's final step, showing the
            value it returned.
          </li>
          <li>
            <strong>Explanation panel</strong> -- a plain-English description of what this step just did. A
            small badge marks whether it came from <strong>Gemini</strong> (AI-generated) or a{' '}
            <strong>template</strong> (a deterministic fallback used automatically when Gemini isn't
            configured/reachable) -- both are accurate, the badge is purely informational.
          </li>
          <li>
            <strong>Ask AI</strong> -- answers here are generated fresh for your specific question about the
            step you're currently viewing; they aren't saved between visits.
          </li>
          <li>
            <strong>Control-Flow diagram</strong> (Mermaid flowchart, bottom of the page) -- a map of the
            entire procedure's shape: boxes for statements, diamonds for <code>IF</code> conditions, loops
            for <code>WHILE</code>. The node matching your current step is highlighted, and the path already
            taken through branches/loops is styled differently from paths not taken, so you can see at a
            glance which route execution followed.
          </li>
          <li>
            <strong>Step Log</strong> -- a plain list of every step in the current run in order, each
            showing its line number and statement text, with a colored flag on any step where an error
            condition fired.
          </li>
          <li>
            <strong>SQL Console result panel</strong> (plain SQL runs only -- replaces everything above)
            -- a status line describing what ran, then either a row table (for a query) or nothing further
            (for a write), or a coral error banner if the SQL itself failed.
          </li>
        </ul>
      </HelpSection>

      <HelpSection id="other-pages" title="7. Other pages">
        <ul className="help-control-list">
          <li>
            <strong>History</strong> -- every successful past procedure/function run is saved
            automatically (plain SQL runs are not). Click a row to replay it (reopens it on the SQL
            Console page without re-running it), <strong>Delete</strong> a single row, or{' '}
            <strong>Clear all</strong> to wipe the whole log.
          </li>
          <li>
            <strong>Compare</strong> -- runs two procedures side by side (independently, each its own
            editor) and steps through both traces together, flagging the first point where they diverge.
          </li>
          <li>
            <strong>AI Practice</strong> -- a standalone, general-purpose competitive-exam practice tool
            (not tied to any sample or trace). Pick a difficulty (Easy/Medium/Hard, as large color-coded
            cards) and a question count (1-15), then <strong>Generate Practice Set</strong> asks Gemini for
            that many GATE-DBMS-PYQ-and-placement-style multiple-choice questions on procedures, functions,
            cursors, exception handling, and control flow (falling back to a built-in question bank if
            Gemini is unavailable). Questions are shown one at a time: picking the right answer immediately
            shows the explanation and a Next button; picking wrong the <em>first</em> time shows "not quite
            -- try again" and lets you pick again without counting against your score -- only a second wrong
            answer on the same question counts as incorrect and reveals the correct one. The final score
            screen breaks down correct-on-first-try / correct-on-retry / incorrect, plus an expandable
            per-question review. This is separate from Predict Mode on the SQL Console page.
          </li>
          <li>
            <strong>Learn</strong> -- concept explanation, an instructional video, a Deep Dive panel with
            runnable write-ups for each supported SQL construct, and references, in that order.
          </li>
        </ul>
      </HelpSection>
    </section>
  )
}

export default HelpPage
