# 17. Debugging Type Errors

Goal: move quickly when `aster check` complains.

## Use `check`, `ast`, and `hir`

```bash
uv run aster check file.aster
uv run aster ast file.aster
uv run aster hir file.aster
```

Tips:

- If the parser surprises you, use `aster ast` to confirm the shape.
- If a type mismatch surprises you, use `aster hir` to see the inferred types.
- Add type annotations selectively to “pin” intent:
  - `x: Int := ...`
  - `f: Fn(Int) -> Int := ...`

## Exercise

1. Make a program with an intentional mismatch, then fix it by adding one annotation.

