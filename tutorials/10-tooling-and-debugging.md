# 10. Tooling and Debugging

Goal: use the CLI to inspect and debug programs.

## Useful commands

```bash
uv run aster run file.aster
uv run aster check file.aster
uv run aster fmt file.aster
uv run aster ast file.aster
uv run aster hir file.aster
uv run aster repl
```

## When to use which

- `check`: parse + semantic analysis (fast feedback).
- `ast`: verify parsing when a syntax change surprises you.
- `hir`: inspect typed lowering when you are debugging type errors.
- `repl`: experiment with small snippets.

## Exercises

1. Run `ast` on a small file and find the node for a lambda.
2. Intentionally cause a type error and see how `check` reports it.

