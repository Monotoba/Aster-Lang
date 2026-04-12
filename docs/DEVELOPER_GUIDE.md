# Developer Guide

## Development principles

- language design must be coherent across syntax, semantics, tooling, and implementation
- parser design should remain friendly to formatter and IDE tooling
- ownership and references must be explicit enough for static analysis
- the formatter should prefer a CST-backed approach
- examples are part of the spec and must be maintained as such

## Package intent

- `ast.py` — AST node definitions
- `lexer.py` — tokenization and indentation handling
- `parser.py` — recursive-descent / Pratt hybrid parser
- `interpreter.py` — direct execution engine
- `compiler.py` — lowering and backend entry points
- `backend.py` — backend adapter interface and registry
- `backend_adapters.py` — default backend adapters wired into CLI build
- `formatter.py` — canonical source formatting
- `cli.py` — command-line entry
- `diagnostics.py` — error and warning structures

## Recommended implementation order

1. spans and diagnostics
2. tokens
3. lexer
4. parser
5. AST validation
6. interpreter core
7. formatter
8. compiler IR

## TDD strategy

Each feature should have:
- syntax tests
- semantic tests if applicable
- interpreter or formatter tests
- example doc updates
