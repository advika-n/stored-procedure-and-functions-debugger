import pytest

from app.tokenizer import TokenizerError, tokenize


def _pairs(tokens):
    """Reduce tokens to (type, value) pairs for easy comparison in tests."""
    return [(t["type"], t["value"]) for t in tokens]


def test_assignment_statement():
    code = "SET total = price * quantity;"
    tokens = tokenize(code)

    assert _pairs(tokens) == [
        ("KEYWORD", "SET"),
        ("IDENTIFIER", "total"),
        ("OPERATOR", "="),
        ("IDENTIFIER", "price"),
        ("OPERATOR", "*"),
        ("IDENTIFIER", "quantity"),
        ("PUNCTUATION", ";"),
    ]

    # Every token should carry position info alongside type/value.
    for token in tokens:
        assert set(token.keys()) == {"type", "value", "pos", "line", "column"}
        assert token["line"] == 1

    # Spot-check a couple of offsets on the single-line input.
    assert tokens[0]["pos"] == 0  # "SET" starts at the beginning
    assert tokens[1]["pos"] == code.index("total")


def test_if_statement():
    code = (
        "IF price > 100 THEN\n"
        "    SET discount = 10;\n"
        "ELSE\n"
        "    SET discount = 0;\n"
        "END IF;"
    )
    tokens = tokenize(code)

    assert _pairs(tokens) == [
        ("KEYWORD", "IF"),
        ("IDENTIFIER", "price"),
        ("OPERATOR", ">"),
        ("NUMBER", "100"),
        ("KEYWORD", "THEN"),
        ("KEYWORD", "SET"),
        ("IDENTIFIER", "discount"),
        ("OPERATOR", "="),
        ("NUMBER", "10"),
        ("PUNCTUATION", ";"),
        ("KEYWORD", "ELSE"),
        ("KEYWORD", "SET"),
        ("IDENTIFIER", "discount"),
        ("OPERATOR", "="),
        ("NUMBER", "0"),
        ("PUNCTUATION", ";"),
        ("KEYWORD", "END"),
        ("KEYWORD", "IF"),
        ("PUNCTUATION", ";"),
    ]

    # The SET token in the ELSE branch should report the right line number.
    else_set = next(
        t for t in tokens if t["value"] == "SET" and t["line"] == 4
    )
    assert else_set["column"] == 5  # indented by 4 spaces


def test_keywords_are_case_insensitive():
    tokens = tokenize("set X = 1;")
    assert tokens[0]["type"] == "KEYWORD"
    assert tokens[0]["value"] == "set"  # original casing preserved in value


def test_not_equal_operator_is_single_token():
    tokens = tokenize("IF x != 5 THEN END IF;")
    op_tokens = [t for t in tokens if t["type"] == "OPERATOR"]
    assert _pairs(op_tokens) == [("OPERATOR", "!=")]


def test_string_literal():
    tokens = tokenize(r"SET name = 'O\'Brien';")
    # Backslash-escaped quotes stay inside the token; the string closes
    # only at an unescaped closing quote.
    string_tokens = [t for t in tokens if t["type"] == "STRING"]
    assert len(string_tokens) == 1
    assert string_tokens[0]["value"] == r"'O\'Brien'"


def test_declare_with_default_and_types():
    tokens = tokenize("DECLARE total NUMBER DEFAULT 0;")
    assert _pairs(tokens) == [
        ("KEYWORD", "DECLARE"),
        ("IDENTIFIER", "total"),
        ("IDENTIFIER", "NUMBER"),
        ("KEYWORD", "DEFAULT"),
        ("NUMBER", "0"),
        ("PUNCTUATION", ";"),
    ]


def test_unexpected_character_raises():
    with pytest.raises(TokenizerError) as exc_info:
        tokenize("SET x = @1;")

    err = exc_info.value
    assert err.char == "@"
    assert err.pos == "SET x = @1;".index("@")


def test_empty_input_returns_no_tokens():
    assert tokenize("") == []


def test_whitespace_only_input_returns_no_tokens():
    assert tokenize("   \n\t  \n") == []


# -- cursors ------------------------------------------------------------


def test_declare_cursor_statement():
    code = "DECLARE cur CURSOR FOR SELECT col1, col2 FROM tbl WHERE x = 1;"
    tokens = tokenize(code)

    assert _pairs(tokens) == [
        ("KEYWORD", "DECLARE"),
        ("IDENTIFIER", "cur"),
        ("KEYWORD", "CURSOR"),
        ("KEYWORD", "FOR"),
        ("KEYWORD", "SELECT"),
        ("IDENTIFIER", "col1"),
        ("PUNCTUATION", ","),
        ("IDENTIFIER", "col2"),
        ("KEYWORD", "FROM"),
        ("IDENTIFIER", "tbl"),
        ("KEYWORD", "WHERE"),
        ("IDENTIFIER", "x"),
        ("OPERATOR", "="),
        ("NUMBER", "1"),
        ("PUNCTUATION", ";"),
    ]


def test_open_fetch_close_statements():
    tokens = tokenize("OPEN cur; FETCH cur INTO a, b; CLOSE cur;")
    assert _pairs(tokens) == [
        ("KEYWORD", "OPEN"),
        ("IDENTIFIER", "cur"),
        ("PUNCTUATION", ";"),
        ("KEYWORD", "FETCH"),
        ("IDENTIFIER", "cur"),
        ("KEYWORD", "INTO"),
        ("IDENTIFIER", "a"),
        ("PUNCTUATION", ","),
        ("IDENTIFIER", "b"),
        ("PUNCTUATION", ";"),
        ("KEYWORD", "CLOSE"),
        ("IDENTIFIER", "cur"),
        ("PUNCTUATION", ";"),
    ]


def test_percent_found_and_notfound_tokens():
    tokens = tokenize("WHILE cur%FOUND DO END WHILE;")
    assert _pairs(tokens)[:5] == [
        ("KEYWORD", "WHILE"),
        ("IDENTIFIER", "cur"),
        ("OPERATOR", "%"),
        ("KEYWORD", "FOUND"),
        ("KEYWORD", "DO"),
    ]

    tokens = tokenize("IF cur%NOTFOUND THEN END IF;")
    assert _pairs(tokens)[:4] == [
        ("KEYWORD", "IF"),
        ("IDENTIFIER", "cur"),
        ("OPERATOR", "%"),
        ("KEYWORD", "NOTFOUND"),
    ]


# -- exception handlers ---------------------------------------------------


def test_declare_continue_handler_statement():
    code = "DECLARE CONTINUE HANDLER FOR NOT_FOUND SET done = 1;"
    tokens = tokenize(code)
    assert _pairs(tokens) == [
        ("KEYWORD", "DECLARE"),
        ("KEYWORD", "CONTINUE"),
        ("KEYWORD", "HANDLER"),
        ("KEYWORD", "FOR"),
        ("KEYWORD", "NOT_FOUND"),
        ("KEYWORD", "SET"),
        ("IDENTIFIER", "done"),
        ("OPERATOR", "="),
        ("NUMBER", "1"),
        ("PUNCTUATION", ";"),
    ]


def test_division_by_zero_condition_keyword():
    tokens = tokenize("DECLARE CONTINUE HANDLER FOR DIVISION_BY_ZERO SET x = 0;")
    assert ("KEYWORD", "DIVISION_BY_ZERO") in _pairs(tokens)


def test_not_found_and_notfound_are_distinct_keywords():
    # NOT_FOUND (handler condition, underscore) vs NOTFOUND (cursor
    # attribute suffix, no underscore) are deliberately different
    # tokens -- see app.parser's module docstring.
    tokens = tokenize("NOT_FOUND NOTFOUND")
    assert _pairs(tokens) == [("KEYWORD", "NOT_FOUND"), ("KEYWORD", "NOTFOUND")]


# -- CREATE FUNCTION ------------------------------------------------------


def test_create_function_header_tokens():
    tokens = tokenize("CREATE FUNCTION GetTotal(price DECIMAL) RETURNS DECIMAL")
    assert _pairs(tokens) == [
        ("KEYWORD", "CREATE"),
        ("KEYWORD", "FUNCTION"),
        ("IDENTIFIER", "GetTotal"),
        ("PUNCTUATION", "("),
        ("IDENTIFIER", "price"),
        ("IDENTIFIER", "DECIMAL"),
        ("PUNCTUATION", ")"),
        ("KEYWORD", "RETURNS"),
        ("IDENTIFIER", "DECIMAL"),
    ]


def test_return_statement_tokens():
    tokens = tokenize("RETURN total * 0.9;")
    assert _pairs(tokens)[0] == ("KEYWORD", "RETURN")
