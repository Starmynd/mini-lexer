# mini-lexer

A compact lexer for arithmetic expressions: a hand-rolled character-by-character
scanner versus the "naive" single-regex approach — with an honest benchmark.

A small demonstration of a classic engineering lesson: measure before you
optimize. The hand-written scanner wins on pure tokenization speed, but on real
workloads the bottleneck is often elsewhere entirely (I/O, memory, disk).

## What's inside

- `Lexer` — one pass over the input, no regexes; `slots`/`frozen` dataclass tokens
- `regex_lex` — the competitor: same tokens via one big regex
- `--bench` — speed comparison on a large input
- `--test` — mini test suite (including error handling on garbage input)

## Usage

```bash
python3 lexer.py --demo    # tokens for a sample (default)
python3 lexer.py --bench   # ms/pass: hand scanner vs regex
python3 lexer.py --test    # mini test suite
```

Example output:

```
IDENT('rate') OP('=') LPAREN('(') IDENT('base') NUMBER('2.5') ...
```

Token kinds: `NUMBER`, `IDENT`, `OP (+ - * / % = < > !)`, `LPAREN`, `RPAREN`,
`NEWLINE`, `EOF`. Unknown characters raise `LexError` with a position.

## As a library

```python
from lexer import Lexer, Kind

for tok in Lexer("rate = (base * 2.5 + bonus) / 100").tokens():
    print(tok.kind.name, tok.value, tok.pos)
```

No dependencies, standard library only (Python 3.10+).

## License

MIT
