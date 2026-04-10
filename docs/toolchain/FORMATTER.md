# Formatter Design Notes

## Goals

- canonical formatting
- idempotence
- preserve comments
- remain stable under repeated runs
- make structure visually obvious

## Recommendation

Use a CST-backed formatter, not a pure AST formatter.

## Style guidelines

- spaces for indentation only
- predictable blank-line rules
- trailing commas where structure benefits
- minimal ambiguity around lambdas, types, and blocks
