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
    ast = _ast(
        """CREATE PROCEDURE CalculateTotal()
BEGIN
    DECLARE price NUMBER DEFAULT 25;
    DECLARE quantity NUMBER DEFAULT 4;
    DECLARE total NUMBER DEFAULT 0;
    SET total = price * quantity;
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
