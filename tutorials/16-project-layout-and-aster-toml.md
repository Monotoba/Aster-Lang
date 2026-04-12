# 16. Project Layout and `aster.toml`

Goal: understand how imports resolve in larger projects.

## Recap: how `use` resolves

- `use helpers` resolves `helpers.aster` relative to the importing file.
- If an ancestor directory contains `aster.toml`, that directory becomes a project root.
- With a project root, you can add more roots under `[modules].search_roots`.

Example `aster.toml`:

```toml
[package]
name = "app"

[modules]
search_roots = ["src", "vendor"]
```

## CLI overrides

- `aster run/check/build --search-root PATH`
- `aster run/check/build --dep NAME=PATH` (local path dependencies)

## Exercise

1. Create `src/` and move a helper module there. Use `aster.toml` to keep imports clean.

