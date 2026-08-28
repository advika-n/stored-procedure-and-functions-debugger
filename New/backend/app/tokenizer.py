"""Lexer for a small procedural SQL subset.

Turns raw procedure/function source text into a flat list of tokens.
Each token is a dict with the shape::

    {
        "type": "KEYWORD" | "IDENTIFIER" | "NUMBER" | "STRING"
                | "OPERATOR" | "PUNCTUATION",
        "value": "<the literal text that was matched>",
        "pos": <0-based character offset where the token starts>,
        "line": <1-based line number>,
        "column": <1-based column number>,
    }

Supported keywords (case-insensitive):
    DECLARE, SET, IF, THEN, ELSE, END, WHILE, DO, BEGIN, IN, OUT, DEFAULT,
    CURSOR, FOR, OPEN, FETCH, INTO, CLOSE, SELECT, FROM, WHERE,
    FOUND, NOTFOUND, CONTINUE, HANDLER, NOT_FOUND, DIVISION_BY_ZERO,
    CREATE, FUNCTION, RETURNS, RETURN, PROCEDURE, INOUT

Supported operators:
    +  -  *  /  >  <  =  !=
    % is also recognized, but only as the cursor-attribute suffix in
    `cur_name%FOUND` / `cur_name%NOTFOUND` (see app.parser) -- it is
    not a general modulo operator.

Supported punctuation:
    (  )  ,  ;

Whitespace is skipped and does not produce a token. Any character that
doesn't match a known token shape raises a TokenizerError pointing at
the offending position.
"""

from __future__ import annotations

import re

KEYWORDS = {
    "DECLARE",
    "SET",
    "IF",
    "THEN",
    "ELSE",
    "END",
    "WHILE",
    "DO",
    "BEGIN",
    "IN",
    "OUT",
    "DEFAULT",
    # -- cursors (see app.parser / app.interpreter) --
    "CURSOR",
    "FOR",
    "OPEN",
    "FETCH",
    "INTO",
    "CLOSE",
    # Embedded-SELECT keywords. The parser doesn't parse the query
    # itself (it's captured as a raw token run and handed to SQLite
    # verbatim at OPEN time) -- these are reserved mainly so they read
    # as keywords rather than plain identifiers.
    "SELECT",
    "FROM",
    "WHERE",
    # cur_name%FOUND / cur_name%NOTFOUND cursor-attribute expressions.
    "FOUND",
    "NOTFOUND",
    # -- exception handlers (see app.parser / app.interpreter) --
    # NOT_FOUND (with underscore -- a handler condition name) is
    # deliberately distinct from NOTFOUND above (no underscore -- a
    # cursor-attribute expression); see app.parser's module docstring.
    "CONTINUE",
    "HANDLER",
    "NOT_FOUND",
    "DIVISION_BY_ZERO",
    # -- CREATE FUNCTION (see app.parser / app.interpreter) --
    "CREATE",
    "FUNCTION",
    "RETURNS",
    "RETURN",
    # -- CREATE PROCEDURE (see app.parser / app.interpreter) --
    # BEGIN, IN, and OUT above were already keywords from earlier
    # phases; PROCEDURE and INOUT were NOT and are added here --
    # despite what an earlier task description assumed, INOUT in
    # particular did not already tokenize as a single keyword (it
    # would otherwise have fallen through as a plain IDENTIFIER).
    "PROCEDURE",
    "INOUT",
}

# Order matters: longer/more-specific patterns must come before shorter
# ones that would otherwise shadow them (e.g. NEQ before OPERATOR, and
# NUMBER's float form before its integer form).
_TOKEN_SPEC = [
    ("WS", r"\s+"),
    ("STRING", r"'(?:[^'\\]|\\.)*'"),
    ("NEQ", r"!="),
    ("NUMBER", r"\d+\.\d+|\d+"),
    ("IDENT", r"[A-Za-z_][A-Za-z0-9_]*"),
    ("OPERATOR", r"[+\-*/><=%]"),
    ("PUNCTUATION", r"[(),;]"),
    ("MISMATCH", r"."),
]

_MASTER_RE = re.compile(
    "|".join(f"(?P<{name}>{pattern})" for name, pattern in _TOKEN_SPEC),
    re.DOTALL,
)


class TokenizerError(ValueError):
    """Raised when the input contains a character no rule can match."""

    def __init__(self, char: str, pos: int, line: int, column: int):
        super().__init__(
            f"Unexpected character {char!r} at line {line}, column {column} "
            f"(pos {pos})"
        )
        self.char = char
        self.pos = pos
        self.line = line
        self.column = column


def tokenize(code: str) -> list[dict]:
    """Convert SQL procedure/function source text into a list of tokens.

    Args:
        code: raw source text.

    Returns:
        A list of token dicts, in source order. Whitespace is dropped;
        every other lexeme becomes exactly one token.

    Raises:
        TokenizerError: if a character doesn't match any known token
            shape (e.g. a stray '#' or '@').
    """
    tokens: list[dict] = []
    line = 1
    line_start = 0  # index into `code` where the current line begins

    for match in _MASTER_RE.finditer(code):
        kind = match.lastgroup
        value = match.group()
        pos = match.start()
        column = pos - line_start + 1

        if kind == "WS":
            # Advance line/column bookkeeping, but emit no token.
            newlines = value.count("\n")
            if newlines:
                line += newlines
                line_start = pos + value.rindex("\n") + 1
            continue

        if kind == "MISMATCH":
            raise TokenizerError(value, pos, line, column)

        if kind == "IDENT":
            upper = value.upper()
            token_type = "KEYWORD" if upper in KEYWORDS else "IDENTIFIER"
        elif kind == "NEQ":
            token_type = "OPERATOR"
        else:
            token_type = kind

        tokens.append(
            {
                "type": token_type,
                "value": value,
                "pos": pos,
                "line": line,
                "column": column,
            }
        )

    return tokens
