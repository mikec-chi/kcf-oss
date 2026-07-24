from __future__ import annotations

from dataclasses import dataclass
import re


TOKEN = re.compile(
    r"(?P<WS>[ \t\r\n]+)|"
    r"(?P<LINE>//[^\n]*)|"
    r"(?P<BLOCK>/\*.*?\*/)|"
    r"(?P<ARROW>->)|"
    r"(?P<STRING>\"(?:\\.|[^\"\\])*\")|"
    r"(?P<NUMBER>-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?)|"
    r"(?P<IDENT>[A-Za-z_][A-Za-z0-9_-]*(?:\.[A-Za-z_][A-Za-z0-9_-]*)*)|"
    r"(?P<SYMBOL>[{}\[\]:;=,])",
    re.DOTALL,
)


class LexError(ValueError):
    pass


@dataclass(frozen=True)
class Token:
    kind: str
    value: str
    line: int
    column: int
    end_line: int
    end_column: int


def tokenize(text: str) -> list[Token]:
    tokens: list[Token] = []
    offset = 0
    line = 1
    column = 1
    while offset < len(text):
        match = TOKEN.match(text, offset)
        if not match:
            snippet = text[offset : offset + 30].splitlines()[0]
            raise LexError(f"Unexpected input at {line}:{column}: {snippet!r}")
        value = match.group(0)
        start_line, start_column = line, column
        parts = value.split("\n")
        if len(parts) > 1:
            line += len(parts) - 1
            column = len(parts[-1]) + 1
        else:
            column += len(value)
        kind = match.lastgroup or ""
        if kind not in {"WS", "LINE", "BLOCK"}:
            tokens.append(Token(kind, value, start_line, start_column, line, column))
        offset = match.end()
    tokens.append(Token("EOF", "", line, column, line, column))
    return tokens
