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
     aggregate query (SUM/COUNT/...)
  3. nested-loops             -- a WHILE loop nested inside another
     WHILE loop (O(n^2) row-by-row risk)
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
          safe alternative to a handler, not a missing one.
  5. magic-number             -- the same non-trivial numeric literal
     (i.e. not 0 or 1) hard-coded more than once
  6. cursor-not-closed        -- an OPENed cursor with no matching CLOSE
     anywhere in the procedure

-- Explicitly NOT implemented ---------------------------------------------

"Dynamic SQL string concatenation (SQL injection risk pattern)" was one
of the candidates for this phase but is NOT implemented: this grammar
has no EXECUTE/EXEC-IMMEDIATE construct and no way to build a SQL string
at runtime and hand it to the database -- every cursor's query is fixed,
literal text captured verbatim at parse time (see
`app.parser._parse_declare_cursor`/`CursorDeclNode`), never assembled
from concatenated variables. There is nothing of that shape in this
language for a check to find, so none was written, rather than forcing
one that could never fire.
"""

from __future__ import annotations

import re
from collections.abc import Iterator

_SELECT_STAR_RE = re.compile(r"select\s+\*", re.IGNORECASE)
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
    IF/WHILE bodies and a handler's single action statement -- every place
    this grammar allows a nested statement to appear."""
    for stmt in statements:
        yield stmt
        kind = stmt["type"]
        if kind == "IfStatement":
            yield from _iter_statements(stmt["then_body"])
            if stmt["else_body"] is not None:
                yield from _iter_statements(stmt["else_body"])
        elif kind == "WhileStatement":
            yield from _iter_statements(stmt["body"])
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
    elif kind == "ReturnNode":
        yield from _iter_exprs(stmt["value"])


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
            if kind == "WhileStatement":
                if enclosing_loop_line is not None:
                    issues.append(
                        _issue(
                            category="nested-loops",
                            severity="suggestion",
                            title="Nested loops",
                            line=stmt["line"],
                            message=(
                                "This WHILE loop is nested inside another WHILE loop (started at "
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


# -- entry point ---------------------------------------------------------------

_CHECKS = (
    _check_select_star,
    _check_cursor_could_be_set_based,
    _check_nested_loops,
    _check_missing_error_handling,
    _check_magic_numbers,
    _check_cursor_not_closed,
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
