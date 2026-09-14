from app import advisor
from app.parser import parse
from app.tokenizer import tokenize


def _ast(code):
    """A real AST, produced by the actual tokenizer/parser -- never a
    hand-built dict -- so every check below is exercised against
    genuine parser output, matching this project's existing testing
    convention (see e.g. test_report.py)."""
    return parse(tokenize(code))


def _categories(issues):
    return [issue["category"] for issue in issues]


# -- clean procedures produce no issues --------------------------------------


def test_clean_procedure_has_no_issues():
    # Every declared variable must actually be read somewhere for this to
    # stay clean under the unused-variable/never-read-variable checks (see
    # advisor.py SS8/SS9) -- `total` is read by its own self-referencing
    # second SET, exactly like this app's real CalculateTotal sample reads
    # `total` again via `SET tax = total * 0.08;`.
    ast = _ast(
        """CREATE PROCEDURE CalculateTotal()
BEGIN
    DECLARE price NUMBER DEFAULT 25;
    DECLARE quantity NUMBER DEFAULT 4;
    DECLARE total NUMBER DEFAULT 0;
    SET total = price * quantity;
    SET total = total + 1;
END
"""
    )
    assert advisor.analyze(ast) == []


def test_every_issue_has_the_expected_shape():
    ast = _ast(
        """CREATE PROCEDURE Leaky()
BEGIN
    DECLARE cur CURSOR FOR SELECT * FROM products;
    OPEN cur;
END
"""
    )
    issues = advisor.analyze(ast)
    assert issues
    for issue in issues:
        assert set(issue.keys()) == {"category", "severity", "title", "line", "message", "suggestion"}
        assert issue["severity"] in ("warning", "suggestion")
        assert issue["message"]
        assert issue["suggestion"]


# -- 1. SELECT * --------------------------------------------------------------


def test_select_star_is_flagged():
    ast = _ast(
        """CREATE PROCEDURE Bad()
BEGIN
    DECLARE cur CURSOR FOR SELECT * FROM products;
    OPEN cur;
    CLOSE cur;
END
"""
    )
    issues = advisor.analyze(ast)
    assert "select-star" in _categories(issues)
    hit = next(i for i in issues if i["category"] == "select-star")
    assert hit["severity"] == "suggestion"
    assert hit["line"] == 3


def test_explicit_columns_are_not_flagged():
    ast = _ast(
        """CREATE PROCEDURE Good()
BEGIN
    DECLARE cur CURSOR FOR SELECT name, price FROM products;
    OPEN cur;
    CLOSE cur;
END
"""
    )
    assert "select-star" not in _categories(advisor.analyze(ast))


# -- 2. cursor loop that only accumulates -------------------------------------


def test_cursor_accumulation_loop_is_flagged():
    ast = _ast(
        """CREATE PROCEDURE ProductPriceTotal()
BEGIN
    DECLARE total NUMBER DEFAULT 0;
    DECLARE item_name STRING DEFAULT '';
    DECLARE item_price NUMBER DEFAULT 0;
    DECLARE prod_cursor CURSOR FOR SELECT name, price FROM products;
    OPEN prod_cursor;
    WHILE prod_cursor%FOUND DO
        FETCH prod_cursor INTO item_name, item_price;
        SET total = total + item_price;
    END WHILE;
    CLOSE prod_cursor;
END
"""
    )
    issues = advisor.analyze(ast)
    assert "cursor-could-be-set-based" in _categories(issues)


def test_cursor_loop_with_non_accumulator_logic_is_not_flagged():
    # The loop body does real per-row conditional work, not just summing
    # -- not the "could just be one aggregate query" shape.
    ast = _ast(
        """CREATE PROCEDURE PrintExpensive()
BEGIN
    DECLARE item_name STRING DEFAULT '';
    DECLARE item_price NUMBER DEFAULT 0;
    DECLARE flagCount NUMBER DEFAULT 0;
    DECLARE cur CURSOR FOR SELECT name, price FROM products;
    OPEN cur;
    WHILE cur%FOUND DO
        FETCH cur INTO item_name, item_price;
        IF item_price > 100 THEN
            SET flagCount = 5;
        END IF;
    END WHILE;
    CLOSE cur;
END
"""
    )
    assert "cursor-could-be-set-based" not in _categories(advisor.analyze(ast))


# -- 3. nested loops ------------------------------------------------------------


def test_nested_while_loops_are_flagged():
    ast = _ast(
        """CREATE PROCEDURE Nested()
BEGIN
    DECLARE outer NUMBER DEFAULT 0;
    DECLARE inner NUMBER DEFAULT 0;
    WHILE outer < 3 DO
        WHILE inner < 3 DO
            SET inner = inner + 1;
        END WHILE;
        SET outer = outer + 1;
    END WHILE;
END
"""
    )
    issues = advisor.analyze(ast)
    assert "nested-loops" in _categories(issues)
    hit = next(i for i in issues if i["category"] == "nested-loops")
    assert hit["line"] == 6  # the INNER while's line, not the outer's


def test_single_loop_is_not_flagged():
    ast = _ast(
        """CREATE PROCEDURE Single()
BEGIN
    DECLARE i NUMBER DEFAULT 0;
    WHILE i < 3 DO
        SET i = i + 1;
    END WHILE;
END
"""
    )
    assert "nested-loops" not in _categories(advisor.analyze(ast))


def test_two_sibling_loops_are_not_nested():
    ast = _ast(
        """CREATE PROCEDURE Siblings()
BEGIN
    DECLARE i NUMBER DEFAULT 0;
    DECLARE j NUMBER DEFAULT 0;
    WHILE i < 3 DO
        SET i = i + 1;
    END WHILE;
    WHILE j < 3 DO
        SET j = j + 1;
    END WHILE;
END
"""
    )
    assert "nested-loops" not in _categories(advisor.analyze(ast))


# -- 4a. division without a DIVISION_BY_ZERO handler --------------------------


def test_unhandled_division_is_flagged_as_a_warning():
    ast = _ast(
        """CREATE PROCEDURE Divide()
BEGIN
    DECLARE total NUMBER DEFAULT 10;
    DECLARE count NUMBER DEFAULT 2;
    DECLARE average NUMBER DEFAULT 0;
    SET average = total / count;
END
"""
    )
    issues = advisor.analyze(ast)
    hits = [i for i in issues if i["category"] == "missing-error-handling" and "DIVISION_BY_ZERO" in i["title"]]
    assert len(hits) == 1
    assert hits[0]["severity"] == "warning"


def test_handled_division_is_not_flagged():
    ast = _ast(
        """CREATE PROCEDURE SafeDivide()
BEGIN
    DECLARE total NUMBER DEFAULT 10;
    DECLARE count NUMBER DEFAULT 2;
    DECLARE average NUMBER DEFAULT 0;
    DECLARE CONTINUE HANDLER FOR DIVISION_BY_ZERO SET average = 0;
    SET average = total / count;
END
"""
    )
    issues = advisor.analyze(ast)
    assert not [i for i in issues if i["category"] == "missing-error-handling" and "DIVISION_BY_ZERO" in i["title"]]


# -- 4b. FETCH with no %FOUND guard and no NOT_FOUND handler ------------------


def test_unguarded_fetch_is_flagged_as_a_suggestion_not_a_warning():
    ast = _ast(
        """CREATE PROCEDURE Unguarded()
BEGIN
    DECLARE done NUMBER DEFAULT 0;
    DECLARE item_name STRING DEFAULT '';
    DECLARE item_price NUMBER DEFAULT 0;
    DECLARE cur CURSOR FOR SELECT name, price FROM products;
    OPEN cur;
    WHILE done = 0 DO
        FETCH cur INTO item_name, item_price;
        SET done = 1;
    END WHILE;
    CLOSE cur;
END
"""
    )
    issues = advisor.analyze(ast)
    hits = [i for i in issues if i["category"] == "missing-error-handling" and "NOT_FOUND" in i["title"]]
    assert len(hits) == 1
    assert hits[0]["severity"] == "suggestion"


def test_fetch_guarded_by_percent_found_loop_is_not_flagged():
    # This is ProductPriceTotal's own idiom -- the correct, safe
    # alternative to a handler, not a missing one.
    ast = _ast(
        """CREATE PROCEDURE Guarded()
BEGIN
    DECLARE item_name STRING DEFAULT '';
    DECLARE item_price NUMBER DEFAULT 0;
    DECLARE cur CURSOR FOR SELECT name, price FROM products;
    OPEN cur;
    WHILE cur%FOUND DO
        FETCH cur INTO item_name, item_price;
    END WHILE;
    CLOSE cur;
END
"""
    )
    issues = advisor.analyze(ast)
    assert not [i for i in issues if i["category"] == "missing-error-handling" and "NOT_FOUND" in i["title"]]


def test_fetch_backed_by_handler_is_not_flagged():
    ast = _ast(
        """CREATE PROCEDURE Handled()
BEGIN
    DECLARE done NUMBER DEFAULT 0;
    DECLARE item_name STRING DEFAULT '';
    DECLARE item_price NUMBER DEFAULT 0;
    DECLARE CONTINUE HANDLER FOR NOT_FOUND SET done = 1;
    DECLARE cur CURSOR FOR SELECT name, price FROM products;
    OPEN cur;
    WHILE done = 0 DO
        FETCH cur INTO item_name, item_price;
    END WHILE;
    CLOSE cur;
END
"""
    )
    issues = advisor.analyze(ast)
    assert not [i for i in issues if i["category"] == "missing-error-handling" and "NOT_FOUND" in i["title"]]


# -- 5. repeated magic numbers --------------------------------------------------


def test_repeated_literal_is_flagged():
    ast = _ast(
        """CREATE PROCEDURE Repeats()
BEGIN
    DECLARE a NUMBER DEFAULT 0;
    DECLARE b NUMBER DEFAULT 0;
    SET a = 100;
    SET b = 100;
END
"""
    )
    issues = advisor.analyze(ast)
    hits = [i for i in issues if i["category"] == "magic-number"]
    assert len(hits) == 1
    assert "100" in hits[0]["title"]
    assert hits[0]["line"] == 5


def test_single_occurrence_literal_is_not_flagged():
    ast = _ast(
        """CREATE PROCEDURE OneOff()
BEGIN
    DECLARE a NUMBER DEFAULT 0;
    SET a = 100;
END
"""
    )
    assert "magic-number" not in _categories(advisor.analyze(ast))


def test_trivial_zero_and_one_are_never_flagged_even_when_repeated():
    ast = _ast(
        """CREATE PROCEDURE Trivial()
BEGIN
    DECLARE a NUMBER DEFAULT 0;
    DECLARE b NUMBER DEFAULT 1;
    SET a = 0;
    SET b = 1;
END
"""
    )
    assert "magic-number" not in _categories(advisor.analyze(ast))


# -- 6. cursor opened but never closed ------------------------------------------


def test_unclosed_cursor_is_flagged_as_a_warning():
    ast = _ast(
        """CREATE PROCEDURE Leaky()
BEGIN
    DECLARE cur CURSOR FOR SELECT name, price FROM products;
    OPEN cur;
END
"""
    )
    issues = advisor.analyze(ast)
    hits = [i for i in issues if i["category"] == "cursor-not-closed"]
    assert len(hits) == 1
    assert hits[0]["severity"] == "warning"
    assert "cur" in hits[0]["title"]


def test_closed_cursor_is_not_flagged():
    ast = _ast(
        """CREATE PROCEDURE Tidy()
BEGIN
    DECLARE cur CURSOR FOR SELECT name, price FROM products;
    OPEN cur;
    CLOSE cur;
END
"""
    )
    assert "cursor-not-closed" not in _categories(advisor.analyze(ast))


# -- 7. Unreachable code --------------------------------------------------------


def test_code_after_return_is_flagged():
    ast = _ast(
        """CREATE PROCEDURE Foo()
BEGIN
    DECLARE a NUMBER DEFAULT 1;
    RETURN a;
    SET a = 2;
    SET a = 3;
END
"""
    )
    issues = advisor.analyze(ast)
    hits = [i for i in issues if i["category"] == "unreachable-code" and i["title"] == "Unreachable code after RETURN"]
    assert len(hits) == 1
    assert hits[0]["severity"] == "warning"
    # Flags the whole dead run as one issue, anchored at the first dead line.
    assert hits[0]["line"] == 5


def test_return_with_nothing_after_it_is_not_flagged():
    ast = _ast(
        """CREATE FUNCTION Foo() RETURNS NUMBER
BEGIN
    DECLARE a NUMBER DEFAULT 1;
    RETURN a;
END
"""
    )
    assert "unreachable-code" not in _categories(advisor.analyze(ast))


def test_return_inside_if_does_not_flag_code_after_the_if_itself():
    # The RETURN only makes the rest of ITS OWN block (inside the IF)
    # unreachable -- code after the IF statement, back in the outer
    # block, is still perfectly reachable whenever the IF's condition is
    # false, so it must not be flagged.
    ast = _ast(
        """CREATE PROCEDURE Foo()
BEGIN
    DECLARE a NUMBER DEFAULT 1;
    IF a > 100 THEN
        RETURN a;
    END IF;
    SET a = 2;
END
"""
    )
    assert "unreachable-code" not in _categories(advisor.analyze(ast))


def test_constant_false_condition_flags_then_branch():
    ast = _ast(
        """CREATE PROCEDURE Foo()
BEGIN
    DECLARE a NUMBER DEFAULT 1;
    IF 1 > 2 THEN
        SET a = 99;
    END IF;
END
"""
    )
    issues = advisor.analyze(ast)
    hits = [i for i in issues if i["category"] == "unreachable-code" and i["title"] == "THEN branch can never execute"]
    assert len(hits) == 1
    assert hits[0]["severity"] == "warning"
    assert hits[0]["line"] == 5


def test_constant_true_condition_flags_else_branch():
    ast = _ast(
        """CREATE PROCEDURE Foo()
BEGIN
    DECLARE a NUMBER DEFAULT 1;
    IF 5 > 1 THEN
        SET a = 1;
    ELSE
        SET a = 2;
    END IF;
END
"""
    )
    issues = advisor.analyze(ast)
    hits = [i for i in issues if i["category"] == "unreachable-code" and i["title"] == "ELSE branch can never execute"]
    assert len(hits) == 1
    assert hits[0]["line"] == 7


def test_ordinary_data_dependent_condition_is_not_flagged():
    # The overwhelming common case -- a condition that references a
    # variable, not two literal values, must never be treated as a
    # compile-time constant.
    ast = _ast(
        """CREATE PROCEDURE Foo()
BEGIN
    DECLARE a NUMBER DEFAULT 1;
    IF a > 100 THEN
        SET a = 2;
    ELSE
        SET a = 3;
    END IF;
END
"""
    )
    assert "unreachable-code" not in _categories(advisor.analyze(ast))


# -- 8. Unused variables ---------------------------------------------------------


def test_variable_set_but_never_read_is_flagged():
    ast = _ast(
        """CREATE PROCEDURE Foo()
BEGIN
    DECLARE score NUMBER DEFAULT 82;
    DECLARE grade NUMBER DEFAULT 0;
    IF score > 59 THEN
        SET grade = 4;
    ELSE
        SET grade = 2;
    END IF;
END
"""
    )
    issues = advisor.analyze(ast)
    hits = [i for i in issues if i["category"] == "unused-variable"]
    assert len(hits) == 1
    assert hits[0]["severity"] == "suggestion"
    assert "grade" in hits[0]["title"]
    assert hits[0]["line"] == 4


def test_variable_read_in_a_condition_is_not_flagged():
    ast = _ast(
        """CREATE PROCEDURE Foo()
BEGIN
    DECLARE score NUMBER DEFAULT 82;
    DECLARE grade NUMBER DEFAULT 0;
    IF score > 59 THEN
        SET grade = 4;
    END IF;
    SET grade = grade + 1;
END
"""
    )
    assert "unused-variable" not in _categories(advisor.analyze(ast))


def test_variable_declared_and_never_touched_again_is_flagged():
    ast = _ast(
        """CREATE PROCEDURE Foo()
BEGIN
    DECLARE unused NUMBER DEFAULT 0;
    DECLARE a NUMBER DEFAULT 1;
    SET a = a + 1;
END
"""
    )
    issues = advisor.analyze(ast)
    hits = [i for i in issues if i["category"] == "unused-variable"]
    assert len(hits) == 1
    assert "unused" in hits[0]["title"]


def test_out_parameter_never_read_is_not_flagged_as_unused():
    # OUT is write-only by design (see interpreter.py) -- an OUT param
    # that's never read inside the procedure is completely normal, and
    # this check is scoped to DECLAREd locals only anyway (see
    # advisor.py SS8's own docstring), so a param never even reaches
    # this check regardless of mode.
    ast = _ast(
        """CREATE PROCEDURE Foo(OUT result NUMBER)
BEGIN
    DECLARE rate NUMBER DEFAULT 0.08;
    SET result = 100 * rate;
END
"""
    )
    assert "unused-variable" not in _categories(advisor.analyze(ast))


def test_call_argument_counts_as_a_read():
    # A single CREATE PROCEDURE definition parses to a plain
    # ProcedureNode (not a ProgramNode -- see app.parser's module
    # docstring), which DOES have a "body" the advisor walks, even
    # though `Helper` is never actually defined here -- the advisor
    # never executes anything, so a CALL target that wouldn't resolve
    # at runtime is irrelevant to this purely static check.
    ast = _ast(
        """CREATE PROCEDURE Foo()
BEGIN
    DECLARE a NUMBER DEFAULT 1;
    CALL Helper(a);
END
"""
    )
    assert "unused-variable" not in _categories(advisor.analyze(ast))


def test_function_call_expression_argument_counts_as_a_read():
    # FunctionCallExpr (added in a later phase -- "function calls inside
    # procedures") carries its own sub-expressions in `args`, not
    # `left`/`right`/`operand` -- `_iter_exprs` needs its own case for
    # this (see advisor.py) or a variable used ONLY as a function-call
    # argument would be wrongly flagged unused-variable. `Helper` is
    # never actually defined here, same reasoning as the CALL-argument
    # test above: the advisor is purely static and never executes
    # anything, so an unresolved call target is irrelevant to it.
    ast = _ast(
        """CREATE PROCEDURE Foo()
BEGIN
    DECLARE a NUMBER DEFAULT 1;
    DECLARE b NUMBER DEFAULT 0;
    SET b = Helper(a) + 1;
    SET b = b + 1;
END
"""
    )
    assert "unused-variable" not in _categories(advisor.analyze(ast))


def test_function_call_expression_nested_argument_counts_as_a_read():
    # Same fix, one level deeper -- a variable used only inside a
    # function call that is ITSELF an argument to another function call
    # (or nested inside a BinaryExpr inside that argument) must still be
    # found by `_iter_exprs`'s recursion.
    ast = _ast(
        """CREATE PROCEDURE Foo()
BEGIN
    DECLARE a NUMBER DEFAULT 1;
    DECLARE b NUMBER DEFAULT 0;
    SET b = Outer(Inner(a + 1));
    SET b = b + 1;
END
"""
    )
    assert "unused-variable" not in _categories(advisor.analyze(ast))


def test_program_node_with_multiple_definitions_is_not_analyzed_yet():
    # Two chained CREATE definitions wrap into a ProgramNode, whose
    # top-level `body` key doesn't exist (see app.parser's module
    # docstring) -- `analyze()`'s `ast.get("body", [])` degrades to `[]`
    # for it, a pre-existing, documented limitation from the CALL-support
    # phase that every check (old and new) inherits unchanged, not
    # something this phase fixes.
    ast = _ast(
        """CREATE PROCEDURE Helper(IN x NUMBER, OUT y NUMBER)
BEGIN
    SET y = x;
END;

CREATE PROCEDURE Foo()
BEGIN
    DECLARE a NUMBER DEFAULT 1;
    DECLARE unused NUMBER DEFAULT 0;
    CALL Helper(a, unused);
END
"""
    )
    assert ast["type"] == "ProgramNode"
    assert advisor.analyze(ast) == []


# -- 9. Never-read variables (dead stores) ---------------------------------------


def test_overwritten_before_read_is_flagged():
    ast = _ast(
        """CREATE PROCEDURE Foo()
BEGIN
    DECLARE total NUMBER DEFAULT 0;
    SET total = 5;
    SET total = 200;
    SET total = total + 1;
END
"""
    )
    issues = advisor.analyze(ast)
    hits = [i for i in issues if i["category"] == "never-read-variable"]
    assert len(hits) == 1
    assert hits[0]["severity"] == "warning"
    assert hits[0]["line"] == 4  # anchored at the wasted first SET
    assert "total" in hits[0]["title"]
    # never-read-variable is NOT the same case as unused-variable here --
    # total genuinely is read eventually (by its own final self-reference),
    # so it must not also show up as fully "unused".
    assert "unused-variable" not in _categories(issues)


def test_self_referencing_accumulation_is_not_flagged():
    # `SET x = x + 1;` reads x on its own right-hand side before
    # overwriting it -- this is completely ordinary accumulation
    # (every WHILE-loop counter/running-total in this app's own sample
    # library works exactly this way) and must never be flagged.
    ast = _ast(
        """CREATE PROCEDURE Foo()
BEGIN
    DECLARE total NUMBER DEFAULT 0;
    SET total = total + 1;
    SET total = total + 1;
END
"""
    )
    assert "never-read-variable" not in _categories(advisor.analyze(ast))


def test_declare_default_then_set_is_not_flagged():
    # The idiomatic "initialize, then compute" pattern used throughout
    # this app's own sample library (CalculateTotal, CalculateDiscount,
    # ...) -- a DECLARE ... DEFAULT is deliberately NOT treated as a
    # "first write" the way a SET is (see advisor.py's module
    # docstring's "Explicitly NOT implemented" section).
    ast = _ast(
        """CREATE PROCEDURE Foo()
BEGIN
    DECLARE total NUMBER DEFAULT 0;
    DECLARE price NUMBER DEFAULT 25;
    DECLARE quantity NUMBER DEFAULT 4;
    SET total = price * quantity;
END
"""
    )
    assert "never-read-variable" not in _categories(advisor.analyze(ast))


def test_read_between_two_writes_is_not_flagged():
    ast = _ast(
        """CREATE PROCEDURE Foo()
BEGIN
    DECLARE total NUMBER DEFAULT 0;
    DECLARE tax NUMBER DEFAULT 0;
    SET total = 100;
    SET tax = total * 0.08;
    SET total = 200;
END
"""
    )
    assert "never-read-variable" not in _categories(advisor.analyze(ast))


def test_write_write_in_different_if_branches_is_not_flagged():
    # then_body and else_body are separate statement lists (see
    # `_iter_statement_lists`) -- only one of them ever actually runs,
    # so two writes to the same name in DIFFERENT branches are not a
    # same-block clobber.
    ast = _ast(
        """CREATE PROCEDURE Foo()
BEGIN
    DECLARE grade NUMBER DEFAULT 0;
    DECLARE score NUMBER DEFAULT 82;
    IF score > 59 THEN
        SET grade = 4;
    ELSE
        SET grade = 2;
    END IF;
    SET score = grade;
END
"""
    )
    assert "never-read-variable" not in _categories(advisor.analyze(ast))


def test_unrelated_statement_between_writes_does_not_block_detection():
    ast = _ast(
        """CREATE PROCEDURE Foo()
BEGIN
    DECLARE total NUMBER DEFAULT 0;
    DECLARE other NUMBER DEFAULT 0;
    DECLARE result NUMBER DEFAULT 0;
    SET total = 5;
    SET other = 1;
    SET total = 200;
    SET result = other;
END
"""
    )
    issues = advisor.analyze(ast)
    hits = [i for i in issues if i["category"] == "never-read-variable"]
    assert len(hits) == 1
    assert hits[0]["line"] == 6
    assert "total" in hits[0]["title"]


# -- works across all three AST shapes (bare / ProcedureNode / FunctionNode) --


def test_analyze_works_on_bare_procedure_ast():
    ast = _ast("DECLARE a NUMBER DEFAULT 100;\nSET a = 100;\n")
    assert ast["type"] == "Procedure"
    assert "magic-number" in _categories(advisor.analyze(ast))


def test_analyze_works_on_function_ast():
    ast = _ast(
        """CREATE FUNCTION F() RETURNS NUMBER
BEGIN
    DECLARE a NUMBER DEFAULT 0;
    SET a = 100;
    RETURN 100;
END
"""
    )
    assert ast["type"] == "FunctionNode"
    assert "magic-number" in _categories(advisor.analyze(ast))


# -- ordering ------------------------------------------------------------------


def test_issues_are_sorted_by_line_number():
    ast = _ast(
        """CREATE PROCEDURE Multi()
BEGIN
    DECLARE cur CURSOR FOR SELECT * FROM products;
    DECLARE a NUMBER DEFAULT 0;
    OPEN cur;
    SET a = 100;
    SET a = 100;
END
"""
    )
    issues = advisor.analyze(ast)
    lines = [i["line"] for i in issues if i["line"] is not None]
    assert lines == sorted(lines)
