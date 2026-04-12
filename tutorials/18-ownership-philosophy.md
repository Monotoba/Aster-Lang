# 18. Ownership Philosophy (Aster Style)

Goal: learn how Aster introduces ownership without becoming “Rust-hard”.

## The guiding idea

Aster aims to keep the “Python mental model” for everyday code:

- variables are simple bindings
- mutation is explicit (`mut` and `<-`)
- values behave like values

Ownership/borrowing is introduced as a tool for:

- making aliasing/mutation explicit in APIs
- enabling future low-level backends and performance features
- communicating “this might be unsafe” at the boundary (`*raw`)

## It is opt-in (for now)

There is a CLI switch that controls ownership-surface diagnostics:

```bash
uv run aster check file.aster --ownership off
uv run aster check file.aster --ownership warn
uv run aster check file.aster --ownership deny
```

Defaults:

- `off` by default, so you can experiment freely
- `warn` is for learning and for library authors
- `deny` is for projects that want ownership/borrow *violations* to be errors (stricter feedback)

## Aster’s “gentle” approach (planned)

- Start with warnings that teach, not failures that block.
- Avoid lifetime syntax until it is truly needed.
- Prefer “make mutation/aliasing obvious” over “prove everything”.
