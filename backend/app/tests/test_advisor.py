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


# -- CASE statement cross-cutting coverage ---------------------------------------
# CASE (added in a later phase than every check above) needed the shared AST
# walkers (_iter_statements/_statement_exprs/_iter_statement_lists) plus two
# hand-rolled walkers (_check_nested_loops's own `walk`, _find_unguarded_fetch)
# taught about it explicitly -- these tests prove each check actually sees
# inside a CASE branch, not just that CASE itself doesn't crash anything.


def test_variable_read_only_in_a_case_operand_counts_as_a_read():
    ast = _ast(
        """CREATE PROCEDURE Foo()
BEGIN
    DECLARE a NUMBER DEFAULT 1;
    CASE a
        WHEN 1 THEN
            SET a = 2;
    END CASE;
END
"""
    )
    assert "unused-variable" not in _categories(advisor.analyze(ast))


def test_variable_read_only_in_a_searched_case_when_condition_counts_as_a_read():
    ast = _ast(
        """CREATE PROCEDURE Foo()
BEGIN
    DECLARE a NUMBER DEFAULT 1;
    CASE
        WHEN a = 1 THEN
            SET a = 2;
    END CASE;
END
"""
    )
    assert "unused-variable" not in _categories(advisor.analyze(ast))


def test_variable_read_only_inside_a_case_branch_body_counts_as_a_read():
    ast = _ast(
        """CREATE PROCEDURE Foo()
BEGIN
    DECLARE a NUMBER DEFAULT 1;
    DECLARE b NUMBER DEFAULT 0;
    CASE b
        WHEN 0 THEN
            SET a = a + 1;
    END CASE;
END
"""
    )
    assert "unused-variable" not in _categories(advisor.analyze(ast))


def test_dead_store_detected_within_a_single_case_branch_body():
    ast = _ast(
        """CREATE PROCEDURE Foo()
BEGIN
    DECLARE a NUMBER DEFAULT 1;
    DECLARE total NUMBER DEFAULT 0;
    CASE a
        WHEN 1 THEN
            SET total = 5;
            SET total = 200;
    END CASE;
    SET total = total + 1;
END
"""
    )
    issues = advisor.analyze(ast)
    hits = [i for i in issues if i["category"] == "never-read-variable"]
    assert len(hits) == 1
    assert "total" in hits[0]["title"]


def test_writes_in_different_when_bodies_are_not_a_dead_store():
    # Each WHEN's body is its own statement list (only one ever actually
    # runs) -- two writes to the same name in DIFFERENT branches must
    # not be treated as a same-block clobber, same as IF's then/else.
    ast = _ast(
        """CREATE PROCEDURE Foo()
BEGIN
    DECLARE a NUMBER DEFAULT 1;
    DECLARE label NUMBER DEFAULT 0;
    CASE a
        WHEN 1 THEN
            SET label = 10;
        WHEN 2 THEN
            SET label = 20;
    END CASE;
    SET label = label + 1;
END
"""
    )
    assert "never-read-variable" not in _categories(advisor.analyze(ast))


def test_unreachable_code_after_return_inside_a_when_body():
    ast = _ast(
        """CREATE FUNCTION Foo(n NUMBER) RETURNS NUMBER
BEGIN
    CASE
        WHEN n > 1 THEN
            RETURN 1;
            RETURN 2;
        ELSE
            RETURN 0;
    END CASE;
END
"""
    )
    issues = advisor.analyze(ast)
    hits = [i for i in issues if i["category"] == "unreachable-code" and i["title"] == "Unreachable code after RETURN"]
    assert len(hits) == 1


def test_constant_false_when_condition_is_flagged_for_searched_case():
    ast = _ast(
        """CREATE PROCEDURE Foo()
BEGIN
    DECLARE a NUMBER DEFAULT 0;
    CASE
        WHEN 1 > 2 THEN
            SET a = 1;
        WHEN a = 0 THEN
            SET a = 2;
    END CASE;
END
"""
    )
    issues = advisor.analyze(ast)
    hits = [i for i in issues if i["category"] == "unreachable-code" and i["title"] == "WHEN branch can never execute"]
    assert len(hits) == 1
    assert hits[0]["line"] == 6


def test_constant_true_when_condition_flags_everything_after_it():
    ast = _ast(
        """CREATE PROCEDURE Foo()
BEGIN
    DECLARE a NUMBER DEFAULT 0;
    CASE
        WHEN 5 > 1 THEN
            SET a = 1;
        WHEN a = 0 THEN
            SET a = 2;
        ELSE
            SET a = 3;
    END CASE;
END
"""
    )
    issues = advisor.analyze(ast)
    hits = [i for i in issues if i["category"] == "unreachable-code" and i["title"] == "Later WHEN/ELSE can never execute"]
    assert len(hits) == 1
    assert hits[0]["line"] == 8  # the next WHEN's own body, the first dead line


def test_ordinary_when_condition_is_not_flagged():
    ast = _ast(
        """CREATE PROCEDURE Foo()
BEGIN
    DECLARE a NUMBER DEFAULT 0;
    CASE
        WHEN a > 10 THEN
            SET a = 1;
        ELSE
            SET a = 2;
    END CASE;
END
"""
    )
    assert "unreachable-code" not in _categories(advisor.analyze(ast))


def test_simple_case_constant_folding_is_deliberately_not_attempted():
    # See advisor.py's own item 7c docstring for why: folding a simple
    # CASE's operand-vs-WHEN-value equality is out of scope for this
    # phase, even though `CASE 5 WHEN 5 THEN ...` is, logically, an
    # always-matching WHEN just like the searched-CASE case above.
    ast = _ast(
        """CREATE PROCEDURE Foo()
BEGIN
    DECLARE a NUMBER DEFAULT 0;
    CASE 5
        WHEN 5 THEN
            SET a = 1;
        WHEN 6 THEN
            SET a = 2;
    END CASE;
END
"""
    )
    assert "unreachable-code" not in _categories(advisor.analyze(ast))


def test_magic_number_detected_in_case_operand_and_when_values():
    ast = _ast(
        """CREATE PROCEDURE Foo()
BEGIN
    DECLARE a NUMBER DEFAULT 42;
    DECLARE b NUMBER DEFAULT 0;
    CASE a
        WHEN 42 THEN
            SET b = 1;
    END CASE;
END
"""
    )
    issues = advisor.analyze(ast)
    hits = [i for i in issues if i["category"] == "magic-number"]
    assert len(hits) == 1
    assert "42" in hits[0]["title"]


def test_cursor_fetch_inside_a_case_branch_is_seen_by_missing_error_handling():
    ast = _ast(
        """CREATE PROCEDURE Foo()
BEGIN
    DECLARE flag NUMBER DEFAULT 0;
    DECLARE item_name STRING DEFAULT '';
    DECLARE cur CURSOR FOR SELECT name FROM products;
    OPEN cur;
    CASE flag
        WHEN 0 THEN
            FETCH cur INTO item_name;
    END CASE;
    CLOSE cur;
END
"""
    )
    issues = advisor.analyze(ast)
    hits = [i for i in issues if i["category"] == "missing-error-handling"]
    assert len(hits) == 1
    assert "cur" in hits[0]["title"]


def test_while_nested_inside_case_nested_inside_while_is_detected():
    ast = _ast(
        """CREATE PROCEDURE Foo()
BEGIN
    DECLARE i NUMBER DEFAULT 0;
    DECLARE j NUMBER DEFAULT 0;
    DECLARE flag NUMBER DEFAULT 1;
    WHILE i < 3 DO
        CASE flag
            WHEN 1 THEN
                WHILE j < 3 DO
                    SET j = j + 1;
                END WHILE;
        END CASE;
        SET i = i + 1;
    END WHILE;
END
"""
    )
    assert "nested-loops" in _categories(advisor.analyze(ast))


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


# -- LOOP/LEAVE cross-cutting coverage --------------------------------------
# Added in the LOOP/LEAVE support phase -- same discipline the CASE
# statement phase established: check every walker directly rather than
# assume the shared `_iter_statements`/`_iter_statement_lists` fix alone
# is enough (see advisor.py's own `_check_nested_loops`/
# `_find_unguarded_fetch` -- both hand-rolled, neither built on the
# shared walkers).


def test_nested_loop_inside_while_is_flagged():
    ast = _ast(
        """CREATE PROCEDURE Nested()
BEGIN
    DECLARE outer NUMBER DEFAULT 0;
    DECLARE inner NUMBER DEFAULT 0;
    WHILE outer < 3 DO
        LOOP
            SET inner = inner + 1;
            LEAVE;
        END LOOP;
        SET outer = outer + 1;
    END WHILE;
END
"""
    )
    assert "nested-loops" in _categories(advisor.analyze(ast))


def test_nested_while_inside_loop_is_flagged():
    ast = _ast(
        """CREATE PROCEDURE Nested()
BEGIN
    DECLARE outer NUMBER DEFAULT 0;
    DECLARE inner NUMBER DEFAULT 0;
    outer: LOOP
        WHILE inner < 3 DO
            SET inner = inner + 1;
        END WHILE;
        SET outer = outer + 1;
        IF outer > 3 THEN
            LEAVE outer;
        END IF;
    END LOOP outer;
END
"""
    )
    assert "nested-loops" in _categories(advisor.analyze(ast))


def test_nested_loop_inside_loop_is_flagged():
    ast = _ast(
        """CREATE PROCEDURE Nested()
BEGIN
    outer: LOOP
        inner: LOOP
            LEAVE inner;
        END LOOP inner;
        LEAVE outer;
    END LOOP outer;
END
"""
    )
    issues = advisor.analyze(ast)
    assert "nested-loops" in _categories(issues)
    hit = next(i for i in issues if i["category"] == "nested-loops")
    assert hit["line"] == 4  # the INNER loop's line, not the outer's


def test_single_loop_is_not_flagged_as_nested():
    ast = _ast(
        """CREATE PROCEDURE Single()
BEGIN
    LOOP
        LEAVE;
    END LOOP;
END
"""
    )
    assert "nested-loops" not in _categories(advisor.analyze(ast))


def test_fetch_inside_loop_with_no_guard_is_flagged():
    # LOOP has no condition of its own, so unlike a %FOUND-guarded WHILE
    # there is nothing for `_find_unguarded_fetch` to treat as a guard
    # here -- see advisor.py's own module docstring item 4b/2 for why
    # this is a deliberate, documented scope boundary, not a bug.
    ast = _ast(
        """CREATE PROCEDURE Foo()
BEGIN
    DECLARE item_name STRING DEFAULT '';
    DECLARE cur CURSOR FOR SELECT name FROM products;
    OPEN cur;
    LOOP
        FETCH cur INTO item_name;
        LEAVE;
    END LOOP;
    CLOSE cur;
END
"""
    )
    issues = advisor.analyze(ast)
    hits = [i for i in issues if i["category"] == "missing-error-handling"]
    assert len(hits) == 1
    assert "cur" in hits[0]["title"]


def test_fetch_inside_loop_guarded_by_retrospective_notfound_leave_is_still_flagged():
    # Documents the exact scope boundary advisor.py's own docstring
    # calls out: the idiomatic LOOP-based cursor exit (FETCH, then check
    # %NOTFOUND and LEAVE) is retrospective, not predictive, and this
    # check does not recognize it as a guard -- a real, accepted false
    # positive on an otherwise-correct pattern, not a crash or a wrong
    # answer.
    ast = _ast(
        """CREATE PROCEDURE Foo()
BEGIN
    DECLARE item_name STRING DEFAULT '';
    DECLARE cur CURSOR FOR SELECT name FROM products;
    OPEN cur;
    LOOP
        FETCH cur INTO item_name;
        IF cur%NOTFOUND THEN
            LEAVE;
        END IF;
    END LOOP;
    CLOSE cur;
END
"""
    )
    issues = advisor.analyze(ast)
    hits = [i for i in issues if i["category"] == "missing-error-handling"]
    assert len(hits) == 1


def test_fetch_inside_loop_backed_by_not_found_handler_is_not_flagged():
    ast = _ast(
        """CREATE PROCEDURE Foo()
BEGIN
    DECLARE done NUMBER DEFAULT 0;
    DECLARE item_name STRING DEFAULT '';
    DECLARE cur CURSOR FOR SELECT name FROM products;
    DECLARE CONTINUE HANDLER FOR NOT_FOUND SET done = 1;
    OPEN cur;
    LOOP
        FETCH cur INTO item_name;
        IF done = 1 THEN
            LEAVE;
        END IF;
    END LOOP;
    CLOSE cur;
END
"""
    )
    issues = advisor.analyze(ast)
    assert not any(i["category"] == "missing-error-handling" and "cur" in i["title"] for i in issues)


def test_code_after_leave_is_flagged():
    ast = _ast(
        """CREATE PROCEDURE Foo()
BEGIN
    DECLARE i NUMBER DEFAULT 0;
    LOOP
        SET i = i + 1;
        LEAVE;
        SET i = 999;
    END LOOP;
END
"""
    )
    issues = advisor.analyze(ast)
    hit = next(i for i in issues if i["category"] == "unreachable-code")
    assert hit["line"] == 7
    assert "LEAVE" in hit["title"]


def test_leave_with_nothing_after_it_is_not_flagged():
    ast = _ast(
        """CREATE PROCEDURE Foo()
BEGIN
    LOOP
        LEAVE;
    END LOOP;
END
"""
    )
    assert "unreachable-code" not in _categories(advisor.analyze(ast))


def test_leave_inside_if_does_not_flag_code_after_the_if_itself():
    # Mirrors RETURN's own equivalent test (SS7a): the statements after
    # the enclosing IF, in the OUTER block, are a separate statement list
    # from the one the LEAVE actually lives in -- they're still
    # perfectly reachable (the IF's own condition might be false), so
    # they must NOT be flagged, only whatever textually follows the
    # LEAVE within its own THEN body would be.
    ast = _ast(
        """CREATE PROCEDURE Foo()
BEGIN
    DECLARE i NUMBER DEFAULT 0;
    LOOP
        SET i = i + 1;
        IF i > 3 THEN
            LEAVE;
        END IF;
        SET i = i + 1;
    END LOOP;
END
"""
    )
    assert "unreachable-code" not in _categories(advisor.analyze(ast))


def test_variable_read_only_inside_a_loop_body_counts_as_a_read():
    ast = _ast(
        """CREATE PROCEDURE Foo()
BEGIN
    DECLARE limit NUMBER DEFAULT 3;
    DECLARE i NUMBER DEFAULT 0;
    LOOP
        SET i = i + 1;
        IF i > limit THEN
            LEAVE;
        END IF;
    END LOOP;
END
"""
    )
    assert "unused-variable" not in _categories(advisor.analyze(ast))


def test_read_of_a_variable_inside_a_loop_body_prevents_a_false_dead_store_flag():
    ast = _ast(
        """CREATE PROCEDURE Foo()
BEGIN
    DECLARE x NUMBER DEFAULT 1;
    DECLARE y NUMBER DEFAULT 0;
    SET x = 1;
    LOOP
        SET y = x;
        LEAVE;
    END LOOP;
    SET x = 2;
END
"""
    )
    assert "never-read-variable" not in _categories(advisor.analyze(ast))


def test_dead_store_across_a_loop_that_never_touches_the_variable_is_still_flagged():
    ast = _ast(
        """CREATE PROCEDURE Foo()
BEGIN
    DECLARE x NUMBER DEFAULT 1;
    DECLARE z NUMBER DEFAULT 0;
    SET x = 1;
    LOOP
        SET z = 1;
        LEAVE;
    END LOOP;
    SET x = 2;
    SET z = x;
END
"""
    )
    issues = advisor.analyze(ast)
    hit = next(i for i in issues if i["category"] == "never-read-variable")
    assert "'x'" in hit["title"]
    assert hit["line"] == 5  # the first (dead) `SET x = 1;`, not the second


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
