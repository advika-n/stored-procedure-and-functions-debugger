"""Recursive-descent parser for a small procedural SQL subset.

Consumes the token list produced by :mod:`app.tokenizer` and builds an
AST. Every AST node is a plain dict with a ``"type"`` field (and, for
statement nodes, a ``"line"`` field) so the tree can be dumped straight
to JSON for inspection or shipped over the wire to a frontend.

Supported grammar (informal, keywords in CAPS are literal tokens):

    program     := (function_def | procedure_def)+ | statement*

    function_def := CREATE FUNCTION IDENT '(' func_param (',' func_param)* ')'
                     RETURNS IDENT
                     BEGIN statement* END ';'?
    func_param   := IDENT IDENT

    procedure_def := CREATE PROCEDURE IDENT '(' proc_param (',' proc_param)* ')'
                      BEGIN statement* END ';'?
    proc_param    := (IN | OUT | INOUT)? IDENT IDENT

    statement   := declare_stmt | declare_cursor_stmt | declare_handler_stmt
                    | set_stmt | if_stmt | while_stmt | case_stmt | return_stmt
                    | open_cursor_stmt | fetch_cursor_stmt | close_cursor_stmt
                    | call_stmt | loop_stmt | leave_stmt | sql_stmt
                    | select_into_stmt

    declare_stmt        := DECLARE IDENT IDENT (DEFAULT expr)? ';'
    declare_cursor_stmt := DECLARE IDENT CURSOR FOR <raw tokens up to ';'> ';'
    declare_handler_stmt := DECLARE CONTINUE HANDLER FOR
                             (NOT_FOUND | DIVISION_BY_ZERO) statement
    set_stmt             := SET IDENT '=' expr ';'
    if_stmt      := IF expr THEN statement*
                     (ELSE statement*)?
                     END IF ';'
    while_stmt   := WHILE expr DO statement* END WHILE ';'
    case_stmt    := CASE expr? (WHEN expr THEN statement*)+
                     (ELSE statement*)?
                     END CASE ';'
    return_stmt  := RETURN expr ';'
    open_cursor_stmt  := OPEN IDENT ';'
    fetch_cursor_stmt := FETCH IDENT INTO IDENT (',' IDENT)* ';'
    close_cursor_stmt := CLOSE IDENT ';'
    call_stmt         := CALL IDENT '(' (expr (',' expr)*)? ')' ';'
    loop_stmt         := (IDENT ':')? LOOP statement* END LOOP IDENT? ';'
    leave_stmt        := LEAVE IDENT? ';'

    sql_stmt     := (CREATE TABLE | INSERT | UPDATE | DELETE | SELECT) <raw tokens up to ';'> ';'

    select_into_stmt := SELECT <raw tokens up to INTO> INTO IDENT (',' IDENT)*
                          <raw tokens up to ';'> ';'
                         -- only when an INTO appears before the next FROM
                         -- or ';' (see `_select_has_into`); otherwise a
                         -- bare SELECT is a sql_stmt above, not this.

    expr         := comparison
    comparison   := term (('>' | '<' | '=' | '!=' | '>=' | '<=' | '<>') term)*
    term         := factor (('+' | '-') factor)*
    factor       := unary (('*' | '/') unary)*
    unary        := '-' unary | primary
    primary      := NUMBER | STRING | NULL | function_call_expr
                     | IDENT ('%' (FOUND | NOTFOUND))?
                     | '(' expr ')'
    function_call_expr := IDENT '(' (expr (',' expr)*)? ')'

BEGIN/END (as a bare block), IN and OUT are recognized by the tokenizer
as keywords but are not part of this grammar subset outside of a
function_def's own BEGIN...END wrapper (see "Functions" below), so the
parser does not accept them elsewhere.

-- Procedures: two forms, both fully supported ---------------------------

A procedure can be written either way, and both are first-class:

  1. The bare statement body (`program := statement*`), with NO
     `CREATE`/`BEGIN`/`END` wrapper at all -- the ONLY form this
     grammar understood before CREATE PROCEDURE support existed (see
     Theory.jsx's StoredProceduresTopic, which used to describe this
     as the only option; it's been updated). `parse()` returns this as
     ``{"type": "Procedure", "body": [...]}`` -- no "name"/"params"
     keys at all. This is the permanent backward-compatibility path:
     every pre-existing sample, and every persisted History entry
     saved before CREATE PROCEDURE support existed, is exactly this
     shape and keeps parsing/running identically forever. Do not
     remove or change this path.
  2. The full `CREATE PROCEDURE name(params) BEGIN ... END` wrapper,
     parsed by `parse_procedure_def()` into
     ``{"type": "ProcedureNode", "name", "params", "body", "line"}`` --
     deliberately a *different* type string from plain "Procedure",
     precisely so old callers pattern-matching on `"Procedure"` are
     never surprised by a new shape showing up under the same name.

`parse()` picks between the three grammars (function_def,
procedure_def, or the bare statement* fallback) by peeking at the
first one or two tokens: a leading `CREATE FUNCTION` routes to
`function_def`, a leading `CREATE PROCEDURE` routes to
`procedure_def`, and anything else (including a `CREATE` followed by
neither) falls through to -- or errors out of -- the appropriate path.
Everywhere in this codebase that needs to know "is this AST a
function", the check is `ast["type"] == "FunctionNode"`; nothing needs
to distinguish "Procedure" from "ProcedureNode" specifically, since
both describe a procedure and neither ever needs a RETURN.

A procedure_def's params carry a `mode` ("IN", "OUT", or "INOUT",
defaulting to "IN" when omitted) -- unlike a function_def's params,
which never have a mode at all (see "Functions" below). See
app.interpreter's module docstring for what OUT/INOUT actually do at
runtime.

-- CALL and multi-procedure sources (procedure calling procedure) --------

`CALL name(arg1, arg2, ...);` invokes another procedure by name --
parses to ``{"type": "CallStatement", "name", "args", "line"}``, where
`args` is a list of ordinary expression nodes (see `expr` above; a bare
Identifier, a literal, or any arithmetic expression are all valid
argument syntax -- app.interpreter is what later requires an OUT/INOUT
argument specifically to be an Identifier, since that's a semantic rule
about writability, not a grammar rule). `CALL` is parseable anywhere an
ordinary statement is (inside IF/WHILE bodies, inside a handler's
action, inside another procedure's own body), exactly like every other
statement type.

For CALL to have anything to call, `parse()` now accepts **more than
one** `CREATE PROCEDURE`/`CREATE FUNCTION` definition chained back to
back in a single submission -- previously (and still, when there's only
one) `parse()` returns exactly that one ProcedureNode/FunctionNode, byte
-identical to before this existed. When it sees a *second* `CREATE`
right after the first definition's closing `END`/`END;`, it keeps
parsing definitions until they run out, and wraps them in a new
top-level node:

    {"type": "ProgramNode", "definitions": [ProcedureNode | FunctionNode, ...], "line": ...}

**Convention: the LAST definition in source order is the entry point**
-- the one app.interpreter actually executes when you run this AST,
exactly the way you'd run a single procedure today. Every definition
(including the entry one itself, and including any FunctionNode
definitions) is registered by name so `CALL` can find it -- app.
interpreter is what enforces that a `CALL` target must specifically be
a ProcedureNode (calling a FunctionNode by name via CALL is a clear
runtime error, not silently allowed -- a FunctionNode is invoked
differently, as an expression: see "Function calls in expressions"
below). Registering the entry procedure under its own name
too is what makes straightforward self-recursion possible without any
extra syntax. Definition order in the source does NOT matter for
resolving a CALL target -- the whole registry is built before anything
executes, so a definition can freely CALL a sibling defined earlier OR
later in the same source; only WHICH one is the entry point depends on
position (the last one).

The bare/legacy Procedure form (no CREATE wrapper at all) is
**unaffected by any of this** -- it has no name, so it can never be a
CALL target, and a submission that starts with anything other than
CREATE always parses as exactly one bare Procedure, exactly as before.
A CALL statement inside a bare Procedure's body is syntactically legal
(CALL is just another statement) but will always fail at runtime with
"procedure is not defined", since a bare-form submission can never
carry sibling definitions for it to find -- an honest limitation, not a
bug: mixing the bare form with CREATE-wrapped multi-procedure sources in
one submission isn't supported.

See app.interpreter's module docstring for exactly how a CALL executes
(argument binding, scope isolation, OUT/INOUT propagation, the call-
depth guard, and the step-trace fields that make a nested call visible).

-- Functions ------------------------------------------------------------

A function's parameters are plain `name TYPE` pairs -- no IN/OUT mode,
unlike a hypothetical procedure parameter list. They aren't
auto-declared as zero-valued locals; a caller supplies their values
the exact same way procedure parameters already do here (via the
interpreter's `initial_params`), so referencing a parameter that
wasn't supplied raises the same "not declared" error an undeclared
procedure variable would.

`RETURN expr;` is parseable anywhere an ordinary statement is (inside
IF/WHILE bodies included) via the normal `_parse_statement` dispatch --
it is not restricted to appearing only at a function's top level.
app.interpreter enforces that a function actually executes one before
its body runs out.

-- Function calls in expressions -------------------------------------------

`name(arg1, arg2, ...)` is valid anywhere `expr` is -- an assignment's
right-hand side, an IF/WHILE condition, a RETURN's own value, another
function call's or CALL statement's own argument list, and so on --
parsed at the `primary` level (`_parse_primary`) as
``{"type": "FunctionCallExpr", "name", "args", "line"}``, where `args`
is a list of ordinary expression nodes (same shape as a CALL
statement's own `args` -- see "CALL and multi-procedure sources"
above). This is the *expression-position* counterpart to `CALL`: CALL
is a standalone statement that can only target a ProcedureNode and
never produces a usable value, while a FunctionCallExpr is a value
`app.interpreter` substitutes into whatever expression it appears in,
and can only target a FunctionNode (calling a ProcedureNode's name
this way, or CALLing a FunctionNode's name, are both clear runtime
errors -- see app.interpreter's own module docstring for the full
reasoning and the execution/scope-isolation mechanics, which are
deliberately the same machinery `CALL` already uses, not a second
implementation).

Disambiguation from a plain variable reference is a simple one-token
lookahead in `_parse_primary`: after consuming an IDENTIFIER, a `(`
next means a function call, `%FOUND`/`%NOTFOUND` means a cursor-
attribute expression, and anything else means an ordinary Identifier
-- these three are mutually exclusive by construction (a variable
name is never immediately followed by `(` in this grammar otherwise),
so there is no real ambiguity to resolve, just a peek.

-- CASE statement -----------------------------------------------------------

Both common CASE forms are supported, and -- deliberately -- as ONE AST
node type, not two, since a simple CASE is just syntactic sugar over a
searched CASE (compare each WHEN value against the same operand,
instead of evaluating each WHEN as its own independent condition); one
node type means app.interpreter, app.advisor, and cfg.js each only ever
need one case for CASE, not two nearly-identical ones.

  - Simple CASE:   ``CASE expr WHEN val1 THEN ... WHEN val2 THEN ... ELSE ... END CASE;``
  - Searched CASE: ``CASE WHEN cond1 THEN ... WHEN cond2 THEN ... ELSE ... END CASE;``

`_parse_case` tells the two forms apart with a single-token lookahead
right after CASE: a WHEN next means searched (no operand); anything
else is parsed as `expr` and becomes the simple form's operand. Every
WHEN clause after that parses identically regardless of form -- an
expression (the comparison value for simple CASE, the boolean
condition for searched CASE; app.interpreter is what actually
distinguishes them at evaluation time, not the parser), then THEN,
then a statement block. Each WHEN clause's body, and the optional
ELSE's body, are parsed with `_parse_block` -- the exact same
block-parsing helper `if_stmt`/`while_stmt` already use, with
terminators `{WHEN, ELSE, END}` for a WHEN body (so it naturally stops
at the next WHEN, an ELSE, or END) and `{END}` for the ELSE body,
mirroring `if_stmt`'s own `then_body`/`else_body` terminator sets
exactly -- no new block-parsing pattern was invented for this. Just
like `if_stmt`/`while_stmt`, the statement is closed by `END CASE ';'`
-- the same "END <KEYWORD> ';'" shape every other block statement in
this grammar already uses. At least one WHEN clause is required (a
bare `CASE expr END CASE;` with none is a clear ParserError, not a
silently-accepted no-op statement).

Produces:

    {
        "type": "CaseStatement",
        "operand": expr | None,        # None => searched CASE
        "when_clauses": [
            {"when": expr, "body": [statement, ...], "line": int}, ...
        ],
        "else_body": [statement, ...] | None,
        "line": int,
    }

See app.interpreter's own "CASE statement" module docstring section for
how `operand`/`when_clauses`/`else_body` actually get evaluated
(including what happens when nothing matches and there's no ELSE).

-- LOOP / LEAVE -------------------------------------------------------------

`LOOP ... END LOOP;` is an unconditional block -- unlike WHILE, it has no
condition of its own at all, so the only way out is an explicit `LEAVE;`
executed somewhere inside its body (or, as a safety net, the same
MAX_LOOP_ITERATIONS guard WHILE already has -- see app.interpreter). A
LOOP may optionally be labeled, MySQL-style: `mylabel: LOOP ... END LOOP
mylabel;` -- the label is a plain IDENTIFIER immediately followed by a
literal ':' token before LOOP (this is the only construct in this
grammar that uses a bare colon, which is why ':' only became a real
token in this phase -- see app.tokenizer). The label may be repeated
after the closing `END LOOP`, or omitted there even if the opening one
had it; if both are present, they must match (a clear ParserError
otherwise, not a silent typo). Both the opening and closing labels are
fully optional -- a bare, unlabeled `LOOP ... END LOOP;` (matching the
form Theory.jsx's own ControlFlowTopic already describes -- "a bare LOOP
... until an explicit LEAVE") is just as valid as a labeled one; labels
only start to matter once loops are nested and a `LEAVE` needs to name
*which* enclosing one to break (see below).

`_parse_statement` tells a labeled LOOP apart from every other statement
with a one-token lookahead: every other statement in this grammar starts
with a KEYWORD, so an IDENTIFIER immediately followed by ':' is
unambiguously a loop label (there's no other legal way for a statement
to start with a bare IDENTIFIER), never confused with an ordinary
expression or assignment target.

Each WHEN clause's own body-parsing convention carries over here too:
the loop body is parsed via `_parse_block({"END"})` -- the exact same
block-parsing helper IF/WHILE/CASE already use -- so a LOOP can contain,
and be contained by, any other statement type (IF/WHILE/CASE/another
LOOP/CALL/...) exactly like they can nest inside each other already; no
new nesting mechanism was needed.

`LEAVE;` (unlabeled) or `LEAVE mylabel;` (labeled) exits a loop
immediately -- app.interpreter is what actually resolves *which*
enclosing LOOP an unlabeled LEAVE targets (always the innermost one) or
validates that a labeled LEAVE names a loop that's genuinely currently
enclosing it (a clear InterpreterError if not -- this is a runtime check,
not a parse-time one, matching how this grammar validates everything
else that depends on nesting/scope, e.g. an OUT/INOUT CALL argument
needing to be a plain Identifier). `LEAVE` is parseable anywhere any
other statement is, exactly like every other statement type -- including
inside an IF/WHILE/CASE that is itself inside the LOOP it's leaving,
which is the normal, expected shape (`LOOP ... IF cond THEN LEAVE;
END IF; ... END LOOP;`).

Produces:

    {"type": "LoopStatement", "label": str | None, "body": [statement, ...], "line": int}
    {"type": "LeaveStatement", "label": str | None, "line": int}

See app.interpreter's own "LOOP / LEAVE" module docstring section for
how a LEAVE actually unwinds to the correct enclosing LOOP (including
across nested loops), how loop-label scope is isolated across a CALL/
function-call boundary, and the step-trace shape this reuses from WHILE.

-- SQL passthrough statements (CREATE TABLE / INSERT / UPDATE / DELETE / SELECT) --

Five statement types, all parseable anywhere any other statement is
(inside IF/WHILE/CASE/LOOP bodies, a handler's action, ...), exactly like
every other statement type in this grammar -- and all sharing ONE AST
node type and ONE parsing method, `_parse_sql_passthrough`:

  ``CREATE TABLE ...;``
  ``INSERT INTO ...;``
  ``UPDATE ...;``
  ``DELETE FROM ...;``
  ``SELECT ...;``

A bare ``SELECT`` here means the whole result set comes back as one
DebugStep's worth of rows/columns, nothing assigned into a variable --
for a single-row lookup that assigns each selected column into its own
procedure-scope variable, see "SELECT ... INTO" below instead, a
DIFFERENT statement type with its own AST node and parsing method.
`_parse_statement`'s own dispatch (`_select_has_into`) tells the two
apart before committing to either: an INTO appearing before the next
FROM/';' routes to SelectIntoStatement, anything else falls through to
this SqlStatement passthrough.

**Superseded feature, not an addition alongside it**: an earlier phase
gave CREATE TABLE/INSERT/UPDATE/DELETE their own four structured AST node
types (`CreateTableStatement`/`InsertStatement`/`UpdateStatement`/
`DeleteStatement`), each deeply parsed (column defs, a real `expr` for
every VALUES/SET/WHERE value) and executed by app.interpreter as a pure
Python simulation (`Interpreter.tables`) -- never touching real SQLite,
and for exactly that reason never visible to a cursor's embedded SELECT.
This phase retires all four of those node types and that entire
simulation in favor of the raw-passthrough approach below, closing that
gap: these statements now execute for real, against the exact same
persistent database (`app.user_db`) a cursor's SELECT already reads from
-- see app.interpreter's own section of this same name for the execution
side, and `docs/features.md` for the full retirement rationale. This is
a real, deliberate behavior change to an already-shipped feature, not a
new one bolted on beside it.

Like a cursor's embedded SELECT (see "Cursors" below), NONE of these five
are parsed into any further structure -- `_parse_sql_passthrough` just
captures every token from the leading keyword up to the closing ';'
verbatim and reassembles it into one raw SQL string via the exact same
`_render_raw_query` helper the cursor path already uses, producing:

    {"type": "SqlStatement", "keyword": "CREATE" | "INSERT" | "UPDATE" | "DELETE" | "SELECT",
     "sql": str, "line": int}

`keyword` is which of the five this is (recorded by the parser, which
already knows -- it dispatched here because it saw that keyword) --
`sql` is the ENTIRE statement text including that leading keyword itself
(unlike `CursorDeclNode.query`, which starts only after `CURSOR FOR`).
app.interpreter hands `sql` straight to SQLite unmodified; there is no
column-definition parsing, no VALUES/SET/WHERE expression parsing, and
critically **no variable interpolation** -- a raw statement cannot
reference a procedure-scope DECLAREd variable by name the way the old
simulated UPDATE/DELETE's WHERE or the old INSERT's VALUES could
(`UPDATE t SET price = price - discount` now means the literal SQL
column/identifier `discount`, which SQLite will reject as "no such
column" unless a real column happens to share that name -- it is NOT
substituted with the current value of a same-named procedure variable).
This is a genuine capability loss relative to the retired feature,
traded deliberately for "real SQL, real database, real interoperability
with cursors" per this phase's own instruction -- a procedure that needs
a variable's value inside one of these statements must currently splice
it into the SQL text itself before it reaches the parser (e.g. building
the string is not supported either -- there is no string-concatenation
expression in this grammar -- so today this genuinely only works with
literal values, exactly like a cursor's own embedded SELECT already only
ever worked with literals, never a bound parameter).

Round-trips cleanly for every comparison operator this grammar's own
tokenizer knows, `<=`/`>=`/`<>` included: each is lexed as ONE OPERATOR
token carrying its full text (see app.tokenizer), so `_render_raw_query`
never has to reassemble a two-character operator out of two separate
one-character tokens with a space forced between them. (This used to be
a real, documented caveat -- `<=`/`>=`/`<>` would tokenize as two
separate operator tokens and reassemble as invalid SQL like `score > =
90` -- fixed as part of extending the *procedural* comparison rule above
to accept them too; see app.tokenizer's own module docstring for the
lexing-order fix that made both true at once.)

**Top-level dispatch note**: `CREATE` was, before this, only ever the
first token of a `CREATE FUNCTION`/`CREATE PROCEDURE` definition (see
"Procedures: two forms" and "CALL and multi-procedure sources" above),
so `parse()`'s own top-level dispatch used to treat ANY leading `CREATE`
as the start of a chained-definitions source. `CREATE TABLE` breaks that
assumption -- it's an ordinary *statement*, not a top-level definition,
and can legally be the very first line of a bare/legacy procedure body
with no wrapper at all. `parse()` now peeks a second token ahead before
committing to the definition-chain path: only `CREATE PROCEDURE`/`CREATE
FUNCTION` specifically routes there; a leading `CREATE TABLE` (or any
other `CREATE ...`) falls through to the ordinary bare statement-list
grammar, where `_parse_statement`'s own `CREATE TABLE` lookahead handles
it as a normal statement. `CREATE TABLE` is NOT itself a chainable
top-level definition (there's no "CALL a table" concept) -- it only ever
appears as a statement inside a procedure/function body or a bare
statement list, never as a sibling of a `CREATE PROCEDURE`/`CREATE
FUNCTION` definition chain.

-- SELECT ... INTO ----------------------------------------------------------

A single-row lookup, distinct from both the cursor mechanism (DECLARE
CURSOR/OPEN/FETCH/CLOSE, entirely unchanged by this) and the standalone
``SELECT`` SqlStatement passthrough above (a whole result set as one
DebugStep, nothing assigned to a variable):

    ``SELECT col1, col2, ... INTO var1, var2, ... FROM table WHERE condition;``

Own AST node type, own parsing method (`_parse_select_into`), not a
variant of either of the other two. Two spans are captured verbatim,
exactly like `_parse_sql_passthrough`/`_parse_declare_cursor` already
capture their own raw SQL text -- the column list between SELECT and
INTO, and everything after the INTO variable list up to the closing
';' (the FROM/WHERE clause) -- with the INTO variable list itself parsed
structurally in between, token-for-token the same way
`_parse_fetch_cursor` already parses a FETCH's own `INTO var1, var2`
list. The two raw spans are then rejoined into one ready-to-execute
query with the INTO clause removed (real SQLite has no ``SELECT ...
INTO ...`` syntax in this position -- that's a T-SQL/PL-SQL-ism this
grammar borrows only as procedural sugar, never hands to SQLite
verbatim):

    {"type": "SelectIntoStatement", "targets": [str, ...],
     "query": str,  # "SELECT <cols> FROM ... WHERE ..." -- INTO clause stripped
     "line": int}

Same "no variable interpolation, literals only" limitation as every
other raw-passthrough statement above applies to the WHERE clause here
too. **Dispatch**: `_parse_statement` sees a bare `SELECT` and must
decide between this and the plain SqlStatement passthrough BEFORE
committing to either parsing method -- `_select_has_into` does a bounded
lookahead (no consumption) for an INTO keyword appearing before the next
FROM or the statement-ending ';'; found means SELECT ... INTO, not found
means an ordinary standalone SELECT. See app.interpreter's own "SELECT
... INTO" module docstring section for how zero/one/many-row results are
handled (the zero-row case deliberately reuses cursor FETCH's own
NOT_FOUND condition, not a new error path).

-- Cursors -----------------------------------------------------------------

A cursor declaration's embedded SELECT is *not* parsed into its own AST:
the tokens between FOR and the closing ';' are captured verbatim and
reassembled into a single SQL string (CursorDeclNode.query), which
app.interpreter hands straight to SQLite when the cursor is OPENed. Every
comparison operator this grammar's own tokenizer knows (=, >, <, !=, >=,
<=, <>) round-trips correctly inside an embedded WHERE clause -- each is
one OPERATOR token carrying its full text, so reassembly never splits a
two-character operator across two tokens (see "SQL passthrough
statements" above for the fix that made this true).

`cur_name%FOUND` / `cur_name%NOTFOUND` are a pragmatic, and deliberately
*asymmetric*, reading of Oracle's cursor-attribute syntax: %FOUND is
predictive ("is a row ready for the next FETCH"), which is what makes
`WHILE cur%FOUND DO ... FETCH ... END WHILE` work as an ordinary
WHILE-first-checks-then-runs loop; %NOTFOUND is retrospective ("did the
FETCH just before this check fail"), which is what makes the
`FETCH ...; IF cur%NOTFOUND THEN ...` fallback pattern work. They are
NOT simple negations of each other -- see app.interpreter's module
docstring for why, and for the evaluation itself.

-- Exception handlers -------------------------------------------------------

`DECLARE CONTINUE HANDLER FOR <condition> <statement>` registers a single
statement to run automatically when `<condition>` is triggered later in
the procedure. Exactly two conditions are supported -- NOT_FOUND (a
FETCH finds no row) and DIVISION_BY_ZERO (a `/` divides by zero) -- this
is not the general MySQL condition system (no SQLSTATE values, no named
conditions, no EXIT handlers, only CONTINUE). The handler's action is a
single statement, not a BEGIN...END block, for the same reason the rest
of this grammar has no blocks.

Handlers are procedure-scoped, not block-scoped: real MySQL ties a
handler's lifetime to its enclosing BEGIN...END block; this grammar has
no blocks to scope to, so a handler registered anywhere is active for
the rest of the procedure's execution from that point on -- it must be
declared (i.e. actually executed, in top-to-bottom program order) before
the code that could trigger it, same as any other DECLARE. See
app.interpreter's module docstring for exactly when each condition is
non-fatal vs. still a hard error.
"""

from __future__ import annotations

COMPARISON_OPERATORS = {">", "<", "=", "!=", ">=", "<=", "<>"}
ADDITIVE_OPERATORS = {"+", "-"}
MULTIPLICATIVE_OPERATORS = {"*", "/"}


class ParserError(ValueError):
    """Raised when the token stream doesn't match the grammar."""

    def __init__(self, message: str, token: dict | None, line: int | None = None):
        if token is not None:
            line = token["line"]
            message = (
                f"{message} (got {token['type']} {token['value']!r} "
                f"at line {token['line']}, column {token['column']})"
            )
        elif line is not None:
            message = f"{message} (got end of input after line {line})"
        else:
            message = f"{message} (got end of input)"
        super().__init__(message)
        self.token = token
        # Best-effort line for API responses: the offending token's line,
        # or (when input just ran out) the last line seen, or None if the
        # input was empty from the start.
        self.line = line


class Parser:
    """Holds parse position over a fixed token list."""

    def __init__(self, tokens: list[dict]):
        self.tokens = tokens
        self.pos = 0
        self._last_line: int | None = None  # line of the last consumed token

    # -- token stream helpers -------------------------------------------------

    def _peek(self) -> dict | None:
        if self.pos < len(self.tokens):
            return self.tokens[self.pos]
        return None

    def _advance(self) -> dict | None:
        token = self._peek()
        if token is not None:
            self.pos += 1
            self._last_line = token["line"]
        return token

    def _peek_ahead_is(self, type_: str, value: str | None = None) -> bool:
        """Like `_check`, but looks one token past the current position
        without consuming anything -- used to tell a loop label (`IDENT
        ':'`) apart from every other statement (see the module
        docstring's "LOOP / LEAVE" section), and to tell a `CREATE
        TABLE` statement apart from a `CREATE PROCEDURE`/`CREATE
        FUNCTION` definition (see "SQL passthrough statements" below).
        `value` is compared case-insensitively, same as `_check`, since a
        KEYWORD's own case never matters in this grammar."""
        token = self.tokens[self.pos + 1] if self.pos + 1 < len(self.tokens) else None
        if token is None or token["type"] != type_:
            return False
        if value is not None and token["value"].upper() != value:
            return False
        return True

    def _select_has_into(self) -> bool:
        """Bounded lookahead from a bare SELECT (still unconsumed, sitting
        at the current position) to tell a `SELECT ... INTO ...`
        single-row lookup (`_parse_select_into`) apart from a standalone
        SqlStatement SELECT passthrough (`_parse_sql_passthrough`) --
        see the module docstring's "SELECT ... INTO" section. Scans
        forward for an INTO keyword; the first of INTO / FROM / ';'
        encountered settles it, since INTO always comes right after the
        column list and before FROM in this grammar's own SELECT ...
        INTO form. Consumes nothing -- a pure peek, same contract as
        `_peek_ahead_is`, just not limited to exactly one token ahead."""
        i = self.pos + 1
        while i < len(self.tokens):
            token = self.tokens[i]
            if token["type"] == "KEYWORD" and token["value"].upper() == "INTO":
                return True
            if token["type"] == "KEYWORD" and token["value"].upper() == "FROM":
                return False
            if token["type"] == "PUNCTUATION" and token["value"] == ";":
                return False
            i += 1
        return False

    def _error(self, message: str, token: dict | None = None) -> ParserError:
        """Build a ParserError, falling back to the last consumed token's
        line when we've run out of input to point at directly."""
        if token is None:
            token = self._peek()
        return ParserError(message, token, line=self._last_line)

    def _check(self, type_: str, value: str | None = None) -> bool:
        token = self._peek()
        if token is None or token["type"] != type_:
            return False
        if value is not None and token["value"].upper() != value:
            return False
        return True

    def _match(self, type_: str, value: str | None = None) -> dict | None:
        if self._check(type_, value):
            return self._advance()
        return None

    def _expect(self, type_: str, value: str | None = None) -> dict:
        token = self._match(type_, value)
        if token is None:
            wanted = value if value is not None else type_
            raise self._error(f"Expected {wanted!r}")
        return token

    def _keyword(self, name: str) -> dict:
        return self._expect("KEYWORD", name)

    # -- entry point ------------------------------------------------------

    def parse_procedure(self) -> dict:
        body = []
        while self._peek() is not None:
            body.append(self._parse_statement())
        return {"type": "Procedure", "body": body}

    def parse_function_def(self) -> dict:
        start = self._keyword("CREATE")
        self._keyword("FUNCTION")
        name_token = self._expect("IDENTIFIER")

        self._expect("PUNCTUATION", "(")
        params: list[dict] = []
        if not self._check("PUNCTUATION", ")"):
            params.append(self._parse_function_param())
            while self._match("PUNCTUATION", ","):
                params.append(self._parse_function_param())
        self._expect("PUNCTUATION", ")")

        self._keyword("RETURNS")
        return_type_token = self._expect("IDENTIFIER")

        self._keyword("BEGIN")
        body = self._parse_block({"END"})
        self._keyword("END")
        self._match("PUNCTUATION", ";")  # optional trailing ';' after END

        return {
            "type": "FunctionNode",
            "name": name_token["value"],
            "params": params,
            "returnType": return_type_token["value"],
            "body": body,
            "line": start["line"],
        }

    def _parse_function_param(self) -> dict:
        # Plain `name TYPE` -- no IN/OUT mode, unlike a procedure
        # parameter (see module docstring's "Functions" section).
        name_token = self._expect("IDENTIFIER")
        type_token = self._expect("IDENTIFIER")
        return {"name": name_token["value"], "type": type_token["value"]}

    def parse_procedure_def(self) -> dict:
        start = self._keyword("CREATE")
        self._keyword("PROCEDURE")
        name_token = self._expect("IDENTIFIER")

        self._expect("PUNCTUATION", "(")
        params: list[dict] = []
        if not self._check("PUNCTUATION", ")"):
            params.append(self._parse_procedure_param())
            while self._match("PUNCTUATION", ","):
                params.append(self._parse_procedure_param())
        self._expect("PUNCTUATION", ")")

        self._keyword("BEGIN")
        body = self._parse_block({"END"})
        self._keyword("END")
        self._match("PUNCTUATION", ";")  # optional trailing ';' after END

        return {
            "type": "ProcedureNode",
            "name": name_token["value"],
            "params": params,
            "body": body,
            "line": start["line"],
        }

    def _parse_procedure_param(self) -> dict:
        # (IN | OUT | INOUT)? name TYPE -- mode defaults to "IN" when
        # omitted, matching ordinary SQL/PSM behavior.
        mode = "IN"
        for candidate in ("IN", "OUT", "INOUT"):
            if self._match("KEYWORD", candidate):
                mode = candidate
                break
        name_token = self._expect("IDENTIFIER")
        type_token = self._expect("IDENTIFIER")
        return {"name": name_token["value"], "mode": mode, "type": type_token["value"]}

    # -- statements ---------------------------------------------------------

    def _parse_statement(self) -> dict:
        token = self._peek()
        if token is None:
            raise self._error("Expected a statement")

        if self._check("KEYWORD", "DECLARE"):
            return self._parse_declare()
        if self._check("KEYWORD", "SET"):
            return self._parse_set()
        if self._check("KEYWORD", "IF"):
            return self._parse_if()
        if self._check("KEYWORD", "WHILE"):
            return self._parse_while()
        if self._check("KEYWORD", "CASE"):
            return self._parse_case()
        if self._check("KEYWORD", "OPEN"):
            return self._parse_open_cursor()
        if self._check("KEYWORD", "FETCH"):
            return self._parse_fetch_cursor()
        if self._check("KEYWORD", "CLOSE"):
            return self._parse_close_cursor()
        if self._check("KEYWORD", "RETURN"):
            return self._parse_return()
        if self._check("KEYWORD", "CALL"):
            return self._parse_call()
        if self._check("KEYWORD", "LOOP"):
            return self._parse_loop(label=None)
        if self._check("KEYWORD", "LEAVE"):
            return self._parse_leave()
        if self._check("KEYWORD", "CREATE") and self._peek_ahead_is("KEYWORD", "TABLE"):
            return self._parse_sql_passthrough("CREATE")
        if self._check("KEYWORD", "INSERT"):
            return self._parse_sql_passthrough("INSERT")
        if self._check("KEYWORD", "UPDATE"):
            return self._parse_sql_passthrough("UPDATE")
        if self._check("KEYWORD", "DELETE"):
            return self._parse_sql_passthrough("DELETE")
        if self._check("KEYWORD", "SELECT"):
            # Two different statement types share a bare SELECT keyword
            # -- see the module docstring's "SELECT ... INTO" section for
            # why this has to be a lookahead decided BEFORE either
            # parsing method runs, not a fallback after one fails.
            if self._select_has_into():
                return self._parse_select_into()
            return self._parse_sql_passthrough("SELECT")
        if self._check("IDENTIFIER") and self._peek_ahead_is("PUNCTUATION", ":"):
            # `label: LOOP ...` -- see the module docstring's "LOOP /
            # LEAVE" section for why an IDENTIFIER immediately followed
            # by ':' is unambiguously a loop label and nothing else (no
            # other statement in this grammar can start with a bare
            # IDENTIFIER).
            label_token = self._advance()
            self._expect("PUNCTUATION", ":")
            return self._parse_loop(label=label_token["value"], start=label_token)

        raise self._error(
            "Expected DECLARE, SET, IF, WHILE, CASE, RETURN, OPEN, FETCH, CLOSE, CALL, LOOP, "
            "LEAVE, CREATE TABLE, INSERT, UPDATE, DELETE, or SELECT",
            token,
        )

    def _parse_return(self) -> dict:
        start = self._keyword("RETURN")
        value = self._parse_expr()
        self._expect("PUNCTUATION", ";")
        return {"type": "ReturnNode", "value": value, "line": start["line"]}

    def _parse_call(self) -> dict:
        start = self._keyword("CALL")
        name_token = self._expect("IDENTIFIER")

        self._expect("PUNCTUATION", "(")
        args: list[dict] = []
        if not self._check("PUNCTUATION", ")"):
            args.append(self._parse_expr())
            while self._match("PUNCTUATION", ","):
                args.append(self._parse_expr())
        self._expect("PUNCTUATION", ")")
        self._expect("PUNCTUATION", ";")

        return {
            "type": "CallStatement",
            "name": name_token["value"],
            "args": args,
            "line": start["line"],
        }

    def _parse_declare(self) -> dict:
        start = self._keyword("DECLARE")

        # DECLARE CONTINUE HANDLER FOR ... branches off into a handler
        # declaration before we even look for a name -- it has no
        # IDENT in that position, unlike every other DECLARE form.
        if self._check("KEYWORD", "CONTINUE"):
            return self._parse_declare_handler(start)

        name_token = self._expect("IDENTIFIER")

        # DECLARE cur CURSOR FOR ... branches off into a cursor
        # declaration -- everything else falls through to the ordinary
        # `DECLARE name TYPE (DEFAULT expr)?` form below.
        if self._check("KEYWORD", "CURSOR"):
            return self._parse_declare_cursor(start, name_token)

        type_token = self._expect("IDENTIFIER")
        default = None
        if self._match("KEYWORD", "DEFAULT"):
            default = self._parse_expr()
        self._expect("PUNCTUATION", ";")
        return {
            "type": "DeclareStatement",
            "name": name_token["value"],
            "var_type": type_token["value"],
            "default": default,
            "line": start["line"],
        }

    def _parse_declare_cursor(self, start: dict, name_token: dict) -> dict:
        self._keyword("CURSOR")
        self._keyword("FOR")

        # Capture the embedded SELECT verbatim -- no attempt to parse
        # its grammar, just collect tokens up to the statement-ending
        # ';' (see the module docstring's "Cursors" section for the
        # round-tripping caveats this implies).
        query_tokens: list[dict] = []
        while self._peek() is not None and not self._check("PUNCTUATION", ";"):
            query_tokens.append(self._advance())
        if not query_tokens:
            raise self._error("Expected a query after CURSOR FOR")
        self._expect("PUNCTUATION", ";")

        return {
            "type": "CursorDeclNode",
            "name": name_token["value"],
            "query": _render_raw_query(query_tokens),
            "line": start["line"],
        }

    def _parse_declare_handler(self, start: dict) -> dict:
        self._keyword("CONTINUE")
        self._keyword("HANDLER")
        self._keyword("FOR")

        condition_token = self._peek()
        if self._match("KEYWORD", "NOT_FOUND"):
            condition = "NOT_FOUND"
        elif self._match("KEYWORD", "DIVISION_BY_ZERO"):
            condition = "DIVISION_BY_ZERO"
        else:
            raise self._error("Expected NOT_FOUND or DIVISION_BY_ZERO", condition_token)

        # A single statement, not a BEGIN...END block -- see the module
        # docstring's "Exception handlers" section.
        action = self._parse_statement()

        return {
            "type": "HandlerDeclNode",
            "condition": condition,
            "action": action,
            "line": start["line"],
        }

    def _parse_open_cursor(self) -> dict:
        start = self._keyword("OPEN")
        name_token = self._expect("IDENTIFIER")
        self._expect("PUNCTUATION", ";")
        return {
            "type": "OpenCursorNode",
            "name": name_token["value"],
            "line": start["line"],
        }

    def _parse_fetch_cursor(self) -> dict:
        start = self._keyword("FETCH")
        name_token = self._expect("IDENTIFIER")
        self._keyword("INTO")

        targets = [self._expect("IDENTIFIER")["value"]]
        while self._match("PUNCTUATION", ","):
            targets.append(self._expect("IDENTIFIER")["value"])

        self._expect("PUNCTUATION", ";")
        return {
            "type": "FetchCursorNode",
            "name": name_token["value"],
            "targets": targets,
            "line": start["line"],
        }

    def _parse_close_cursor(self) -> dict:
        start = self._keyword("CLOSE")
        name_token = self._expect("IDENTIFIER")
        self._expect("PUNCTUATION", ";")
        return {
            "type": "CloseCursorNode",
            "name": name_token["value"],
            "line": start["line"],
        }

    def _parse_set(self) -> dict:
        start = self._keyword("SET")
        target_token = self._expect("IDENTIFIER")
        self._expect("OPERATOR", "=")
        value = self._parse_expr()
        self._expect("PUNCTUATION", ";")
        return {
            "type": "SetStatement",
            "target": target_token["value"],
            "value": value,
            "line": start["line"],
        }

    def _parse_block(self, terminators: set[str]) -> list[dict]:
        """Parse statements until a KEYWORD in `terminators` is next."""
        statements = []
        while self._peek() is not None and not (
            self._peek()["type"] == "KEYWORD"
            and self._peek()["value"].upper() in terminators
        ):
            statements.append(self._parse_statement())
        return statements

    def _parse_if(self) -> dict:
        start = self._keyword("IF")
        condition = self._parse_expr()
        self._keyword("THEN")
        then_body = self._parse_block({"ELSE", "END"})

        else_body = None
        if self._match("KEYWORD", "ELSE"):
            else_body = self._parse_block({"END"})

        self._keyword("END")
        self._keyword("IF")
        self._expect("PUNCTUATION", ";")

        return {
            "type": "IfStatement",
            "condition": condition,
            "then_body": then_body,
            "else_body": else_body,
            "line": start["line"],
        }

    def _parse_while(self) -> dict:
        start = self._keyword("WHILE")
        condition = self._parse_expr()
        self._keyword("DO")
        body = self._parse_block({"END"})
        self._keyword("END")
        self._keyword("WHILE")
        self._expect("PUNCTUATION", ";")

        return {
            "type": "WhileStatement",
            "condition": condition,
            "body": body,
            "line": start["line"],
        }

    def _parse_case(self) -> dict:
        """Both CASE forms, as one node type -- see the module
        docstring's "CASE statement" section for the full design."""
        start = self._keyword("CASE")

        # A WHEN right after CASE means searched (no operand); anything
        # else is the simple form's operand expression.
        operand = None
        if not self._check("KEYWORD", "WHEN"):
            operand = self._parse_expr()

        when_clauses: list[dict] = []
        while self._check("KEYWORD", "WHEN"):
            when_start = self._keyword("WHEN")
            when_expr = self._parse_expr()
            self._keyword("THEN")
            body = self._parse_block({"WHEN", "ELSE", "END"})
            when_clauses.append({"when": when_expr, "body": body, "line": when_start["line"]})

        if not when_clauses:
            raise self._error("Expected at least one WHEN clause in CASE")

        else_body = None
        if self._match("KEYWORD", "ELSE"):
            else_body = self._parse_block({"END"})

        self._keyword("END")
        self._keyword("CASE")
        self._expect("PUNCTUATION", ";")

        return {
            "type": "CaseStatement",
            "operand": operand,
            "when_clauses": when_clauses,
            "else_body": else_body,
            "line": start["line"],
        }

    def _parse_loop(self, label: str | None, start: dict | None = None) -> dict:
        """`(IDENT ':')? LOOP statement* END LOOP IDENT? ';'` -- see the
        module docstring's "LOOP / LEAVE" section. `label`/`start` are
        already-consumed by `_parse_statement` when a label was present
        (the label token doubles as the statement's own `line`, matching
        how every other labeled construct in this grammar anchors its
        line to its own first token); otherwise this method consumes the
        LOOP keyword itself as both."""
        loop_token = self._keyword("LOOP")
        if start is None:
            start = loop_token
        body = self._parse_block({"END"})
        self._keyword("END")
        self._keyword("LOOP")

        # An optional closing label -- MySQL-style, purely for
        # readability on a long loop body. If both are given they must
        # agree; a closing label with no opening one is a clear mistake
        # (there's nothing for it to confirm), not silently accepted.
        if self._check("IDENTIFIER"):
            end_label_token = self._advance()
            if label is None:
                raise self._error(
                    f"END LOOP names label {end_label_token['value']!r} but this LOOP has no "
                    "opening label",
                    end_label_token,
                )
            if end_label_token["value"] != label:
                raise self._error(
                    f"END LOOP label {end_label_token['value']!r} does not match this LOOP's "
                    f"opening label {label!r}",
                    end_label_token,
                )

        self._expect("PUNCTUATION", ";")

        return {
            "type": "LoopStatement",
            "label": label,
            "body": body,
            "line": start["line"],
        }

    def _parse_leave(self) -> dict:
        start = self._keyword("LEAVE")
        label = None
        if self._check("IDENTIFIER"):
            label = self._advance()["value"]
        self._expect("PUNCTUATION", ";")
        return {"type": "LeaveStatement", "label": label, "line": start["line"]}

    # -- SQL passthrough statements (CREATE TABLE / INSERT / UPDATE / -------
    # DELETE / SELECT) -- see the module docstring's section of the same
    # name for the full design; app.interpreter's own section of the same
    # name for how the captured `sql` text actually executes.

    def _parse_sql_passthrough(self, keyword: str) -> dict:
        """Capture the ENTIRE statement -- starting at `keyword` itself,
        already sitting under the cursor -- verbatim up to the closing
        ';', exactly like `_parse_declare_cursor` already captures a
        cursor's embedded SELECT (just starting one token earlier: that
        one begins capture only after `CURSOR FOR`, this one includes
        the leading keyword since there's no earlier wrapper to skip
        past). No structure is parsed at all -- not even enough to know
        a table name -- see the module docstring for exactly what this
        trades away (constraint enforcement, WHERE/VALUES expression
        parsing, variable interpolation) for real-SQLite execution."""
        start = self._peek()
        sql_tokens: list[dict] = []
        while self._peek() is not None and not self._check("PUNCTUATION", ";"):
            sql_tokens.append(self._advance())
        if not sql_tokens:
            raise self._error(f"Expected a SQL statement after {keyword}")
        self._expect("PUNCTUATION", ";")

        return {
            "type": "SqlStatement",
            "keyword": keyword,
            "sql": _render_raw_query(sql_tokens),
            "line": start["line"],
        }

    # -- SELECT ... INTO -------------------------------------------------
    # See the module docstring's section of the same name for the full
    # design; app.interpreter's own section of the same name for how
    # zero/one/many-row results are handled.

    def _parse_select_into(self) -> dict:
        """Called only after `_select_has_into` (see `_parse_statement`)
        already confirmed an INTO appears before the next FROM/';', so
        this can capture up to INTO unconditionally with no further
        disambiguation. Two raw-captured spans sandwich a structurally
        parsed INTO variable list -- the column list before INTO (exactly
        like `_parse_sql_passthrough` captures its own raw SQL), the
        variable list itself (token-for-token like `_parse_fetch_cursor`
        already parses a FETCH's own `INTO var1, var2` list), then the
        FROM/WHERE clause after it, up to the closing ';'."""
        start = self._keyword("SELECT")

        select_tokens: list[dict] = []
        while self._peek() is not None and not self._check("KEYWORD", "INTO"):
            select_tokens.append(self._advance())
        if not select_tokens:
            raise self._error("Expected a column list between SELECT and INTO")
        self._keyword("INTO")

        targets = [self._expect("IDENTIFIER")["value"]]
        while self._match("PUNCTUATION", ","):
            targets.append(self._expect("IDENTIFIER")["value"])

        tail_tokens: list[dict] = []
        while self._peek() is not None and not self._check("PUNCTUATION", ";"):
            tail_tokens.append(self._advance())
        if not tail_tokens:
            raise self._error("Expected FROM ... after SELECT ... INTO var-list")
        self._expect("PUNCTUATION", ";")

        # Rejoined into one ready-to-execute query with the INTO clause
        # removed -- real SQLite has no `SELECT ... INTO ...` syntax in
        # this position, so this can never be handed to it verbatim (see
        # the module docstring).
        select_clause = _render_raw_query(select_tokens)
        tail_clause = _render_raw_query(tail_tokens)
        return {
            "type": "SelectIntoStatement",
            "selectClause": select_clause,
            "targets": targets,
            "tailClause": tail_clause,
            "query": f"SELECT {select_clause} {tail_clause}",
            "line": start["line"],
        }

    # -- expressions (precedence climbing) -----------------------------------

    def _parse_expr(self) -> dict:
        return self._parse_comparison()

    def _parse_comparison(self) -> dict:
        left = self._parse_term()
        while self._peek() is not None and (
            self._peek()["type"] == "OPERATOR"
            and self._peek()["value"] in COMPARISON_OPERATORS
        ):
            op_token = self._advance()
            right = self._parse_term()
            left = {
                "type": "BinaryExpr",
                "operator": op_token["value"],
                "left": left,
                "right": right,
                "line": op_token["line"],
            }
        return left

    def _parse_term(self) -> dict:
        left = self._parse_factor()
        while self._peek() is not None and (
            self._peek()["type"] == "OPERATOR"
            and self._peek()["value"] in ADDITIVE_OPERATORS
        ):
            op_token = self._advance()
            right = self._parse_factor()
            left = {
                "type": "BinaryExpr",
                "operator": op_token["value"],
                "left": left,
                "right": right,
                "line": op_token["line"],
            }
        return left

    def _parse_factor(self) -> dict:
        left = self._parse_unary()
        while self._peek() is not None and (
            self._peek()["type"] == "OPERATOR"
            and self._peek()["value"] in MULTIPLICATIVE_OPERATORS
        ):
            op_token = self._advance()
            right = self._parse_unary()
            left = {
                "type": "BinaryExpr",
                "operator": op_token["value"],
                "left": left,
                "right": right,
                "line": op_token["line"],
            }
        return left

    def _parse_unary(self) -> dict:
        if self._check("OPERATOR", "-"):
            op_token = self._advance()
            operand = self._parse_unary()
            return {
                "type": "UnaryExpr",
                "operator": op_token["value"],
                "operand": operand,
                "line": op_token["line"],
            }
        return self._parse_primary()

    def _parse_primary(self) -> dict:
        token = self._peek()
        if token is None:
            raise self._error("Expected an expression")

        if token["type"] == "NUMBER":
            self._advance()
            value = float(token["value"]) if "." in token["value"] else int(token["value"])
            return {"type": "NumberLiteral", "value": value, "line": token["line"]}

        if token["type"] == "STRING":
            self._advance()
            return {
                "type": "StringLiteral",
                "value": token["value"][1:-1],  # strip surrounding quotes
                "line": token["line"],
            }

        if token["type"] == "KEYWORD" and token["value"].upper() == "NULL":
            # A primary-expression literal, valid anywhere any other
            # literal is (an ordinary SET/DECLARE DEFAULT/IF condition,
            # ...); evaluates to Python `None`, same as a DECLAREd-but-
            # unset variable already does. Originally added alongside the
            # since-retired simulated table-statement feature as an
            # explicit INSERT value -- that grammar is gone (see the
            # module docstring's "SQL passthrough statements" section),
            # but NULL itself stayed as an ordinary literal since nothing
            # about it was specific to that feature.
            self._advance()
            return {"type": "NullLiteral", "line": token["line"]}

        if token["type"] == "IDENTIFIER":
            self._advance()
            # name(...) -- a function call used as an expression (see
            # the module docstring's "Function calls in expressions"
            # section), distinct from a standalone CALL statement
            # (call_stmt above, which can only target a procedure and
            # is parsed by `_parse_call` instead). Checked before the
            # cursor-attribute case below since the two are mutually
            # exclusive by construction.
            if self._check("PUNCTUATION", "("):
                return self._parse_function_call_expr(token)
            # cur_name%FOUND / cur_name%NOTFOUND -- a cursor-attribute
            # expression rather than a plain variable reference. See
            # the module docstring's "Cursors" section for what %FOUND
            # means here.
            if self._check("OPERATOR", "%"):
                self._advance()
                if self._match("KEYWORD", "FOUND"):
                    return {"type": "CursorFoundExpr", "cursor": token["value"], "line": token["line"]}
                if self._match("KEYWORD", "NOTFOUND"):
                    return {"type": "CursorNotFoundExpr", "cursor": token["value"], "line": token["line"]}
                raise self._error("Expected FOUND or NOTFOUND after '%'")
            return {"type": "Identifier", "name": token["value"], "line": token["line"]}

        if token["type"] == "PUNCTUATION" and token["value"] == "(":
            self._advance()
            expr = self._parse_expr()
            self._expect("PUNCTUATION", ")")
            return expr

        raise self._error("Expected a number, string, NULL, identifier, or '('", token)

    def _parse_function_call_expr(self, name_token: dict) -> dict:
        """`name(arg1, arg2, ...)` as an expression -- see the module
        docstring's "Function calls in expressions" section. Called from
        `_parse_primary` once it's already peeked a `(` right after an
        IDENTIFIER; `name_token` is that already-consumed IDENTIFIER
        token. Same argument-list grammar as `_parse_call`'s
        CallStatement (any expression is syntactically valid here --
        app.interpreter is what later requires the target to actually be
        a FunctionNode with a matching parameter count)."""
        self._expect("PUNCTUATION", "(")
        args: list[dict] = []
        if not self._check("PUNCTUATION", ")"):
            args.append(self._parse_expr())
            while self._match("PUNCTUATION", ","):
                args.append(self._parse_expr())
        self._expect("PUNCTUATION", ")")
        return {
            "type": "FunctionCallExpr",
            "name": name_token["value"],
            "args": args,
            "line": name_token["line"],
        }


# -- raw query reconstruction (for cursor declarations) ----------------------


def _render_raw_query(tokens: list[dict]) -> str:
    """Reassemble a run of raw tokens (captured verbatim between CURSOR
    FOR and the closing ';') back into a single SQL string to hand to
    the SQLite driver at OPEN time.

    Round-trips every case this grammar's own tokenizer understands
    (SELECT ... FROM ... WHERE col = / > / < / != / >= / <= / <>
    value/'string') -- every comparison operator lexes as exactly one
    OPERATOR token carrying its full text (see app.tokenizer), so
    reassembly never splits a two-character operator across two tokens.
    """
    parts: list[str] = []
    for token in tokens:
        if token["value"] == "," and parts:
            parts[-1] += ","  # attach directly to the previous token
        else:
            parts.append(token["value"])
    return " ".join(parts)


def _is_definition_start(parser: Parser) -> bool:
    """Whether the parser is sitting on the start of a chainable
    `CREATE PROCEDURE`/`CREATE FUNCTION` definition -- see the module
    docstring's "SQL passthrough statements" section's "Top-level
    dispatch note" for why this is no longer just "peek at a bare CREATE": a
    `CREATE TABLE` statement (or any other `CREATE ...`) must fall
    through to the ordinary bare statement-list grammar instead."""
    if not parser._check("KEYWORD", "CREATE"):
        return False
    following = parser.tokens[parser.pos + 1] if parser.pos + 1 < len(parser.tokens) else None
    return (
        following is not None
        and following["type"] == "KEYWORD"
        and following["value"].upper() in ("PROCEDURE", "FUNCTION")
    )


def _parse_one_definition(parser: Parser) -> dict:
    """Parse exactly one CREATE PROCEDURE/CREATE FUNCTION definition
    starting at the parser's current position (which must be sitting on
    a CREATE token) -- factored out of `parse()` so it can be called
    once for the common single-definition case or repeatedly for a
    chained multi-procedure source (see the module docstring's "CALL
    and multi-procedure sources" section)."""
    following = parser.tokens[parser.pos + 1] if parser.pos + 1 < len(parser.tokens) else None
    if following is not None and following["type"] == "KEYWORD" and following["value"].upper() == "PROCEDURE":
        return parser.parse_procedure_def()
    if following is not None and following["type"] == "KEYWORD" and following["value"].upper() == "FUNCTION":
        return parser.parse_function_def()
    raise parser._error("Expected FUNCTION or PROCEDURE after CREATE", following)


def parse(tokens: list[dict]) -> dict:
    """Parse a full token list into a Procedure, ProcedureNode,
    FunctionNode, or (multi-procedure source) ProgramNode AST.

    Dispatches by peeking at the first one or two tokens: a leading
    ``CREATE PROCEDURE`` parses a full ``CREATE PROCEDURE ... BEGIN
    ... END`` definition, a leading ``CREATE FUNCTION`` parses a full
    ``CREATE FUNCTION ... RETURNS ... BEGIN ... END`` definition, and
    anything else (no leading ``CREATE`` at all) falls back to the
    original bare statement-list grammar -- a procedure body typed
    with no wrapper, exactly as every pre-existing sample and every
    History entry saved before ``CREATE PROCEDURE`` support existed
    already does. See the module docstring's "Procedures: two forms"
    section.

    If, after one CREATE definition, another CREATE immediately
    follows, parsing continues -- collecting every chained definition
    -- rather than stopping at the first one. With exactly one
    definition the return value is byte-identical to before this
    existed (a bare ProcedureNode/FunctionNode, not wrapped in
    anything); with two or more, they're wrapped in a ProgramNode. See
    the module docstring's "CALL and multi-procedure sources" section
    for the full convention (the LAST definition is the entry point;
    every definition is registered by name for CALL to find).

    Args:
        tokens: the token list produced by ``app.tokenizer.tokenize``.

    Returns:
        One of:
          - ``{"type": "Procedure", "body": [...]}`` (bare form)
          - ``{"type": "ProcedureNode", "name", "params", "body"}``
            (wrapped form, alone)
          - ``{"type": "FunctionNode", "name", "params", "returnType",
            "body"}`` (alone)
          - ``{"type": "ProgramNode", "definitions": [...], "line"}``
            (two or more CREATE definitions chained together)

    Raises:
        ParserError: if the tokens don't match the supported grammar,
            including a ``CREATE`` followed by neither ``FUNCTION`` nor
            ``PROCEDURE``.
    """
    parser = Parser(tokens)
    if _is_definition_start(parser):
        # Only the FIRST token decides whether this source is a
        # definition-chain at all (vs. falling through to the ordinary
        # bare statement-list grammar below, where a `CREATE TABLE`
        # dispatches as an ordinary statement instead -- see the module
        # docstring's "SQL passthrough statements" section). Once we're
        # genuinely inside a chain, every SUBSEQUENT leading `CREATE`
        # still unconditionally means "another PROCEDURE/FUNCTION
        # definition follows" -- `_parse_one_definition` itself raises a
        # clear error otherwise (e.g. a stray `CREATE TABLE ...;` between
        # two chained definitions, which is not supported syntax -- see
        # that same docstring section) rather than silently stopping the
        # chain and leaving unparsed tokens behind.
        definitions = [_parse_one_definition(parser)]
        while parser._check("KEYWORD", "CREATE"):
            definitions.append(_parse_one_definition(parser))
        if len(definitions) == 1:
            return definitions[0]
        return {
            "type": "ProgramNode",
            "definitions": definitions,
            "line": definitions[0]["line"],
        }
    return parser.parse_procedure()
