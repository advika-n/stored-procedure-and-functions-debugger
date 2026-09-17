// Static reference content for the Learn page's "Deep Dive" panel (formerly
// its own standalone Theory tab, merged into Learn -- see LearnPage.jsx).
// Each entry is a short, skimmable page (150-300 words + one code example),
// not a textbook chapter -- something to read before or during a debugging
// session, not instead of one. StoredProceduresTopic was dropped when this
// merged into Learn: its content duplicated Learn's own Concept Explanation
// section (what a procedure/function is, why they exist, procedure vs.
// function).

export function VariablesTopic() {
  return (
    <>
      <p>
        <code>DECLARE name TYPE [DEFAULT expr];</code> introduces a local
        variable inside a procedure's body, with a type and an optional
        starting value. Leave off <code>DEFAULT</code> and the variable
        starts unset until something assigns to it. Every declared
        variable is <strong>scoped to that one procedure call</strong> --
        it's created when the body starts running and gone when it ends;
        nothing outside the procedure (another session, another call) can
        see it.
      </p>
      <p>
        <code>SET name = expr;</code> assigns a new value to an already-declared
        variable, as many times as you like. This is different from an{' '}
        <strong>IN/OUT parameter</strong>: parameters are declared in the
        procedure's own parameter list and are how values cross the
        boundary with the caller -- <code>IN</code> brings a value in,{' '}
        <code>OUT</code> sends one back. A <code>DECLARE</code>d variable
        is private working storage the caller never sees directly.
      </p>
      <p className="theory-code-label">A variable's value changing across two statements:</p>
      <pre className="theory-code">{`DECLARE total NUMBER DEFAULT 0;
SET total = 10;
SET total = total + 5;   -- total is now 15`}</pre>
      <p className="theory-note">
        This tool's parser understands <code>DECLARE</code>/
        <code>SET</code> but not a parameter list -- every sample here
        declares its own inputs with <code>DEFAULT</code> rather than
        taking <code>IN</code> parameters.
      </p>
    </>
  )
}

export function ControlFlowTopic() {
  return (
    <>
      <p>
        <code>IF cond THEN ... ELSEIF cond2 THEN ... ELSE ... END IF</code>{' '}
        evaluates a condition and branches: the first true condition's
        block runs, and if none are true the (optional) <code>ELSE</code>{' '}
        block runs instead. This debugger's grammar supports{' '}
        <code>IF</code>/<code>ELSE</code>/<code>END IF</code> but not{' '}
        <code>ELSEIF</code> chaining directly -- nest another{' '}
        <code>IF</code> inside the <code>ELSE</code> (or <code>THEN</code>)
        to get the same effect, as the GradeClassifier sample does.
      </p>
      <p>
        <code>WHILE cond DO ... END WHILE</code> is a{' '}
        <strong>pre-test</strong> loop: the condition is checked{' '}
        <em>before</em> every iteration, including the first -- if it's
        false to start with, the body never runs at all.
      </p>
      <p>
        <code>LOOP ... END LOOP</code> is different from <code>WHILE</code>{' '}
        in one key way: it has <em>no condition of its own at all</em> --
        the only way out is an explicit <code>LEAVE;</code> executed
        somewhere inside its body (this tool also caps runaway loops at
        10,000 iterations as a safety net, same as <code>WHILE</code>).
        A <code>LOOP</code> can optionally be labeled (
        <code>mylabel: LOOP ... END LOOP mylabel;</code>) so a{' '}
        <code>LEAVE mylabel;</code> deep inside a nested loop can name{' '}
        <em>which</em> enclosing loop to break out of, not just the
        innermost one -- an unlabeled <code>LEAVE;</code> always breaks
        the innermost loop. Worth knowing, though not part of this
        tool's grammar: some dialects also offer{' '}
        <code>REPEAT ... UNTIL</code> (a <strong>post-test</strong> loop
        -- the body always runs at least once, since the condition is
        checked after).
      </p>
      <p>
        In this debugger, each condition check -- whether it's an{' '}
        <code>IF</code> or a <code>WHILE</code> -- is its own step in the
        trace, with the evaluated result attached. A <code>LOOP</code>{' '}
        gets one step per iteration too, reusing the same trace shape
        (just with no real condition to show). Only the branch (or loop
        body) actually taken adds further steps after it; the untaken
        side contributes nothing, which is what you're seeing when the
        flowchart leaves one path uncolored.
      </p>
      <p className="theory-code-label">IF/ELSE and a WHILE loop:</p>
      <pre className="theory-code">{`IF total > 100 THEN
    SET discount = total * 0.1;
ELSE
    SET discount = total * 0.05;
END IF;

WHILE counter < 5 DO
    SET counter = counter + 1;
END WHILE;`}</pre>
      <p className="theory-code-label">A labeled LOOP with LEAVE:</p>
      <pre className="theory-code">{`counter: LOOP
    SET total = total + 1;
    IF total > 5 THEN
        LEAVE counter;
    END IF;
END LOOP counter;`}</pre>
    </>
  )
}

export function CursorsTopic() {
  return (
    <>
      <p>
        A <strong>cursor</strong> is a pointer into the result set of a
        query, letting a procedure walk through it <em>one row at a
        time</em> instead of operating on the whole set at once --
        useful when the logic genuinely differs per row in a way plain
        set-based SQL can't express cleanly.
      </p>
      <p>Its lifecycle has four steps, all supported here:</p>
      <ol className="theory-list">
        <li>
          <code>DECLARE cursor_name CURSOR FOR SELECT ...;</code> --
          associates a name with a query, without running it yet. The
          embedded <code>SELECT</code> is captured as raw text (this
          interpreter doesn't parse SQL query grammar) and handed to the
          database exactly as written when the cursor opens.
        </li>
        <li>
          <code>OPEN cursor_name;</code> -- runs the query and buffers
          every row, positioned just before the first one.
        </li>
        <li>
          <code>FETCH cursor_name INTO var1, var2, ...;</code> -- reads
          the current row's columns into variables and advances to the
          next row. Running <code>FETCH</code> past the last row doesn't
          crash -- see the NOT_FOUND handler condition below.
        </li>
        <li>
          <code>CLOSE cursor_name;</code> -- releases the result set once
          you're done with it.
        </li>
      </ol>
      <p>
        Cursors are usually a last resort: if the same result can be
        produced with one set-based statement (an <code>UPDATE</code>{' '}
        joined to the source table, say), that's almost always faster than
        fetching row by row. Reach for a cursor when the per-row logic
        genuinely can't be expressed as a single query -- e.g. calling
        another procedure once per row, or building output that depends
        on running totals across rows in order.
      </p>
      <p className="theory-code-label">
        Looping through rows with <code>cur%FOUND</code> (a pragmatic,
        predictive reading -- "is a row ready right now" -- of Oracle's
        cursor-attribute syntax; see the ExceptionHandlingTopic below for
        the more standard <code>NOT_FOUND</code> handler style):
      </p>
      <pre className="theory-code">{`DECLARE total NUMBER DEFAULT 0;
DECLARE item_name STRING DEFAULT '';
DECLARE item_price NUMBER DEFAULT 0;
DECLARE prod_cursor CURSOR FOR SELECT name, price FROM products;

OPEN prod_cursor;
WHILE prod_cursor%FOUND DO
    FETCH prod_cursor INTO item_name, item_price;
    SET total = total + item_price;
END WHILE;
CLOSE prod_cursor;`}</pre>
      <p className="theory-note">
        Runnable as-is -- it's the <strong>ProductPriceTotal</strong> sample.
        Its query runs against a small, fixed, built-in demo table (
        <code>products(name, price)</code>, 3 rows) every debug run gets
        for free, since there's no schema-editing feature yet. Your own
        cursor queries need to target that same table. Only single-character
        comparisons (<code>=</code>, <code>&gt;</code>, <code>&lt;</code>,{' '}
        <code>!=</code>) round-trip correctly inside an embedded{' '}
        <code>WHERE</code> clause.
      </p>
    </>
  )
}

export function ExceptionHandlingTopic() {
  return (
    <>
      <p>
        Procedures declare handlers to react to conditions raised while
        they run, instead of letting the whole call fail outright.
        MySQL-style dialects use{' '}
        <code>DECLARE ... HANDLER FOR condition ...</code>; Oracle's
        PL/SQL spells the same idea differently, with a{' '}
        <code>BEGIN ... EXCEPTION WHEN ... END</code> block at the end of
        the procedure.
      </p>
      <p>
        Real dialects handle many conditions -- NOT FOUND, division by
        zero, constraint violations, deadlocks, and more, often via a
        catch-all like MySQL's <code>SQLEXCEPTION</code>. This debugger's
        scope is deliberately much narrower: exactly two conditions,{' '}
        <strong>NOT_FOUND</strong> (a <code>FETCH</code> ran past the last
        row of a cursor) and <strong>DIVISION_BY_ZERO</strong> (a{' '}
        <code>/</code> divided by zero) -- nothing else raises a
        handleable condition here.
      </p>
      <p>
        The syntax is <code>DECLARE CONTINUE HANDLER FOR condition
        statement;</code> -- only <strong>CONTINUE</strong> handlers are
        supported (resume at the next statement after the one that
        triggered), not MySQL's <code>EXIT</code> handlers (leave the
        enclosing block), and the action is a single statement, not a{' '}
        <code>BEGIN...END</code> block. A handler is registered the moment
        its <code>DECLARE</code> actually runs, and stays active for the
        rest of the procedure from that point on. A triggered condition
        without a matching handler is <strong>not fatal for NOT_FOUND</strong>{' '}
        (it always shows up as a visible, unhandled step in the trace) but{' '}
        <strong>still aborts the run for DIVISION_BY_ZERO</strong>, exactly
        as it did before handlers existed -- declaring a handler is what
        makes a division mistake recoverable instead of fatal.
      </p>
      <p className="theory-code-label">
        Both conditions actually firing in one procedure -- a cursor whose{' '}
        <code>WHERE</code> matches nothing (NOT_FOUND on the very first
        fetch), followed by an average over zero rows (DIVISION_BY_ZERO):
      </p>
      <pre className="theory-code">{`DECLARE total NUMBER DEFAULT 0;
DECLARE count NUMBER DEFAULT 0;
DECLARE average NUMBER DEFAULT -1;
DECLARE done NUMBER DEFAULT 0;
DECLARE item_name STRING DEFAULT '';
DECLARE item_price NUMBER DEFAULT 0;
DECLARE CONTINUE HANDLER FOR NOT_FOUND SET done = 1;
DECLARE CONTINUE HANDLER FOR DIVISION_BY_ZERO SET average = 0;
DECLARE premium_cursor CURSOR FOR SELECT name, price FROM products WHERE price > 1000;

OPEN premium_cursor;
WHILE done = 0 DO
    FETCH premium_cursor INTO item_name, item_price;
    IF done = 0 THEN
        SET total = total + item_price;
        SET count = count + 1;
    END IF;
END WHILE;
CLOSE premium_cursor;
SET average = total / count;`}</pre>
      <p className="theory-note">
        Runnable as-is -- it's the <strong>SafeAverageWithHandlers</strong>{' '}
        sample. Note the <code>IF done = 0</code> guard around the
        accumulation: a <code>CONTINUE</code> handler resumes at the{' '}
        <em>next statement</em>, not by skipping the rest of the loop
        body, so without that guard the fetch that triggers NOT_FOUND
        would still fall through to processing stale data. That's a real
        MySQL gotcha, not an artifact of this interpreter.
      </p>
    </>
  )
}

export function PuttingItTogetherTopic() {
  return (
    <>
      <p>
        Everything on the previous pages shows up in one small, real
        procedure -- the same CalculateDiscount example the debugger runs
        throughout this tool. Step through it there and each numbered
        line below corresponds to exactly one entry in the trace.
      </p>
      <pre className="theory-code theory-code-annotated">{`CREATE PROCEDURE CalculateDiscount()  -- (0)
BEGIN
    DECLARE price NUMBER DEFAULT 20;      -- (1)
    DECLARE quantity NUMBER DEFAULT 6;    -- (1)
    DECLARE total NUMBER DEFAULT 0;       -- (1)
    DECLARE discount NUMBER DEFAULT 0;    -- (1)
    SET total = price * quantity;         -- (2)
    IF total > 100 THEN                   -- (3)
        SET discount = total * 0.1;
    ELSE
        SET discount = total * 0.05;
    END IF;
    SET total = total - discount;         -- (2)
END`}</pre>
      <ol className="theory-list">
        <li>
          <strong>(0) The wrapper</strong> -- <code>CREATE PROCEDURE
          CalculateDiscount() BEGIN ... END</code> is parsed and executed
          just like the body inside it; no params are declared here since
          the sample is fully self-contained. It doesn't produce a step of
          its own -- only the statements inside <code>BEGIN...END</code> do.
        </li>
        <li>
          <strong>(1) Variables</strong> -- four <code>DECLARE</code>s give
          the procedure its working storage, each with a default so the
          sample runs with no extra input.
        </li>
        <li>
          <strong>(2) Assignment</strong> -- two <code>SET</code>s compute a
          value from the current variables and store it back; the second
          one only makes sense once the IF/ELSE below has set{' '}
          <code>discount</code>.
        </li>
        <li>
          <strong>(3) IF/ELSE</strong> -- the condition is checked exactly
          once, and only the branch it picks contributes a step to the
          trace. That's why the flowchart's untaken branch never turns
          teal: it genuinely didn't run.
        </li>
      </ol>
    </>
  )
}

