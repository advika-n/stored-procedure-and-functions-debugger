"""SQL Anti-Pattern Advisor -- a static, linter-style pass over the
already-parsed AST (see app.parser), never the interpreter's execution
trace. Every check below only reads the AST `app.parser.parse()` already
produces -- no new parsing/tokenizing of its own, and no dependency on
whether the procedure actually runs successfully afterward, so issues
can in principle be surfaced the moment a procedure parses, before (or
even instead of) running it.

Trigger point actually chosen (see main.py's `/debug` handler): analysis
runs automatically as part of every successful `/debug` call, reusing
the exact `ast` that call already builds, rather than a separate
"Analyze" button/endpoint -- one request already parses the code and
already needs to hand `ast` back to the frontend for the flowchart, so
adding `issues` alongside it is a free, zero-extra-round-trip addition
instead of a second network call for something the backend already
computed the input for.

-- Detected anti-patterns (six) -----------------------------------------

  1. select-star             -- SELECT * in a cursor's embedded query
  2. cursor-could-be-set-based -- a cursor loop whose body only
     accumulates a running total/count, better expressed as one
     aggregate query (SUM/COUNT/...). Deliberately still WHILE-only,
     not extended to a LOOP-based cursor loop (see "LOOP / LEAVE" --
     added in a later phase than this check): a LOOP-based cursor loop
     idiomatically exits via `FETCH ...; IF cur%NOTFOUND THEN LEAVE;
     END IF;` rather than a %FOUND-guarded WHILE condition, which is a
     genuinely different shape this check's own accumulator-detection
     logic doesn't currently recognize -- a real, separate piece of
     work, not a natural one-line extension of what already exists for
     WHILE (unlike `nested-loops`/`missing-error-handling` below, which
     needed LOOP support just to keep seeing INTO a LOOP's body at all,
     this check still sees everything inside a LOOP correctly; it just
     doesn't recognize LOOP itself as a candidate loop shape yet).
  3. nested-loops             -- a WHILE or LOOP nested inside another
     WHILE or LOOP (O(n^2) row-by-row risk) -- LOOP support (see "LOOP /
     LEAVE" below) generalized this from WHILE-only the moment a second
     loop construct existed, since the risk this check warns about has
     nothing to do with which loop keyword was used.
  4. missing-error-handling   -- two sub-cases, deliberately NOT treated
     as equally severe (see interpreter.py's module docstring's
     "Exception handlers" section for why they're asymmetric there too):
       a. a division with no DECLARE CONTINUE HANDLER FOR
          DIVISION_BY_ZERO anywhere in scope -- flagged as a "warning"
          because an unhandled DIVISION_BY_ZERO genuinely aborts the run.
       b. a cursor FETCH that is neither guarded by a preceding
          `cursor%FOUND` loop check nor backed by a DECLARE CONTINUE
          HANDLER FOR NOT_FOUND -- flagged only as a "suggestion",
          because this interpreter treats an unhandled NOT_FOUND as
          always non-fatal (it never actually stops the procedure); the
          issue is trace clarity ("why does this step show an error?"),
          not a real crash risk. A FETCH guarded by a %FOUND loop
          condition (see ProductPriceTotal in samples.js) is NOT flagged
          at all -- that predictive-%FOUND idiom is exactly the correct,
          safe alternative to a handler, not a missing one. A FETCH
          inside a LOOP (see "LOOP / LEAVE" below) is still correctly
          seen by this check (LOOP has no condition to guard with
          %FOUND, so `guarded_cursors` just passes through unchanged --
          see `_find_unguarded_fetch`'s own LoopStatement case), but a
          LOOP's own idiomatic retrospective guard (`FETCH ...; IF
          cur%NOTFOUND THEN LEAVE; END IF;`) is NOT recognized as a
          guard here -- a deliberate, documented scope boundary, not a
          bug (see item 2's own note above for the fuller reasoning).
  5. magic-number             -- the same non-trivial numeric literal
     (i.e. not 0 or 1) hard-coded more than once
  6. cursor-not-closed        -- an OPENed cursor with no matching CLOSE
     anywhere in the procedure

-- Extended static analysis warnings (three more, added in a later phase) --

  7. unreachable-code        -- two distinct, purely AST-provable
     sub-cases, both severity "warning" (dead code is a correctness
     smell, not just a style nit):
       a. any statement positionally after an unconditional exit --
          RETURN or LEAVE (see app.parser's "LOOP / LEAVE" section,
          added in a later phase than this check's original RETURN-only
          form) -- within the SAME statement list (see
          `_iter_statement_lists`). Both unconditionally unwind
          execution the instant they run (see interpreter.py's
          "Functions" section for RETURN, and its own "LOOP / LEAVE"
          section for LEAVE: "no statement after a RETURN ever runs,
          even other statements later in the same block", and the
          equivalent for LEAVE stopping the enclosing loop), regardless
          of whether it's inside a procedure or a function (RETURN) or
          which loop it's leaving (LEAVE), and regardless of whether the
          statement's own enclosing IF/WHILE/CASE is even entered at
          runtime -- the statements are dead *by position*, independent
          of any one run's actual control flow.
       b. an IF whose condition is a compile-time constant (every leaf
          a NumberLiteral, e.g. `IF 1 > 2 THEN ...`) -- one of its two
          arms can then never run no matter what happens elsewhere.
          Deliberately does NOT extend this to WHILE (a
          constant-false WHILE never running is a much rarer, more
          contrived pattern, and this grammar's non-comparison "bare
          value as a condition" and other constant-condition shapes
          multiply the cases fast for little real payoff) -- IF/ELSE
          branch-level dead code is the well-scoped, high-value case.
       c. (added alongside CASE statement support) a SEARCHED CASE's
          WHEN whose own condition is a compile-time constant -- a
          constant-false WHEN's own body can never run; a constant-true
          WHEN always matches first, so every WHEN/ELSE after it can
          never run either. Deliberately scoped to searched CASE only
          (`operand is None`) -- folding a SIMPLE CASE's `operand =
          value` equality would need `_fold_constant` to also handle
          STRING literals and non-numeric equality (it currently only
          ever produces a number or a bool from purely numeric/
          comparison expressions), which is a real, separate piece of
          work rather than a natural extension of what already exists
          for IF; left out rather than half-built.
  8. unused-variable          -- a DECLAREd local whose value is never
     read by ANY expression anywhere in the procedure/function (a
     condition, another statement's right-hand side, a RETURN, or a
     CALL argument) -- being assigned one or more times does not count
     as "used" (see `_all_read_names`). Deliberately scoped to
     DECLAREd locals only, not procedure/function parameters: this
     grammar's parameter nodes carry no line number of their own (see
     `app.parser._parse_procedure_param`/`_parse_function_param`), so
     there is no single unambiguous line to point at for "this
     parameter is unused" the way there is for a DECLARE -- a future
     phase could extend this against the procedure/function's own
     header line if that turns out to matter. Severity "suggestion"
     (cleanup, not a runtime risk).
  9. never-read-variable      -- "dead store" detection, related to
     unused-variable but genuinely distinguishable from it in this
     grammar (see the long comment above `_check_never_read_variables`
     for the full reasoning, and the "explicitly NOT implemented"
     section below for what was deliberately left out to keep it
     false-positive-free): a SET assigns a value to a variable, then a
     LATER SET to that same name overwrites it before anything ever
     reads the first value -- the first assignment's work was wasted,
     even though the variable IS read at some other point (which is
     exactly what makes this a different case from "never read at
     all"). Severity "warning" (much likelier to be an actual forgotten
     read than ordinary unused cleanup).

-- User-created tables check (one more, added alongside CREATE TABLE /
   INSERT / UPDATE / DELETE support) ---------------------------------------

  10. missing-where-clause    -- an UPDATE or DELETE with no WHERE clause
      at all, so it unconditionally touches EVERY row currently in the
      table -- a classic footgun (a forgotten WHERE turning a one-row
      fix into a table-wide rewrite/wipe). Severity "warning", same
      tier as `missing-error-handling`'s DIVISION_BY_ZERO case: this is
      a real correctness risk, not just a style nit, though (like every
      other check here) it's a static AST check, not a runtime guess --
      an UPDATE/DELETE with no WHERE is sometimes genuinely intentional
      (e.g. clearing a staging table), so this always fires on the
      *shape* of the statement, with no attempt to infer intent.

-- Explicitly NOT implemented ---------------------------------------------

"Dynamic SQL string concatenation (SQL injection risk pattern)" was one
of the candidates for the original six checks but is NOT implemented:
this grammar has no EXECUTE/EXEC-IMMEDIATE construct and no way to
build a SQL string at runtime and hand it to the database -- every
cursor's query is fixed, literal text captured verbatim at parse time
(see `app.parser._parse_declare_cursor`/`CursorDeclNode`), never
assembled from concatenated variables. There is nothing of that shape
in this language for a check to find, so none was written, rather than
forcing one that could never fire.

For the never-read-variable check specifically, `DECLARE x TYPE DEFAULT
expr;` is deliberately NOT treated as a "first write" the way a SET is,
even though it fits the letter of "written multiple times... before
being overwritten" when immediately followed by a SET to the same name.
`DECLARE total NUMBER DEFAULT 0; SET total = price * quantity;` is the
standard, idiomatic way this grammar initializes a variable right
before computing it -- used throughout this app's own sample library
(CalculateTotal, CalculateDiscount, TieredPricingCalculator, and more).
Treating that pattern as a dead store would fire on a large fraction of
completely normal code; this was verified directly against all 13
built-in samples before settling on SET-to-SET only (see
PROMPT_LOG.md/HANDOFF.md for this phase). The same reasoning excludes a
procedure parameter's own caller-supplied starting value from ever
seeding a "pending write" -- see `_check_never_read_variables`'s own
docstring.
"""

from __future__ import annotations

import re
from collections.abc import Iterator

from app.sql_console import extract_table_name

_SELECT_STAR_RE = re.compile(r"select\s+\*", re.IGNORECASE)
_WHERE_RE = re.compile(r"\bwhere\b", re.IGNORECASE)
_TRIVIAL_NUMBERS = {0, 1}
_ACCUMULATOR_OPERATORS = {"+", "-", "*", "/"}


def _issue(*, category: str, severity: str, title: str, line: int | None, message: str, suggestion: str) -> dict:
    return {
        "category": category,
        "severity": severity,
        "title": title,
        "line": line,
        "message": message,
        "suggestion": suggestion,
    }


# -- generic AST walkers ------------------------------------------------------
# Shared by every check below so each one only states *what* it's looking
# for, not how to descend through IF/WHILE/handler bodies -- see
# app.parser's module docstring for the node shapes these rely on.


def _iter_statements(statements: list[dict]) -> Iterator[dict]:
    """Yield every statement in `statements`, recursively descending into
    IF/WHILE/CASE/LOOP bodies and a handler's single action statement --
    every place this grammar allows a nested statement to appear."""
    for stmt in statements:
        yield stmt
        kind = stmt["type"]
        if kind == "IfStatement":
            yield from _iter_statements(stmt["then_body"])
            if stmt["else_body"] is not None:
                yield from _iter_statements(stmt["else_body"])
        elif kind == "WhileStatement":
            yield from _iter_statements(stmt["body"])
        elif kind == "LoopStatement":
            # LOOP/LEAVE (see app.parser's "LOOP / LEAVE" section --
            # added in a later phase than the six original checks below)
            # -- a LoopStatement's own body is just another nested
            # statement list, exactly like WhileStatement's.
            yield from _iter_statements(stmt["body"])
        elif kind == "CaseStatement":
            # CASE (see app.parser's "CASE statement" section -- added in
            # a later phase than the six original checks below) has N
            # WHEN bodies, not just one then_body, plus an optional
            # else_body -- descend into all of them, same reasoning as
            # IfStatement just above.
            for clause in stmt["when_clauses"]:
                yield from _iter_statements(clause["body"])
            if stmt["else_body"] is not None:
                yield from _iter_statements(stmt["else_body"])
        elif kind == "HandlerDeclNode":
            yield from _iter_statements([stmt["action"]])


def _iter_exprs(node: dict | None) -> Iterator[dict]:
    """Yield `node` and every expression reachable from it."""
    if node is None:
        return
    yield node
    kind = node["type"]
    if kind == "BinaryExpr":
        yield from _iter_exprs(node["left"])
        yield from _iter_exprs(node["right"])
    elif kind == "UnaryExpr":
        yield from _iter_exprs(node["operand"])
    elif kind == "FunctionCallExpr":
        # A FunctionCallExpr (see app.parser's "Function calls in
        # expressions" section -- added in a later phase than the six
        # original checks below) carries its own sub-expressions in
        # `args`, not `left`/`right`/`operand`. Descending into them
        # here, at this single shared low-level walker, is what makes
        # every check built on top of `_iter_exprs`/`_statement_exprs`
        # (magic-number, unused-variable, never-read-variable, ...)
        # correctly see a variable used ONLY as a function-call
        # argument as read/touched, without any of those checks needing
        # their own FunctionCallExpr-specific code.
        for arg in node["args"]:
            yield from _iter_exprs(arg)


def _statement_exprs(stmt: dict) -> Iterator[dict]:
    """Every expression a single statement carries directly (not
    recursing into a nested statement's own body -- combine with
    `_iter_statements` for that, as every check below does)."""
    kind = stmt["type"]
    if kind == "DeclareStatement" and stmt["default"] is not None:
        yield from _iter_exprs(stmt["default"])
    elif kind == "SetStatement":
        yield from _iter_exprs(stmt["value"])
    elif kind in ("IfStatement", "WhileStatement"):
        yield from _iter_exprs(stmt["condition"])
    elif kind == "CaseStatement":
        # The operand (simple CASE only -- None for searched CASE) plus
        # every WHEN clause's own test expression; each clause's `body`
        # is a nested statement list, not an expression, so it's NOT
        # yielded here -- combine with `_iter_statements`/
        # `_iter_statement_lists` for that, same convention as
        # IfStatement's then_body/else_body.
        if stmt["operand"] is not None:
            yield from _iter_exprs(stmt["operand"])
        for clause in stmt["when_clauses"]:
            yield from _iter_exprs(clause["when"])
    elif kind == "ReturnNode":
        yield from _iter_exprs(stmt["value"])
    # SqlStatement (CREATE TABLE/INSERT/UPDATE/DELETE/SELECT -- see
    # app.parser's "SQL passthrough statements" section) deliberately has
    # NO case here: its `sql` is raw text, not an expression tree, so
    # magic-number/unused-variable/never-read-variable/missing-error-
    # handling cannot see inside it -- the same scope boundary a cursor's
    # own embedded query (CursorDeclNode.query, also raw text) already
    # has and was never given a case here either. SelectIntoStatement
    # (see app.parser's "SELECT ... INTO" section) gets the identical
    # omission for the identical reason -- its `query` is raw text too.


def _iter_statement_lists(statements: list[dict]) -> Iterator[list[dict]]:
    """Yield `statements` itself, then recursively the body of every
    nested IF/WHILE/handler-action list it contains -- every distinct
    statement list this grammar has. Unlike `_iter_statements` (which
    flattens the whole tree into one sequence of individual statements),
    this preserves block boundaries, for a check that cares about
    *sequential position within one straight-line block* -- unreachable-
    after-RETURN and the never-read/dead-store check both need this;
    the six original checks never did, which is why it didn't exist
    before this phase."""
    yield statements
    for stmt in statements:
        kind = stmt["type"]
        if kind == "IfStatement":
            yield from _iter_statement_lists(stmt["then_body"])
            if stmt["else_body"] is not None:
                yield from _iter_statement_lists(stmt["else_body"])
        elif kind == "WhileStatement":
            yield from _iter_statement_lists(stmt["body"])
        elif kind == "LoopStatement":
            yield from _iter_statement_lists(stmt["body"])
        elif kind == "CaseStatement":
            for clause in stmt["when_clauses"]:
                yield from _iter_statement_lists(clause["body"])
            if stmt["else_body"] is not None:
                yield from _iter_statement_lists(stmt["else_body"])
        elif kind == "HandlerDeclNode":
            yield from _iter_statement_lists([stmt["action"]])


def _fold_constant(expr: dict):
    """Attempt to evaluate `expr` as a compile-time constant, using only
    NumberLiteral leaves and this grammar's arithmetic (+ - * /) and
    comparison (> < = !=) operators -- mirrors `Interpreter._evaluate`/
    `_evaluate_binary` exactly (interpreter.py) so a folded result always
    means the same thing the interpreter would compute at runtime.
    Returns None the moment anything isn't a compile-time constant (an
    Identifier, a STRING literal, a cursor %FOUND/%NOTFOUND check, ...)
    -- by far the common case, and correctly leaves those conditions
    alone."""
    kind = expr["type"]
    if kind == "NumberLiteral":
        return expr["value"]
    if kind == "UnaryExpr":
        operand = _fold_constant(expr["operand"])
        if operand is None or expr["operator"] != "-":
            return None
        return -operand
    if kind == "BinaryExpr":
        left = _fold_constant(expr["left"])
        right = _fold_constant(expr["right"])
        if left is None or right is None:
            return None
        op = expr["operator"]
        if op == "+":
            return left + right
        if op == "-":
            return left - right
        if op == "*":
            return left * right
        if op == "/":
            return left / right if right != 0 else None
        if op == ">":
            return left > right
        if op == "<":
            return left < right
        if op == "=":
            return left == right
        if op == "!=":
            return left != right
    return None


def _render_constant_expr(expr: dict) -> str:
    """A minimal stringifier for a message -- only ever called on an
    expression `_fold_constant` already proved is built entirely from
    NumberLiteral/UnaryExpr/BinaryExpr, so it never needs to handle
    Identifier/StringLiteral/cursor-check nodes at all."""
    kind = expr["type"]
    if kind == "NumberLiteral":
        return _format_number(expr["value"])
    if kind == "UnaryExpr":
        return f"-{_render_constant_expr(expr['operand'])}"
    if kind == "BinaryExpr":
        return f"{_render_constant_expr(expr['left'])} {expr['operator']} {_render_constant_expr(expr['right'])}"
    return "?"


def _format_number(value) -> str:
    return str(value)


# -- 1. SELECT * -----------------------------------------------------------


def _check_select_star(statements: list[dict], issues: list[dict]) -> None:
    for stmt in _iter_statements(statements):
        if stmt["type"] == "CursorDeclNode" and _SELECT_STAR_RE.search(stmt["query"]):
            issues.append(
                _issue(
                    category="select-star",
                    severity="suggestion",
                    title="SELECT * in cursor query",
                    line=stmt["line"],
                    message=(
                        f"Cursor '{stmt['name']}' selects every column with SELECT * instead of "
                        "naming the columns it actually uses."
                    ),
                    suggestion=(
                        "List only the columns this cursor's FETCH targets actually need (e.g. "
                        "SELECT name, price instead of SELECT *) -- it documents intent and won't "
                        "silently pick up columns added to the table later."
                    ),
                )
            )
        # SqlStatement (see app.parser's "SQL passthrough statements"
        # section, added in a later phase than the original six checks
        # above) can ALSO be a standalone SELECT, not just a cursor's
        # embedded one -- same anti-pattern, same regex-on-raw-text
        # detection, just a different statement shape and wording.
        elif stmt["type"] == "SqlStatement" and stmt["keyword"] == "SELECT" and _SELECT_STAR_RE.search(stmt["sql"]):
            issues.append(
                _issue(
                    category="select-star",
                    severity="suggestion",
                    title="SELECT * in query",
                    line=stmt["line"],
                    message="This SELECT reads every column with SELECT * instead of naming the columns it actually uses.",
                    suggestion=(
                        "List only the columns this statement actually needs (e.g. SELECT name, "
                        "price instead of SELECT *) -- it documents intent and won't silently pick "
                        "up columns added to the table later."
                    ),
                )
            )


# -- 2. Cursor loop that only accumulates a running total/count --------------


def _is_accumulator_set(stmt: dict) -> bool:
    value = stmt["value"]
    return (
        value["type"] == "BinaryExpr"
        and value["operator"] in _ACCUMULATOR_OPERATORS
        and value["left"]["type"] == "Identifier"
        and value["left"]["name"] == stmt["target"]
    )


def _check_cursor_could_be_set_based(statements: list[dict], issues: list[dict]) -> None:
    for stmt in _iter_statements(statements):
        if stmt["type"] != "WhileStatement":
            continue
        inner = list(_iter_statements(stmt["body"]))
        fetches = [s for s in inner if s["type"] == "FetchCursorNode"]
        sets = [s for s in inner if s["type"] == "SetStatement"]
        if not fetches or not sets:
            continue
        if all(_is_accumulator_set(s) for s in sets):
            cursor_names = ", ".join(sorted({f["name"] for f in fetches}))
            issues.append(
                _issue(
                    category="cursor-could-be-set-based",
                    severity="suggestion",
                    title="Cursor loop only accumulates a running total",
                    line=stmt["line"],
                    message=(
                        f"This WHILE loop's only job, once it FETCHes from '{cursor_names}', is to "
                        "add into a running total/counter one row at a time -- that's exactly what "
                        "SQL's own aggregate functions do in a single query."
                    ),
                    suggestion=(
                        "Prefer a single set-based query (e.g. SELECT SUM(...) / COUNT(...) ...) "
                        "over fetching every row into a cursor loop just to add them up by hand."
                    ),
                )
            )


# -- 3. Nested loops -----------------------------------------------------------


def _check_nested_loops(statements: list[dict], issues: list[dict]) -> None:
    def walk(stmts: list[dict], enclosing_loop_line: int | None) -> None:
        for stmt in stmts:
            kind = stmt["type"]
            if kind in ("WhileStatement", "LoopStatement"):
                # LOOP/LEAVE (see app.parser's "LOOP / LEAVE" section --
                # added in a later phase than this check's original
                # WHILE-only form) is just another loop construct for
                # this check's own purpose -- a LOOP nested inside a
                # WHILE, a WHILE nested inside a LOOP, or a LOOP nested
                # inside another LOOP are all the same O(n²) row-by-row
                # risk shape a WHILE-inside-WHILE already is, so `kind`
                # itself doesn't matter here, only "is this a loop and is
                # it nested inside another one".
                loop_word = "WHILE" if kind == "WhileStatement" else "LOOP"
                if enclosing_loop_line is not None:
                    issues.append(
                        _issue(
                            category="nested-loops",
                            severity="suggestion",
                            title="Nested loops",
                            line=stmt["line"],
                            message=(
                                f"This {loop_word} loop is nested inside another loop (started at "
                                f"line {enclosing_loop_line}), so its entire body runs again for "
                                "every iteration of the outer loop -- a classic O(n²) "
                                "row-by-row processing shape."
                            ),
                            suggestion=(
                                "Check whether the inner loop's work can be hoisted out of the "
                                "outer loop, replaced with a single query that joins/aggregates "
                                "across both row sets, or otherwise restructured to avoid the "
                                "repeated pass."
                            ),
                        )
                    )
                walk(stmt["body"], stmt["line"])
            elif kind == "IfStatement":
                walk(stmt["then_body"], enclosing_loop_line)
                if stmt["else_body"] is not None:
                    walk(stmt["else_body"], enclosing_loop_line)
            elif kind == "CaseStatement":
                # Not built on `_iter_statements` (this walker threads its
                # own `enclosing_loop_line` state through the recursion),
                # so it needs its own CaseStatement case -- same shape as
                # the IfStatement one just above.
                for clause in stmt["when_clauses"]:
                    walk(clause["body"], enclosing_loop_line)
                if stmt["else_body"] is not None:
                    walk(stmt["else_body"], enclosing_loop_line)
            elif kind == "HandlerDeclNode":
                walk([stmt["action"]], enclosing_loop_line)

    walk(statements, None)


# -- 4. Missing exception handling around risky operations -------------------


def _condition_guards_cursor(condition: dict, cursor_name: str) -> bool:
    return any(
        expr["type"] == "CursorFoundExpr" and expr["cursor"] == cursor_name for expr in _iter_exprs(condition)
    )


def _find_unguarded_fetch(statements: list[dict], guarded_cursors: frozenset[str]) -> dict | None:
    for stmt in statements:
        kind = stmt["type"]
        if kind == "FetchCursorNode" and stmt["name"] not in guarded_cursors:
            return stmt
        if kind == "IfStatement":
            found = _find_unguarded_fetch(stmt["then_body"], guarded_cursors)
            if found is not None:
                return found
            if stmt["else_body"] is not None:
                found = _find_unguarded_fetch(stmt["else_body"], guarded_cursors)
                if found is not None:
                    return found
        elif kind == "WhileStatement":
            inner_guarded = set(guarded_cursors)
            for expr in _iter_exprs(stmt["condition"]):
                if expr["type"] == "CursorFoundExpr":
                    inner_guarded.add(expr["cursor"])
            found = _find_unguarded_fetch(stmt["body"], frozenset(inner_guarded))
            if found is not None:
                return found
        elif kind == "LoopStatement":
            # LOOP/LEAVE (see app.parser's "LOOP / LEAVE" section --
            # added in a later phase than this check) has no condition of
            # its own at all, so unlike WhileStatement above there is no
            # %FOUND to extract from a header -- `guarded_cursors` passes
            # through completely unchanged into the body. (A LOOP-based
            # cursor loop's real guard idiom is `FETCH ...; IF
            # cur%NOTFOUND THEN LEAVE; END IF;` inside the body --
            # retrospective, not predictive -- which this check does not
            # recognize as a guard at all, same as it already doesn't
            # recognize a NOT_FOUND handler action other than an actual
            # DECLARE CONTINUE HANDLER FOR NOT_FOUND; a LOOP-based cursor
            # sample using that idiom will genuinely, correctly-by-this-
            # check's-own-rules surface a missing-error-handling
            # suggestion for its FETCH, same as any other unguarded one.)
            found = _find_unguarded_fetch(stmt["body"], guarded_cursors)
            if found is not None:
                return found
        elif kind == "CaseStatement":
            # Also not built on `_iter_statements`/`_iter_statement_lists`
            # (it threads its own `guarded_cursors` set through the
            # recursion, growing it inside a WHILE the same way a WHILE's
            # own condition does), so it needs its own CaseStatement case
            # too -- same shape as the IfStatement one above. A WHEN's own
            # test expression can't itself be a %FOUND guard (that's only
            # meaningful as a WHILE's condition), so `guarded_cursors`
            # passes through unchanged into every branch.
            for clause in stmt["when_clauses"]:
                found = _find_unguarded_fetch(clause["body"], guarded_cursors)
                if found is not None:
                    return found
            if stmt["else_body"] is not None:
                found = _find_unguarded_fetch(stmt["else_body"], guarded_cursors)
                if found is not None:
                    return found
        elif kind == "HandlerDeclNode":
            found = _find_unguarded_fetch([stmt["action"]], guarded_cursors)
            if found is not None:
                return found
    return None


def _check_missing_error_handling(statements: list[dict], issues: list[dict]) -> None:
    all_stmts = list(_iter_statements(statements))
    handler_conditions = {s["condition"] for s in all_stmts if s["type"] == "HandlerDeclNode"}

    division_line = next(
        (
            expr["line"]
            for stmt in all_stmts
            for expr in _statement_exprs(stmt)
            if expr["type"] == "BinaryExpr" and expr["operator"] == "/"
        ),
        None,
    )
    if division_line is not None and "DIVISION_BY_ZERO" not in handler_conditions:
        issues.append(
            _issue(
                category="missing-error-handling",
                severity="warning",
                title="Division with no DIVISION_BY_ZERO handler",
                line=division_line,
                message=(
                    "This procedure divides two values but never declares a CONTINUE HANDLER FOR "
                    "DIVISION_BY_ZERO -- if the divisor is ever 0 at runtime, execution stops with "
                    "an unhandled error."
                ),
                suggestion=(
                    "Add DECLARE CONTINUE HANDLER FOR DIVISION_BY_ZERO SET <flag> = <safe value>; "
                    "(or otherwise guard the divisor) before this division runs."
                ),
            )
        )

    if "NOT_FOUND" not in handler_conditions:
        unguarded = _find_unguarded_fetch(statements, frozenset())
        if unguarded is not None:
            issues.append(
                _issue(
                    category="missing-error-handling",
                    severity="suggestion",
                    title=f"Cursor '{unguarded['name']}' FETCHed with no NOT_FOUND safeguard",
                    line=unguarded["line"],
                    message=(
                        f"This FETCH from '{unguarded['name']}' isn't guarded by a preceding "
                        f"{unguarded['name']}%FOUND loop check, and no CONTINUE HANDLER FOR "
                        "NOT_FOUND is declared either. Fetching past the last row won't stop the "
                        "procedure (NOT_FOUND is always non-fatal here), but it will show up as an "
                        "unhandled error in the trace, which is easy to mistake for a real bug."
                    ),
                    suggestion=(
                        f"Either check {unguarded['name']}%FOUND before each FETCH, or declare "
                        "DECLARE CONTINUE HANDLER FOR NOT_FOUND SET <done-flag> = 1; so exhausting "
                        "the cursor is an explicit, intentional loop exit instead of an incidental "
                        "unhandled error."
                    ),
                )
            )


# -- 5. Repeated magic numbers -------------------------------------------------


def _check_magic_numbers(statements: list[dict], issues: list[dict]) -> None:
    occurrences: dict[float, list[int]] = {}
    for stmt in _iter_statements(statements):
        for expr in _statement_exprs(stmt):
            if expr["type"] == "NumberLiteral" and expr["value"] not in _TRIVIAL_NUMBERS:
                occurrences.setdefault(expr["value"], []).append(expr["line"])

    for value, lines in occurrences.items():
        if len(lines) < 2:
            continue
        formatted = _format_number(value)
        issues.append(
            _issue(
                category="magic-number",
                severity="suggestion",
                title=f"Repeated hard-coded value {formatted}",
                line=lines[0],
                message=(
                    f"The literal {formatted} appears {len(lines)} times (lines "
                    f"{', '.join(str(line) for line in lines)}) instead of being declared once."
                ),
                suggestion=(
                    f"DECLARE a named variable for {formatted} once and reference that instead -- "
                    "a business rule hard-coded in multiple places is easy to update incompletely "
                    "later."
                ),
            )
        )


# -- 6. Cursor opened but never closed -----------------------------------------


def _check_cursor_not_closed(statements: list[dict], issues: list[dict]) -> None:
    all_stmts = list(_iter_statements(statements))
    opened = {s["name"]: s["line"] for s in all_stmts if s["type"] == "OpenCursorNode"}
    closed = {s["name"] for s in all_stmts if s["type"] == "CloseCursorNode"}
    for name, line in opened.items():
        if name in closed:
            continue
        issues.append(
            _issue(
                category="cursor-not-closed",
                severity="warning",
                title=f"Cursor '{name}' opened but never closed",
                line=line,
                message=(
                    f"Cursor '{name}' is OPENed here but there's no matching CLOSE anywhere in "
                    "this procedure -- the cursor (and the result set it holds) is left open for "
                    "the rest of the run."
                ),
                suggestion=f"Add CLOSE {name}; once this cursor's rows have been fully processed.",
            )
        )


# -- 7. Unreachable code --------------------------------------------------------


def _check_unreachable_code(statements: list[dict], issues: list[dict]) -> None:
    # a) anything positionally after an unconditional exit -- a RETURN or
    #    a LEAVE (see app.parser's "LOOP / LEAVE" section, added in a
    #    later phase than RETURN's own original version of this check) --
    #    in the same statement list. Both unconditionally stop this
    #    statement list the instant they run (RETURN stops the whole
    #    procedure/function; LEAVE stops the enclosing loop and resumes
    #    right after it -- see interpreter.py's own "LOOP / LEAVE"
    #    section), so anything positioned after either one, in the SAME
    #    block, is dead *by position*, independent of any one run's
    #    actual control flow -- exactly the same reasoning RETURN's own
    #    case already established, just with a second construct that has
    #    the same unconditional-exit property.
    for block in _iter_statement_lists(statements):
        for index, stmt in enumerate(block):
            kind = stmt["type"]
            if kind == "ReturnNode":
                exit_word, halts = "RETURN", "exits execution"
            elif kind == "LeaveStatement":
                exit_word, halts = "LEAVE", "exits the enclosing loop"
            else:
                continue
            remainder = block[index + 1 :]
            if remainder:
                first_line = remainder[0]["line"]
                last_line = remainder[-1]["line"]
                line_range = f"{first_line}-{last_line}" if last_line != first_line else str(first_line)
                issues.append(
                    _issue(
                        category="unreachable-code",
                        severity="warning",
                        title=f"Unreachable code after {exit_word}",
                        line=first_line,
                        message=(
                            f"{exit_word} on line {stmt['line']} unconditionally {halts} here, so "
                            f"the statement(s) on line {line_range} can never run, no matter what "
                            "happens elsewhere in this procedure/function."
                        ),
                        suggestion=(
                            f"Remove the dead code, or move it before the {exit_word} if it was "
                            "meant to run first."
                        ),
                    )
                )
            # Everything else in this block is already unreachable because
            # of this same RETURN/LEAVE -- a second one further down (if
            # any) would itself be unreachable, not a new, independent
            # case.
            break

    # b) an IF whose condition is a compile-time constant, so one arm can
    #    never run regardless of anything else in the procedure.
    for stmt in _iter_statements(statements):
        if stmt["type"] != "IfStatement":
            continue
        folded = _fold_constant(stmt["condition"])
        if folded is None:
            continue
        if bool(folded):
            dead_body, branch_word = stmt["else_body"], "ELSE"
        else:
            dead_body, branch_word = stmt["then_body"], "THEN"
        if not dead_body:
            continue
        rendered = _render_constant_expr(stmt["condition"])
        issues.append(
            _issue(
                category="unreachable-code",
                severity="warning",
                title=f"{branch_word} branch can never execute",
                line=dead_body[0]["line"],
                message=(
                    f"This IF's condition ({rendered}) is a fixed constant that always evaluates to "
                    f"{'true' if folded else 'false'}, so the {branch_word} branch starting at line "
                    f"{dead_body[0]['line']} can never run."
                ),
                suggestion=(
                    "Remove the dead branch, or check whether the condition was meant to reference a "
                    "variable instead of two literal values."
                ),
            )
        )

    # c) a SEARCHED CASE's WHEN whose own condition is a compile-time
    #    constant -- see the module docstring's item 7c for why this is
    #    scoped to searched CASE only, not simple CASE.
    for stmt in _iter_statements(statements):
        if stmt["type"] != "CaseStatement" or stmt["operand"] is not None:
            continue
        when_clauses = stmt["when_clauses"]
        for index, clause in enumerate(when_clauses):
            folded = _fold_constant(clause["when"])
            if folded is None:
                continue
            rendered = _render_constant_expr(clause["when"])
            if not bool(folded):
                if not clause["body"]:
                    continue
                first_line = clause["body"][0]["line"]
                issues.append(
                    _issue(
                        category="unreachable-code",
                        severity="warning",
                        title="WHEN branch can never execute",
                        line=first_line,
                        message=(
                            f"This WHEN's condition ({rendered}) is a fixed constant that always "
                            f"evaluates to false, so the branch starting at line {first_line} can "
                            "never run."
                        ),
                        suggestion=(
                            "Remove the dead WHEN clause, or check whether the condition was meant "
                            "to reference a variable instead of two literal values."
                        ),
                    )
                )
                continue
            # folded True -- this WHEN always matches first, so every
            # WHEN/ELSE after it can never run.
            remainder = [s for later in when_clauses[index + 1 :] for s in later["body"]]
            if stmt["else_body"]:
                remainder += stmt["else_body"]
            if not remainder:
                break
            first_line = remainder[0]["line"]
            issues.append(
                _issue(
                    category="unreachable-code",
                    severity="warning",
                    title="Later WHEN/ELSE can never execute",
                    line=first_line,
                    message=(
                        f"This WHEN's condition ({rendered}) is a fixed constant that always "
                        "evaluates to true, so it always matches first -- every WHEN/ELSE after it "
                        f"(starting at line {first_line}) can never run."
                    ),
                    suggestion=(
                        "Remove the dead WHEN/ELSE clauses after this one, or check whether this "
                        "condition was meant to reference a variable instead of two literal values."
                    ),
                )
            )
            break  # nothing after an always-true WHEN needs checking further


# -- 8. Unused variables ---------------------------------------------------------


def _read_names_in_statement(stmt: dict) -> set[str]:
    """Every variable name this ONE statement reads (not writes), not
    recursing into a nested statement's own body -- combine with
    `_iter_statements` for that, as `_all_read_names` below does. A
    SET's own `target` (the LHS), a FETCH's `targets`, and a
    SelectIntoStatement's own `targets` are writes, not reads, and are
    deliberately excluded here (`_statement_exprs` has no case for
    SelectIntoStatement for exactly this reason -- see its own comment);
    a SET's `value` expression (including a self-reference, e.g.
    `SET x = x + 1;` -- accumulating into a variable is a legitimate
    read of it, not a spurious "never read"), an IF/WHILE `condition`, a
    RETURN's `value`, a DECLARE's own `default` expression, and a
    CALL's `args` all count as reads."""
    names: set[str] = set()
    for expr in _statement_exprs(stmt):
        for sub in _iter_exprs(expr):
            if sub["type"] == "Identifier":
                names.add(sub["name"])
    if stmt["type"] == "CallStatement":
        for arg in stmt["args"]:
            for sub in _iter_exprs(arg):
                if sub["type"] == "Identifier":
                    names.add(sub["name"])
    return names


def _all_read_names(statements: list[dict]) -> set[str]:
    names: set[str] = set()
    for stmt in _iter_statements(statements):
        names |= _read_names_in_statement(stmt)
    return names


def _check_unused_variables(statements: list[dict], issues: list[dict]) -> None:
    read_names = _all_read_names(statements)
    for stmt in _iter_statements(statements):
        if stmt["type"] != "DeclareStatement":
            continue
        name = stmt["name"]
        if name in read_names:
            continue
        issues.append(
            _issue(
                category="unused-variable",
                severity="suggestion",
                title=f"Variable '{name}' is never read",
                line=stmt["line"],
                message=(
                    f"'{name}' is declared here, and may be assigned a value later, but that value is "
                    "never read by any expression anywhere in this procedure/function -- not in a "
                    "condition, another statement's right-hand side, a RETURN, or a CALL argument."
                ),
                suggestion=(
                    f"Remove '{name}' if it's genuinely unneeded, or use its value somewhere -- if it's "
                    "meant to be visible to the caller, consider an OUT parameter instead of a plain "
                    "local."
                ),
            )
        )


# -- 9. Never-read variables (dead stores) ---------------------------------------


def _touched_names(stmt: dict) -> set[str]:
    """Every variable name potentially read OR written anywhere within
    `stmt`, including inside any statement list nested inside it (an
    IF/WHILE body, a handler's action) and a CALL's own arguments.
    Used only by `_check_never_read_variables` below as a conservative
    "this statement might consume or redefine any of these names, stop
    tracking them" barrier -- not a precise read/write distinction,
    since a false "might touch it" only costs a missed warning, never a
    wrong one, which is the safe direction to err in here."""
    names: set[str] = set()
    for inner in _iter_statements([stmt]):
        for expr in _statement_exprs(inner):
            for sub in _iter_exprs(expr):
                if sub["type"] == "Identifier":
                    names.add(sub["name"])
        kind = inner["type"]
        if kind == "SetStatement":
            names.add(inner["target"])
        elif kind == "CallStatement":
            for arg in inner["args"]:
                for sub in _iter_exprs(arg):
                    if sub["type"] == "Identifier":
                        names.add(sub["name"])
        elif kind == "FetchCursorNode":
            names.update(inner["targets"])
        elif kind == "SelectIntoStatement":
            # Same treatment as FetchCursorNode's own `targets` just
            # above -- a write, not a read (see `_read_names_in_statement`
            # below), but still something this conservative "might touch
            # it" barrier needs to know about.
            names.update(inner["targets"])
    return names


def _check_never_read_variables(statements: list[dict], issues: list[dict]) -> None:
    """"Dead store" detection: a SET assigns a value to a variable, then
    a LATER SET to that same name overwrites it before anything ever
    reads the first value in between -- the first assignment's work was
    wasted. Distinguishable from unused-variable (8 above): a
    dead-stored variable can still be read *elsewhere*, just not
    between these two particular writes, and being read at all is
    exactly what keeps it off the unused-variable list -- so this
    check is genuinely a different, narrower finding on this grammar,
    not the same case in disguise.

    Deliberately scoped to a straight-line run within ONE statement
    list (see `_iter_statement_lists`) -- this grammar has no dataflow
    analysis across an IF's branches or across a WHILE loop's own
    iterations (a write in one iteration reaching a read in the next is
    exactly the kind of loop-carried dependency a real liveness
    analysis needs a fixed-point computation over the control-flow
    graph to get right, which is out of scope here), so this only
    catches the unambiguous case: two SETs to the same name in the same
    block, with nothing observed in between that could plausibly read
    it. Any IF/WHILE/handler/CALL encountered between two writes is
    treated as a conservative barrier (`_touched_names`) rather than
    analyzed -- it stops tracking the names that statement could
    plausibly touch, rather than risk a wrong accusation.

    Deliberately does NOT treat `DECLARE x TYPE DEFAULT expr;` as a
    "first write" the way a SET is -- see the module docstring's
    "Explicitly NOT implemented" section for why (this idiom is used
    throughout this app's own sample library, and flagging it would be
    noise, not a real finding)."""
    for block in _iter_statement_lists(statements):
        pending: dict[str, int] = {}  # variable name -> line of its latest un-consumed SET
        for stmt in block:
            if stmt["type"] == "SetStatement":
                target = stmt["target"]
                read_here = {
                    sub["name"]
                    for expr in _statement_exprs(stmt)
                    for sub in _iter_exprs(expr)
                    if sub["type"] == "Identifier"
                }
                for name in read_here:
                    pending.pop(name, None)
                if target in pending:
                    issues.append(
                        _issue(
                            category="never-read-variable",
                            severity="warning",
                            title=f"Value assigned to '{target}' is never read",
                            line=pending[target],
                            message=(
                                f"'{target}' is set here, but that value is never read anywhere -- "
                                f"it's unconditionally overwritten by another SET on line {stmt['line']} "
                                "before anything gets the chance to use it."
                            ),
                            suggestion=(
                                f"Remove this assignment if it's genuinely dead, or read '{target}' "
                                "(in a condition, another expression, or a RETURN) before overwriting "
                                "it if the first value was meant to matter."
                            ),
                        )
                    )
                pending[target] = stmt["line"]
            else:
                for name in _touched_names(stmt):
                    pending.pop(name, None)


# -- 10. UPDATE/DELETE with no WHERE clause -------------------------------------


def _check_missing_where_clause(statements: list[dict], issues: list[dict]) -> None:
    # `stmt["where"]` no longer exists (SqlStatement carries raw `sql`
    # text, not a parsed WHERE expression -- see app.parser's "SQL
    # passthrough statements" section), so this is now a regex over the
    # raw text rather than an `is None` check -- the same "detect it
    # from the text, don't parse it" approach `_check_select_star`
    # already uses for a cursor's embedded query. A WHERE appearing
    # anywhere in the text (there's no sub-clause to confuse it with,
    # since this grammar's passthrough statements have nothing after a
    # WHERE that could itself contain the word) is good enough to avoid
    # a false positive.
    for stmt in _iter_statements(statements):
        if stmt["type"] != "SqlStatement" or stmt["keyword"] not in ("UPDATE", "DELETE"):
            continue
        if _WHERE_RE.search(stmt["sql"]):
            continue
        verb = stmt["keyword"]
        table_name = extract_table_name(verb, stmt["sql"]) or "?"
        issues.append(
            _issue(
                category="missing-where-clause",
                severity="warning",
                title=f"{verb} with no WHERE clause",
                line=stmt["line"],
                message=(
                    f"This {verb} on table '{table_name}' has no WHERE clause, so it "
                    "touches every row currently in the table."
                ),
                suggestion=(
                    f"Add a WHERE clause that narrows this {verb} to only the row(s) it's "
                    "meant to affect, or confirm that touching every row is really intended."
                ),
            )
        )


# -- entry point ---------------------------------------------------------------

_CHECKS = (
    _check_select_star,
    _check_cursor_could_be_set_based,
    _check_nested_loops,
    _check_missing_error_handling,
    _check_magic_numbers,
    _check_cursor_not_closed,
    _check_unreachable_code,
    _check_unused_variables,
    _check_never_read_variables,
    _check_missing_where_clause,
)


def analyze(ast: dict) -> list[dict]:
    """Run every anti-pattern check against `ast` (a Procedure,
    ProcedureNode, or FunctionNode -- see app.parser) and return the
    findings, sorted by line number (unlocated issues last, though none
    of the checks above currently produce one) for a stable, readable
    order."""
    body = ast.get("body", [])
    issues: list[dict] = []
    for check in _CHECKS:
        check(body, issues)
    issues.sort(key=lambda issue: (issue["line"] is None, issue["line"] or 0, issue["category"]))
    return issues
