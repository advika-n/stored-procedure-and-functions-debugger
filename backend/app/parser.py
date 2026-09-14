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
                    | set_stmt | if_stmt | while_stmt | return_stmt
                    | open_cursor_stmt | fetch_cursor_stmt | close_cursor_stmt
                    | call_stmt

    declare_stmt        := DECLARE IDENT IDENT (DEFAULT expr)? ';'
    declare_cursor_stmt := DECLARE IDENT CURSOR FOR <raw tokens up to ';'> ';'
    declare_handler_stmt := DECLARE CONTINUE HANDLER FOR
                             (NOT_FOUND | DIVISION_BY_ZERO) statement
    set_stmt             := SET IDENT '=' expr ';'
    if_stmt      := IF expr THEN statement*
                     (ELSE statement*)?
                     END IF ';'
    while_stmt   := WHILE expr DO statement* END WHILE ';'
    return_stmt  := RETURN expr ';'
    open_cursor_stmt  := OPEN IDENT ';'
    fetch_cursor_stmt := FETCH IDENT INTO IDENT (',' IDENT)* ';'
    close_cursor_stmt := CLOSE IDENT ';'
    call_stmt         := CALL IDENT '(' (expr (',' expr)*)? ')' ';'

    expr         := comparison
    comparison   := term (('>' | '<' | '=' | '!=') term)*
    term         := factor (('+' | '-') factor)*
    factor       := unary (('*' | '/') unary)*
    unary        := '-' unary | primary
    primary      := NUMBER | STRING | function_call_expr
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

-- Cursors -----------------------------------------------------------------

A cursor declaration's embedded SELECT is *not* parsed into its own AST:
the tokens between FOR and the closing ';' are captured verbatim and
reassembled into a single SQL string (CursorDeclNode.query), which
app.interpreter hands straight to SQLite when the cursor is OPENed. This
means only single-character comparison operators from this grammar's own
token set round-trip correctly inside an embedded WHERE clause (=, >, <,
!=) -- multi-character SQL operators this tokenizer doesn't know as a
single token (<=, >=, <>) will NOT reconstruct correctly, since they'd be
captured as two separate tokens with a space forced between them.

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

COMPARISON_OPERATORS = {">", "<", "=", "!="}
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

        raise self._error(
            "Expected DECLARE, SET, IF, WHILE, RETURN, OPEN, FETCH, CLOSE, or CALL", token
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

        raise self._error("Expected a number, string, identifier, or '('", token)

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

    Good enough to round-trip the common cases this grammar's own
    tokenizer already understands (SELECT ... FROM ... WHERE col = /
    > / < / != value/'string'); see the module docstring for what does
    NOT round-trip cleanly (<=, >=, <>).
    """
    parts: list[str] = []
    for token in tokens:
        if token["value"] == "," and parts:
            parts[-1] += ","  # attach directly to the previous token
        else:
            parts.append(token["value"])
    return " ".join(parts)


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
    if parser._check("KEYWORD", "CREATE"):
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
