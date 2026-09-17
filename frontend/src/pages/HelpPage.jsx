// Full user manual -- a mandatory, graded course requirement (see
// CLAUDE.md §5). Every control described below was read directly off
// Layout.jsx and DebuggerPage.jsx (plus History.jsx/QuizPage.jsx for the
// "other pages" section) rather than invented, so this stays accurate as
// the actual source of truth. Uses <details>/<summary> for the
// accordion sections -- native, keyboard/screen-reader accessible, no
// extra JS state needed -- styled in App.css's Help page block, fully
// theme-aware via the existing CSS custom properties (no hard-coded
// colors here).

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
          This is a <strong>Stored Procedure &amp; Function Debugger</strong>. You write (or pick from a
          library) a small procedural-SQL program -- a <code>CREATE PROCEDURE</code> or{' '}
          <code>CREATE FUNCTION</code> -- and the tool <em>simulates</em> its execution one statement at a
          time, rather than just running it and showing you a final result. At every step it shows you
          exactly which line is executing, what every variable currently holds, which branch of an{' '}
          <code>IF</code> or loop was taken, and a control-flow diagram highlighting where you are inside
          the procedure's overall shape. A built-in AI (Google Gemini, with an automatic fallback when it's
          unavailable) explains each step in plain English, and you can ask it free-form questions about
          what's happening.
        </p>
        <p>
          It's meant for learning how procedural SQL constructs -- <code>DECLARE</code>/<code>SET</code>,{' '}
          <code>IF</code>/<code>WHILE</code>, cursors, and exception handlers -- actually execute, not for
          running real production SQL against a real database.
        </p>
      </HelpSection>

      <HelpSection id="inputs" title="2. What inputs you can give it">
        <p>The Debugger page's editor accepts two forms of procedural SQL:</p>
        <ul className="about-list">
          <li>
            <code>CREATE PROCEDURE name(params) BEGIN ... END</code> -- a procedure, optionally with{' '}
            <code>IN</code>/<code>OUT</code>/<code>INOUT</code> parameters.
          </li>
          <li>
            <code>CREATE FUNCTION name(params) RETURNS type BEGIN ... END</code> -- a function, which must
            end by executing a <code>RETURN expr;</code>.
          </li>
        </ul>
        <p>
          Inside the body: <code>DECLARE</code>/<code>SET</code> for variables, <code>IF...ELSE...END IF</code>{' '}
          and <code>WHILE...DO...END WHILE</code> for control flow, cursors (<code>DECLARE ... CURSOR
          FOR SELECT ...</code>, <code>OPEN</code>/<code>FETCH...INTO</code>/<code>CLOSE</code>,{' '}
          <code>%FOUND</code>/<code>%NOTFOUND</code>), and <code>DECLARE CONTINUE HANDLER FOR NOT_FOUND |
          DIVISION_BY_ZERO</code> exception handlers. See the <strong>Theory</strong> tab for a runnable
          example of each of these, and the <strong>About</strong> page for the full grammar reference.
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
        <p>
          Cursor <code>SELECT</code> queries run against a small, fixed demo table,{' '}
          <code>products(name, price)</code> (3 rows), that's automatically available every time you debug --
          there's no schema to set up.
        </p>
      </HelpSection>

      <HelpSection id="providing-input" title="3. How to provide input, step by step">
        <ol className="help-steps">
          <li>
            Go to the <strong>Debugger</strong> tab in the top navigation.
          </li>
          <li>
            Either click a card in the <strong>Procedure Library</strong> panel on the left to load a
            ready-made sample, or click <strong>+ New / Custom Procedure</strong> to clear the editor and
            write your own.
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
            Click the <strong>Debug</strong> button under the editor to run it.
          </li>
        </ol>
      </HelpSection>

      <HelpSection id="controls" title="4. What every button and control does">
        <p>Top navigation and header, present on every page:</p>
        <ul className="help-control-list">
          <li>
            <strong>Home / Debugger / Theory / History / Quiz / About / Help</strong> -- the page tabs.
            Debugger is the main tool; Theory has concept write-ups with runnable examples; History is your
            saved past runs; Quiz is a standalone AI-generated multiple-choice quiz.
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

        <p>Debugger page -- top bar:</p>
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

        <p>Debugger page -- Procedure Library panel (left):</p>
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

        <p>Debugger page -- Editor panel (middle):</p>
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
            <strong>Debug</strong> -- parses and runs your procedure, generating the full step trace from
            scratch. This also clears any previous trace, explanations, and Ask AI conversation.
          </li>
        </ul>

        <p>Debugger page -- Live State panel (right):</p>
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

        <p>Debugger page -- Ask AI panel:</p>
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

        <p>Debugger page -- Step Log panel (bottom):</p>
        <ul className="help-control-list">
          <li>
            <strong>Any row</strong> -- click a past step in the log to jump straight to it, same as
            dragging the scrubber to that position.
          </li>
        </ul>
      </HelpSection>

      <HelpSection id="processing" title="5. How processing takes place">
        <p>In plain terms, once you click Debug, four things happen in order:</p>
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
            <strong>Simulated execution:</strong> that structure is walked one statement at a time, in a
            sandboxed environment that isn't a real database -- variables are tracked, conditions are
            evaluated, loops repeat, and cursor queries run against the small built-in demo table. Every
            single statement produces one "step," recording the line number, the statement's text, and the
            full state of every variable at that point.
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
        </ul>
      </HelpSection>

      <HelpSection id="other-pages" title="7. Other pages">
        <ul className="help-control-list">
          <li>
            <strong>History</strong> -- every successful past Debug run is saved automatically. Click a row
            to replay it (reopens it in the Debugger without re-running it), <strong>Delete</strong> a
            single row, or <strong>Clear all</strong> to wipe the whole log.
          </li>
          <li>
            <strong>Quiz</strong> -- a standalone 5-question AI-generated multiple-choice quiz, either on
            general procedural-SQL theory or based on whichever procedure you last had loaded in the
            Debugger. This is separate from Predict Mode inside the Debugger itself.
          </li>
          <li>
            <strong>Theory</strong> -- concept write-ups with runnable examples for each supported SQL
            construct.
          </li>
        </ul>
      </HelpSection>
    </section>
  )
}

export default HelpPage
