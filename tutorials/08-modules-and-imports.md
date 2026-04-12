# 08. Modules and Imports

Goal: split code into files and import across them.

## The rules

- A module is a `.aster` file.
- `use helpers` looks for `helpers.aster` relative to the importing file (plus configured search roots).
- Only `pub` declarations are exported from a module.

## Minimal example

Create `helpers.aster`:

```aster
pub fn double(x: Int) -> Int:
    return x + x
```

Create `main.aster`:

```aster
use helpers

fn main():
    print(helpers.double(21))
```

Run:

```bash
uv run aster run main.aster
```

## Import variants

```aster
use math_utils
use math_utils as math
use math_utils: add, sub
```

## Projects and `aster.toml` (optional)

If a directory contains `aster.toml`, Aster treats it as a project root for module resolution and can
add additional search roots.

## Exercises

1. Add a second `pub fn` to `helpers.aster` and call it from `main.aster`.
2. Try `use helpers as h` and call `h.double(21)`.

