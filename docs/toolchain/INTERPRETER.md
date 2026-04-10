# Interpreter Design Notes

## Scope

The interpreter should execute a parsed, semantically checked AST for fast feedback, scripting, tests, and a REPL.

## Early milestones

1. literals and arithmetic
2. bindings and mutation
3. blocks and scope
4. functions and closures
5. lists, tuples, records
6. control flow
7. pattern matching
8. modules

## Runtime model

- values
- environments
- frames
- closures
- diagnostics
- effect boundaries

## Non-goals for first milestone

- concurrency
- ownership enforcement
- aggressive optimization
