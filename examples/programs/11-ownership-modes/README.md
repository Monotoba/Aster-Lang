# 11. Ownership and Borrowing: Philosophy Demo (Surface Only)

This program is about *API intent*, not runtime behavior. Ownership/borrowing is currently a surface
that can be:

- ignored (`--ownership off`, default)
- warned about (`--ownership warn`)
- treated as errors when rules are violated (`--ownership deny`)

Try:

```bash
uv run aster check examples/programs/11-ownership-modes/main.aster --ownership warn
uv run aster check examples/programs/11-ownership-modes/main.aster --ownership deny
```

And it should still run:

```bash
uv run aster run examples/programs/11-ownership-modes/main.aster
```
