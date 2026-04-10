# Railroad Diagram Guide

The `grammar/` directory contains Bottlecaps-compatible W3C-style EBNF.

## Files

- `grammar/aster-core.ebnf`
- `grammar/aster-full.ebnf`

## Notes

Aster is indentation-sensitive, so the grammar models:
- `NEWLINE`
- `INDENT`
- `DEDENT`
- `EOF`

as lexer-generated tokens.

## Suggested diagram entry points

- `AsterModule`
- `FunctionDecl`
- `TypeExpr`
- `Expression`
- `Pattern`
- `TraitDecl`
- `ImplDecl`

## Usage

Paste the EBNF file contents into the Bottlecaps Railroad Diagram Generator.
