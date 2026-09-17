import json

import pytest

from app.parser import ParserError, parse
from app.tokenizer import tokenize

SAMPLE_PROCEDURE = """\
DECLARE total NUMBER DEFAULT 0;
SET total = price * quantity;
IF total > 100 THEN
    SET total = total - 10;
ELSE
    SET total = total + 5;
END IF;
"""


def test_parse_declare_assignment_and_if_else_prints_ast():
    """Parse a small procedure and print its AST as JSON.

    Run with `pytest -s` to see the printed tree and eyeball it
    against SAMPLE_PROCEDURE above.
    """
    tokens = tokenize(SAMPLE_PROCEDURE)
    ast = parse(tokens)

    print("\n--- source ---")
    print(SAMPLE_PROCEDURE)
    print("--- AST ---")
    print(json.dumps(ast, indent=2))

    # Top-level shape: DECLARE, SET, IF -- three statements.
    assert ast["type"] == "Procedure"
    assert [stmt["type"] for stmt in ast["body"]] == [
        "DeclareStatement",
        "SetStatement",
        "IfStatement",
    ]

    declare, set_stmt, if_stmt = ast["body"]

    # DECLARE total NUMBER DEFAULT 0;  (line 1)
    assert declare["name"] == "total"
    assert declare["var_type"] == "NUMBER"
    assert declare["default"] == {"type": "NumberLiteral", "value": 0, "line": 1}
    assert declare["line"] == 1

    # SET total = price * quantity;  (line 2)
    assert set_stmt["target"] == "total"
    assert set_stmt["value"] == {
        "type": "BinaryExpr",
        "operator": "*",
        "left": {"type": "Identifier", "name": "price", "line": 2},
        "right": {"type": "Identifier", "name": "quantity", "line": 2},
        "line": 2,
    }
    assert set_stmt["line"] == 2

    # IF total > 100 THEN ... ELSE ... END IF;  (line 3)
    assert if_stmt["line"] == 3
    assert if_stmt["condition"] == {
        "type": "BinaryExpr",
        "operator": ">",
        "left": {"type": "Identifier", "name": "total", "line": 3},
        "right": {"type": "NumberLiteral", "value": 100, "line": 3},
        "line": 3,
    }
    assert [s["type"] for s in if_stmt["then_body"]] == ["SetStatement"]
    assert if_stmt["then_body"][0]["line"] == 4
    assert [s["type"] for s in if_stmt["else_body"]] == ["SetStatement"]
    assert if_stmt["else_body"][0]["line"] == 6


def test_while_loop():
    code = """\
WHILE count < 10 DO
    SET count = count + 1;
END WHILE;
"""
    ast = parse(tokenize(code))
    while_stmt = ast["body"][0]

    assert while_stmt["type"] == "WhileStatement"
    assert while_stmt["line"] == 1
    assert while_stmt["condition"] == {
        "type": "BinaryExpr",
        "operator": "<",
        "left": {"type": "Identifier", "name": "count", "line": 1},
        "right": {"type": "NumberLiteral", "value": 10, "line": 1},
        "line": 1,
    }
    assert len(while_stmt["body"]) == 1
    assert while_stmt["body"][0]["type"] == "SetStatement"


def test_operator_precedence():
    # `2 + 3 * 4` should parse as `2 + (3 * 4)`, not `(2 + 3) * 4`.
    ast = parse(tokenize("SET x = 2 + 3 * 4;"))
    value = ast["body"][0]["value"]

    assert value["operator"] == "+"
    assert value["left"] == {"type": "NumberLiteral", "value": 2, "line": 1}
    assert value["right"]["operator"] == "*"
    assert value["right"]["left"] == {"type": "NumberLiteral", "value": 3, "line": 1}
    assert value["right"]["right"] == {"type": "NumberLiteral", "value": 4, "line": 1}


def test_parenthesized_expression_overrides_precedence():
    # `(2 + 3) * 4` should keep the addition grouped.
    ast = parse(tokenize("SET x = (2 + 3) * 4;"))
    value = ast["body"][0]["value"]

    assert value["operator"] == "*"
    assert value["left"]["operator"] == "+"


def test_unary_minus():
    ast = parse(tokenize("SET x = -5;"))
    value = ast["body"][0]["value"]
    assert value == {
        "type": "UnaryExpr",
        "operator": "-",
        "operand": {"type": "NumberLiteral", "value": 5, "line": 1},
        "line": 1,
    }


def test_missing_semicolon_raises_parser_error():
    with pytest.raises(ParserError):
        parse(tokenize("SET x = 1"))


def test_if_without_end_raises_parser_error():
    with pytest.raises(ParserError):
        parse(tokenize("IF x > 1 THEN SET x = 2;"))


def test_empty_procedure_parses_to_empty_body():
    assert parse(tokenize("")) == {"type": "Procedure", "body": []}


# -- cursors ------------------------------------------------------------


def test_declare_cursor_captures_query_as_a_raw_string():
    code = "DECLARE prod_cursor CURSOR FOR SELECT name, price FROM products WHERE price > 5;"
    ast = parse(tokenize(code))
    decl = ast["body"][0]

    assert decl == {
        "type": "CursorDeclNode",
        "name": "prod_cursor",
        "query": "SELECT name, price FROM products WHERE price > 5",
        "line": 1,
    }


def test_declare_cursor_without_a_query_raises():
    with pytest.raises(ParserError):
        parse(tokenize("DECLARE cur CURSOR FOR;"))


def test_open_fetch_close_cursor_statements():
    code = """\
OPEN prod_cursor;
FETCH prod_cursor INTO item_name, item_price;
CLOSE prod_cursor;
"""
    ast = parse(tokenize(code))
    open_stmt, fetch_stmt, close_stmt = ast["body"]

    assert open_stmt == {"type": "OpenCursorNode", "name": "prod_cursor", "line": 1}
    assert fetch_stmt == {
        "type": "FetchCursorNode",
        "name": "prod_cursor",
        "targets": ["item_name", "item_price"],
        "line": 2,
    }
    assert close_stmt == {"type": "CloseCursorNode", "name": "prod_cursor", "line": 3}


def test_fetch_into_single_target():
    ast = parse(tokenize("FETCH cur INTO only_target;"))
    assert ast["body"][0]["targets"] == ["only_target"]


def test_cursor_found_and_notfound_expressions():
    ast = parse(tokenize("WHILE prod_cursor%FOUND DO END WHILE;"))
    condition = ast["body"][0]["condition"]
    assert condition == {"type": "CursorFoundExpr", "cursor": "prod_cursor", "line": 1}

    ast = parse(tokenize("IF prod_cursor%NOTFOUND THEN SET x = 1; END IF;"))
    condition = ast["body"][0]["condition"]
    assert condition == {"type": "CursorNotFoundExpr", "cursor": "prod_cursor", "line": 1}


def test_percent_without_found_or_notfound_raises():
    with pytest.raises(ParserError):
        parse(tokenize("SET x = cur % 2;"))


def test_a_regular_declare_still_parses_after_adding_cursor_support():
    # Guards against the CURSOR-lookahead in _parse_declare breaking the
    # ordinary `DECLARE name TYPE DEFAULT expr` path.
    ast = parse(tokenize("DECLARE total NUMBER DEFAULT 0;"))
    assert ast["body"][0]["type"] == "DeclareStatement"


# -- exception handlers ---------------------------------------------------


def test_declare_continue_handler_for_not_found():
    ast = parse(tokenize("DECLARE CONTINUE HANDLER FOR NOT_FOUND SET done = 1;"))
    decl = ast["body"][0]

    assert decl["type"] == "HandlerDeclNode"
    assert decl["condition"] == "NOT_FOUND"
    assert decl["line"] == 1
    assert decl["action"] == {
        "type": "SetStatement",
        "target": "done",
        "value": {"type": "NumberLiteral", "value": 1, "line": 1},
        "line": 1,
    }


def test_declare_continue_handler_for_division_by_zero():
    ast = parse(tokenize("DECLARE CONTINUE HANDLER FOR DIVISION_BY_ZERO SET total = 0;"))
    decl = ast["body"][0]
    assert decl["condition"] == "DIVISION_BY_ZERO"
    assert decl["action"]["type"] == "SetStatement"


def test_handler_action_can_be_any_supported_statement_type():
    # Not just SET -- an IF is a perfectly valid single handler action.
    ast = parse(tokenize("DECLARE CONTINUE HANDLER FOR NOT_FOUND IF x > 0 THEN SET x = 0; END IF;"))
    assert ast["body"][0]["action"]["type"] == "IfStatement"


def test_declare_handler_with_unknown_condition_raises():
    with pytest.raises(ParserError):
        parse(tokenize("DECLARE CONTINUE HANDLER FOR SOMETHING_ELSE SET x = 1;"))


def test_a_regular_declare_still_parses_after_adding_handler_support():
    # Guards against the CONTINUE-lookahead in _parse_declare breaking
    # the ordinary `DECLARE name TYPE DEFAULT expr` path.
    ast = parse(tokenize("DECLARE total NUMBER DEFAULT 0;"))
    assert ast["body"][0]["type"] == "DeclareStatement"


# -- CREATE FUNCTION ------------------------------------------------------

GET_DISCOUNTED_PRICE = """\
CREATE FUNCTION GetDiscountedPrice(price DECIMAL, quantity INT)
RETURNS DECIMAL
BEGIN
    DECLARE total DECIMAL;
    SET total = price * quantity;
    IF total > 1000 THEN
        RETURN total * 0.9;
    ELSE
        RETURN total;
    END IF;
END
"""


def test_create_function_parses_to_a_function_node():
    ast = parse(tokenize(GET_DISCOUNTED_PRICE))

    assert ast["type"] == "FunctionNode"
    assert ast["name"] == "GetDiscountedPrice"
    assert ast["params"] == [{"name": "price", "type": "DECIMAL"}, {"name": "quantity", "type": "INT"}]
    assert ast["returnType"] == "DECIMAL"
    assert ast["line"] == 1


def test_create_function_body_contains_return_nodes_inside_if_branches():
    ast = parse(tokenize(GET_DISCOUNTED_PRICE))
    body = ast["body"]

    assert [s["type"] for s in body] == ["DeclareStatement", "SetStatement", "IfStatement"]
    if_stmt = body[2]
    assert if_stmt["then_body"][0]["type"] == "ReturnNode"
    assert if_stmt["else_body"][0]["type"] == "ReturnNode"


def test_return_node_shape():
    ast = parse(tokenize("RETURN total * 0.9;"))
    node = ast["body"][0]
    assert node == {
        "type": "ReturnNode",
        "value": {
            "type": "BinaryExpr",
            "operator": "*",
            "left": {"type": "Identifier", "name": "total", "line": 1},
            "right": {"type": "NumberLiteral", "value": 0.9, "line": 1},
            "line": 1,
        },
        "line": 1,
    }


def test_function_with_no_params():
    ast = parse(tokenize("CREATE FUNCTION Constant() RETURNS NUMBER BEGIN RETURN 42; END"))
    assert ast["params"] == []


def test_function_without_trailing_semicolon_after_end_is_fine():
    # The sample task's own example has no ';' after the closing END.
    ast = parse(tokenize("CREATE FUNCTION F() RETURNS NUMBER BEGIN RETURN 1; END"))
    assert ast["type"] == "FunctionNode"


def test_function_with_trailing_semicolon_after_end_also_fine():
    ast = parse(tokenize("CREATE FUNCTION F() RETURNS NUMBER BEGIN RETURN 1; END;"))
    assert ast["type"] == "FunctionNode"


def test_ordinary_procedure_body_still_parses_as_procedure_not_function():
    # A leading CREATE routes to the function grammar; anything else
    # still routes to the ordinary bare-statement-list procedure body,
    # completely unchanged.
    ast = parse(tokenize("DECLARE total NUMBER DEFAULT 0;\nSET total = 1;\n"))
    assert ast["type"] == "Procedure"


def test_create_procedure_wrapper_now_parses_to_a_procedure_node():
    # Superseded by full CREATE PROCEDURE support -- see
    # test_create_procedure.py for the dedicated coverage. This just
    # confirms the specific case the old (now-removed) "not supported"
    # assertion covered actually parses correctly today.
    ast = parse(tokenize("CREATE PROCEDURE Foo() BEGIN SET x = 1; END"))
    assert ast["type"] == "ProcedureNode"
    assert ast["name"] == "Foo"


def test_bare_create_table_is_not_a_definition_chain_error_it_is_a_valid_statement():
    # Superseded by CREATE TABLE support (see test_sql_passthrough_
    # statement.py for the dedicated coverage): a solitary leading
    # `CREATE TABLE ...;` used to be the go-to example of "CREATE
    # followed by neither FUNCTION nor PROCEDURE" and raised a
    # ParserError -- it's now a genuinely valid bare-form statement
    # instead (see parser.py's module docstring's "SQL passthrough
    # statements" section, "Top-level dispatch note").
    ast = parse(tokenize("CREATE TABLE Foo (x NUMBER);"))
    assert ast["type"] == "Procedure"
    assert ast["body"][0]["type"] == "SqlStatement"
    assert ast["body"][0]["keyword"] == "CREATE"


def test_create_with_neither_function_nor_procedure_raises_a_clear_error():
    # The "Expected FUNCTION or PROCEDURE after CREATE" error is now only
    # reachable for a CREATE that isn't PROCEDURE/FUNCTION/TABLE-shaped,
    # and only once a definition chain has already genuinely started (a
    # bare leading CREATE TABLE, or any other non-chain-starting CREATE,
    # falls through to the ordinary statement grammar instead -- see
    # `_is_definition_start` above).
    code = "CREATE PROCEDURE A() BEGIN END\nCREATE TABLE t (x NUMBER);"
    with pytest.raises(ParserError, match="Expected FUNCTION or PROCEDURE"):
        parse(tokenize(code))


def test_return_is_parseable_inside_a_while_loop_too():
    # RETURN dispatches through the ordinary _parse_statement, so it's
    # valid anywhere a statement is -- not just inside IF.
    ast = parse(tokenize("WHILE x < 10 DO RETURN x; END WHILE;"))
    while_stmt = ast["body"][0]
    assert while_stmt["body"][0]["type"] == "ReturnNode"


# -- CREATE PROCEDURE ---------------------------------------------------

APPLY_DISCOUNT_PROCEDURE = """\
CREATE PROCEDURE ApplyDiscount(IN price NUMBER, IN quantity NUMBER, OUT total NUMBER)
BEGIN
    SET total = price * quantity;
    IF total > 100 THEN
        SET total = total * 0.9;
    END IF;
END
"""


def test_create_procedure_parses_to_a_procedure_node():
    ast = parse(tokenize(APPLY_DISCOUNT_PROCEDURE))

    assert ast["type"] == "ProcedureNode"
    assert ast["name"] == "ApplyDiscount"
    assert ast["params"] == [
        {"name": "price", "mode": "IN", "type": "NUMBER"},
        {"name": "quantity", "mode": "IN", "type": "NUMBER"},
        {"name": "total", "mode": "OUT", "type": "NUMBER"},
    ]
    assert ast["line"] == 1
    assert "returnType" not in ast  # that's a FunctionNode-only field


def test_create_procedure_body_parses_normally():
    ast = parse(tokenize(APPLY_DISCOUNT_PROCEDURE))
    assert [s["type"] for s in ast["body"]] == ["SetStatement", "IfStatement"]


def test_procedure_param_mode_defaults_to_in_when_omitted():
    ast = parse(tokenize("CREATE PROCEDURE P(x NUMBER) BEGIN SET x = 1; END"))
    assert ast["params"] == [{"name": "x", "mode": "IN", "type": "NUMBER"}]


def test_procedure_param_supports_inout_mode():
    ast = parse(tokenize("CREATE PROCEDURE P(INOUT x NUMBER) BEGIN SET x = 1; END"))
    assert ast["params"] == [{"name": "x", "mode": "INOUT", "type": "NUMBER"}]


def test_procedure_with_no_params():
    ast = parse(tokenize("CREATE PROCEDURE P() BEGIN SET x = 1; END"))
    assert ast["params"] == []


def test_procedure_without_trailing_semicolon_after_end_is_fine():
    ast = parse(tokenize("CREATE PROCEDURE P() BEGIN SET x = 1; END"))
    assert ast["type"] == "ProcedureNode"


def test_procedure_with_trailing_semicolon_after_end_also_fine():
    ast = parse(tokenize("CREATE PROCEDURE P() BEGIN SET x = 1; END;"))
    assert ast["type"] == "ProcedureNode"


def test_bare_statement_list_procedure_is_completely_unaffected():
    """The critical regression check: an existing sample's exact code,
    parsed with no CREATE wrapper at all, must produce the exact same
    AST shape it always has -- plain "Procedure", no name/params/line-
    of-a-wrapper, nothing new leaking in."""
    code = """\
DECLARE price NUMBER DEFAULT 20;
DECLARE quantity NUMBER DEFAULT 6;
DECLARE total NUMBER DEFAULT 0;
DECLARE discount NUMBER DEFAULT 0;
SET total = price * quantity;
IF total > 100 THEN
    SET discount = total * 0.1;
ELSE
    SET discount = total * 0.05;
END IF;
SET total = total - discount;
"""
    ast = parse(tokenize(code))
    assert ast["type"] == "Procedure"
    assert set(ast.keys()) == {"type", "body"}  # no name/params/line leaking in
    assert [s["type"] for s in ast["body"]] == [
        "DeclareStatement",
        "DeclareStatement",
        "DeclareStatement",
        "DeclareStatement",
        "SetStatement",
        "IfStatement",
        "SetStatement",
    ]
