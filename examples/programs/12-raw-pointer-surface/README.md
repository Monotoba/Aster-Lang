# 12. Raw Pointer Surface (No Runtime Pointers Yet)

This is a “design surface” example: raw pointers are explicit in type annotations so unsafe boundaries
stay visible in APIs.

Try:

```bash
uv run aster check examples/programs/12-raw-pointer-surface/main.aster --ownership warn
uv run aster check examples/programs/12-raw-pointer-surface/main.aster --ownership deny
```

Run:

```bash
uv run aster run examples/programs/12-raw-pointer-surface/main.aster
```

