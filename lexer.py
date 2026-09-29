#!/usr/bin/env python3
"""
mini-lexer — a compact lexer for arithmetic expressions.

A hand-rolled character-by-character scanner versus the "naive" single-regex
approach, with an honest benchmark so you don't optimize what's actually
bottlenecked elsewhere.

Usage:
    python3 lexer.py --demo     # show tokens for a sample
    python3 lexer.py --bench    # benchmark: hand-written scanner vs regex
    python3 lexer.py --test     # mini test suite
"""

from __future__ import annotations

import re
import sys
import time
from dataclasses import dataclass
from enum import Enum, auto
from typing import Iterator


class Kind(Enum):
    NUMBER = auto()
    IDENT = auto()
    OP = auto()
    LPAREN = auto()
    RPAREN = auto()
    NEWLINE = auto()
    EOF = auto()


@dataclass(frozen=True, slots=True)
class Token:
    kind: Kind
    value: str
    pos: int

    def __repr__(self) -> str:  # short output for the demo
        return f"{self.kind.name}({self.value!r})"


class LexError(ValueError):
    pass


_OPERATORS = {"+", "-", "*", "/", "%", "=", "<", ">", "!"}
_DIGITS = frozenset("0123456789")
_IDENT_START = frozenset("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ_")
_IDENT_BODY = _IDENT_START | _DIGITS


class Lexer:
    """Hand-written scanner: one pass over the string, no regexes."""

    __slots__ = ("src", "i", "n")

    def __init__(self, src: str) -> None:
        self.src = src
        self.i = 0
        self.n = len(src)

    def tokens(self) -> Iterator[Token]:
        src, n = self.src, self.n
        i = 0
        while i < n:
            ch = src[i]
            if ch in " \t\r":
                i += 1
                continue
            if ch == "\n":
                yield Token(Kind.NEWLINE, "\n", i)
                i += 1
                continue
            if ch in _DIGITS:
                j = i + 1
                while j < n and (src[j] in _DIGITS or (src[j] == "." and j + 1 < n and src[j + 1] in _DIGITS)):
                    j += 1
                yield Token(Kind.NUMBER, src[i:j], i)
                i = j
                continue
            if ch in _IDENT_START:
                j = i + 1
                while j < n and src[j] in _IDENT_BODY:
                    j += 1
                yield Token(Kind.IDENT, src[i:j], i)
                i = j
                continue
            if ch == "(":
                yield Token(Kind.LPAREN, "(", i)
                i += 1
                continue
            if ch == ")":
                yield Token(Kind.RPAREN, ")", i)
                i += 1
                continue
            if ch in _OPERATORS:
                yield Token(Kind.OP, ch, i)
                i += 1
                continue
            raise LexError(f"unexpected character {ch!r} at position {i}")
        yield Token(Kind.EOF, "", n)


# The "naive" competitor — one big regex (how people usually write it quickly).
_REGEX = re.compile(
    r"(?P<WS>[ \t\r]+)"
    r"|(?P<NL>\n)"
    r"|(?P<NUM>\d+(?:\.\d+)?)"
    r"|(?P<IDENT>[A-Za-z_][A-Za-z0-9_]*)"
    r"|(?P<LPAREN>\()"
    r"|(?P<RPAREN>\))"
    r"|(?P<OP>[+\-*/%=<>!])"
)
_GROUP = {"NL": Kind.NEWLINE, "NUM": Kind.NUMBER, "IDENT": Kind.IDENT,
          "LPAREN": Kind.LPAREN, "RPAREN": Kind.RPAREN, "OP": Kind.OP}


def regex_lex(src: str) -> list[Token]:
    out: list[Token] = []
    pos = 0
    for m in _REGEX.finditer(src):
        if m.start() != pos:  # skipped garbage — the plain regex would just jump over it
            raise LexError(f"unexpected character {src[pos]!r} at position {pos}")
        pos = m.end()
        kind = m.lastgroup
        if kind == "WS":
            continue
        out.append(Token(_GROUP[kind], m.group(), m.start()))
    if pos != len(src):
        raise LexError(f"unexpected character {src[pos]!r} at position {pos}")
    out.append(Token(Kind.EOF, "", len(src)))
    return out


def lex_all(src: str) -> list[Token]:
    return list(Lexer(src).tokens())


SAMPLE = (
    "rate = (base * 2.5 + bonus) / 100\n"
    "limit = rate - 42 % 7\n"
    "flag_a = x1 < y2\n"
)


def _bench_round(src: str, fn, rounds: int) -> float:
    t0 = time.perf_counter()
    for _ in range(rounds):
        fn(src)
    return (time.perf_counter() - t0) / rounds * 1e3  # ms per pass


def bench() -> None:
    big = SAMPLE * 500
    rounds = 40
    manual = _bench_round(big, lex_all, rounds)
    rx = _bench_round(big, regex_lex, rounds)
    print(f"input: {len(big):,} chars, {rounds} rounds")
    print(f"hand scanner : {manual:8.3f} ms/pass")
    print(f"regex scanner: {rx:8.3f} ms/pass")
    winner = "hand scanner" if manual < rx else "regex"
    print(f"faster: {winner} (x{(max(manual, rx) / max(min(manual, rx), 1e-9)):.2f})")


def test() -> None:
    cases = {
        "1 + 2*3": ["NUMBER('1')", "OP('+')", "NUMBER('2')", "OP('*')", "NUMBER('3')"],
        "foo_1=(bar)": ["IDENT('foo_1')", "OP('=')", "LPAREN('(')", "IDENT('bar')", "RPAREN(')')"],
        "2.5\n": ["NUMBER('2.5')", "NEWLINE('\\n')"],
    }
    for src, expected in cases.items():
        got = [repr(t).replace("Kind.", "") for t in lex_all(src) if t.kind is not Kind.EOF]
        assert got == expected, f"{src!r}: {got} != {expected}"
        got_r = [repr(t).replace("Kind.", "") for t in regex_lex(src) if t.kind is not Kind.EOF]
        assert got_r == expected, f"regex {src!r}: {got_r}"
    for bad in ["1 $ 2", "a @ b"]:
        for fn in (lex_all, regex_lex):
            try:
                fn(bad)
            except LexError:
                pass
            else:
                raise AssertionError(f"{bad!r} should have failed ({fn.__name__})")
    print("ok: all mini-tests passed")


def main() -> int:
    args = set(sys.argv[1:])
    if "--bench" in args:
        bench()
    elif "--test" in args:
        test()
    else:
        for t in lex_all(SAMPLE):
            print(t)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
