"""Tree-walking interpreter for the AST produced by :mod:`app.parser`.

Executes a ProcedureNode statement by statement against a variable
scope, and after *every* statement emits a :class:`DebugStep` — a
snapshot of "what just happened" that a frontend debugger UI can step
through one at a time.

Entry point::

    run(ast, initial_params) -> list[DebugStep]

Each DebugStep captures:
    stepNumber      -- 1-based order of execution
    line            -- source line the executed statement started on
    nodeType        -- AST node type that produced this step
    statementText   -- the statement rendered back to readable source
    variables       -- {name: {value, type, changed}} for every
                       variable currently in scope
    branch          -- for IfStatement steps only: {condition,
                       result, path} describing which way the branch
                       went; None for every other step

WhileStatement gets the same per-statement step treatment, plus one
extra step per loop-condition check carrying an analogous `loop`
object ({condition, result, iteration}) -- not part of the original
spec (which only calls out IfNode), but a natural extension so a
WHILE loop is traceable the same way an IF is. To keep runaway
procedures from hanging the interpreter, loops are capped at
MAX_LOOP_ITERATIONS.

-- Cursors ------------------------------------------------------------

CursorDeclNode / OpenCursorNode / FetchCursorNode / CloseCursorNode
(see app.parser) are executed against a real ``sqlite3.Connection`` --
by default a private in-memory one the Interpreter creates for itself,
or one the caller supplies (e.g. a test that has pre-seeded a table).
There is no schema-authoring feature yet, so a cursor's query against
the default connection will simply fail with SQLite's own "no such
table" error at OPEN time -- a deliberate, documented scope boundary,
not a bug.

Cursor state lives in ``Interpreter.cursors`` (keyed by cursor name),
kept entirely separate from ``self.scope``: cursors aren't SQL
variables and never appear in a DebugStep's `variables` snapshot or
the frontend's variable watch table. Each DebugStep for a cursor
statement instead carries a `cursor` object -- see DebugStep.to_dict.

OPEN eagerly runs the query and buffers every row (simplest possible
correct behavior for the small result sets this debugger deals with;
a real driver would stream). FETCH walks that buffered list one row
at a time; running past the end does not raise -- it's recorded as a
normal DebugStep with `cursor.hasMore = False` and no assignment to
the target variables, exactly like a real FETCH exhausting a cursor.

`cur%FOUND` and `cur%NOTFOUND` are NOT simple negations of each other
here, on purpose -- they're read predictively vs. retrospectively to
match how each is actually used idiomatically:

  - %FOUND is *predictive*: "is there a row ready for the next FETCH
    right now" (same value as `cursor.hasMore`). This is what makes
    `WHILE cur%FOUND DO ... FETCH ... END WHILE` work as an ordinary
    WHILE-checks-then-runs loop -- checked *before* each FETCH.
  - %NOTFOUND is *retrospective*: "did the most recently completed
    FETCH fail to find a row". This is what makes the
    `FETCH ...; IF cur%NOTFOUND THEN SET done = 1; ...` fallback
    pattern work -- checked *after* a FETCH, inside the loop body.

Deriving %NOTFOUND as `not %FOUND` would misfire: a FETCH that just
found the very last real row leaves nothing for *next* time, so
predictive %FOUND is already false, and `not %FOUND` would wrongly
read as "that FETCH failed" when it just succeeded. So each cursor
tracks its last FETCH's own outcome (`last_fetch_found`) separately
from its position, and %NOTFOUND reads that instead.

-- Exception handlers ---------------------------------------------------

`DECLARE CONTINUE HANDLER FOR NOT_FOUND <stmt>` and
`DECLARE CONTINUE HANDLER FOR DIVISION_BY_ZERO <stmt>` (see app.parser)
register a single statement to auto-run when that condition is
triggered. Handlers are procedure-scoped and registered in
``Interpreter.handlers`` (condition -> action AST) the moment their
DECLARE actually executes -- see app.parser's module docstring for why
there's no block scoping here.

When a condition triggers, the *triggering* statement's own DebugStep
always gets an `error` field: ``{condition, message, handler}``, where
`handler` names the registered handler or is the literal string
``"unhandled"``. If a handler *is* registered, its action statement runs
immediately after, as its own separate DebugStep -- so the trace reads
"the thing that failed" followed by "the handler responding to it".

The two conditions are NOT symmetric in how a missing handler behaves,
and that asymmetry is deliberate:

  - NOT_FOUND is always non-fatal, handled or not (this was already
    true before handlers existed at all -- a FETCH running past the
    end of a cursor was never a Python-level error, see "Cursors"
    above). An unhandled NOT_FOUND is fully visible in a live trace
    with `error.handler == "unhandled"`.
  - DIVISION_BY_ZERO keeps its pre-existing behavior when unhandled: it
    still raises InterpreterError and aborts the run, exactly as it did
    before handlers existed (so existing procedures that rely on a
    division mistake being loudly fatal keep working). It only becomes
    non-fatal -- recorded on the triggering step, target assignment
    skipped, handler action runs next -- once a
    `DECLARE CONTINUE HANDLER FOR DIVISION_BY_ZERO` is actually
    registered. Because of this, `error.handler == "unhandled"` for
    DIVISION_BY_ZERO is only ever a theoretical value (the interpreter
    raises before that step could be returned to a caller); the
    frontend still renders it correctly for consistency and in case a
    future caller wants a partial trace.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field

MAX_LOOP_ITERATIONS = 10_000


class InterpreterError(RuntimeError):
    """Raised for runtime errors while executing the AST (undefined
    variable, division by zero, a runaway loop, ...)."""

    def __init__(self, message: str, line: int | None = None):
        if line is not None:
            message = f"{message} (line {line})"
        super().__init__(message)
        self.line = line


class _DivisionByZeroSignal(Exception):
    """Internal control-flow signal, never surfaced to callers: raised
    by `_evaluate_binary` on a `/` by zero, and caught at each
    top-level statement boundary (_exec_declare, _exec_set, _exec_if,
    _exec_while) so that boundary can decide -- per the module
    docstring's "Exception handlers" section -- whether a registered
    CONTINUE HANDLER makes this non-fatal, or whether it should still
    become the ordinary, procedure-aborting InterpreterError it always
    was before handlers existed."""

    def __init__(self, line: int | None):
        super().__init__("Division by zero")
        self.line = line


_HANDLER_LABELS = {
    "NOT_FOUND": "NOT_FOUND handler",
    "DIVISION_BY_ZERO": "DIVISION_BY_ZERO handler",
}


@dataclass
class DebugStep:
    step_number: int
    line: int
    node_type: str
    statement_text: str
    variables: dict
    branch: dict | None = None
    loop: dict | None = None
    cursor: dict | None = None
    error: dict | None = None

    def to_dict(self) -> dict:
        """Serialize using the camelCase keys the frontend expects."""
        step = {
            "stepNumber": self.step_number,
            "line": self.line,
            "nodeType": self.node_type,
            "statementText": self.statement_text,
            "variables": self.variables,
        }
        if self.branch is not None:
            step["branch"] = self.branch
        if self.loop is not None:
            step["loop"] = self.loop
        if self.cursor is not None:
            step["cursor"] = self.cursor
        if self.error is not None:
            step["error"] = self.error
        return step


# -- rendering AST nodes back to readable source text ------------------------

_BINARY_OPERATOR_TEXT = {"+", "-", "*", "/", ">", "<", "=", "!="}


def render_expr(node: dict) -> str:
    """Render an expression node back into SQL-ish source text."""
    kind = node["type"]
    if kind == "NumberLiteral":
        return str(node["value"])
    if kind == "StringLiteral":
        return f"'{node['value']}'"
    if kind == "Identifier":
        return node["name"]
    if kind == "UnaryExpr":
        return f"{node['operator']}{render_expr(node['operand'])}"
    if kind == "BinaryExpr":
        return (
            f"{render_expr(node['left'])} {node['operator']} "
            f"{render_expr(node['right'])}"
        )
    if kind == "CursorFoundExpr":
        return f"{node['cursor']}%FOUND"
    if kind == "CursorNotFoundExpr":
        return f"{node['cursor']}%NOTFOUND"
    raise InterpreterError(f"Cannot render unknown expression node {kind!r}")


def render_statement_header(node: dict) -> str:
    """Render just the statement's own line (no nested block body)."""
    kind = node["type"]
    if kind == "DeclareStatement":
        text = f"DECLARE {node['name']} {node['var_type']}"
        if node["default"] is not None:
            text += f" DEFAULT {render_expr(node['default'])}"
        return text + ";"
    if kind == "SetStatement":
        return f"SET {node['target']} = {render_expr(node['value'])};"
    if kind == "IfStatement":
        return f"IF {render_expr(node['condition'])} THEN"
    if kind == "WhileStatement":
        return f"WHILE {render_expr(node['condition'])} DO"
    if kind == "CursorDeclNode":
        return f"DECLARE {node['name']} CURSOR FOR {node['query']};"
    if kind == "OpenCursorNode":
        return f"OPEN {node['name']};"
    if kind == "FetchCursorNode":
        return f"FETCH {node['name']} INTO {', '.join(node['targets'])};"
    if kind == "CloseCursorNode":
        return f"CLOSE {node['name']};"
    if kind == "HandlerDeclNode":
        # render_statement_header(action) already ends in ';' -- no
        # extra trailing punctuation needed here.
        return f"DECLARE CONTINUE HANDLER FOR {node['condition']} {render_statement_header(node['action'])}"
    raise InterpreterError(f"Cannot render unknown statement node {kind!r}")


# -- value <-> debugger type name ---------------------------------------------


def _type_name(value) -> str:
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, (int, float)):
        return "number"
    if isinstance(value, str):
        return "string"
    if value is None:
        return "null"
    return type(value).__name__


class Interpreter:
    def __init__(self, initial_params: dict, db_connection: sqlite3.Connection | None = None):
        self.scope: dict = dict(initial_params)
        self.steps: list[DebugStep] = []
        self._step_number = 0
        # Baseline for diffing "changed": start from the params as given,
        # so a param that's never touched shows changed=False throughout.
        self._previous_values: dict = dict(initial_params)

        # Cursors, keyed by name -- deliberately separate from `scope`
        # (see module docstring's "Cursors" section). Each entry:
        # {"query": str, "rows": [dict, ...], "pos": int, "open": bool}.
        self.cursors: dict[str, dict] = {}

        # Exception handlers, keyed by condition ("NOT_FOUND" or
        # "DIVISION_BY_ZERO") -> that handler's action statement AST.
        # See module docstring's "Exception handlers" section.
        self.handlers: dict[str, dict] = {}

        # Own a private in-memory connection unless the caller supplies
        # one (e.g. a test that pre-seeded a table) -- closed again in
        # the module-level `run()` below, only if we're the ones who
        # opened it.
        self._db = db_connection if db_connection is not None else sqlite3.connect(":memory:")
        self._owns_db = db_connection is None

    # -- public API -----------------------------------------------------------

    def run(self, body: list[dict]) -> list[DebugStep]:
        self._execute_block(body)
        return self.steps

    # -- statement execution ----------------------------------------------

    def _execute_block(self, statements: list[dict]) -> None:
        for statement in statements:
            self._execute_statement(statement)

    def _execute_statement(self, node: dict) -> None:
        kind = node["type"]
        if kind == "DeclareStatement":
            self._exec_declare(node)
        elif kind == "SetStatement":
            self._exec_set(node)
        elif kind == "IfStatement":
            self._exec_if(node)
        elif kind == "WhileStatement":
            self._exec_while(node)
        elif kind == "CursorDeclNode":
            self._exec_declare_cursor(node)
        elif kind == "OpenCursorNode":
            self._exec_open_cursor(node)
        elif kind == "FetchCursorNode":
            self._exec_fetch_cursor(node)
        elif kind == "CloseCursorNode":
            self._exec_close_cursor(node)
        elif kind == "HandlerDeclNode":
            self._exec_declare_handler(node)
        else:
            raise InterpreterError(
                f"Don't know how to execute node type {kind!r}", node.get("line")
            )

    def _exec_declare(self, node: dict) -> None:
        value = None
        error_info = None
        if node["default"] is not None:
            try:
                value = self._evaluate(node["default"])
            except _DivisionByZeroSignal as signal:
                error_info = self._handle_division_by_zero(signal)
        self.scope[node["name"]] = value
        self._record_step(node, render_statement_header(node), error=error_info)
        self._run_handler_if_triggered(error_info)

    def _exec_set(self, node: dict) -> None:
        target = node["target"]
        if target not in self.scope:
            raise InterpreterError(
                f"Variable '{target}' is not declared", node["line"]
            )
        error_info = None
        try:
            self.scope[target] = self._evaluate(node["value"])
        except _DivisionByZeroSignal as signal:
            # Target keeps its previous value -- the assignment simply
            # didn't happen, same as the expression never completing.
            error_info = self._handle_division_by_zero(signal)
        self._record_step(node, render_statement_header(node), error=error_info)
        self._run_handler_if_triggered(error_info)

    def _exec_if(self, node: dict) -> None:
        error_info = None
        try:
            condition_value = self._evaluate(node["condition"])
            result = bool(condition_value)
        except _DivisionByZeroSignal as signal:
            error_info = self._handle_division_by_zero(signal)
            result = False  # condition couldn't be evaluated -- don't guess a branch

        if result:
            path = "then"
        elif node["else_body"] is not None:
            path = "else"
        else:
            path = "none"

        branch = {
            "condition": render_expr(node["condition"]),
            "result": result,
            "path": path,
        }
        self._record_step(node, render_statement_header(node), branch=branch, error=error_info)
        self._run_handler_if_triggered(error_info)

        if result:
            self._execute_block(node["then_body"])
        elif node["else_body"] is not None:
            self._execute_block(node["else_body"])

    def _exec_while(self, node: dict) -> None:
        iteration = 0
        while True:
            error_info = None
            try:
                condition_value = self._evaluate(node["condition"])
                result = bool(condition_value)
            except _DivisionByZeroSignal as signal:
                error_info = self._handle_division_by_zero(signal)
                result = False  # can't evaluate the condition -- exit rather than spin

            iteration += 1
            if iteration > MAX_LOOP_ITERATIONS:
                raise InterpreterError(
                    f"WHILE loop exceeded {MAX_LOOP_ITERATIONS} iterations "
                    "(possible infinite loop)",
                    node["line"],
                )

            loop = {
                "condition": render_expr(node["condition"]),
                "result": result,
                "iteration": iteration,
            }
            self._record_step(node, render_statement_header(node), loop=loop, error=error_info)
            self._run_handler_if_triggered(error_info)

            if not result:
                break
            self._execute_block(node["body"])

    # -- exception handlers -----------------------------------------------

    def _exec_declare_handler(self, node: dict) -> None:
        condition = node["condition"]
        if condition in self.handlers:
            raise InterpreterError(
                f"A CONTINUE HANDLER FOR {condition} is already declared", node["line"]
            )
        self.handlers[condition] = node["action"]
        self._record_step(node, render_statement_header(node))

    def _condition_error_info(self, condition: str, message: str) -> dict:
        """Build the `error` dict for a triggered condition. Does NOT
        run the handler itself -- see `_run_handler_if_triggered`,
        called separately (and later) so the *triggering* statement's
        own DebugStep is recorded before the handler action's step."""
        handler = self.handlers.get(condition)
        label = _HANDLER_LABELS[condition] if handler is not None else "unhandled"
        return {"condition": condition, "message": message, "handler": label}

    def _handle_division_by_zero(self, signal: "_DivisionByZeroSignal") -> dict:
        """Build DIVISION_BY_ZERO's `error` info, or re-raise as the
        ordinary, procedure-aborting InterpreterError it always was
        before handlers existed if nothing is registered to catch it
        (see module docstring's "Exception handlers" section for why
        this differs from NOT_FOUND, which is unconditionally
        non-fatal)."""
        error_info = self._condition_error_info("DIVISION_BY_ZERO", "Division by zero")
        if error_info["handler"] == "unhandled":
            raise InterpreterError("Division by zero", signal.line) from signal
        return error_info

    def _run_handler_if_triggered(self, error_info: dict | None) -> None:
        """After the triggering statement's own DebugStep has been
        recorded, actually run the registered handler's action (as its
        own subsequent DebugStep). No-op if nothing triggered, or if
        what triggered was unhandled."""
        if error_info is None:
            return
        action = self.handlers.get(error_info["condition"])
        if action is not None:
            self._execute_statement(action)

    # -- cursors --------------------------------------------------------------

    def _require_cursor(self, name: str, line: int | None) -> dict:
        state = self.cursors.get(name)
        if state is None:
            raise InterpreterError(f"Cursor '{name}' is not declared", line)
        return state

    def _cursor_has_more(self, name: str, line: int | None) -> bool:
        """Whether `name`'s cursor is open and has a row ready to FETCH
        right now. Backs the DebugStep `cursor.hasMore` field and the
        *predictive* %FOUND expression -- see the module docstring for
        why %FOUND means this rather than Oracle's retrospective "did
        the last FETCH succeed"."""
        state = self._require_cursor(name, line)
        return state["open"] and state["pos"] < len(state["rows"])

    def _cursor_last_fetch_not_found(self, name: str, line: int | None) -> bool:
        """Whether `name`'s most recently completed FETCH found no row.

        Deliberately NOT `not _cursor_has_more(...)`: %FOUND is
        predictive (checked *before* a FETCH, in a WHILE condition) but
        %NOTFOUND is retrospective (checked *after* a FETCH, inside the
        loop body -- see CURSOR_EXPLICIT_FLAG_PROCEDURE-style tests).
        Treating them as simple negations of each other would make a
        FETCH that just found the very last real row report %NOTFOUND
        as true (nothing is left for *next* time), which is wrong --
        that FETCH succeeded. So this tracks the last FETCH's own
        outcome directly instead of deriving it from `pos`."""
        state = self._require_cursor(name, line)
        return state["last_fetch_found"] is False

    def _exec_declare_cursor(self, node: dict) -> None:
        name = node["name"]
        if name in self.cursors:
            raise InterpreterError(f"Cursor '{name}' is already declared", node["line"])
        self.cursors[name] = {
            "query": node["query"],
            "rows": [],
            "pos": 0,
            "open": False,
            "last_fetch_found": None,  # None = no FETCH has run yet
        }
        cursor_info = {"name": name, "currentRow": None, "rowIndex": 0, "hasMore": False}
        self._record_step(node, render_statement_header(node), cursor=cursor_info)

    def _exec_open_cursor(self, node: dict) -> None:
        name = node["name"]
        state = self._require_cursor(name, node["line"])
        if state["open"]:
            raise InterpreterError(f"Cursor '{name}' is already open", node["line"])

        try:
            db_cursor = self._db.execute(state["query"])
            columns = [d[0] for d in db_cursor.description] if db_cursor.description else []
            rows = [dict(zip(columns, row)) for row in db_cursor.fetchall()]
        except sqlite3.Error as exc:
            raise InterpreterError(f"Cursor '{name}' query failed: {exc}", node["line"]) from exc

        state["rows"] = rows
        state["pos"] = 0
        state["open"] = True
        state["last_fetch_found"] = None  # reset: no FETCH since this OPEN yet
        cursor_info = {"name": name, "currentRow": None, "rowIndex": 0, "hasMore": len(rows) > 0}
        self._record_step(node, render_statement_header(node), cursor=cursor_info)

    def _exec_fetch_cursor(self, node: dict) -> None:
        name = node["name"]
        state = self._require_cursor(name, node["line"])
        if not state["open"]:
            raise InterpreterError(f"Cursor '{name}' is not open", node["line"])

        targets = node["targets"]
        rows = state["rows"]
        pos = state["pos"]
        error_info = None

        if pos < len(rows):
            row = rows[pos]
            values = list(row.values())
            if len(values) != len(targets):
                raise InterpreterError(
                    f"Cursor '{name}' returns {len(values)} column(s) but "
                    f"FETCH names {len(targets)} target variable(s)",
                    node["line"],
                )
            for target, value in zip(targets, values):
                if target not in self.scope:
                    raise InterpreterError(f"Variable '{target}' is not declared", node["line"])
                self.scope[target] = value

            state["pos"] = pos + 1
            state["last_fetch_found"] = True
            cursor_info = {
                "name": name,
                "currentRow": row,
                "rowIndex": pos,
                "hasMore": state["pos"] < len(rows),
            }
        else:
            # Exhausted -- NOT a Python exception. Recorded as an
            # ordinary DebugStep with hasMore=False and no target
            # assignment, same as a real driver's FETCH-past-the-end.
            # NOT_FOUND is unconditionally non-fatal (unlike
            # DIVISION_BY_ZERO) -- see module docstring.
            state["last_fetch_found"] = False
            cursor_info = {"name": name, "currentRow": None, "rowIndex": pos, "hasMore": False}
            error_info = self._condition_error_info(
                "NOT_FOUND", f"Cursor '{name}' has no more rows to fetch"
            )

        self._record_step(node, render_statement_header(node), cursor=cursor_info, error=error_info)
        self._run_handler_if_triggered(error_info)

    def _exec_close_cursor(self, node: dict) -> None:
        name = node["name"]
        state = self._require_cursor(name, node["line"])
        if not state["open"]:
            raise InterpreterError(f"Cursor '{name}' is not open", node["line"])

        state["open"] = False
        cursor_info = {"name": name, "currentRow": None, "rowIndex": state["pos"], "hasMore": False}
        self._record_step(node, render_statement_header(node), cursor=cursor_info)

    # -- expression evaluation ----------------------------------------------

    def _evaluate(self, node: dict):
        kind = node["type"]
        if kind == "NumberLiteral":
            return node["value"]
        if kind == "StringLiteral":
            return node["value"]
        if kind == "Identifier":
            name = node["name"]
            if name not in self.scope:
                raise InterpreterError(
                    f"Variable '{name}' is not declared", node["line"]
                )
            return self.scope[name]
        if kind == "UnaryExpr":
            operand = self._evaluate(node["operand"])
            if node["operator"] == "-":
                return -operand
            raise InterpreterError(
                f"Unknown unary operator {node['operator']!r}", node["line"]
            )
        if kind == "BinaryExpr":
            return self._evaluate_binary(node)
        if kind == "CursorFoundExpr":
            return self._cursor_has_more(node["cursor"], node.get("line"))
        if kind == "CursorNotFoundExpr":
            return self._cursor_last_fetch_not_found(node["cursor"], node.get("line"))
        raise InterpreterError(
            f"Cannot evaluate unknown expression node {kind!r}", node.get("line")
        )

    def _evaluate_binary(self, node: dict):
        left = self._evaluate(node["left"])
        right = self._evaluate(node["right"])
        op = node["operator"]
        line = node["line"]

        if op == "+":
            return left + right
        if op == "-":
            return left - right
        if op == "*":
            return left * right
        if op == "/":
            if right == 0:
                # Not raised as InterpreterError directly -- caught at
                # the enclosing statement boundary, which decides (via
                # _handle_division_by_zero) whether a registered
                # CONTINUE HANDLER makes this non-fatal. See module
                # docstring's "Exception handlers" section.
                raise _DivisionByZeroSignal(line)
            return left / right
        if op == ">":
            return left > right
        if op == "<":
            return left < right
        if op == "=":
            return left == right
        if op == "!=":
            return left != right
        raise InterpreterError(f"Unknown operator {op!r}", line)

    # -- DebugStep recording ----------------------------------------------

    def _snapshot_variables(self) -> dict:
        snapshot = {}
        for name, value in self.scope.items():
            previous = self._previous_values.get(name, _UNSET)
            snapshot[name] = {
                "value": value,
                "type": _type_name(value),
                "changed": previous is _UNSET or previous != value,
            }
        self._previous_values = dict(self.scope)
        return snapshot

    def _record_step(
        self,
        node: dict,
        statement_text: str,
        branch: dict | None = None,
        loop: dict | None = None,
        cursor: dict | None = None,
        error: dict | None = None,
    ) -> DebugStep:
        self._step_number += 1
        step = DebugStep(
            step_number=self._step_number,
            line=node["line"],
            node_type=node["type"],
            statement_text=statement_text,
            variables=self._snapshot_variables(),
            branch=branch,
            loop=loop,
            cursor=cursor,
            error=error,
        )
        self.steps.append(step)
        return step


_UNSET = object()


def run(
    ast: dict,
    initial_params: dict | None = None,
    db_connection: sqlite3.Connection | None = None,
) -> list[DebugStep]:
    """Execute a ProcedureNode AST and return its full DebugStep trace.

    Args:
        ast: the ``{"type": "Procedure", "body": [...]}`` root produced
            by ``app.parser.parse``.
        initial_params: starting values for the procedure's input
            parameters (e.g. ``{"price": 20, "quantity": 6}``).
        db_connection: the SQLite connection cursor statements run
            their queries against. Defaults to a fresh, empty
            in-memory database (closed again once this run finishes) --
            pass a pre-seeded connection (e.g. in a test) so OPEN
            actually has a table to query.

    Returns:
        One DebugStep per executed statement (and, for WHILE, one
        extra DebugStep per condition check), in execution order.

    Raises:
        InterpreterError: on undefined variables, an unhandled
            division by zero (see module docstring's "Exception
            handlers" section -- a *handled* one does not raise), a
            WHILE loop that exceeds MAX_LOOP_ITERATIONS, a cursor error
            (undeclared/already-open/not-open cursor, a query that
            fails against the database, or a FETCH whose target count
            doesn't match the query's column count), or a duplicate
            CONTINUE HANDLER for the same condition. NOT_FOUND never
            raises -- see "Cursors" above.
    """
    interpreter = Interpreter(initial_params or {}, db_connection=db_connection)
    try:
        return interpreter.run(ast["body"])
    finally:
        if interpreter._owns_db:
            interpreter._db.close()
