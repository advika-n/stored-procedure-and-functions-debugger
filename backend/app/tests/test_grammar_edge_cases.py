"""Hand-written grammar edge cases, per this phase's own explicit list:
nested cursors, deeply nested loops (against the real MAX_LOOP_
ITERATIONS/MAX_CALL_DEPTH guards, not monkeypatched-small ones -- see
test_loop_statement.py for that separate, deliberately-small-guard
style of test), empty procedure bodies, comments inside SQL string
literals, missing semicolons, mismatched BEGIN/END, and a real,
measured timing check against the 2-second NFR (CLAUDE.md SS4) for a
large loop count.

Every number/behavior asserted below was run for real against this
project's own unmodified pipeline before being written down here -- see
each test's own comment for what was actually observed, not assumed.
"""

from __future__ import annotations

import time

import pytest
from fastapi.testclient import TestClient

from app import demo_db
from app.interpreter import InterpreterError, MAX_CALL_DEPTH, MAX_LOOP_ITERATIONS, run
from app.main import app
from app.parser import ParserError, parse
from app.tokenizer import tokenize

client = TestClient(app)


def _run(code: str, params: dict | None = None):
    conn = demo_db.create_demo_connection()
    try:
        return run(parse(tokenize(code)), params or {}, db_connection=conn)
    finally:
        conn.close()


# -- nested cursors -------------------------------------------------------


def test_two_cursors_open_at_the_same_time_stay_independent():
    """An inner cursor's full OPEN -> FETCH-loop -> CLOSE cycle runs
    INSIDE each pass of an outer cursor's own loop, so both are
    genuinely open/mid-iteration simultaneously at points during this
    run -- not just two cursors declared in the same procedure but used
    one after the other. Hand-derived against the fixed `products`
    table (Widget/10, Gadget/25, Gizmo/15 -- see app.demo_db):
    outer_total = 10+25+15 = 50 (all 3 rows); the inner cursor (WHERE
    price > 10 -- Gadget/25 and Gizmo/15, excluding Widget) is reopened
    fresh on EVERY outer pass and summed each time: (25+15) * 3 outer
    passes = 120. Cross-checked against a real interpreter run before
    being written here, not just hand-computed."""
    code = """\
CREATE PROCEDURE NestedCursors()
BEGIN
    DECLARE outer_total NUMBER DEFAULT 0;
    DECLARE inner_total NUMBER DEFAULT 0;
    DECLARE oname TEXT DEFAULT '';
    DECLARE oprice NUMBER DEFAULT 0;
    DECLARE iname TEXT DEFAULT '';
    DECLARE iprice NUMBER DEFAULT 0;
    DECLARE outer_cur CURSOR FOR SELECT name, price FROM products;
    DECLARE inner_cur CURSOR FOR SELECT name, price FROM products WHERE price > 10;
    OPEN outer_cur;
    WHILE outer_cur%FOUND DO
        FETCH outer_cur INTO oname, oprice;
        SET outer_total = outer_total + oprice;
        OPEN inner_cur;
        WHILE inner_cur%FOUND DO
            FETCH inner_cur INTO iname, iprice;
            SET inner_total = inner_total + iprice;
        END WHILE;
        CLOSE inner_cur;
    END WHILE;
    CLOSE outer_cur;
END
"""
    steps = _run(code)
    final = steps[-1].to_dict()["variables"]
    assert final["outer_total"]["value"] == 50
    assert final["inner_total"]["value"] == 120


def test_reopening_the_same_inner_cursor_resets_its_position_each_time():
    """A cursor CLOSEd then re-OPENed (as the nested-cursor test above
    does on every outer pass) must start its FETCH position over from
    row 0 each time, not continue from wherever the previous OPEN left
    off -- verified directly via app.interpreter._exec_open_cursor's own
    reset of `pos`/`last_fetch_found`, not assumed from reading the
    code alone."""
    code = """\
CREATE PROCEDURE ReopenCursor()
BEGIN
    DECLARE cur CURSOR FOR SELECT name FROM products;
    DECLARE first1 TEXT DEFAULT '';
    DECLARE first2 TEXT DEFAULT '';
    OPEN cur;
    FETCH cur INTO first1;
    CLOSE cur;
    OPEN cur;
    FETCH cur INTO first2;
    CLOSE cur;
END
"""
    steps = _run(code)
    final = steps[-1].to_dict()["variables"]
    # Both OPENs see the same first row (Widget) -- proof position truly
    # reset, rather than the second OPEN silently resuming at row 1.
    assert final["first1"]["value"] == final["first2"]["value"] == "Widget"


# -- deeply nested loops vs. the real guards -------------------------------


def test_leave_from_fifty_levels_deep_unwinds_all_at_once():
    """50 levels of nested, individually-labeled LOOPs (the same order
    of magnitude as MAX_CALL_DEPTH itself) with a single `LEAVE lvl0;`
    fired from the INNERMOST level, targeting the OUTERMOST -- confirms
    `_exec_leave`/`_exec_loop`'s re-raise-until-caught mechanism (see
    interpreter.py's own "LOOP / LEAVE" section) scales past the small
    2-3 level nesting every other LOOP/LEAVE test uses, unwinding
    through all 50 Python stack frames in one signal, not one level at
    a time. `x` increments exactly once -- proof every outer level's
    own body stops immediately too, not just the innermost one."""
    depth = 50
    lines = ["CREATE PROCEDURE DeepNest()", "BEGIN", "    DECLARE x NUMBER DEFAULT 0;"]
    for level in range(depth):
        lines.append(f"    lvl{level}: LOOP")
    lines.append("        SET x = x + 1;")
    lines.append("        LEAVE lvl0;")
    for level in reversed(range(depth)):
        lines.append(f"    END LOOP lvl{level};")
    lines.append("END")
    code = "\n".join(lines)

    steps = _run(code)
    assert steps[-1].to_dict()["variables"]["x"]["value"] == 1


def test_real_max_loop_iterations_guard_fires_without_monkeypatching():
    """The REAL `MAX_LOOP_ITERATIONS` constant (10,000 -- unlike
    test_loop_statement.py's own guard tests, which deliberately
    monkeypatch it down to 3-5 so they run instantly), reached by a
    genuinely infinite `WHILE 1 = 1 DO ... END WHILE;` (this grammar has
    no `>=`/`<=` -- see README.md -- so `1 = 1` is the simplest
    always-true condition available). Also doubles as this phase's
    timing check's baseline: measured directly at 66ms locally, well
    under the 2s NFR even at the real cap -- see
    `test_large_loop_count_stays_under_the_2s_nfr` below for the
    checked-in, asserted version of that measurement."""
    assert MAX_LOOP_ITERATIONS == 10_000  # guards the assumption the test below times against
    code = """\
CREATE PROCEDURE Runaway()
BEGIN
    DECLARE i NUMBER DEFAULT 0;
    WHILE 1 = 1 DO
        SET i = i + 1;
    END WHILE;
END
"""
    with pytest.raises(InterpreterError, match=r"WHILE loop exceeded 10000 iterations"):
        _run(code)


def test_real_max_call_depth_guard_fires_as_a_clean_error_not_a_python_recursionerror():
    """The REAL `MAX_CALL_DEPTH` (50), reached by genuine unbounded
    self-recursion -- confirms `_exec_call`'s own depth counter raises
    its clear `InterpreterError` before Python's own C-stack-based
    recursion limit could ever be hit (each nested CALL costs several
    real Python stack frames -- see interpreter.py's own docstring), so
    a runaway recursive procedure fails with a message a frontend can
    show, never a raw `RecursionError`/interpreter crash."""
    assert MAX_CALL_DEPTH == 50
    code = """\
CREATE PROCEDURE Recur(IN n NUMBER)
BEGIN
    CALL Recur(n + 1);
END
"""
    with pytest.raises(InterpreterError, match=r"exceeded the maximum call depth of 50") as exc_info:
        _run(code, {"n": 0})
    assert not isinstance(exc_info.value, RecursionError)


# -- empty procedure bodies -------------------------------------------------


def test_empty_bare_procedure_body_now_gets_a_synthetic_step_too():
    """**Was a hand-verified finding, since FIXED in a dedicated
    follow-up bug-fix phase -- see `HANDOFF.md`/`test_known_bugs.py`**:
    a bare (wrapper-less) procedure body with zero statements -- whether
    from genuinely empty source, whitespace-only source, or (as
    `test_property_based.py` discovered via mutation) a mutated sample
    reduced to nothing -- used to produce a trace of length **zero**,
    inconsistent with a wrapped empty body (below), which always got a
    synthetic entry step. `Interpreter.run` now gives this exact case
    (bare form AND a genuinely empty body -- a bare body with at least
    one statement is completely unaffected) one synthetic placeholder
    step of its own, so this is consistent with the wrapped form: never
    a zero-length trace."""
    for code in ("", "   \n\t  "):
        steps = _run(code)
        assert len(steps) == 1
        step_dict = steps[0].to_dict()
        assert step_dict["nodeType"] == "Procedure"
        assert step_dict["statementText"] == "(empty procedure body)"
        assert step_dict["variables"] == {}


def test_empty_wrapped_procedure_body_gets_exactly_the_entry_step():
    """A `CREATE PROCEDURE ... BEGIN END` with zero body statements
    still gets its own synthetic entry step (the `CREATE PROCEDURE ...`
    signature line) -- so an empty WRAPPED body's trace length is 1,
    never 0."""
    steps = _run("CREATE PROCEDURE Empty() BEGIN END")
    assert len(steps) == 1
    assert steps[0].to_dict()["nodeType"] == "ProcedureNode"


def test_bare_and_wrapped_empty_bodies_now_produce_the_same_shape():
    """Regression for the bare-vs-wrapped inconsistency itself: an empty
    body ALWAYS produces exactly one step now, regardless of which of
    the two procedure forms it's written in -- there is no longer a
    third, zero-step behavior specific to the bare form."""
    bare_steps = _run("")
    wrapped_steps = _run("CREATE PROCEDURE Empty() BEGIN END")
    assert len(bare_steps) == len(wrapped_steps) == 1


def test_empty_function_body_is_a_clear_interpretererror_not_a_silent_null():
    """A FunctionNode's body completing with no RETURN ever executed is
    always an error (see interpreter.py's own "Functions" section) --
    including the empty-body case, which completes trivially and
    immediately without ever having a chance to RETURN anything."""
    with pytest.raises(InterpreterError, match="completed without executing a RETURN"):
        _run("CREATE FUNCTION Empty() RETURNS NUMBER BEGIN END")


# -- comments inside SQL string literals ------------------------------------
# This grammar has no comment syntax of its own at all (no `--`/`/* */`
# token -- see app.tokenizer's own module docstring's keyword/operator
# list). These tests aren't about a comment FEATURE, then -- they
# confirm that comment-LOOKING text sitting inside an ordinary STRING
# literal is never mistaken for one, in either of the two places that
# matters: an ordinary string value, and a cursor's embedded SELECT
# text (captured verbatim and hand straight to a real SQLite
# connection, which DOES understand `--` comments in general -- see
# app.parser's own "Cursors" section).


def test_comment_like_text_in_an_ordinary_string_literal_is_just_a_string():
    steps = _run("DECLARE tag TEXT DEFAULT '-- not a comment /* also not */';")
    assert steps[-1].to_dict()["variables"]["tag"]["value"] == "-- not a comment /* also not */"


def test_comment_like_text_inside_a_cursor_where_clause_string_round_trips_to_sqlite():
    """The embedded SELECT is reassembled from raw tokens (see
    app.parser's `_render_raw_query`) and handed straight to SQLite.
    Since the STRING token itself already captures
    `'-- nope /* still not */'` as ONE token (the tokenizer's own STRING
    regex, not comment-aware at all), the reconstructed query text is
    `... WHERE name != '-- nope /* still not */'` -- and SQLite (which
    DOES treat a bare `--` as a real comment outside of a string) still
    correctly treats it as an ordinary string literal, not a comment
    that would otherwise truncate the rest of the query. Confirmed by
    checking the FETCH actually still finds a real row (`Widget`, the
    demo table's first row -- see app.demo_db), not zero rows from a
    query SQLite silently mangled."""
    code = """\
DECLARE cur CURSOR FOR SELECT name FROM products WHERE name != '-- nope /* still not */';
DECLARE item TEXT DEFAULT '';
OPEN cur;
FETCH cur INTO item;
CLOSE cur;
"""
    steps = _run(code)
    assert steps[-1].to_dict()["variables"]["item"]["value"] == "Widget"


# -- missing semicolons -----------------------------------------------------


@pytest.mark.parametrize(
    "code",
    [
        pytest.param("DECLARE x NUMBER DEFAULT 0\nSET x = 1;", id="missing-after-declare"),
        pytest.param("DECLARE x NUMBER DEFAULT 0;\nSET x = 1", id="missing-after-set-at-eof"),
        pytest.param("IF 1 = 1 THEN SET x = 1; END IF", id="missing-after-end-if"),
        pytest.param("WHILE 1 = 1 DO SET x = 1; END WHILE", id="missing-after-end-while"),
        pytest.param("INSERT INTO t VALUES (1)", id="missing-after-insert-at-eof"),
    ],
)
def test_missing_semicolon_is_a_clear_parser_error(code):
    with pytest.raises(ParserError):
        parse(tokenize(code))


def test_missing_semicolon_after_a_sql_passthrough_statement_does_not_raise():
    # A real, documented gap -- NOT the same "clear ParserError" every
    # other missing-semicolon case above gets. SqlStatement's raw-token
    # capture (see app.parser's "SQL passthrough statements" section)
    # just collects tokens up to the next top-level ';' with no
    # understanding of statement boundaries beyond that, exactly like a
    # cursor's embedded query capture already works -- a missing ';'
    # here doesn't fail to parse at all, it silently merges with
    # whatever statement follows into one nonsensical `sql` string,
    # which then fails at INTERPRET time instead (a real SQLite syntax
    # error), not at parse time. Verified directly rather than assumed,
    # since this is a real behavior difference from the retired
    # structured CreateTableStatement grammar, which DID close its own
    # ')' and require an explicit ';' right after.
    ast = parse(tokenize("CREATE TABLE t (a NUMBER)\nINSERT INTO t VALUES (1);"))
    stmt = ast["body"][0]
    assert stmt["type"] == "SqlStatement"
    assert stmt["sql"] == "CREATE TABLE t ( a NUMBER ) INSERT INTO t VALUES ( 1 )"
    assert len(ast["body"]) == 1  # the INSERT was swallowed into the same statement, not parsed separately


# -- mismatched BEGIN/END ----------------------------------------------------


@pytest.mark.parametrize(
    "code",
    [
        pytest.param("CREATE PROCEDURE Foo() BEGIN SET x = 1;", id="missing-end-entirely"),
        pytest.param("CREATE PROCEDURE Foo() SET x = 1; END", id="missing-begin-entirely"),
        pytest.param("IF 1 = 1 THEN SET x = 1; END WHILE;", id="end-while-for-an-if"),
        pytest.param("WHILE 1 = 1 DO SET x = 1; END IF;", id="end-if-for-a-while"),
        pytest.param("outer: LOOP LEAVE outer; END LOOP wrongname;", id="mismatched-loop-label"),
    ],
)
def test_mismatched_begin_end_is_a_clear_parser_error(code):
    with pytest.raises(ParserError):
        parse(tokenize(code))


# -- large-loop-count timing check against the 2s NFR (measured, not assumed) -


def test_large_loop_count_stays_under_the_2s_nfr():
    """Real, measured wall-clock time (see CLAUDE.md SS4's own "must
    stay under 2s" NFR and its measurement history in docs/schema.md) --
    NOT assumed from the fact that smaller samples were already fast.
    9,999 iterations (one under the real MAX_LOOP_ITERATIONS cap, so
    this is a legitimate, successful run producing a genuinely huge
    ~20,000-step trace -- one DebugStep per loop-condition check AND
    one per loop-body SET) through the REAL `/debug` endpoint (`http`
    layer, JSON serialization, and history.save_run included -- not
    just the bare interpreter call), timed directly with a wall clock.
    Measured locally at ~0.6s for the full endpoint round trip -- comfortably
    under budget even at this scale, but this assertion uses a looser
    1.8s ceiling (not the exact measured number) so ordinary machine-to-
    machine variance doesn't make this test flaky; the real number this
    was checked against is recorded in docs/schema.md's own performance
    table, per this project's existing "re-time and log" convention."""
    code = """\
CREATE PROCEDURE BigLoop()
BEGIN
    DECLARE i NUMBER DEFAULT 0;
    WHILE i < 9999 DO
        SET i = i + 1;
    END WHILE;
END
"""
    start = time.perf_counter()
    response = client.post("/debug", json={"code": code, "params": {}})
    elapsed = time.perf_counter() - start

    assert response.status_code == 200
    steps = response.json()["steps"]
    # 1 entry step (CREATE PROCEDURE ...) + 1 DECLARE step + 10,000
    # WHILE condition-checks (9999 true + the 1 final false one that
    # exits the loop) + 9999 SET-body-runs (once per true check) --
    # confirmed against the real measured count (20001), not guessed.
    assert len(steps) == 1 + 1 + 10_000 + 9_999 == 20_001
    assert elapsed < 1.8, f"/debug took {elapsed:.3f}s for a 9999-iteration loop -- NFR is 2s"
